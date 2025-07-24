#!/usr/bin/env python3
"""
Complete Climate Risk RAG System - Standardized Deployment
This CDK app deploys the complete system with standardized layers and proper IAM roles.
Based on the systematic redeployment process documented in REDEPLOYMENT_GUIDE.md
"""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_s3 as s3,
    aws_sns as sns,
    aws_sqs as sqs,
    aws_sns_subscriptions as sns_subscriptions,
    aws_s3_notifications as s3n,
    aws_lambda_event_sources as lambda_event_sources,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_opensearch as opensearch,
    Duration,
    RemovalPolicy
)
from constructs import Construct

class DocumentProcessingLambdaRoleConstruct(Construct):
    """Construct for creating the standardized document processing Lambda role"""
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create the document processing Lambda role
        self.role = iam.Role(
            self, "DocumentProcessingLambdaRole",
            role_name="document-processing-lambda-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole")
            ]
        )
        
        # Create custom policy for document processing
        policy_document = iam.PolicyDocument(
            statements=[
                # CloudWatch Logs
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream", 
                        "logs:PutLogEvents"
                    ],
                    resources=["arn:aws:logs:*:*:*"]
                ),
                # VPC Access
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ec2:CreateNetworkInterface",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DeleteNetworkInterface",
                        "ec2:AttachNetworkInterface",
                        "ec2:DetachNetworkInterface"
                    ],
                    resources=["*"]
                ),
                # Textract
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "textract:StartDocumentTextDetection",
                        "textract:StartDocumentAnalysis",
                        "textract:GetDocumentTextDetection",
                        "textract:GetDocumentAnalysis"
                    ],
                    resources=["*"]
                ),
                # Comprehend
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "comprehend:DetectEntities",
                        "comprehend:DetectKeyPhrases",
                        "comprehend:StartEntitiesDetectionJob",
                        "comprehend:StartKeyPhrasesDetectionJob",
                        "comprehend:DescribeEntitiesDetectionJob",
                        "comprehend:DescribeKeyPhrasesDetectionJob",
                        "comprehend:ListEntitiesDetectionJobs",
                        "comprehend:ListKeyPhrasesDetectionJobs"
                    ],
                    resources=["*"]
                ),
                # S3 Access
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:ListBucket",
                        "s3:DeleteObject"
                    ],
                    resources=[
                        "arn:aws:s3:::solve-global-kr-*",
                        "arn:aws:s3:::solve-global-kr-*/*"
                    ]
                ),
                # SNS
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["sns:Publish"],
                    resources=["arn:aws:sns:*:*:*"]
                ),
                # SQS
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "sqs:ReceiveMessage",
                        "sqs:DeleteMessage",
                        "sqs:GetQueueAttributes"
                    ],
                    resources=["arn:aws:sqs:*:*:*"]
                ),
                # Secrets Manager
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["secretsmanager:GetSecretValue"],
                    resources=["arn:aws:secretsmanager:*:*:secret:rds!db-*"]
                ),
                # IAM Pass Role
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["iam:PassRole"],
                    resources=[
                        "arn:aws:iam::*:role/comprehend-data-access-role",
                        "arn:aws:iam::*:role/solve-global-kr-textract-service-role"
                    ]
                ),
                # OpenSearch
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "es:ESHttpPost",
                        "es:ESHttpPut", 
                        "es:ESHttpGet",
                        "es:ESHttpDelete"
                    ],
                    resources=["arn:aws:es:*:*:domain/solve-global-kr-*/*"]
                )
            ]
        )
        
        # Attach the custom policy
        self.policy = iam.Policy(
            self, "DocumentProcessingPolicy",
            policy_name="document-processing-policy",
            document=policy_document
        )
        self.role.attach_inline_policy(self.policy)

class StandardizedLambdaLayersConstruct(Construct):
    """Construct for referencing standardized Lambda layers"""
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Reference existing standardized layers
        self.database_core_layer = _lambda.LayerVersion.from_layer_version_arn(
            self, "DatabaseCoreLayer",
            layer_version_arn="arn:aws:lambda:us-east-1:861276078413:layer:database-core-layer:16"
        )
        
        self.database_dependencies_layer = _lambda.LayerVersion.from_layer_version_arn(
            self, "DatabaseDependenciesLayer", 
            layer_version_arn="arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies:2"
        )
        
        self.opensearch_dependencies_layer = _lambda.LayerVersion.from_layer_version_arn(
            self, "OpenSearchDependenciesLayer",
            layer_version_arn="arn:aws:lambda:us-east-1:861276078413:layer:opensearch-dependencies:4"
        )

