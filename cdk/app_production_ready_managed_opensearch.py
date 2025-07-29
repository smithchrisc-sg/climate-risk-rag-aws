#!/usr/bin/env python3
"""
Production-Ready Climate Risk RAG System CDK App - AWS Managed OpenSearch Version
Comprehensive deployment with AWS Managed OpenSearch instead of serverless

This CDK app deploys the complete system with:
- AWS Managed OpenSearch Domain (cost-optimized)
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
    aws_sqs as sqs,
    aws_sns_subscriptions as sns_subscriptions,
    aws_s3_notifications as s3n,
    aws_lambda_event_sources as lambda_event_sources,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_opensearchservice as opensearch,  # Fixed import name
    aws_neptune as neptune,
    aws_secretsmanager as secretsmanager,
    Duration,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct

class ClimateRiskRAGProductionManagedOpenSearchStack(Stack):
    """Production-ready Climate Risk RAG system with AWS Managed OpenSearch"""
    
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
            description="Security group for Lambda functions with database, Neptune, and OpenSearch access",
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
        
        # Create IAM roles (must be before OpenSearch domain)
        self.create_iam_roles()
        
        # Create AWS Managed OpenSearch domain
        self.create_opensearch_domain()
        
        # Create Lambda functions for complete pipeline
        self.create_pipeline_lambda_functions()
        
        # Set up S3 event notifications
        self.setup_s3_notifications()
        
        # Create outputs
        self.create_outputs()
    
    def create_opensearch_domain(self):
        """Create AWS Managed OpenSearch domain for vector and keyword search"""
        
        # Create security group for OpenSearch domain
        self.opensearch_sg = ec2.SecurityGroup(
            self, "OpenSearchSecurityGroup",
            vpc=self.vpc,
            description="Security group for AWS Managed OpenSearch domain",
            allow_all_outbound=False
        )
        
        # Allow HTTPS access from Lambda security group
        self.opensearch_sg.add_ingress_rule(
            peer=self.lambda_sg,
            connection=ec2.Port.tcp(443),
            description="HTTPS access from Lambda functions"
        )
        
        # Add egress rule to Lambda SG for OpenSearch access
        self.lambda_sg.add_egress_rule(
            peer=self.opensearch_sg,
            connection=ec2.Port.tcp(443),
            description="Allow Lambda to connect to OpenSearch"
        )
        
        # Create master user password secret
        self.opensearch_master_secret = secretsmanager.Secret(
            self, "OpenSearchMasterPassword",
            description="OpenSearch master user password",
            secret_name="solve-global-kr-opensearch-master-password",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/\"\\",
                include_space=False,
                password_length=32
            )
        )
        
        # OpenSearch domain configuration - single node for cost optimization
        # For production scaling, increase data_nodes and enable multi-AZ
        
        # Use CfnDomain for explicit control over zone awareness
        self.opensearch_domain = opensearch.CfnDomain(
            self, "OpenSearchDomain",
            domain_name="solve-global-kr-search",
            engine_version="OpenSearch_2.7",
            
            # Cluster configuration with zone awareness properly configured for VPC
            cluster_config={
                "InstanceType": "m6g.large.search",
                "InstanceCount": 2,  # Minimum 2 nodes for zone awareness
                "DedicatedMasterEnabled": False,
                "ZoneAwarenessEnabled": True,  # Required for VPC
                "ZoneAwarenessConfig": {
                    "AvailabilityZoneCount": 2  # Required when ZoneAwarenessEnabled=True
                }
            },
            
            # EBS configuration (complete format required for m6g instance types)
            ebs_options={
                "EBSEnabled": True,
                "VolumeType": "gp3",
                "VolumeSize": 20,
                "Iops": 3000,
                "Throughput": 125
            },
            
            # VPC configuration - use both subnets for zone awareness
            vpc_options={
                "SubnetIds": [self.database_subnet_1.subnet_id, self.database_subnet_2.subnet_id],
                "SecurityGroupIds": [self.opensearch_sg.security_group_id]
            },
            
            # Advanced security options
            advanced_security_options={
                "Enabled": True,
                "InternalUserDatabaseEnabled": True,
                "MasterUserOptions": {
                    "MasterUserName": "admin",
                    "MasterUserPassword": self.opensearch_master_secret.secret_value.unsafe_unwrap()
                }
            },
            
            # Encryption settings
            encryption_at_rest_options={
                "Enabled": True
            },
            node_to_node_encryption_options={
                "Enabled": True
            },
            domain_endpoint_options={
                "EnforceHTTPS": True
            },
            
            # Logging configuration
            log_publishing_options={
                "ES_APPLICATION_LOGS": {
                    "CloudWatchLogsLogGroupArn": f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/opensearch/domains/solve-global-kr-search/application-logs",
                    "Enabled": True
                }
            },
            
            # Automated snapshots
            snapshot_options={
                "AutomatedSnapshotStartHour": 2
            }
        )
        
        # Output the domain information (CfnDomain uses different attributes)
        CfnOutput(
            self, "OpenSearchDomainEndpoint",
            value=f"https://{self.opensearch_domain.attr_domain_endpoint}",
            description="OpenSearch domain endpoint"
        )
        
        CfnOutput(
            self, "OpenSearchDomainArn",
            value=self.opensearch_domain.attr_arn,
            description="OpenSearch domain ARN"
        )
        
        CfnOutput(
            self, "OpenSearchMasterSecretArn",
            value=self.opensearch_master_secret.secret_arn,
            description="OpenSearch master password secret ARN"
        )
    def create_s3_buckets(self):
        """Import existing S3 buckets instead of creating new ones"""
        
        # Import existing source documents bucket
        self.source_documents_bucket = s3.Bucket.from_bucket_name(
            self, "SourceDocumentsBucket",
            bucket_name=f"solve-global-kr-dl-source-documents-{self.account}-{self.region}"
        )
        
        # Import existing processed documents bucket
        self.documents_bucket = s3.Bucket.from_bucket_name(
            self, "DocumentsBucket",
            bucket_name=f"solve-global-kr-documents-{self.account}-{self.region}"
        )
        
        # Import existing text extraction results bucket
        self.text_bucket = s3.Bucket.from_bucket_name(
            self, "TextBucket",
            bucket_name=f"solve-global-kr-dl-text-{self.account}-{self.region}"
        )
        
        # Import existing text chunks bucket
        self.chunks_bucket = s3.Bucket.from_bucket_name(
            self, "ChunksBucket",
            bucket_name=f"solve-global-kr-dl-chunks-{self.account}-{self.region}"
        )
        
        # Import existing vector embeddings bucket
        self.embeddings_bucket = s3.Bucket.from_bucket_name(
            self, "EmbeddingsBucket",
            bucket_name=f"solve-global-kr-embeddings-{self.account}-{self.region}"
        )
        
        # Import existing knowledge graph TTL files bucket
        self.kg_bucket = s3.Bucket.from_bucket_name(
            self, "KnowledgeGraphBucket",
            bucket_name=f"solve-global-kr-kg-data-{self.account}-{self.region}"
        )
        
        # Import existing cache and metadata bucket
        self.cache_bucket = s3.Bucket.from_bucket_name(
            self, "CacheBucket",
            bucket_name=f"solve-global-kr-cache-{self.account}-{self.region}"
        )
    
    def create_sns_topics(self):
        """Import existing SNS topics instead of creating new ones"""
        
        # Import existing text extraction ready topic
        self.text_extraction_ready_topic = sns.Topic.from_topic_arn(
            self, "TextExtractionReadyTopic",
            topic_arn="arn:aws:sns:us-east-1:861276078413:text-extraction-complete"
        )
        
        # Import existing text ready topic
        self.text_ready_topic = sns.Topic.from_topic_arn(
            self, "TextReadyTopic",
            topic_arn="arn:aws:sns:us-east-1:861276078413:text-chunking-complete"
        )
        
        # Import existing chunks ready topic
        self.chunks_ready_topic = sns.Topic.from_topic_arn(
            self, "ChunksReadyTopic",
            topic_arn="arn:aws:sns:us-east-1:861276078413:chunks-ready"
        )
        
        # Import existing vector embeddings ready topic
        self.vector_embeddings_ready_topic = sns.Topic.from_topic_arn(
            self, "VectorEmbeddingsReadyTopic",
            topic_arn="arn:aws:sns:us-east-1:861276078413:vector-embeddings-complete"
        )
        
        # Import existing KG triples ready topic
        self.kg_triples_ready_topic = sns.Topic.from_topic_arn(
            self, "KGTriplesReadyTopic",
            topic_arn="arn:aws:sns:us-east-1:861276078413:kg-triples-ready"
        )
        
        # Import existing NLP ready topic
        self.nlp_ready_topic = sns.Topic.from_topic_arn(
            self, "NLPReadyTopic",
            topic_arn="arn:aws:sns:us-east-1:861276078413:nlp-processing-complete"
        )
    
    def create_lambda_layers(self):
        """Create Lambda layers for shared dependencies"""
        
        # Database Core Layer (existing - from infrastructure guide)
        self.database_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "DatabaseCoreLayer",
            layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:database-core-layer:16"
        )
        
        # Knowledge Graph Layer (existing - from infrastructure guide)
        self.knowledge_graph_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "KnowledgeGraphLayer",
            layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:knowledge-graph-layer:6"
        )
        
        # Database Dependencies Layer (existing)
        self.database_dependencies_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "DatabaseDependenciesLayer",
            layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:database-dependencies:2"
        )
    def create_iam_roles(self):
        """Create standardized IAM roles per infrastructure guide with OpenSearch permissions"""
        
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
                        # AWS Managed OpenSearch permissions (updated from serverless)
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "es:ESHttpPost",
                                "es:ESHttpPut",
                                "es:ESHttpGet",
                                "es:ESHttpDelete",
                                "es:ESHttpHead",
                                "es:DescribeDomain",
                                "es:DescribeDomains",
                                "es:ListDomainNames"
                            ],
                            resources=[
                                f"arn:aws:es:{self.region}:{self.account}:domain/solve-global-kr-search/*",
                                f"arn:aws:es:{self.region}:{self.account}:domain/solve-global-kr-search"
                            ]
                        ),
                        # Secrets Manager permissions (including OpenSearch master password)
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
        """Create all Lambda functions for the complete pipeline with OpenSearch integration"""
        
        # Database URL from infrastructure guide
        database_url = "postgresql://postgres:c0xfd_t#PBUqV(pLM-9IqM59G:>c@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require"
        
        # Common environment variables including OpenSearch
        common_env = {
            "DATABASE_URL": database_url,
            "LAMBDA_ENVIRONMENT": "true",
            "OPENSEARCH_ENDPOINT": self.opensearch_domain.attr_domain_endpoint,
            "OPENSEARCH_MASTER_SECRET_ARN": self.opensearch_master_secret.secret_arn
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
                "CHUNKS_READY_TOPIC_ARN": self.chunks_ready_topic.topic_arn,
                "CHUNKS_BUCKET": self.chunks_bucket.bucket_name
            }
        )
        
        # 4. Vector Embeddings Worker (with OpenSearch integration)
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
        
        # 5. Keyword Indexer (with OpenSearch integration)
        self.keyword_indexer_worker = lambda_.Function(
            self, "KeywordIndexerWorker",
            function_name="solve-global-kr-keyword-indexer-worker",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/keyword-indexer"),  # Fixed path
            role=self.lambda_role,
            timeout=Duration.minutes(15),
            memory_size=1024,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[self.database_subnet_1, self.database_subnet_2]),
            security_groups=[self.lambda_sg],
            layers=[self.database_layer, self.database_dependencies_layer],
            environment={
                **common_env,
                "KEYWORD_INDEXING_READY_TOPIC_ARN": self.chunks_ready_topic.topic_arn  # Reuse chunks ready
            }
        )
        
        # 6. Document Structure KG Processor (using Knowledge Graph Layer)
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
                "NEPTUNE_ENDPOINT": "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com",
                "NEPTUNE_PORT": "8182"
            }
        )
        
        # 7. KG Triple Loader (using Knowledge Graph Layer with bulk load)
        self.kg_triple_loader = lambda_.Function(
            self, "KGTripleLoader",
            function_name="kg-triple-loader",  # Keep existing name for compatibility
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/kg-triple-loader"),
            role=self.lambda_role,
            timeout=Duration.minutes(15),
            memory_size=1024,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[self.neptune_subnet_1, self.neptune_subnet_2]),
            security_groups=[self.lambda_sg],
            layers=[self.database_layer, self.knowledge_graph_layer],
            environment={
                "DATABASE_SECRET_NAME": "rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863",
                "DB_PORT": "5432",
                "NEPTUNE_ENDPOINT": "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com",
                "TTL_BUCKET": "solve-global-kr-dl-neptune-ttl-861276078413-us-east-1",
                "DB_NAME": "climate_risk_rag",
                "NEPTUNE_PORT": "8182",
                "DB_HOST": "solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com"
            }
        )
        
        # 8. NLP Processor (future - placeholder for now)
        self.nlp_processor = lambda_.Function(
            self, "NLPProcessor",
            function_name="solve-global-kr-nlp-processor",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/nlp-processor"),
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
        """SNS subscriptions already configured in existing infrastructure"""
        # Skip SNS subscriptions setup since we're importing existing topics
        # and don't want to modify their existing subscription configurations
        pass
    
    def setup_s3_notifications(self):
        """S3 notifications already configured in existing infrastructure"""
        # Skip S3 notifications setup since we're importing existing buckets
        # and don't want to modify their existing notification configurations
        pass
    
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
            self, "TextExtractionReadyTopicArn",
            value=self.text_extraction_ready_topic.topic_arn,
            description="Text extraction ready SNS topic ARN"
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

# Deploy production-ready stack with AWS Managed OpenSearch
production_stack = ClimateRiskRAGProductionManagedOpenSearchStack(
    app, 
    "ClimateRiskRAGProductionManagedOpenSearch",
    env=env,
    description="Production-ready Climate Risk RAG system with AWS Managed OpenSearch (cost-optimized)"
)

app.synth()
