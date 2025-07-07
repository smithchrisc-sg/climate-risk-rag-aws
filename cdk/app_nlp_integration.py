#!/usr/bin/env python3
"""
CDK Stack for NLP Integration Pipeline
Deploys NLP processor and worker with S3 data lake storage
"""
import os
from aws_cdk import (
    App, Stack, Duration, Environment,
    aws_lambda as lambda_,
    aws_sns as sns,
    aws_sqs as sqs,
    aws_sns_subscriptions as sns_subscriptions,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_logs as logs,
    aws_s3 as s3,
    CfnOutput
)
from constructs import Construct

class NLPIntegrationStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Import existing VPC
        vpc = ec2.Vpc.from_lookup(self, "ExistingVPC", 
                                  vpc_name="solve-global-kr-rag-vpc")
        
        # Import existing lambda layers
        core_utilities_layer_arn = "arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities-pipeline:2"
        database_layer_arn = "arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies-pipeline:2"
        
        core_utilities_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "CoreUtilitiesLayer", core_utilities_layer_arn)
        database_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "DatabaseLayer", database_layer_arn)
        
        # Create S3 bucket for NLP results (data lake)
        nlp_results_bucket = s3.Bucket(
            self, "NLPResultsBucket",
            bucket_name=f"solve-global-kr-ner-results-{self.account}-{self.region}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ArchiveOldResults",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        )
                    ]
                )
            ]
        )
        
        # SNS Topics for NLP pipeline
        nlp_worker_topic = sns.Topic(
            self, "NLPWorkerTopic",
            topic_name="nlp-worker",
            display_name="NLP Processing Worker Topic"
        )
        
        nlp_completion_topic = sns.Topic(
            self, "NLPCompletionTopic", 
            topic_name="nlp-processing-complete",
            display_name="NLP Processing Completion Topic"
        )
        
        # SQS Queue for NLP worker with DLQ
        nlp_worker_dlq = sqs.Queue(
            self, "NLPWorkerDLQ",
            queue_name="nlp-worker-dlq",
            retention_period=Duration.days(14)
        )
        
        nlp_worker_queue = sqs.Queue(
            self, "NLPWorkerQueue",
            queue_name="nlp-worker-queue",
            visibility_timeout=Duration.minutes(15),  # Longer than Lambda timeout
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=nlp_worker_dlq
            )
        )
        
        # Subscribe queue to worker topic
        nlp_worker_topic.add_subscription(
            sns_subscriptions.SqsSubscription(nlp_worker_queue)
        )
        
        # NLP Processor Lambda (initiator)
        nlp_processor = lambda_.Function(
            self, "NLPProcessor",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="nlp_processor.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/nlp_processor"),
            layers=[core_utilities_layer, database_layer],
            timeout=Duration.minutes(1),
            memory_size=256,
            environment={
                "NLP_WORKER_TOPIC_ARN": nlp_worker_topic.topic_arn,
                "DATABASE_URL": os.environ.get("DATABASE_URL", ""),
                "NLP_PROVIDER": "comprehend"  # Default to Comprehend
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # NLP Worker Lambda (background processor)
        nlp_worker = lambda_.Function(
            self, "NLPWorker",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="nlp_worker.lambda_handler", 
            code=lambda_.Code.from_asset("../lambda/nlp_worker"),
            layers=[core_utilities_layer, database_layer],
            timeout=Duration.minutes(10),
            memory_size=1024,
            vpc=vpc,
            environment={
                "DATABASE_URL": os.environ.get("DATABASE_URL", ""),
                "NLP_COMPLETION_TOPIC_ARN": nlp_completion_topic.topic_arn,
                "NER_RESULTS_BUCKET": nlp_results_bucket.bucket_name,
                "NLP_PROVIDER": "comprehend",
                "COMPREHEND_REGION": "us-east-1"
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # Event source mapping for worker
        nlp_worker.add_event_source_mapping(
            "NLPWorkerEventSource",
            event_source_arn=nlp_worker_queue.queue_arn,
            batch_size=1,  # Process one document at a time
            max_batching_window=Duration.seconds(5)
        )
        
        # IAM Permissions
        
        # NLP processor permissions
        nlp_processor.add_to_role_policy(
            iam.PolicyStatement(
                actions=["sns:Publish"],
                resources=[nlp_worker_topic.topic_arn]
            )
        )
        
        # NLP worker permissions
        nlp_worker.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "comprehend:DetectEntities",
                    "comprehend:DetectKeyPhrases"
                ],
                resources=["*"]  # Comprehend doesn't support resource-level permissions
            )
        )
        
        # S3 permissions for NLP results storage
        nlp_results_bucket.grant_read_write(nlp_worker)
        
        # S3 permissions for reading chunks and full text
        nlp_worker.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject"
                ],
                resources=[
                    "arn:aws:s3:::solve-global-kr-chunks-861276078413-us-east-1/*",
                    "arn:aws:s3:::solve-global-kr-text-861276078413-us-east-1/*"
                ]
            )
        )
        
        nlp_worker.add_to_role_policy(
            iam.PolicyStatement(
                actions=["sns:Publish"],
                resources=[nlp_completion_topic.topic_arn]
            )
        )
        
        # SQS permissions for worker
        nlp_worker_queue.grant_consume_messages(nlp_worker)
        
        # Subscribe processor to existing chunks-ready topic
        chunks_ready_topic_arn = "arn:aws:sns:us-east-1:861276078413:chunks-ready"
        chunks_ready_topic = sns.Topic.from_topic_arn(
            self, "ChunksReadyTopic", chunks_ready_topic_arn)
        
        chunks_ready_topic.add_subscription(
            sns_subscriptions.LambdaSubscription(nlp_processor)
        )
        
        # Grant permission for SNS to invoke the processor
        nlp_processor.add_permission(
            "AllowSNSInvoke",
            principal=iam.ServicePrincipal("sns.amazonaws.com"),
            source_arn=chunks_ready_topic_arn
        )
        
        # Outputs
        CfnOutput(self, "NLPProcessorFunctionName",
                  value=nlp_processor.function_name,
                  description="NLP Processor Function Name")
        
        CfnOutput(self, "NLPWorkerFunctionName", 
                  value=nlp_worker.function_name,
                  description="NLP Worker Function Name")
        
        CfnOutput(self, "NLPResultsBucketName",
                  value=nlp_results_bucket.bucket_name,
                  description="S3 Bucket for NLP Results Data Lake")
        
        CfnOutput(self, "NLPWorkerTopicArn",
                  value=nlp_worker_topic.topic_arn,
                  description="NLP Worker SNS Topic ARN")
        
        CfnOutput(self, "NLPCompletionTopicArn",
                  value=nlp_completion_topic.topic_arn,
                  description="NLP Completion SNS Topic ARN")

# CDK App
app = App()

# Environment configuration
env = Environment(
    account="861276078413",
    region="us-east-1"
)

# Deploy the stack
nlp_stack = NLPIntegrationStack(app, "nlp-integration", env=env)

app.synth()