class MessagingInfrastructureStack(Stack):
    """Stack for SNS topics and SQS queues"""
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # SNS Topics
        self.text_extraction_complete_topic = sns.Topic(
            self, "TextExtractionCompleteTopic",
            topic_name="text-extraction-complete"
        )
        
        self.text_chunking_complete_topic = sns.Topic(
            self, "TextChunkingCompleteTopic", 
            topic_name="text-chunking-complete"
        )
        
        self.textract_completion_topic = sns.Topic(
            self, "TextractCompletionTopic",
            topic_name="solve-global-kr-textract-completion"
        )
        
        # SQS Queues
        self.text_extractor_initiator_queue = sqs.Queue(
            self, "TextExtractorInitiatorQueue",
            queue_name="solve-global-kr-textextractor-initiator-queue",
            visibility_timeout=Duration.seconds(300)
        )
        
        self.text_extractor_processor_queue = sqs.Queue(
            self, "TextExtractorProcessorQueue",
            queue_name="solve-global-kr-textextractor-processor",
            visibility_timeout=Duration.seconds(300)
        )
        
        self.text_chunker_queue = sqs.Queue(
            self, "TextChunkerQueue",
            queue_name="text-chunker-queue",
            visibility_timeout=Duration.seconds(300)
        )
        
        self.keyword_indexer_initiator_queue = sqs.Queue(
            self, "KeywordIndexerInitiatorQueue",
            queue_name="keyword-indexer-initiator-queue",
            visibility_timeout=Duration.seconds(300)
        )
        
        self.nlp_worker_queue = sqs.Queue(
            self, "NlpWorkerQueue",
            queue_name="nlp-worker-queue",
            visibility_timeout=Duration.seconds(300)
        )
        
        # SNS to SQS Subscriptions
        self.text_extraction_complete_topic.add_subscription(
            sns_subscriptions.SqsSubscription(self.text_chunker_queue)
        )
        
        self.text_chunking_complete_topic.add_subscription(
            sns_subscriptions.SqsSubscription(self.keyword_indexer_initiator_queue)
        )
        
        self.text_chunking_complete_topic.add_subscription(
            sns_subscriptions.SqsSubscription(self.nlp_worker_queue)
        )
        
        self.textract_completion_topic.add_subscription(
            sns_subscriptions.SqsSubscription(self.text_extractor_processor_queue)
        )

