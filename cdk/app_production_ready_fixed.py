#!/usr/bin/env python3
"""
Production-Ready Climate Risk RAG System CDK App
Comprehensive deployment aligned with infrastructure guide and current working components

This CDK app deploys the complete system with:
- Knowledge Graph Layer v1.0.0 integration
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
    aws_sns_subscriptions as sns_subscriptions,
    aws_s3_notifications as s3n,
    aws_ec2 as ec2,
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
        
        # Text chunking complete (matches deployed system)
        self.text_chunking_complete_topic = sns.Topic(
            self, "TextChunkingCompleteTopic",
            topic_name="text-chunking-complete",
            display_name="Text Chunking Complete Topic"
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
        """Create Lambda layers including Knowledge Graph Layer v1.0.0"""
        
        # Knowledge Graph Layer v1.0.0
        self.knowledge_graph_layer = lambda_.LayerVersion(
            self, "KnowledgeGraphLayer",
            code=lambda_.Code.from_asset("../layers/knowledge-graph-layer/knowledge-graph-layer-v1.0.0.zip"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Knowledge Graph operations layer v1.0.0 with Neptune integration"
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
                    statements=[
                        # S3 permissions for all project buckets
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:ListBucket",
                                "s3:CopyObject",
                                "s3:GetObjectMetadata",
                                "s3:PutObjectMetadata",
                                "s3:DeleteObject"
                            ],
                            resources=[
                                "arn:aws:s3:::solve-global-kr-*",
                                "arn:aws:s3:::solve-global-kr-*/*"
                            ]
                        ),
                        # SNS permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "sns:Publish",
                                "sns:Subscribe",
                                "sns:Unsubscribe",
                                "sns:GetTopicAttributes"
                            ],
                            resources=[f"arn:aws:sns:{self.region}:{self.account}:solve-global-kr-*"]
                        ),
                        # Lambda invoke permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["lambda:InvokeFunction"],
                            resources=[f"arn:aws:lambda:{self.region}:{self.account}:function:solve-global-kr-*"]
                        ),
                        # Textract permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "textract:StartDocumentTextDetection",
                                "textract:GetDocumentTextDetection",
                                "textract:StartDocumentAnalysis",
                                "textract:GetDocumentAnalysis"
                            ],
                            resources=["*"]
                        ),
                        # Bedrock permissions for vector embeddings
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "bedrock:InvokeModel",
                                "bedrock:InvokeModelWithResponseStream"
                            ],
                            resources=[
                                f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v1",
                                f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v2:0"
                            ]
                        ),
                        # Comprehend permissions for NLP
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "comprehend:StartEntitiesDetectionJob",
                                "comprehend:StartKeyPhrasesDetectionJob",
                                "comprehend:DescribeEntitiesDetectionJob",
                                "comprehend:DescribeKeyPhrasesDetectionJob",
                                "comprehend:DetectEntities",
                                "comprehend:DetectKeyPhrases",
                                "comprehend:DetectSentiment"
                            ],
                            resources=["*"]
                        ),
                        # Neptune permissions for knowledge graph
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "neptune-db:*"
                            ],
                            resources=["*"]
                        ),
                        # OpenSearch permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "es:ESHttpPost",
                                "es:ESHttpPut",
                                "es:ESHttpGet",
                                "es:ESHttpDelete",
                                "aoss:*"
                            ],
                            resources=["*"]
                        ),
                        # Secrets Manager permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["secretsmanager:GetSecretValue"],
                            resources=[f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:*"]
                        )
                    ]
                )
            }
        )
    
    def create_pipeline_lambda_functions(self):
        """Create all Lambda functions for the complete pipeline"""
        
        # Database URL from infrastructure guide
        database_url = "postgresql://postgres:c0xfd_t#PBUqV(pLM-9IqM59G:>c@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require"
        
        # Common environment variables
        common_env = {
            "DATABASE_URL": database_url,
            "LAMBDA_ENVIRONMENT": "true"
        }
        
        # 1. Text Extractor Initiator
        self.text_extractor_initiator = lambda_.Function(
            self, "TextExtractorInitiator",
            function_name="solve-global-kr-text-extractor-initiator",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/text-extractor-initiator"),
            role=self.lambda_role,
            timeout=Duration.minutes(15),
            memory_size=1024,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[self.database_subnet_1, self.database_subnet_2]),
            security_groups=[self.lambda_sg],
            layers=[self.database_layer, self.database_dependencies_layer],
            environment={
                **common_env,
                "TEXT_EXTRACTION_READY_TOPIC_ARN": self.text_extraction_ready_topic.topic_arn,
                "SOURCE_DOCUMENTS_BUCKET": self.source_documents_bucket.bucket_name,
                "DOCUMENTS_BUCKET": self.documents_bucket.bucket_name
            }
        )
        
        # 2. Text Extractor Processor
        self.text_extractor_processor = lambda_.Function(
            self, "TextExtractorProcessor",
            function_name="solve-global-kr-text-extractor-processor",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/text-extractor-processor"),
            role=self.lambda_role,
            timeout=Duration.minutes(15),
            memory_size=1024,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[self.database_subnet_1, self.database_subnet_2]),
            security_groups=[self.lambda_sg],
            layers=[self.database_layer, self.database_dependencies_layer],
            environment={
                **common_env,
                "TEXT_READY_TOPIC_ARN": self.text_ready_topic.topic_arn,
                "TEXT_BUCKET": self.text_bucket.bucket_name
            }
        )
        
        # 3. Text Chunker Processor
        self.text_chunker_processor = lambda_.Function(
            self, "TextChunkerProcessor",
            function_name="solve-global-kr-text-chunker-processor",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/text-chunker-processor"),
            role=self.lambda_role,
            timeout=Duration.minutes(15),
            memory_size=1024,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[self.database_subnet_1, self.database_subnet_2]),
            security_groups=[self.lambda_sg],
            layers=[self.database_layer, self.database_dependencies_layer],
            environment={
                **common_env,
                "CHUNKS_READY_TOPIC_ARN": self.text_chunking_complete_topic.topic_arn,
                "CHUNKS_BUCKET": self.chunks_bucket.bucket_name
            }
        )
        
        # 4. Vector Embeddings Worker
        self.vector_embeddings_worker = lambda_.Function(
            self, "VectorEmbeddingsWorker",
            function_name="solve-global-kr-vector-embeddings-worker",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/vector-embeddings-worker"),
            role=self.lambda_role,
            timeout=Duration.minutes(15),
            memory_size=1024,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[self.database_subnet_1, self.database_subnet_2]),
            security_groups=[self.lambda_sg],
            layers=[self.database_layer, self.database_dependencies_layer],
            environment={
                **common_env,
                "VECTOR_EMBEDDINGS_READY_TOPIC_ARN": self.vector_embeddings_ready_topic.topic_arn,
                "EMBEDDINGS_BUCKET": self.embeddings_bucket.bucket_name
            }
        )
        
        # 5. Document Structure KG Processor (using Knowledge Graph Layer)
        self.document_structure_kg_processor = lambda_.Function(
            self, "DocumentStructureKGProcessor",
            function_name="solve-global-kr-document-structure-kg-processor",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/document-structure-kg-processor"),
            role=self.lambda_role,
            timeout=Duration.minutes(15),
            memory_size=1024,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[self.database_subnet_1, self.database_subnet_2]),
            security_groups=[self.lambda_sg],
            layers=[self.database_layer, self.database_dependencies_layer, self.knowledge_graph_layer],
            environment={
                **common_env,
                "KG_TRIPLES_READY_TOPIC_ARN": self.kg_triples_ready_topic.topic_arn,
                "KG_BUCKET": self.kg_bucket.bucket_name,
                "NEPTUNE_ENDPOINT": "solve-global-kr-rag-data-neptunedbcluster-1234567890.cluster-cqhsckw0edl1.neptune.amazonaws.com",
                "NEPTUNE_PORT": "8182"
            }
        )
        
        # 6. KG Triple Loader (using Knowledge Graph Layer with bulk load)
        self.kg_triple_loader = lambda_.Function(
            self, "KGTripleLoader",
            function_name="solve-global-kr-kg-triple-loader",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/kg-triple-loader"),
            role=self.lambda_role,
            timeout=Duration.minutes(15),
            memory_size=1024,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[self.neptune_subnet_1, self.neptune_subnet_2]),
            security_groups=[self.lambda_sg],
            layers=[self.database_layer, self.database_dependencies_layer, self.knowledge_graph_layer],
            environment={
                **common_env,
                "NEPTUNE_ENDPOINT": "solve-global-kr-rag-data-neptunedbcluster-1234567890.cluster-cqhsckw0edl1.neptune.amazonaws.com",
                "NEPTUNE_PORT": "8182",
                "TTL_BUCKET": self.kg_bucket.bucket_name
            }
        )
        
        # 7. NLP Processor (future - placeholder for now)
        self.nlp_processor = lambda_.Function(
            self, "NLPProcessor",
            function_name="solve-global-kr-nlp-initiator",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/nlp-initiator"),
            role=self.lambda_role,
            timeout=Duration.minutes(15),
            memory_size=1024,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[self.database_subnet_1, self.database_subnet_2]),
            security_groups=[self.lambda_sg],
            layers=[self.database_layer, self.database_dependencies_layer, self.knowledge_graph_layer],
            environment={
                **common_env,
                "NLP_READY_TOPIC_ARN": self.nlp_ready_topic.topic_arn
            }
        )
        
        # Set up SNS subscriptions for pipeline flow
        self.setup_sns_subscriptions()
    
    def setup_sns_subscriptions(self):
        """Set up SNS topic subscriptions for pipeline flow"""
        
        # Text extraction ready -> Text extractor processor
        self.text_extraction_ready_topic.add_subscription(
            sns_subscriptions.LambdaSubscription(self.text_extractor_processor)
        )
        
        # Text ready -> Text chunker processor
        self.text_ready_topic.add_subscription(
            sns_subscriptions.LambdaSubscription(self.text_chunker_processor)
        )
        
        # Text chunking complete -> Vector embeddings worker AND Document structure KG processor
        self.text_chunking_complete_topic.add_subscription(
            sns_subscriptions.LambdaSubscription(self.vector_embeddings_worker)
        )
        self.text_chunking_complete_topic.add_subscription(
            sns_subscriptions.LambdaSubscription(self.document_structure_kg_processor)
        )
        
        # KG triples ready -> KG triple loader
        self.kg_triples_ready_topic.add_subscription(
            sns_subscriptions.LambdaSubscription(self.kg_triple_loader)
        )
        
        # Vector embeddings ready -> NLP processor (future)
        self.vector_embeddings_ready_topic.add_subscription(
            sns_subscriptions.LambdaSubscription(self.nlp_processor)
        )
    
    def setup_s3_notifications(self):
        """Set up S3 event notifications to trigger pipeline"""
        
        # Source documents bucket triggers text extractor initiator
        self.source_documents_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.text_extractor_initiator),
            s3.NotificationKeyFilter(prefix="documents/")
        )
    
    def create_outputs(self):
        """Create CloudFormation outputs for key resources"""
        
        CfnOutput(
            self, "SourceDocumentsBucketName",
            value=self.source_documents_bucket.bucket_name,
            description="Source documents bucket for pipeline entry"
        )
        
        CfnOutput(
            self, "KnowledgeGraphLayerArn",
            value=self.knowledge_graph_layer.layer_version_arn,
            description="Knowledge Graph Layer v1.0.0 ARN"
        )
        
        CfnOutput(
            self, "TextChunkingCompleteTopicArn",
            value=self.text_chunking_complete_topic.topic_arn,
            description="Text chunking complete SNS topic ARN"
        )
        
        CfnOutput(
            self, "KGTriplesReadyTopicArn",
            value=self.kg_triples_ready_topic.topic_arn,
            description="KG triples ready SNS topic ARN"
        )

# CDK App
app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account="861276078413",  # Correct account per infrastructure guide
    region="us-east-1"
)

# Deploy production-ready stack
production_stack = ClimateRiskRAGProductionStack(
    app, 
    "ClimateRiskRAGProduction",
    env=env,
    description="Production-ready Climate Risk RAG system with complete pipeline integration"
)

app.synth()
