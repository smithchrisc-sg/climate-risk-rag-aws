#!/usr/bin/env python3
"""
CDK Stack for Vector Embeddings Pipeline with OpenSearch Serverless Vector Collection
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
    aws_opensearchserverless as opensearchserverless,
    CfnOutput
)
from constructs import Construct
from stacks.database_migration_construct import DatabaseMigrationConstruct

class VectorEmbeddingsPipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Import existing VPC
        vpc = ec2.Vpc.from_lookup(self, "ExistingVPC", 
                                  vpc_name="solve-global-kr-rag-vpc")
        
        # Import existing lambda layers (using actual deployed layers)
        core_utilities_layer_arn = "arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities-pipeline:2"
        database_layer_arn = "arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies-pipeline:2"
        opensearch_layer_arn = "arn:aws:lambda:us-east-1:861276078413:layer:opensearch-dependencies:1"
        numpy_layer_arn = "arn:aws:lambda:us-east-1:861276078413:layer:numpy-dependencies:1"
        
        core_utilities_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "CoreUtilitiesLayer", core_utilities_layer_arn)
        database_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "DatabaseLayer", database_layer_arn)
        opensearch_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "OpenSearchLayer", opensearch_layer_arn)
        numpy_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "NumpyLayer", numpy_layer_arn)
        
        # OpenSearch Serverless Vector Collection Security Policies
        vector_encryption_policy = opensearchserverless.CfnSecurityPolicy(
            self, "VectorEncryptionPolicy",
            name="kr-vectors-encryption",
            type="encryption",
            policy={
                "Rules": [
                    {
                        "ResourceType": "collection",
                        "Resource": ["collection/solve-global-kr-vectors"]
                    }
                ],
                "AWSOwnedKey": True
            }
        )
        
        vector_network_policy = opensearchserverless.CfnSecurityPolicy(
            self, "VectorNetworkPolicy", 
            name="kr-vectors-network",
            type="network",
            policy=[
                {
                    "Rules": [
                        {
                            "ResourceType": "collection",
                            "Resource": ["collection/solve-global-kr-vectors"]
                        },
                        {
                            "ResourceType": "dashboard", 
                            "Resource": ["collection/solve-global-kr-vectors"]
                        }
                    ],
                    "AllowFromPublic": True
                }
            ]
        )
        
        # OpenSearch Serverless Vector Collection
        vector_collection = opensearchserverless.CfnCollection(
            self, "VectorCollection",
            name="solve-global-kr-vectors",
            type="VECTORSEARCH",
            description="Vector embeddings collection for climate risk RAG system"
        )
        vector_collection.add_dependency(vector_encryption_policy)
        vector_collection.add_dependency(vector_network_policy)
        
        # Vector Embeddings Worker (Background) - Define early to get role ARN
        vector_worker = lambda_.Function(
            self, "VectorEmbeddingsWorker",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="vector_embeddings_worker.lambda_handler", 
            code=lambda_.Code.from_asset("../lambda/vector_embeddings_worker"),
            layers=[core_utilities_layer, database_layer, opensearch_layer, numpy_layer],
            timeout=Duration.minutes(15),
            memory_size=2048,
            vpc=vpc,
            environment={
                "OPENSEARCH_ENDPOINT": vector_collection.attr_collection_endpoint,
                "VECTOR_COMPLETION_TOPIC_ARN": "",  # Will be updated after topic creation
                "DATABASE_URL": os.environ.get("DATABASE_URL", ""),
                "EMBEDDINGS_MODEL_TYPE": "titan",  # Use Bedrock Titan
                "COST_THRESHOLD_PER_DOC": "0.50",
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # OpenSearch Data Access Policy (after Lambda function is created)
        vector_data_access_policy = opensearchserverless.CfnAccessPolicy(
            self, "VectorDataAccessPolicy",
            name="kr-vectors-data-access",
            type="data",
            policy=[
                {
                    "Rules": [
                        {
                            "Resource": ["index/solve-global-kr-vectors/*"],
                            "Permission": [
                                "aoss:CreateIndex",
                                "aoss:DeleteIndex", 
                                "aoss:UpdateIndex",
                                "aoss:DescribeIndex",
                                "aoss:ReadDocument",
                                "aoss:WriteDocument"
                            ],
                            "ResourceType": "index"
                        },
                        {
                            "Resource": ["collection/solve-global-kr-vectors"],
                            "Permission": ["aoss:CreateCollectionItems"],
                            "ResourceType": "collection"
                        }
                    ],
                    "Principal": [vector_worker.role.role_arn]
                }
            ]
        )
        vector_data_access_policy.add_dependency(vector_collection)
        
        # Database Migration for Vector Embeddings Schema
        database_migration = DatabaseMigrationConstruct(
            self, "VectorEmbeddingsMigration",
            database_url=os.environ.get("DATABASE_URL", ""),
            vpc=vpc
        )
        
        # SNS Topics
        vector_worker_topic = sns.Topic(
            self, "VectorWorkerTopic",
            topic_name="vector-embeddings-worker",
            display_name="Vector Embeddings Worker Topic"
        )
        
        vector_completion_topic = sns.Topic(
            self, "VectorCompletionTopic", 
            topic_name="vector-embeddings-complete",
            display_name="Vector Embeddings Completion Topic"
        )
        
        # SQS Queue for vector worker with DLQ
        vector_worker_dlq = sqs.Queue(
            self, "VectorWorkerDLQ",
            queue_name="vector-embeddings-worker-dlq",
            retention_period=Duration.days(14)
        )
        
        vector_worker_queue = sqs.Queue(
            self, "VectorWorkerQueue",
            queue_name="vector-embeddings-worker-queue",
            visibility_timeout=Duration.minutes(20),  # Longer than Lambda timeout
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=vector_worker_dlq
            )
        )
        
        # Subscribe queue to worker topic
        vector_worker_topic.add_subscription(
            sns_subscriptions.SqsSubscription(vector_worker_queue)
        )
        
        # Vector Embeddings Processor (Initiator)
        vector_processor = lambda_.Function(
            self, "VectorEmbeddingsProcessor",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="vector_embeddings_processor.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/vector_embeddings_processor"),
            layers=[core_utilities_layer, database_layer],
            timeout=Duration.minutes(1),
            memory_size=256,
            environment={
                "VECTOR_WORKER_TOPIC_ARN": vector_worker_topic.topic_arn,
                "DATABASE_URL": os.environ.get("DATABASE_URL", ""),
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # Update vector worker environment with completion topic ARN
        vector_worker.add_environment("VECTOR_COMPLETION_TOPIC_ARN", vector_completion_topic.topic_arn)
        
        # Event source mapping for worker
        vector_worker.add_event_source_mapping(
            "VectorWorkerEventSource",
            event_source_arn=vector_worker_queue.queue_arn,
            batch_size=1,  # Process one document at a time
            max_batching_window=Duration.seconds(5)
        )
        
        # IAM Permissions
        
        # Vector processor permissions
        vector_processor.add_to_role_policy(
            iam.PolicyStatement(
                actions=["sns:Publish"],
                resources=[vector_worker_topic.topic_arn]
            )
        )
        
        # Vector worker permissions
        vector_worker.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel"
                ],
                resources=[
                    "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
                ]
            )
        )
        
        vector_worker.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "aoss:APIAccessAll"
                ],
                resources=[vector_collection.attr_arn]
            )
        )
        
        vector_worker.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:PutObject"
                ],
                resources=[
                    "arn:aws:s3:::solve-global-kr-chunks-861276078413-us-east-1/*",
                    "arn:aws:s3:::solve-global-kr-embeddings-cache-861276078413-us-east-1/*"
                ]
            )
        )
        
        vector_worker.add_to_role_policy(
            iam.PolicyStatement(
                actions=["sns:Publish"],
                resources=[vector_completion_topic.topic_arn]
            )
        )
        
        # SQS permissions for worker
        vector_worker_queue.grant_consume_messages(vector_worker)
        
        # Subscribe processor to existing chunks-ready topic (not text-chunking-complete)
        chunks_ready_topic_arn = "arn:aws:sns:us-east-1:861276078413:chunks-ready"
        chunks_ready_topic = sns.Topic.from_topic_arn(
            self, "ChunksReadyTopic", chunks_ready_topic_arn)
        
        chunks_ready_topic.add_subscription(
            sns_subscriptions.LambdaSubscription(vector_processor)
        )
        
        # Grant permission for SNS to invoke the processor
        vector_processor.add_permission(
            "AllowSNSInvoke",
            principal=iam.ServicePrincipal("sns.amazonaws.com"),
            source_arn=chunks_ready_topic_arn
        )
        
        # Outputs
        CfnOutput(self, "VectorProcessorFunctionName",
                  value=vector_processor.function_name,
                  description="Vector Embeddings Processor Function Name")
        
        CfnOutput(self, "VectorWorkerFunctionName", 
                  value=vector_worker.function_name,
                  description="Vector Embeddings Worker Function Name")
        CfnOutput(self, "VectorCollectionEndpoint",
                  value=vector_collection.attr_collection_endpoint,
                  description="OpenSearch Serverless Vector Collection Endpoint")
        
        CfnOutput(self, "VectorCollectionArn",
                  value=vector_collection.attr_arn,
                  description="OpenSearch Serverless Vector Collection ARN")
        
        CfnOutput(self, "VectorWorkerTopicArn",
                  value=vector_worker_topic.topic_arn,
                  description="Vector Worker SNS Topic ARN")
        
        CfnOutput(self, "VectorCompletionTopicArn",
                  value=vector_completion_topic.topic_arn,
                  description="Vector Completion SNS Topic ARN")

# CDK App
app = App()

# Environment configuration
env = Environment(
    account="861276078413",
    region="us-east-1"
)

# Deploy the stack
