#!/usr/bin/env python3
"""
Async Keyword Indexer CDK App
Simple callback approach - cost-efficient async processing
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

class AsyncKeywordIndexerStack(cdk.Stack):
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
        
        # Create async keyword indexer functions
        self._create_async_keyword_indexer_functions(vpc)
        
        # Create outputs
        self._create_outputs()

        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Component", "AsyncKeywordIndexer")
        Tags.of(self).add("Phase", "Production")

    def _create_messaging_infrastructure(self, text_ready_topic):
        """Create messaging infrastructure for async processing"""
        
        # Completion topic for callbacks
        self.completion_topic = sns.Topic(
            self, "KeywordIndexingCompletionTopic",
            topic_name="keyword-indexing-complete",
            display_name="Keyword Indexing Completion Notifications"
        )
        
        # Dead Letter Queue for initiator
        self.initiator_dlq = sqs.Queue(
            self, "KeywordIndexerInitiatorDLQ",
            queue_name="keyword-indexer-initiator-dlq",
            retention_period=Duration.days(14),
            visibility_timeout=Duration.minutes(5)
        )
        
        # Main SQS Queue for initiator
        self.initiator_queue = sqs.Queue(
            self, "KeywordIndexerInitiatorQueue",
            queue_name="keyword-indexer-initiator-queue",
            visibility_timeout=Duration.minutes(5),  # Short timeout for quick processing
            receive_message_wait_time=Duration.seconds(20),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=self.initiator_dlq
            )
        )
        
        # Dead Letter Queue for worker
        self.worker_dlq = sqs.Queue(
            self, "KeywordIndexerWorkerDLQ",
            queue_name="keyword-indexer-worker-dlq",
            retention_period=Duration.days(14),
            visibility_timeout=Duration.minutes(15)
        )
        
        # Subscribe initiator queue to text-ready topic
        text_ready_topic.add_subscription(
            sns_subscriptions.SqsSubscription(
                self.initiator_queue,
                raw_message_delivery=False
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
        
        # OpenSearch Layer (reuse existing)
        self.opensearch_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "OpenSearchLayer",
            layer_version_arn="arn:aws:lambda:us-east-1:861276078413:layer:opensearch-dependencies:1"
        )

    def _create_async_keyword_indexer_functions(self, vpc):
        """Create async keyword indexer functions"""
        
        # Common environment variables
        common_env = {
            'TEXT_BUCKET': f'solve-global-kr-text-new-{self.account}-{self.region}',
            'DATABASE_URL': 'postgresql://postgres:-VroWHWQBS5!V)yAcsDC3(3)NHJ5@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require',
            'COMPLETION_TOPIC_ARN': self.completion_topic.topic_arn,
            'PHASE': 'ASYNC_KEYWORD_INDEXING',
        }
        
        # Get database security group
        db_security_group = ec2.SecurityGroup.from_security_group_id(
            self, "DatabaseSecurityGroup",
            security_group_id="sg-09bc56a537bf7ac12"
        )
        
        # Create security group for lambdas
        lambda_security_group = ec2.SecurityGroup(
            self, "AsyncKeywordIndexerSecurityGroup",
            vpc=vpc,
            description="Security group for Async Keyword Indexer Lambdas",
            allow_all_outbound=True
        )
        
        # Allow lambdas to connect to database
        db_security_group.add_ingress_rule(
            peer=lambda_security_group,
            connection=ec2.Port.tcp(5432),
            description="Allow Async Keyword Indexer Lambdas to connect to PostgreSQL"
        )
        
        # 1. Initiator Function (quick processing)
        initiator_env = {
            **common_env,
            'WORKER_FUNCTION_NAME': 'async-keyword-indexer-worker'
        }
        
        self.initiator_role = iam.Role(
            self, "AsyncKeywordIndexerInitiatorRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole")
            ],
            inline_policies={
                "InitiatorPolicy": iam.PolicyDocument(
                    statements=[
                        # S3 read permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["s3:GetObject"],
                            resources=[f"arn:aws:s3:::solve-global-kr-text-new-{self.account}-{self.region}/*"]
                        ),
                        # Lambda invoke permissions for worker
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["lambda:InvokeFunction"],
                            resources=[f"arn:aws:lambda:{self.region}:{self.account}:function:async-keyword-indexer-worker"]
                        ),
                        # SNS publish permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["sns:Publish"],
                            resources=[self.completion_topic.topic_arn]
                        ),
                        # SQS permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"],
                            resources=[self.initiator_queue.queue_arn]
                        )
                    ]
                )
            }
        )
        
        self.initiator_function = lambda_.Function(
            self, "AsyncKeywordIndexerInitiator",
            function_name="async-keyword-indexer-initiator",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="simple_async_processor.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/keyword_indexer"),
            timeout=Duration.minutes(2),  # Short timeout for quick processing
            memory_size=512,  # Lower memory for cost efficiency
            environment=initiator_env,
            role=self.initiator_role,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[lambda_security_group],
            layers=[
                self.climate_risk_core_layer,
                self.database_layer
            ],
            description="Async keyword indexer initiator - quick processing",
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # Add SQS event source to initiator
        self.initiator_function.add_event_source(
            lambda_event_sources.SqsEventSource(
                self.initiator_queue,
                batch_size=1,
                max_batching_window=Duration.seconds(5),
                report_batch_item_failures=True
            )
        )
        
        # 2. Worker Function (background processing)
        worker_env = {
            **common_env,
            'OPENSEARCH_ENDPOINT': 'https://oxxw312s6cktjq4t31k7.us-east-1.aoss.amazonaws.com',
            'INDEX_NAME': 'climate-risk-keyword-index'
        }
        
        self.worker_role = iam.Role(
            self, "AsyncKeywordIndexerWorkerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole")
            ],
            inline_policies={
                "WorkerPolicy": iam.PolicyDocument(
                    statements=[
                        # S3 read permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["s3:GetObject", "s3:ListBucket"],
                            resources=[
                                f"arn:aws:s3:::solve-global-kr-text-new-{self.account}-{self.region}",
                                f"arn:aws:s3:::solve-global-kr-text-new-{self.account}-{self.region}/*"
                            ]
                        ),
                        # OpenSearch Serverless permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["aoss:APIAccessAll"],
                            resources=["arn:aws:aoss:us-east-1:861276078413:collection/oxxw312s6cktjq4t31k7"]
                        ),
                        # SNS publish permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["sns:Publish"],
                            resources=[self.completion_topic.topic_arn]
                        )
                    ]
                )
            }
        )
        
        self.worker_function = lambda_.Function(
            self, "AsyncKeywordIndexerWorker",
            function_name="async-keyword-indexer-worker",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="worker_processor.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/keyword_indexer_worker"),
            timeout=Duration.minutes(10),  # Longer timeout for actual processing
            memory_size=1024,
            environment=worker_env,
            role=self.worker_role,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[lambda_security_group],
            layers=[
                self.climate_risk_core_layer,
                self.database_layer,
                self.opensearch_layer
            ],
            description="Async keyword indexer worker - background processing",
            log_retention=logs.RetentionDays.ONE_WEEK,
            dead_letter_queue=self.worker_dlq
        )

    def _create_outputs(self):
        """Create CloudFormation outputs"""
        
        CfnOutput(
            self, "AsyncKeywordIndexerInitiatorArn",
            value=self.initiator_function.function_arn,
            description="Async Keyword Indexer Initiator Lambda ARN"
        )
        
        CfnOutput(
            self, "AsyncKeywordIndexerWorkerArn", 
            value=self.worker_function.function_arn,
            description="Async Keyword Indexer Worker Lambda ARN"
        )
        
        CfnOutput(
            self, "KeywordIndexingCompletionTopicArn",
            value=self.completion_topic.topic_arn,
            description="Keyword Indexing Completion Topic ARN"
        )
        
        CfnOutput(
            self, "InitiatorQueueUrl",
            value=self.initiator_queue.queue_url,
            description="Keyword Indexer Initiator Queue URL"
        )

# Import SNS subscriptions
from aws_cdk import aws_sns_subscriptions as sns_subscriptions

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account="861276078413",
    region="us-east-1"
)

# Async Keyword Indexer Stack
async_keyword_indexer_stack = AsyncKeywordIndexerStack(
    app,
    "async-keyword-indexer",
    env=env,
    description="Async Keyword Indexer with simple callback approach"
)

app.synth()