class DocumentProcessingStack(Stack):
    """Main stack for document processing Lambda functions"""
    
    def __init__(self, scope: Construct, construct_id: str, 
                 messaging_stack: MessagingInfrastructureStack,
                 vpc_id: str = None,
                 subnet_ids: list = None,
                 security_group_id: str = None,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create IAM role and layers constructs
        self.lambda_role_construct = DocumentProcessingLambdaRoleConstruct(
            self, "DocumentProcessingLambdaRole"
        )
        
        self.layers_construct = StandardizedLambdaLayersConstruct(
            self, "StandardizedLayers"
        )
        
        # VPC Configuration
        if vpc_id and subnet_ids and security_group_id:
            vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_id=vpc_id)
            subnets = [ec2.Subnet.from_subnet_id(self, f"Subnet{i}", subnet_id) 
                      for i, subnet_id in enumerate(subnet_ids)]
            security_group = ec2.SecurityGroup.from_security_group_id(
                self, "SecurityGroup", security_group_id
            )
            vpc_config = _lambda.VpcConfig(
                vpc=vpc,
                subnets=ec2.SubnetSelection(subnets=subnets),
                security_groups=[security_group]
            )
        else:
            vpc_config = None
        
        # Standard environment variables
        standard_env = {
            "DATABASE_SECRET_NAME": "rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863",
            "DB_PORT": "5432",
            "DB_NAME": "climate_risk_rag",
            "DB_HOST": "solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com"
        }
        
        # 1. Cleanup Service
        self.cleanup_service = _lambda.Function(
            self, "CleanupService",
            function_name="cleanup-service",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("lambda/cleanup-service"),
            role=self.lambda_role_construct.role,
            timeout=Duration.seconds(300),
            memory_size=512,
            layers=[
                self.layers_construct.database_core_layer,
                self.layers_construct.database_dependencies_layer
            ],
            environment=standard_env,
            vpc_config=vpc_config
        )
        
        # 2. Pipeline Test Function
        self.pipeline_test_function = _lambda.Function(
            self, "PipelineTestFunction",
            function_name="pipeline-test-function",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("lambda/pipeline-test-function"),
            role=self.lambda_role_construct.role,
            timeout=Duration.seconds(300),
            memory_size=512,
            layers=[
                self.layers_construct.database_core_layer,
                self.layers_construct.database_dependencies_layer
            ],
            environment={
                **standard_env,
                "SOURCE_BUCKET": "solve-global-kr-dl-source-documents-861276078413-us-east-1"
            },
            vpc_config=vpc_config
        )
        
        # 3. Text Extractor Initiator
        self.text_extractor_initiator = _lambda.Function(
            self, "TextExtractorInitiator",
            function_name="text-extractor-initiator",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("lambda/text-extractor-initiator"),
            role=self.lambda_role_construct.role,
            timeout=Duration.seconds(300),
            memory_size=512,
            layers=[
                self.layers_construct.database_core_layer,
                self.layers_construct.database_dependencies_layer
            ],
            environment={
                **standard_env,
                "TEXTRACT_SNS_TOPIC_ARN": messaging_stack.textract_completion_topic.topic_arn,
                "TEXTRACT_SERVICE_ROLE_ARN": "arn:aws:iam::861276078413:role/solve-global-kr-textract-service-role",
                "OUTPUT_BUCKET": "solve-global-kr-dl-text-861276078413-us-east-1"
            },
            vpc_config=vpc_config
        )
        
        # Add event source mapping for text extractor initiator
        self.text_extractor_initiator.add_event_source(
            lambda_event_sources.SqsEventSource(
                messaging_stack.text_extractor_initiator_queue,
                batch_size=10,
                max_batching_window=Duration.seconds(5)
            )
        )
        
        # 4. Text Extractor Processor
        self.text_extractor_processor = _lambda.Function(
            self, "TextExtractorProcessor",
            function_name="text-extractor-processor",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("lambda/text-extractor-processor"),
            role=self.lambda_role_construct.role,
            timeout=Duration.seconds(300),
            memory_size=512,
            layers=[
                self.layers_construct.database_core_layer,
                self.layers_construct.database_dependencies_layer
            ],
            environment={
                **standard_env,
                "OUTPUT_BUCKET": "solve-global-kr-dl-text-861276078413-us-east-1",
                "COMPLETION_TOPIC_ARN": messaging_stack.text_extraction_complete_topic.topic_arn
            },
            vpc_config=vpc_config
        )
        
        # Add event source mapping for text extractor processor
        self.text_extractor_processor.add_event_source(
            lambda_event_sources.SqsEventSource(
                messaging_stack.text_extractor_processor_queue,
                batch_size=10,
                max_batching_window=Duration.seconds(5)
            )
        )
        
        # 5. Text Chunker Processor
        self.text_chunker_processor = _lambda.Function(
            self, "TextChunkerProcessor",
            function_name="text-chunker-processor",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("lambda/text-chunker-processor"),
            role=self.lambda_role_construct.role,
            timeout=Duration.seconds(300),
            memory_size=1024,
            layers=[
                self.layers_construct.database_core_layer,
                self.layers_construct.database_dependencies_layer
            ],
            environment={
                **standard_env,
                "TEXT_BUCKET": "solve-global-kr-dl-text-861276078413-us-east-1",
                "CHUNKS_BUCKET": "solve-global-kr-dl-chunks-861276078413-us-east-1",
                "CHUNKS_READY_TOPIC_ARN": messaging_stack.text_chunking_complete_topic.topic_arn
            },
            vpc_config=vpc_config
        )
        
        # Add event source mapping for text chunker processor
        self.text_chunker_processor.add_event_source(
            lambda_event_sources.SqsEventSource(
                messaging_stack.text_chunker_queue,
                batch_size=10,
                max_batching_window=Duration.seconds(5)
            )
        )
        
        # KG Processing Components
        
        # KG Triples Ready Topic
        self.kg_triples_ready_topic = sns.Topic(
            self, "KGTriplesReadyTopic",
            topic_name="kg-triples-ready",
            display_name="Knowledge Graph Triples Ready for Neptune Loading"
        )
        
        # Reference existing text-chunking-complete topic
        text_chunking_complete_topic_arn = "arn:aws:sns:us-east-1:861276078413:text-chunking-complete"
        text_chunking_complete_topic = sns.Topic.from_topic_arn(
            self, "TextChunkingCompleteTopic", text_chunking_complete_topic_arn
        )
        
        # Document Structure KG Processor
        self.document_structure_kg_processor = _lambda.Function(
            self, "DocumentStructureKGProcessor",
            function_name="document-structure-kg-processor",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("lambda/document-structure-kg-processor"),
            role=self.lambda_role_construct.role,
            timeout=Duration.minutes(5),
            memory_size=1024,
            layers=[
                self.layers_construct.database_core_layer,
                self.layers_construct.database_dependencies_layer
            ],
            environment={
                **standard_env,
                "CHUNKS_BUCKET": "solve-global-kr-dl-chunks-861276078413-us-east-1",
                "TEXT_BUCKET": "solve-global-kr-dl-text-861276078413-us-east-1",
                "TTL_BUCKET": "solve-global-kr-dl-neptune-ttl-861276078413-us-east-1",
                "NEPTUNE_ENDPOINT": "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com",
                "NEPTUNE_PORT": "8182",
                "KG_TRIPLES_READY_TOPIC_ARN": self.kg_triples_ready_topic.topic_arn
            },
            vpc_config=vpc_config
        )
        
        # Subscribe document structure processor to text-chunking-complete topic
        text_chunking_complete_topic.add_subscription(
            sns_subscriptions.LambdaSubscription(self.document_structure_kg_processor)
        )
        
        # Grant permission for SNS to invoke the document structure processor
        self.document_structure_kg_processor.add_permission(
            "AllowSNSInvoke",
            principal=iam.ServicePrincipal("sns.amazonaws.com"),
            source_arn=text_chunking_complete_topic_arn
        )
        
        # KG Integration Worker (Neptune loader)
        self.kg_integration_worker = _lambda.Function(
            self, "KGIntegrationWorker",
            function_name="kg-integration-worker",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("lambda/kg-integration-worker"),
            role=self.lambda_role_construct.role,
            timeout=Duration.minutes(10),  # Neptune loading can take time
            memory_size=512,
            layers=[
                self.layers_construct.database_core_layer,
                self.layers_construct.database_dependencies_layer
            ],
            environment={
                **standard_env,
                "NEPTUNE_ENDPOINT": "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com",
                "NEPTUNE_PORT": "8182",
                "TTL_BUCKET": "solve-global-kr-dl-neptune-ttl-861276078413-us-east-1"
            },
            vpc_config=vpc_config
        )
        
        # Subscribe KG integration worker to kg-triples-ready topic
        self.kg_triples_ready_topic.add_subscription(
            sns_subscriptions.LambdaSubscription(self.kg_integration_worker)
        )
        
        # Grant permission for SNS to invoke the KG integration worker
        self.kg_integration_worker.add_permission(
            "AllowKGTriplesReadySNSInvoke",
            principal=iam.ServicePrincipal("sns.amazonaws.com"),
            source_arn=self.kg_triples_ready_topic.topic_arn
        )

