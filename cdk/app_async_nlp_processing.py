#!/usr/bin/env python3
"""
CDK Stack for Asynchronous NLP Processing Pipeline
Deploys async NLP processor, workers, and monitoring infrastructure
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
    aws_events as events,
    aws_events_targets as targets,
    CfnOutput
)
from constructs import Construct

class AsyncNLPProcessingStack(Stack):
    def __init__(self, scope, construct_id, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        # Import existing VPC
        vpc = ec2.Vpc.from_lookup(self, "ExistingVPC", 
                                  vpc_name="solve-global-kr-rag-vpc")
        
        # Import existing security group
        security_group = ec2.SecurityGroup.from_security_group_id(
            self, "ExistingSecurityGroup",
            security_group_id="sg-0c9e10b9cfb4c9eb0"
        )
        
        # Import existing lambda layer
        database_layer_arn = "arn:aws:lambda:us-east-1:861276078413:layer:database-core-layer:16"
        database_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "DatabaseLayer", database_layer_arn)
        
        # Import existing IAM role
        nlp_lambda_role = iam.Role.from_role_arn(
            self, "NLPLambdaRole",
            role_arn="arn:aws:iam::861276078413:role/nlp-integration-lambda-role"
        )
        
        # Import existing S3 buckets
        ner_results_bucket = s3.Bucket.from_bucket_name(
            self, "NERResultsBucket",
            bucket_name="solve-global-kr-dl-ner-results-861276078413-us-east-1"
        )
        
        chunks_bucket = s3.Bucket.from_bucket_name(
            self, "ChunksBucket", 
            bucket_name="solve-global-kr-dl-chunks-861276078413-us-east-1"
        )
        
        # SNS Topics for Comprehend job completion notifications
        entity_completion_topic = sns.Topic(
            self, "ComprehendEntityCompletionTopic",
            topic_name="comprehend-entity-completion",
            display_name="Comprehend Entity Detection Job Completion"
        )
        
        keyphrase_completion_topic = sns.Topic(
            self, "ComprehendKeyphraseCompletionTopic",
            topic_name="comprehend-keyphrase-completion", 
            display_name="Comprehend Key Phrase Detection Job Completion"
        )
        
        # SQS Queues for async NLP workers with DLQs
        entity_worker_dlq = sqs.Queue(
            self, "EntityWorkerDLQ",
            queue_name="nlp-worker-entity-dlq",
            retention_period=Duration.days(14)
        )
        
        entity_worker_queue = sqs.Queue(
            self, "EntityWorkerQueue",
            queue_name="nlp-worker-entity-queue",
            visibility_timeout=Duration.minutes(16),  # Longer than Lambda timeout
            message_retention_period=Duration.days(14),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=entity_worker_dlq
            )
        )
        
        keyphrase_worker_dlq = sqs.Queue(
            self, "KeyphraseWorkerDLQ",
            queue_name="nlp-worker-keyphrase-dlq",
            retention_period=Duration.days(14)
        )
        
        keyphrase_worker_queue = sqs.Queue(
            self, "KeyphraseWorkerQueue",
            queue_name="nlp-worker-keyphrase-queue",
            visibility_timeout=Duration.minutes(16),  # Longer than Lambda timeout
            message_retention_period=Duration.days(14),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=keyphrase_worker_dlq
            )
        )
        
        # Subscribe queues to completion topics
        entity_completion_topic.add_subscription(
            sns_subscriptions.SqsSubscription(entity_worker_queue)
        )
        
        keyphrase_completion_topic.add_subscription(
            sns_subscriptions.SqsSubscription(keyphrase_worker_queue)
        )
        
        # Environment variables for Lambda functions
        common_env_vars = {
            "NER_RESULTS_BUCKET": ner_results_bucket.bucket_name,
            "CHUNKS_BUCKET": chunks_bucket.bucket_name,
            "COMPREHEND_REGION": "us-east-1",
            "DATABASE_SECRET_NAME": "rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863",
            "DB_PORT": "5432",
            "DB_NAME": "climate_risk_rag",
            "DB_HOST": "solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com"
        }
        
        # Entity Worker Lambda
        entity_worker = lambda_.Function(
            self, "NLPWorkerEntity",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="handler_async.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/nlp-worker"),
            layers=[database_layer],
            timeout=Duration.minutes(15),
            memory_size=1024,
            vpc=vpc,
            security_groups=[security_group],
            role=nlp_lambda_role,
            environment=common_env_vars,
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # Key Phrase Worker Lambda
        keyphrase_worker = lambda_.Function(
            self, "NLPWorkerKeyphrase",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="handler_async.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/nlp-worker"),
            layers=[database_layer],
            timeout=Duration.minutes(15),
            memory_size=1024,
            vpc=vpc,
            security_groups=[security_group],
            role=nlp_lambda_role,
            environment=common_env_vars,
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # Comprehend Job Monitor Lambda
        job_monitor = lambda_.Function(
            self, "ComprehendJobMonitor",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/comprehend-monitor"),
            timeout=Duration.minutes(5),
            memory_size=512,
            role=nlp_lambda_role,
            environment={
                "ENTITY_COMPLETION_TOPIC_ARN": entity_completion_topic.topic_arn,
                "KEYPHRASE_COMPLETION_TOPIC_ARN": keyphrase_completion_topic.topic_arn,
                "COMPREHEND_REGION": "us-east-1",
                "ENTITY_WORKER_FUNCTION": entity_worker.function_name,
                "KEYPHRASE_WORKER_FUNCTION": keyphrase_worker.function_name
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # Event source mappings for workers
        entity_worker.add_event_source_mapping(
            "EntityWorkerEventSource",
            event_source_arn=entity_worker_queue.queue_arn,
            batch_size=1,
            max_batching_window=Duration.seconds(0)
        )
        
        keyphrase_worker.add_event_source_mapping(
            "KeyphraseWorkerEventSource", 
            event_source_arn=keyphrase_worker_queue.queue_arn,
            batch_size=1,
            max_batching_window=Duration.seconds(0)
        )
        
        # CloudWatch Events rule to trigger job monitor every 2 minutes
        monitor_schedule_rule = events.Rule(
            self, "ComprehendJobMonitorSchedule",
            rule_name="comprehend-job-monitor-schedule",
            description="Triggers Comprehend job monitor every 2 minutes",
            schedule=events.Schedule.rate(Duration.minutes(2))
        )
        
        # Add job monitor as target for the schedule rule
        monitor_schedule_rule.add_target(
            targets.LambdaFunction(job_monitor)
        )
        
        # Grant permission for CloudWatch Events to invoke the monitor
        job_monitor.add_permission(
            "AllowCloudWatchEventsInvoke",
            principal=iam.ServicePrincipal("events.amazonaws.com"),
            source_arn=monitor_schedule_rule.rule_arn
        )
        
        # Grant permission for job monitor to invoke worker functions
        job_monitor.add_to_role_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[
                    entity_worker.function_arn,
                    keyphrase_worker.function_arn
                ]
            )
        )
        
        # Update NLP Processor Lambda (existing function)
        nlp_processor = lambda_.Function(
            self, "NLPProcessor",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/nlp-processor"),
            layers=[database_layer],
            timeout=Duration.minutes(5),
            memory_size=512,
            vpc=vpc,
            security_groups=[security_group],
            role=nlp_lambda_role,
            environment={
                **common_env_vars,
                "COMPREHEND_OUTPUT_BUCKET": ner_results_bucket.bucket_name,
                "COMPREHEND_DATA_ACCESS_ROLE_ARN": "arn:aws:iam::861276078413:role/comprehend-data-access-role",
                "ENTITY_COMPLETION_TOPIC_ARN": entity_completion_topic.topic_arn,
                "KEYPHRASE_COMPLETION_TOPIC_ARN": keyphrase_completion_topic.topic_arn
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
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
        
        # CloudWatch Log Groups for better monitoring
        entity_worker_log_group = logs.LogGroup(
            self, "EntityWorkerLogGroup",
            log_group_name=f"/aws/lambda/{entity_worker.function_name}",
            retention=logs.RetentionDays.ONE_WEEK
        )
        
        keyphrase_worker_log_group = logs.LogGroup(
            self, "KeyphraseWorkerLogGroup",
            log_group_name=f"/aws/lambda/{keyphrase_worker.function_name}",
            retention=logs.RetentionDays.ONE_WEEK
        )
        
        job_monitor_log_group = logs.LogGroup(
            self, "JobMonitorLogGroup",
            log_group_name=f"/aws/lambda/{job_monitor.function_name}",
            retention=logs.RetentionDays.ONE_WEEK
        )
        
        # Outputs
        CfnOutput(self, "EntityCompletionTopicArn",
                  value=entity_completion_topic.topic_arn,
                  description="Comprehend Entity Completion SNS Topic ARN")
        
        CfnOutput(self, "KeyphraseCompletionTopicArn",
                  value=keyphrase_completion_topic.topic_arn,
                  description="Comprehend Keyphrase Completion SNS Topic ARN")
        
        CfnOutput(self, "EntityWorkerQueueArn",
                  value=entity_worker_queue.queue_arn,
                  description="Entity Worker SQS Queue ARN")
        
        CfnOutput(self, "KeyphraseWorkerQueueArn",
                  value=keyphrase_worker_queue.queue_arn,
                  description="Keyphrase Worker SQS Queue ARN")
        
        CfnOutput(self, "EntityWorkerFunctionName",
                  value=entity_worker.function_name,
                  description="Entity Worker Lambda Function Name")
        
        CfnOutput(self, "KeyphraseWorkerFunctionName",
                  value=keyphrase_worker.function_name,
                  description="Keyphrase Worker Lambda Function Name")
        
        CfnOutput(self, "JobMonitorFunctionName",
                  value=job_monitor.function_name,
                  description="Comprehend Job Monitor Lambda Function Name")
        
        CfnOutput(self, "NLPProcessorFunctionName",
                  value=nlp_processor.function_name,
                  description="Updated NLP Processor Lambda Function Name")

# CDK App
app = App()

# Environment configuration
env = Environment(
    account="861276078413",
    region="us-east-1"
)

# Deploy the stack
async_nlp_stack = AsyncNLPProcessingStack(app, "async-nlp-processing", env=env)

app.synth()
