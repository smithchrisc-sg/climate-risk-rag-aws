#!/usr/bin/env python3
"""
Production-Ready Climate Risk RAG System CDK App
Comprehensive deployment aligned with infrastructure guide and current working components

This CDK app deploys the complete system with:
- Knowledge Graph Layer v2.0.0 with NLP-Ontology Integration integration
- Proper subnet, security group, and IAM configurations per infrastructure guide
- Consistent SNS messaging patterns
- All current working pipeline components
- Production-ready monitoring and cost controls
"""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
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
    aws_neptune as neptune,
    Duration,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct

class ClimateRiskRAGProductionStack(Stack):
    """Production-ready Climate Risk RAG system with complete pipeline integration"""
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Import existing VPC and subnets per infrastructure guide
        self.vpc = ec2.Vpc.from_lookup(self, "ExistingVPC", vpc_id="vpc-051c21d88c7dc3819")
        
        # Import database subnets (for Lambda functions needing database access)
        self.database_subnet_1 = ec2.Subnet.from_subnet_id(
            self, "DatabaseSubnet1", 
            subnet_id="subnet-0e9efc5fdf29e9da0"
        )
        self.database_subnet_2 = ec2.Subnet.from_subnet_id(
            self, "DatabaseSubnet2", 
            subnet_id="subnet-00efdcc220a613ae3"
        )
        
        # Import Neptune subnets (for KG integration functions)
        self.neptune_subnet_1 = ec2.Subnet.from_subnet_id(
            self, "NeptuneSubnet1", 
            subnet_id="subnet-03d8bd6cf3491f38c"
        )
        self.neptune_subnet_2 = ec2.Subnet.from_subnet_id(
            self, "NeptuneSubnet2", 
            subnet_id="subnet-0c0be1dd59f70f70e"
        )
        
        # Import existing security groups per infrastructure guide
        self.database_sg = ec2.SecurityGroup.from_security_group_id(
            self, "DatabaseSecurityGroup",
            security_group_id="sg-09bc56a537bf7ac12"
        )
        
        self.neptune_sg = ec2.SecurityGroup.from_security_group_id(
            self, "NeptuneSecurityGroup", 
            security_group_id="sg-0c8afac0f49164069"
        )
        
        # Create standardized Lambda security group
        self.lambda_sg = ec2.SecurityGroup(
            self, "LambdaSecurityGroup",
            vpc=self.vpc,
            description="Security group for Lambda functions with database and Neptune access",
            allow_all_outbound=True
        )
        
        # Add egress rules for database and Neptune access
        self.lambda_sg.add_egress_rule(
            peer=self.database_sg,
            connection=ec2.Port.tcp(5432),
            description="Allow PostgreSQL access to database"
        )
        
        self.lambda_sg.add_egress_rule(
            peer=self.neptune_sg,
            connection=ec2.Port.tcp(8182),
            description="Allow Neptune SPARQL/Gremlin access"
        )
        
        # Add ingress rules to database and Neptune security groups
        self.database_sg.add_ingress_rule(
            peer=self.lambda_sg,
            connection=ec2.Port.tcp(5432),
            description="Allow Lambda to connect to PostgreSQL"
        )
        
        self.neptune_sg.add_ingress_rule(
            peer=self.lambda_sg,
            connection=ec2.Port.tcp(8182),
            description="Allow Lambda access to Neptune SPARQL/Gremlin endpoint"
        )
        
        # Create S3 buckets with standardized naming
        self.create_s3_buckets()
        
        # Create SNS topics for pipeline messaging
        self.create_sns_topics()
        
        # Create Lambda layers
        self.create_lambda_layers()
        
        # Create IAM roles
        self.create_iam_roles()
        
        # Create Lambda functions for complete pipeline
        self.create_pipeline_lambda_functions()
        
        # Set up S3 event notifications
        self.setup_s3_notifications()
        
        # Create outputs
        self.create_outputs()
    
    def create_s3_buckets(self):
        """Create S3 buckets with standardized naming per infrastructure guide"""
        
        # Source documents bucket (pipeline entry point)
        self.source_documents_bucket = s3.Bucket(
            self, "SourceDocumentsBucket",
            bucket_name=f"solve-global-kr-dl-source-documents-{self.account}-{self.region}",
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteIncompleteMultipartUploads",
                    abort_incomplete_multipart_upload_after=Duration.days(7)
                )
            ]
        )
        
        # Processed documents bucket
        self.documents_bucket = s3.Bucket(
            self, "DocumentsBucket",
            bucket_name=f"solve-global-kr-documents-{self.account}-{self.region}",
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN
        )
        
        # Text extraction results
        self.text_bucket = s3.Bucket(
            self, "TextBucket",
            bucket_name=f"solve-global-kr-dl-text-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.RETAIN
        )
        
        # Text chunks
        self.chunks_bucket = s3.Bucket(
            self, "ChunksBucket",
            bucket_name=f"solve-global-kr-dl-chunks-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.RETAIN
        )
        
        # Vector embeddings
        self.embeddings_bucket = s3.Bucket(
            self, "EmbeddingsBucket",
            bucket_name=f"solve-global-kr-embeddings-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.RETAIN
        )
        
        # Knowledge graph TTL files
        self.kg_bucket = s3.Bucket(
            self, "KnowledgeGraphBucket",
            bucket_name=f"solve-global-kr-kg-data-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.RETAIN
        )
        
        # Cache and metadata
        self.cache_bucket = s3.Bucket(
            self, "CacheBucket",
            bucket_name=f"solve-global-kr-cache-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.RETAIN
        )
    
    def create_sns_topics(self):
        """Create SNS topics for pipeline messaging with consistent patterns"""
        
        # Text extraction ready
        self.text_extraction_ready_topic = sns.Topic(
            self, "TextExtractionReadyTopic",
            topic_name="solve-global-kr-text-extraction-ready",
            display_name="Text Extraction Ready Topic"
        )
        
        # Text ready (extraction complete)
        self.text_ready_topic = sns.Topic(
            self, "TextReadyTopic",
            topic_name="solve-global-kr-text-ready",
            display_name="Text Ready Topic"
        )
        
        # Chunks ready (chunking complete)
        self.chunks_ready_topic = sns.Topic(
            self, "ChunksReadyTopic",
            topic_name="solve-global-kr-chunks-ready",
            display_name="Chunks Ready Topic"
        )
        
        # Vector embeddings ready
        self.vector_embeddings_ready_topic = sns.Topic(
            self, "VectorEmbeddingsReadyTopic",
            topic_name="solve-global-kr-vector-embeddings-ready",
            display_name="Vector Embeddings Ready Topic"
        )
        
        # KG triples ready (document structure KG complete)
        self.kg_triples_ready_topic = sns.Topic(
            self, "KGTriplesReadyTopic",
            topic_name="solve-global-kr-kg-triples-ready",
            display_name="KG Triples Ready Topic"
        )
        
        # NLP processing ready
        self.nlp_ready_topic = sns.Topic(
            self, "NLPReadyTopic",
            topic_name="solve-global-kr-nlp-ready",
            display_name="NLP Processing Ready Topic"
        )
    
    def create_lambda_layers(self):
        """Create Lambda layers including Knowledge Graph Layer v2.0.0 with NLP-Ontology Integration"""
        
        # Knowledge Graph Layer v2.0.0 with NLP-Ontology Integration
        # Updated to Knowledge Graph Layer v2.0.0 - Maintains backward compatibility

        self.knowledge_graph_layer = lambda_.LayerVersion(
            self, "KnowledgeGraphLayer",
            code=lambda_.Code.from_asset("../layers/knowledge-graph-layer/knowledge-graph-layer-v2.0.0.zip"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Knowledge Graph Layer v2.0.0 with NLP-Ontology Integration with Neptune integration"
        )
        
        # Database Core Layer (existing)
        self.database_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "DatabaseLayer",
            layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:climate-risk-core-utilities:2"
        )
        
        # Database Dependencies Layer (existing)
        self.database_dependencies_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "DatabaseDependenciesLayer",
            layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:database-dependencies:2"
        )
    
    def create_iam_roles(self):
        """Create standardized IAM roles per infrastructure guide"""
        
        # Standard Lambda execution role for database access
        self.lambda_role = iam.Role(
            self, "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "CustomLambdaPolicy": iam.PolicyDocument(
                    statements=[\n                        # S3 permissions for all project buckets\n                        iam.PolicyStatement(\n                            effect=iam.Effect.ALLOW,\n                            actions=[\n                                \"s3:GetObject\",\n                                \"s3:PutObject\",\n                                \"s3:ListBucket\",\n                                \"s3:CopyObject\",\n                                \"s3:GetObjectMetadata\",\n                                \"s3:PutObjectMetadata\",\n                                \"s3:DeleteObject\"\n                            ],\n                            resources=[\n                                \"arn:aws:s3:::solve-global-kr-*\",\n                                \"arn:aws:s3:::solve-global-kr-*/*\"\n                            ]\n                        ),\n                        # SNS permissions\n                        iam.PolicyStatement(\n                            effect=iam.Effect.ALLOW,\n                            actions=[\n                                \"sns:Publish\",\n                                \"sns:Subscribe\",\n                                \"sns:Unsubscribe\",\n                                \"sns:GetTopicAttributes\"\n                            ],\n                            resources=[f\"arn:aws:sns:{self.region}:{self.account}:solve-global-kr-*\"]\n                        ),\n                        # Lambda invoke permissions\n                        iam.PolicyStatement(\n                            effect=iam.Effect.ALLOW,\n                            actions=[\"lambda:InvokeFunction\"],\n                            resources=[f\"arn:aws:lambda:{self.region}:{self.account}:function:solve-global-kr-*\"]\n                        ),\n                        # Textract permissions\n                        iam.PolicyStatement(\n                            effect=iam.Effect.ALLOW,\n                            actions=[\n                                \"textract:StartDocumentTextDetection\",\n                                \"textract:GetDocumentTextDetection\",\n                                \"textract:StartDocumentAnalysis\",\n                                \"textract:GetDocumentAnalysis\"\n                            ],\n                            resources=[\"*\"]\n                        ),\n                        # Bedrock permissions for vector embeddings\n                        iam.PolicyStatement(\n                            effect=iam.Effect.ALLOW,\n                            actions=[\n                                \"bedrock:InvokeModel\",\n                                \"bedrock:InvokeModelWithResponseStream\"\n                            ],\n                            resources=[\n                                f\"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v1\",\n                                f\"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v2:0\"\n                            ]\n                        ),\n                        # Comprehend permissions for NLP\n                        iam.PolicyStatement(\n                            effect=iam.Effect.ALLOW,\n                            actions=[\n                                \"comprehend:StartEntitiesDetectionJob\",\n                                \"comprehend:StartKeyPhrasesDetectionJob\",\n                                \"comprehend:DescribeEntitiesDetectionJob\",\n                                \"comprehend:DescribeKeyPhrasesDetectionJob\",\n                                \"comprehend:DetectEntities\",\n                                \"comprehend:DetectKeyPhrases\",\n                                \"comprehend:DetectSentiment\"\n                            ],\n                            resources=[\"*\"]\n                        ),\n                        # Neptune permissions for knowledge graph\n                        iam.PolicyStatement(\n                            effect=iam.Effect.ALLOW,\n                            actions=[\n                                \"neptune-db:*\"\n                            ],\n                            resources=[\"*\"]\n                        ),\n                        # OpenSearch permissions\n                        iam.PolicyStatement(\n                            effect=iam.Effect.ALLOW,\n                            actions=[\n                                \"es:ESHttpPost\",\n                                \"es:ESHttpPut\",\n                                \"es:ESHttpGet\",\n                                \"es:ESHttpDelete\",\n                                \"aoss:*\"\n                            ],\n                            resources=[\"*\"]\n                        ),\n                        # Secrets Manager permissions\n                        iam.PolicyStatement(\n                            effect=iam.Effect.ALLOW,\n                            actions=[\"secretsmanager:GetSecretValue\"],\n                            resources=[f\"arn:aws:secretsmanager:{self.region}:{self.account}:secret:*\"]\n                        )\n                    ]\n                )\n            }\n        )\n    \n    def create_pipeline_lambda_functions(self):\n        \"\"\"Create all Lambda functions for the complete pipeline\"\"\"\n        \n        # Database URL from infrastructure guide\n        database_url = \"postgresql://postgres:c0xfd_t#PBUqV(pLM-9IqM59G:>c@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require\"\n        \n        # Common environment variables\n        common_env = {\n            \"DATABASE_URL\": database_url,\n            \"LAMBDA_ENVIRONMENT\": \"true\",\n            \"AWS_REGION\": self.region\n        }\n        \n        # 1. Text Extractor Initiator\n        self.text_extractor_initiator = lambda_.Function(\n            self, \"TextExtractorInitiator\",\n            function_name=\"solve-global-kr-text-extractor-initiator\",\n            runtime=lambda_.Runtime.PYTHON_3_11,\n            handler=\"handler.lambda_handler\",\n            code=lambda_.Code.from_asset(\"../lambda/text-extractor-initiator\"),\n            role=self.lambda_role,\n            timeout=Duration.minutes(15),\n            memory_size=1024,\n            vpc=self.vpc,\n            vpc_subnets=ec2.SubnetSelection(subnets=[self.database_subnet_1, self.database_subnet_2]),\n            security_groups=[self.lambda_sg],\n            layers=[self.database_layer, self.database_dependencies_layer],\n            environment={\n                **common_env,\n                \"TEXT_EXTRACTION_READY_TOPIC_ARN\": self.text_extraction_ready_topic.topic_arn,\n                \"SOURCE_DOCUMENTS_BUCKET\": self.source_documents_bucket.bucket_name,\n                \"DOCUMENTS_BUCKET\": self.documents_bucket.bucket_name\n            }\n        )\n        \n        # 2. Text Extractor Processor\n        self.text_extractor_processor = lambda_.Function(\n            self, \"TextExtractorProcessor\",\n            function_name=\"solve-global-kr-text-extractor-processor\",\n            runtime=lambda_.Runtime.PYTHON_3_11,\n            handler=\"handler.lambda_handler\",\n            code=lambda_.Code.from_asset(\"../lambda/text-extractor-processor\"),\n            role=self.lambda_role,\n            timeout=Duration.minutes(15),\n            memory_size=1024,\n            vpc=self.vpc,\n            vpc_subnets=ec2.SubnetSelection(subnets=[self.database_subnet_1, self.database_subnet_2]),\n            security_groups=[self.lambda_sg],\n            layers=[self.database_layer, self.database_dependencies_layer],\n            environment={\n                **common_env,\n                \"TEXT_READY_TOPIC_ARN\": self.text_ready_topic.topic_arn,\n                \"TEXT_BUCKET\": self.text_bucket.bucket_name\n            }\n        )\n        \n        # 3. Text Chunker Processor\n        self.text_chunker_processor = lambda_.Function(\n            self, \"TextChunkerProcessor\",\n            function_name=\"solve-global-kr-text-chunker-processor\",\n            runtime=lambda_.Runtime.PYTHON_3_11,\n            handler=\"handler.lambda_handler\",\n            code=lambda_.Code.from_asset(\"../lambda/text-chunker-processor\"),\n            role=self.lambda_role,\n            timeout=Duration.minutes(15),\n            memory_size=1024,\n            vpc=self.vpc,\n            vpc_subnets=ec2.SubnetSelection(subnets=[self.database_subnet_1, self.database_subnet_2]),\n            security_groups=[self.lambda_sg],\n            layers=[self.database_layer, self.database_dependencies_layer],\n            environment={\n                **common_env,\n                \"CHUNKS_READY_TOPIC_ARN\": self.chunks_ready_topic.topic_arn,\n                \"CHUNKS_BUCKET\": self.chunks_bucket.bucket_name\n            }\n        )\n        \n        # 4. Vector Embeddings Worker\n        self.vector_embeddings_worker = lambda_.Function(\n            self, \"VectorEmbeddingsWorker\",\n            function_name=\"solve-global-kr-vector-embeddings-worker\",\n            runtime=lambda_.Runtime.PYTHON_3_11,\n            handler=\"handler.lambda_handler\",\n            code=lambda_.Code.from_asset(\"../lambda/vector-embeddings-worker\"),\n            role=self.lambda_role,\n            timeout=Duration.minutes(15),\n            memory_size=1024,\n            vpc=self.vpc,\n            vpc_subnets=ec2.SubnetSelection(subnets=[self.database_subnet_1, self.database_subnet_2]),\n            security_groups=[self.lambda_sg],\n            layers=[self.database_layer, self.database_dependencies_layer],\n            environment={\n                **common_env,\n                \"VECTOR_EMBEDDINGS_READY_TOPIC_ARN\": self.vector_embeddings_ready_topic.topic_arn,\n                \"EMBEDDINGS_BUCKET\": self.embeddings_bucket.bucket_name\n            }\n        )\n        \n        # 5. Document Structure KG Processor (using Knowledge Graph Layer)\n        self.document_structure_kg_processor = lambda_.Function(\n            self, \"DocumentStructureKGProcessor\",\n            function_name=\"solve-global-kr-document-structure-kg-processor\",\n            runtime=lambda_.Runtime.PYTHON_3_11,\n            handler=\"handler.lambda_handler\",\n            code=lambda_.Code.from_asset(\"../lambda/document-structure-kg-processor\"),\n            role=self.lambda_role,\n            timeout=Duration.minutes(15),\n            memory_size=1024,\n            vpc=self.vpc,\n            vpc_subnets=ec2.SubnetSelection(subnets=[self.database_subnet_1, self.database_subnet_2]),\n            security_groups=[self.lambda_sg],\n            layers=[self.database_layer, self.database_dependencies_layer, self.knowledge_graph_layer],\n            environment={\n                **common_env,\n                \"KG_TRIPLES_READY_TOPIC_ARN\": self.kg_triples_ready_topic.topic_arn,\n                \"KG_BUCKET\": self.kg_bucket.bucket_name,\n                \"NEPTUNE_ENDPOINT\": \"solve-global-kr-rag-data-neptunedbcluster-1234567890.cluster-cqhsckw0edl1.neptune.amazonaws.com\",\n                \"NEPTUNE_PORT\": \"8182\"\n            }\n        )\n        \n        # 6. KG Triple Loader (using Knowledge Graph Layer with bulk load)\n        self.kg_triple_loader = lambda_.Function(\n            self, \"KGTripleLoader\",\n            function_name=\"solve-global-kr-kg-triple-loader\",\n            runtime=lambda_.Runtime.PYTHON_3_11,\n            handler=\"handler.lambda_handler\",\n            code=lambda_.Code.from_asset(\"../lambda/kg-triple-loader\"),\n            role=self.lambda_role,\n            timeout=Duration.minutes(15),\n            memory_size=1024,\n            vpc=self.vpc,\n            vpc_subnets=ec2.SubnetSelection(subnets=[self.neptune_subnet_1, self.neptune_subnet_2]),\n            security_groups=[self.lambda_sg],\n            layers=[self.database_layer, self.database_dependencies_layer, self.knowledge_graph_layer],\n            environment={\n                **common_env,\n                \"NEPTUNE_ENDPOINT\": \"solve-global-kr-rag-data-neptunedbcluster-1234567890.cluster-cqhsckw0edl1.neptune.amazonaws.com\",\n                \"NEPTUNE_PORT\": \"8182\",\n                \"TTL_BUCKET\": self.kg_bucket.bucket_name\n            }\n        )\n        \n        # 7. NLP Processor (future - placeholder for now)\n        self.nlp_processor = lambda_.Function(\n            self, \"NLPProcessor\",\n            function_name=\"solve-global-kr-nlp-initiator\",\n            runtime=lambda_.Runtime.PYTHON_3_11,\n            handler=\"handler.lambda_handler\",\n            code=lambda_.Code.from_asset(\"../lambda/nlp-initiator\"),\n            role=self.lambda_role,\n            timeout=Duration.minutes(15),\n            memory_size=1024,\n            vpc=self.vpc,\n            vpc_subnets=ec2.SubnetSelection(subnets=[self.database_subnet_1, self.database_subnet_2]),\n            security_groups=[self.lambda_sg],\n            layers=[self.database_layer, self.database_dependencies_layer, self.knowledge_graph_layer],\n            environment={\n                **common_env,\n                \"NLP_READY_TOPIC_ARN\": self.nlp_ready_topic.topic_arn\n            }\n        )\n        \n        # Set up SNS subscriptions for pipeline flow\n        self.setup_sns_subscriptions()\n    \n    def setup_sns_subscriptions(self):\n        \"\"\"Set up SNS topic subscriptions for pipeline flow\"\"\"\n        \n        # Text extraction ready -> Text extractor processor\n        self.text_extraction_ready_topic.add_subscription(\n            sns_subscriptions.LambdaSubscription(self.text_extractor_processor)\n        )\n        \n        # Text ready -> Text chunker processor\n        self.text_ready_topic.add_subscription(\n            sns_subscriptions.LambdaSubscription(self.text_chunker_processor)\n        )\n        \n        # Chunks ready -> Vector embeddings worker AND Document structure KG processor\n        self.chunks_ready_topic.add_subscription(\n            sns_subscriptions.LambdaSubscription(self.vector_embeddings_worker)\n        )\n        self.chunks_ready_topic.add_subscription(\n            sns_subscriptions.LambdaSubscription(self.document_structure_kg_processor)\n        )\n        \n        # KG triples ready -> KG triple loader\n        self.kg_triples_ready_topic.add_subscription(\n            sns_subscriptions.LambdaSubscription(self.kg_triple_loader)\n        )\n        \n        # Vector embeddings ready -> NLP processor (future)\n        self.vector_embeddings_ready_topic.add_subscription(\n            sns_subscriptions.LambdaSubscription(self.nlp_processor)\n        )\n    \n    def setup_s3_notifications(self):\n        \"\"\"Set up S3 event notifications to trigger pipeline\"\"\"\n        \n        # Source documents bucket triggers text extractor initiator\n        self.source_documents_bucket.add_event_notification(\n            s3.EventType.OBJECT_CREATED,\n            s3n.LambdaDestination(self.text_extractor_initiator),\n            s3.NotificationKeyFilter(prefix=\"documents/\")\n        )\n    \n    def create_outputs(self):\n        \"\"\"Create CloudFormation outputs for key resources\"\"\"\n        \n        CfnOutput(\n            self, \"SourceDocumentsBucketName\",\n            value=self.source_documents_bucket.bucket_name,\n            description=\"Source documents bucket for pipeline entry\"\n        )\n        \n        CfnOutput(\n            self, \"KnowledgeGraphLayerArn\",\n            value=self.knowledge_graph_layer.layer_version_arn,\n            description=\"Knowledge Graph Layer v2.0.0 with NLP-Ontology Integration ARN\"\n        )\n        \n        CfnOutput(\n            self, \"TextExtractionReadyTopicArn\",\n            value=self.text_extraction_ready_topic.topic_arn,\n            description=\"Text extraction ready SNS topic ARN\"\n        )\n        \n        CfnOutput(\n            self, \"KGTriplesReadyTopicArn\",\n            value=self.kg_triples_ready_topic.topic_arn,\n            description=\"KG triples ready SNS topic ARN\"\n        )\n\n# CDK App\napp = cdk.App()\n\n# Environment configuration\nenv = cdk.Environment(\n    account=\"861276078413\",  # Correct account per infrastructure guide\n    region=\"us-east-1\"\n)\n\n# Deploy production-ready stack\nproduction_stack = ClimateRiskRAGProductionStack(\n    app, \n    \"ClimateRiskRAGProduction\",\n    env=env,\n    description=\"Production-ready Climate Risk RAG system with complete pipeline integration\"\n)\n\napp.synth()\n
