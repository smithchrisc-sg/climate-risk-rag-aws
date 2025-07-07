#!/usr/bin/env python3
"""
Text Chunker Pipeline Integration CDK App
Complete messaging pipeline with SNS/SQS integration
"""

import aws_cdk as cdk
from aws_cdk import (
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_sns as sns,
    aws_sqs as sqs,
    aws_lambda_event_sources as lambda_event_sources,
    aws_logs as logs,
    Duration,
    CfnOutput,
    Tags
)
from constructs import Construct

class TextChunkerPipelineStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Reference existing VPC
        vpc = ec2.Vpc.from_lookup(
            self, "ExistingVpc",
            vpc_id="vpc-051c21d88c7dc3819"
        )
        
        # Create messaging infrastructure
        self._create_messaging_infrastructure()
        
        # Create lambda layers
        self._create_lambda_layers()
        
        # Create text chunker lambda with pipeline integration
        self._create_text_chunker_lambda(vpc)
        
        # Create outputs
        self._create_outputs()

        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Component", "TextChunkerPipeline")
        Tags.of(self).add("Phase", "Production")

    def _create_messaging_infrastructure(self):
        """Create SNS/SQS messaging infrastructure"""
        
        # Dead Letter Queue for failed messages
        self.text_chunker_dlq = sqs.Queue(
            self, "TextChunkerDLQ",
            queue_name="text-chunker-dlq",
            retention_period=Duration.days(14),
            visibility_timeout=Duration.minutes(15)
        )
        
        # Main SQS Queue for text chunker
        self.text_chunker_queue = sqs.Queue(
            self, "TextChunkerQueue",
            queue_name="text-chunker-queue",
            visibility_timeout=Duration.minutes(15),  # Match lambda timeout
            receive_message_wait_time=Duration.seconds(20),  # Long polling
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=self.text_chunker_dlq
            )
        )
        
        # SNS Topic for text chunker output (chunks ready)
        self.chunks_ready_topic = sns.Topic(
            self, "ChunksReadyTopic",
            topic_name="chunks-ready",
            display_name="Text Chunks Ready for Processing"
        )
        
        # SNS Topic for text extraction completion (input to text chunker)
        # This would normally be created by TextExtractor, but we'll create it for integration
        self.text_ready_topic = sns.Topic(
            self, "TextReadyTopic", 
            topic_name="text-extraction-complete",
            display_name="Text Extraction Complete"
        )
        
        # Subscribe SQS queue to text ready topic
        self.text_ready_topic.add_subscription(
            sns_subscriptions.SqsSubscription(
                self.text_chunker_queue,
                raw_message_delivery=False  # Keep SNS envelope for compatibility
            )
        )

    def _create_lambda_layers(self):
        """Create lambda layers for shared dependencies"""
        
        # Climate Risk Core Layer
        self.climate_risk_core_layer = lambda_.LayerVersion(
            self, "ClimateRiskCoreLayer",
            layer_version_name="climate-risk-core-utilities-pipeline",
            code=lambda_.Code.from_asset("../layers/build/climate-risk-core-layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Core application utilities for pipeline",
        )
        
        # Database Layer
        self.database_layer = lambda_.LayerVersion(
            self, "DatabaseLayer",
            layer_version_name="database-dependencies-pipeline",
            code=lambda_.Code.from_asset("../layers/build/database-layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Database dependencies for pipeline",
        )

    def _create_text_chunker_lambda(self, vpc):
        """Create text chunker lambda with pipeline integration"""
        
        # Environment variables for pipeline integration
        text_chunker_env = {
            'CHUNKS_BUCKET': f'solve-global-kr-chunks-{self.account}-{self.region}',
            'TEXT_BUCKET': f'solve-global-kr-text-new-{self.account}-{self.region}',
            'DATABASE_URL': 'postgresql://postgres:-VroWHWQBS5!V)yAcsDC3(3)NHJ5@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require',
            'CHUNKS_READY_TOPIC_ARN': self.chunks_ready_topic.topic_arn,
            'PHASE': 'PRODUCTION_PIPELINE',
        }
        
        # Create IAM role with pipeline permissions
        self.text_chunker_role = iam.Role(
            self, "TextChunkerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole")
            ],
            inline_policies={
                "TextChunkerPipelinePolicy": iam.PolicyDocument(
                    statements=[
                        # S3 permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:DeleteObject",
                                "s3:ListBucket"
                            ],
                            resources=[
                                f"arn:aws:s3:::solve-global-kr-text-new-{self.account}-{self.region}",
                                f"arn:aws:s3:::solve-global-kr-text-new-{self.account}-{self.region}/*",
                                f"arn:aws:s3:::solve-global-kr-chunks-{self.account}-{self.region}",
                                f"arn:aws:s3:::solve-global-kr-chunks-{self.account}-{self.region}/*"
                            ]
                        ),
                        # SNS permissions for publishing chunks ready messages
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "sns:Publish"
                            ],
                            resources=[
                                self.chunks_ready_topic.topic_arn
                            ]
                        ),
                        # SQS permissions for receiving messages
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "sqs:ReceiveMessage",
                                "sqs:DeleteMessage",
                                "sqs:GetQueueAttributes"
                            ],
                            resources=[
                                self.text_chunker_queue.queue_arn
                            ]
                        ),
                        # CloudWatch Logs permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents"
                            ],
                            resources=["*"]
                        ),
                        # Secrets Manager for database credentials
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "secretsmanager:GetSecretValue"
                            ],
                            resources=[
                                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:rds!db-*"
                            ]
                        )
                    ]
                )
            }
        )
        
        # Get database security group
        db_security_group = ec2.SecurityGroup.from_security_group_id(
            self, "DatabaseSecurityGroup",
            security_group_id="sg-09bc56a537bf7ac12"
        )
        
        # Create security group for lambda
        lambda_security_group = ec2.SecurityGroup(
            self, "TextChunkerSecurityGroup",
            vpc=vpc,
            description="Security group for Text Chunker Lambda Pipeline",
            allow_all_outbound=True
        )
        
        # Allow lambda to connect to database
        db_security_group.add_ingress_rule(
            peer=lambda_security_group,
            connection=ec2.Port.tcp(5432),
            description="Allow Text Chunker Pipeline Lambda to connect to PostgreSQL"
        )
        
        # Text Chunker Lambda Function with pipeline integration
        self.text_chunker_function = lambda_.Function(
            self, "TextChunkerFunction",
            function_name="text-chunker-pipeline",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="text_chunker_processor.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/text_chunker"),
            timeout=Duration.minutes(15),  # Longer timeout for larger documents
            memory_size=1024,
            environment=text_chunker_env,
            role=self.text_chunker_role,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[lambda_security_group],
            layers=[
                self.climate_risk_core_layer,
                self.database_layer
            ],
            description="Text chunker with complete pipeline integration",
            log_retention=logs.RetentionDays.ONE_WEEK
            # Removed reserved_concurrent_executions for account limits
        )
        
        # Add SQS event source to lambda
        self.text_chunker_function.add_event_source(
            lambda_event_sources.SqsEventSource(
                self.text_chunker_queue,
                batch_size=1,  # Process one document at a time
                max_batching_window=Duration.seconds(5),
                report_batch_item_failures=True
            )
        )

    def _create_outputs(self):
        """Create CloudFormation outputs"""
        
        CfnOutput(
            self, "TextChunkerFunctionName",
            value=self.text_chunker_function.function_name,
            description="Text Chunker Pipeline Lambda function name"
        )
        
        CfnOutput(
            self, "TextChunkerFunctionArn", 
            value=self.text_chunker_function.function_arn,
            description="Text Chunker Pipeline Lambda function ARN"
        )
        
        CfnOutput(
            self, "TextChunkerQueueUrl",
            value=self.text_chunker_queue.queue_url,
            description="Text Chunker SQS Queue URL"
        )
        
        CfnOutput(
            self, "TextChunkerQueueArn",
            value=self.text_chunker_queue.queue_arn,
            description="Text Chunker SQS Queue ARN"
        )
        
        CfnOutput(
            self, "ChunksReadyTopicArn",
            value=self.chunks_ready_topic.topic_arn,
            description="Chunks Ready SNS Topic ARN"
        )
        
        CfnOutput(
            self, "TextReadyTopicArn",
            value=self.text_ready_topic.topic_arn,
            description="Text Ready SNS Topic ARN (for TextExtractor integration)"
        )
        
        CfnOutput(
            self, "ClimateRiskCoreLayerArn",
            value=self.climate_risk_core_layer.layer_version_arn,
            description="Climate Risk Core Layer ARN (pipeline version)"
        )
        
        CfnOutput(
            self, "DatabaseLayerArn",
            value=self.database_layer.layer_version_arn,
            description="Database Layer ARN (pipeline version)"
        )

# Import SNS subscriptions
from aws_cdk import aws_sns_subscriptions as sns_subscriptions

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account="861276078413",
    region="us-east-1"
)

# Text Chunker Pipeline Stack
text_chunker_pipeline_stack = TextChunkerPipelineStack(
    app,
    "text-chunker-pipeline",
    env=env,
    description="Text Chunker with Complete Pipeline Integration"
)

app.synth()
