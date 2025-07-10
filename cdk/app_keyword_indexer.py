#!/usr/bin/env python3
"""
Keyword Indexer CDK App
Creates OpenSearch keyword indexing Lambda with SNS/SQS integration
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

class KeywordIndexerStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Reference existing VPC
        vpc = ec2.Vpc.from_lookup(
            self, "ExistingVpc",
            vpc_id="vpc-051c21d88c7dc3819"
        )
        
        # Reference existing SNS topic (text-extraction-complete)
        text_ready_topic = sns.Topic.from_topic_arn(
            self, "TextReadyTopic",
            topic_arn="arn:aws:sns:us-east-1:861276078413:text-extraction-complete"
        )
        
        # Create messaging infrastructure
        self._create_messaging_infrastructure(text_ready_topic)
        
        # Create lambda layers
        self._create_lambda_layers()
        
        # Create keyword indexer lambda
        self._create_keyword_indexer_lambda(vpc)
        
        # Create outputs
        self._create_outputs()

        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Component", "KeywordIndexer")
        Tags.of(self).add("Phase", "Production")

    def _create_messaging_infrastructure(self, text_ready_topic):
        """Create SQS queue for keyword indexing"""
        
        # Dead Letter Queue for failed messages
        self.keyword_indexer_dlq = sqs.Queue(
            self, "KeywordIndexerDLQ",
            queue_name="keyword-indexer-dlq",
            retention_period=Duration.days(14),
            visibility_timeout=Duration.minutes(15)
        )
        
        # Main SQS Queue for keyword indexer
        self.keyword_indexer_queue = sqs.Queue(
            self, "KeywordIndexerQueue",
            queue_name="keyword-indexer-queue",
            visibility_timeout=Duration.minutes(15),  # Match lambda timeout
            receive_message_wait_time=Duration.seconds(20),  # Long polling
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=self.keyword_indexer_dlq
            )
        )
        
        # Subscribe queue to existing text-ready topic
        text_ready_topic.add_subscription(
            sns_subscriptions.SqsSubscription(
                self.keyword_indexer_queue,
                raw_message_delivery=False  # Keep SNS envelope for compatibility
            )
        )

    def _create_lambda_layers(self):
        """Create lambda layers for shared dependencies"""
        
        # Climate Risk Core Layer (reuse existing)
        self.climate_risk_core_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "ClimateRiskCoreLayer",
            layer_version_arn="arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities-pipeline:2"
        )
        
        # Database Layer (reuse existing)
        self.database_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "DatabaseLayer", 
            layer_version_arn="arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies-pipeline:2"
        )
        
        # OpenSearch Layer (new)
        self.opensearch_layer = lambda_.LayerVersion(
            self, "OpenSearchLayer",
            layer_version_name="opensearch-dependencies",
            code=lambda_.Code.from_asset("../layers/build/opensearch-layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="OpenSearch client dependencies",
        )

    def _create_keyword_indexer_lambda(self, vpc):
        """Create keyword indexer lambda with OpenSearch integration"""
        
        # Environment variables
        keyword_indexer_env = {
            'OPENSEARCH_ENDPOINT': 'https://i7dzyfap1fe42z9delui.us-east-1.aoss.amazonaws.com',
            'INDEX_NAME': 'climate-risk-keyword-index',
            'TEXT_BUCKET': f'solve-global-kr-text-new-{self.account}-{self.region}',
            'DATABASE_URL': 'postgresql://postgres:-VroWHWQBS5!V)yAcsDC3(3)NHJ5@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require',
            'PHASE': 'PRODUCTION_KEYWORD_INDEXING',
        }
        
        # Create IAM role with OpenSearch and S3 permissions
        self.keyword_indexer_role = iam.Role(
            self, "KeywordIndexerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole")
            ],
            inline_policies={
                "KeywordIndexerPolicy": iam.PolicyDocument(
                    statements=[
                        # S3 permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:ListBucket"
                            ],
                            resources=[
                                f"arn:aws:s3:::solve-global-kr-text-new-{self.account}-{self.region}",
                                f"arn:aws:s3:::solve-global-kr-text-new-{self.account}-{self.region}/*"
                            ]
                        ),
                        # OpenSearch Serverless permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "aoss:APIAccessAll"
                            ],
                            resources=[
                                "arn:aws:aoss:us-east-1:861276078413:collection/i7dzyfap1fe42z9delui"
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
                                self.keyword_indexer_queue.queue_arn
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
            self, "KeywordIndexerSecurityGroup",
            vpc=vpc,
            description="Security group for Keyword Indexer Lambda",
            allow_all_outbound=True
        )
        
        # Allow lambda to connect to database
        db_security_group.add_ingress_rule(
            peer=lambda_security_group,
            connection=ec2.Port.tcp(5432),
            description="Allow Keyword Indexer Lambda to connect to PostgreSQL"
        )
        
        # Keyword Indexer Lambda Function
        self.keyword_indexer_function = lambda_.Function(
            self, "KeywordIndexerFunction",
            function_name="keyword-indexer",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="keyword_indexer_processor.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/keyword_indexer"),
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment=keyword_indexer_env,
            role=self.keyword_indexer_role,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[lambda_security_group],
            layers=[
                self.climate_risk_core_layer,
                self.database_layer,
                self.opensearch_layer
            ],
            description="Keyword indexer with OpenSearch integration",
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # Add SQS event source to lambda
        self.keyword_indexer_function.add_event_source(
            lambda_event_sources.SqsEventSource(
                self.keyword_indexer_queue,
                batch_size=1,  # Process one document at a time
                max_batching_window=Duration.seconds(5),
                report_batch_item_failures=True
            )
        )

    def _create_outputs(self):
        """Create CloudFormation outputs"""
        
        CfnOutput(
            self, "KeywordIndexerFunctionName",
            value=self.keyword_indexer_function.function_name,
            description="Keyword Indexer Lambda function name"
        )
        
        CfnOutput(
            self, "KeywordIndexerFunctionArn", 
            value=self.keyword_indexer_function.function_arn,
            description="Keyword Indexer Lambda function ARN"
        )
        
        CfnOutput(
            self, "KeywordIndexerQueueUrl",
            value=self.keyword_indexer_queue.queue_url,
            description="Keyword Indexer SQS Queue URL"
        )
        
        CfnOutput(
            self, "KeywordIndexerQueueArn",
            value=self.keyword_indexer_queue.queue_arn,
            description="Keyword Indexer SQS Queue ARN"
        )
        
        CfnOutput(
            self, "OpenSearchEndpoint",
            value="https://i7dzyfap1fe42z9delui.us-east-1.aoss.amazonaws.com",
            description="OpenSearch Serverless Collection Endpoint"
        )

# Import SNS subscriptions
from aws_cdk import aws_sns_subscriptions as sns_subscriptions

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account="861276078413",
    region="us-east-1"
)

# Keyword Indexer Stack
keyword_indexer_stack = KeywordIndexerStack(
    app,
    "keyword-indexer",
    env=env,
    description="Keyword Indexer with OpenSearch integration"
)

app.synth()