class S3NotificationStack(Stack):
    """Stack for S3 bucket notifications"""
    
    def __init__(self, scope: Construct, construct_id: str,
                 messaging_stack: MessagingInfrastructureStack,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Reference existing S3 bucket
        source_bucket = s3.Bucket.from_bucket_name(
            self, "SourceDocumentsBucket",
            "solve-global-kr-dl-source-documents-861276078413-us-east-1"
        )
        
        # Create SNS topic for S3 events
        self.source_document_events_topic = sns.Topic(
            self, "SourceDocumentEventsTopic",
            topic_name="solve-global-kr-source-document-events"
        )
        
        # Subscribe the text extractor initiator queue to the S3 events topic
        self.source_document_events_topic.add_subscription(
            sns_subscriptions.SqsSubscription(messaging_stack.text_extractor_initiator_queue)
        )
        
        # Add S3 notification for both data_lake/ and data-lake/ prefixes
        source_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.SnsDestination(self.source_document_events_topic),
            s3.NotificationKeyFilter(prefix="data_lake/", suffix=".pdf")
        )
        
        source_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.SnsDestination(self.source_document_events_topic),
            s3.NotificationKeyFilter(prefix="data-lake/", suffix=".pdf")
        )

class ClimateRiskRAGApp(cdk.App):
    """Main CDK application for Climate Risk RAG system"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Configuration
        env = cdk.Environment(
            account="861276078413",
            region="us-east-1"
        )
        
        vpc_config = {
            "vpc_id": "vpc-0123456789abcdef0",  # Replace with actual VPC ID
            "subnet_ids": [
                "subnet-03d8bd6cf3491f38c",
                "subnet-0c0be1dd59f70f70e"
            ],
            "security_group_id": "sg-0c9e10b9cfb4c9eb0"
        }
        
        # Create stacks
        messaging_stack = MessagingInfrastructureStack(
            self, "MessagingInfrastructure",
            env=env
        )
        
        document_processing_stack = DocumentProcessingStack(
            self, "DocumentProcessing",
            messaging_stack=messaging_stack,
            env=env,
            **vpc_config
        )
        
        s3_notification_stack = S3NotificationStack(
            self, "S3Notifications",
            messaging_stack=messaging_stack,
            env=env
        )
        
        # Add dependencies
        document_processing_stack.add_dependency(messaging_stack)
        s3_notification_stack.add_dependency(messaging_stack)

if __name__ == "__main__":
    app = ClimateRiskRAGApp()
    app.synth()
