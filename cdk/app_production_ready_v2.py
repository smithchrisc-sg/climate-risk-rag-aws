#!/usr/bin/env python3
"""
Production-Ready Climate Risk RAG System with Knowledge Graph Layer v2.0.0
Updated to use NLP-Ontology Integration while maintaining backward compatibility
"""

import aws_cdk as cdk
from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_sns as sns,
    aws_sqs as sqs,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_rds as rds,
    aws_opensearch as opensearch,
    aws_neptune as neptune,
    CfnOutput
)
from constructs import Construct

class ClimateRiskRAGStackV2(Stack):
    """
    Production-ready Climate Risk RAG System with Knowledge Graph Layer v2.0.0
    Maintains backward compatibility while adding NLP-Ontology integration
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # === INFRASTRUCTURE SETUP (UNCHANGED) ===
        self._setup_vpc_and_networking()
        self._setup_s3_buckets()
        self._setup_sns_topics()
        self._setup_sqs_queues()
        self._setup_iam_roles()
        self._setup_database()
        self._setup_opensearch()
        self._setup_neptune()
        
        # === LAMBDA LAYERS (UPDATED TO v2.0.0) ===
        self._setup_lambda_layers_v2()
        
        # === LAMBDA FUNCTIONS (UPDATED AND NEW) ===
        self._setup_existing_lambda_functions_v2()
        self._setup_new_nlp_lambda_functions()
        
        # === ADMIN UTILITY FUNCTIONS ===
        self._setup_admin_utility_functions()
        
        # === EVENT SUBSCRIPTIONS (UPDATED) ===
        self._setup_event_subscriptions_v2()
        
        # === OUTPUTS (UPDATED) ===
        self._setup_outputs_v2()

    def _setup_vpc_and_networking(self):
        """Setup VPC and networking (unchanged from v1)"""
        # Use existing VPC configuration
        self.vpc = ec2.Vpc.from_lookup(self, "ExistingVPC", vpc_id="vpc-0123456789abcdef0")
        
        # Existing subnets
        self.database_subnet_1 = ec2.Subnet.from_subnet_id(self, "DatabaseSubnet1", subnet_id="subnet-0e9efc5fdf29e9da0")
        self.database_subnet_2 = ec2.Subnet.from_subnet_id(self, "DatabaseSubnet2", subnet_id="subnet-00efdcc220a613ae3")
        self.neptune_subnet_1 = ec2.Subnet.from_subnet_id(self, "NeptuneSubnet1", subnet_id="subnet-0a1b2c3d4e5f6g7h8")
        self.neptune_subnet_2 = ec2.Subnet.from_subnet_id(self, "NeptuneSubnet2", subnet_id="subnet-0h8g6f5e4d3c2b1a0")
        
        # Existing security group
        self.lambda_sg = ec2.SecurityGroup.from_security_group_id(self, "LambdaSG", security_group_id="sg-0123456789abcdef0")

    def _setup_s3_buckets(self):
        """Setup S3 buckets (unchanged from v1)"""
        # Existing buckets
        self.text_bucket = s3.Bucket.from_bucket_name(self, "TextBucket", "solve-global-kr-text-861276078413-us-east-1")
        self.chunks_bucket = s3.Bucket.from_bucket_name(self, "ChunksBucket", "solve-global-kr-chunks-861276078413-us-east-1")
        self.ner_results_bucket = s3.Bucket.from_bucket_name(self, "NERResultsBucket", "solve-global-kr-dl-ner-results-861276078413-us-east-1")
        self.kg_bucket = s3.Bucket.from_bucket_name(self, "KGBucket", "solve-global-kr-dl-kg-861276078413-us-east-1")
        self.ontology_bucket = s3.Bucket.from_bucket_name(self, "OntologyBucket", "solve-global-kr-dl-ontology-861276078413-us-east-1")

    def _setup_sns_topics(self):
        """Setup SNS topics (unchanged from v1)"""
        # Existing topics
        self.text_ready_topic = sns.Topic.from_topic_arn(self, "TextReadyTopic", "arn:aws:sns:us-east-1:861276078413:text-ready")
        self.chunks_ready_topic = sns.Topic.from_topic_arn(self, "ChunksReadyTopic", "arn:aws:sns:us-east-1:861276078413:chunks-ready")
        self.nlp_ready_topic = sns.Topic.from_topic_arn(self, "NLPReadyTopic", "arn:aws:sns:us-east-1:861276078413:nlp-processing-complete")
        self.kg_triples_ready_topic = sns.Topic.from_topic_arn(self, "KGTriplesReadyTopic", "arn:aws:sns:us-east-1:861276078413:kg-triples-ready")

    def _setup_sqs_queues(self):
        """Setup SQS queues (unchanged from v1)"""
        # Existing queues - reference by ARN
        pass

    def _setup_iam_roles(self):
        """Setup IAM roles (unchanged from v1)"""
        # Use existing Lambda execution role
        self.lambda_role = iam.Role.from_role_arn(self, "LambdaRole", "arn:aws:iam::861276078413:role/solve-global-kr-lambda-execution-role")

    def _setup_database(self):
        """Setup PostgreSQL database (unchanged from v1)"""
        # Reference existing database
        pass

    def _setup_opensearch(self):
        """Setup OpenSearch (unchanged from v1)"""
        # Reference existing OpenSearch cluster
        pass

    def _setup_neptune(self):
        """Setup Neptune (unchanged from v1)"""
        # Reference existing Neptune cluster
        self.neptune_endpoint = "solve-global-kr-rag-data-neptunedbcluster-1234567890.cluster-cqhsckw0edl1.neptune.amazonaws.com"

    def _setup_lambda_layers_v2(self):
        """Setup Lambda layers with v2.0.0 Knowledge Graph Layer"""
        
        # Existing layers (unchanged)
        self.database_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "DatabaseLayer",
            layer_version_arn="arn:aws:lambda:us-east-1:861276078413:layer:database-core-layer:16"
        )
        
        self.database_dependencies_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "DatabaseDependenciesLayer", 
            layer_version_arn="arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies:2"
        )
        
        # UPDATED: Knowledge Graph Layer v2.0.0 with NLP-Ontology Integration
        # Updated to Knowledge Graph Layer v2.0.0 - Maintains backward compatibility

        self.knowledge_graph_layer = lambda_.LayerVersion(
            self, "KnowledgeGraphLayerV2",
            code=lambda_.Code.from_asset("../layers/knowledge-graph-layer/knowledge-graph-layer-v2.0.0-minimal.zip"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Knowledge Graph Layer v2.0.0 with NLP-Ontology Integration - Backward Compatible",
            layer_version_name="knowledge-graph-layer-v2"
        )

    def _setup_existing_lambda_functions_v2(self):
        """Setup existing Lambda functions with updated layer"""
        
        # Common environment variables
        common_env = {
            "DATABASE_HOST": "solve-global-kr-rag-data-cluster.cluster-cqhsckw0edl1.rds.amazonaws.com",
            "DATABASE_NAME": "climate_risk_rag",
            "DATABASE_USER": "postgres",
            "DATABASE_PASSWORD_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:861276078413:secret:rds-db-credentials/cluster-ABCDEFGHIJKLMNOP/postgres-AbCdEf",
            "TEXT_BUCKET": self.text_bucket.bucket_name,
            "CHUNKS_BUCKET": self.chunks_bucket.bucket_name,
            "NER_RESULTS_BUCKET": self.ner_results_bucket.bucket_name,
            "KG_BUCKET": self.kg_bucket.bucket_name,
            "ONTOLOGY_BUCKET": self.ontology_bucket.bucket_name
        }
        
        # Common layers for existing functions
        common_layers = [self.database_layer, self.database_dependencies_layer, self.knowledge_graph_layer]
        
        # 1. UPDATED: Document Structure KG Processor (now uses v2.0.0 layer)
        self.document_structure_kg_processor = lambda_.Function(
            self, "DocumentStructureKGProcessor",
            function_name="solve-global-kr-document-structure-kg-processor-v2",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/document-structure-kg-processor"),
            role=self.lambda_role,
            timeout=Duration.minutes(15),
            memory_size=1024,  # Same as before - backward compatible
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[self.database_subnet_1, self.database_subnet_2]),
            security_groups=[self.lambda_sg],
            layers=common_layers,  # Now includes v2.0.0 layer
            environment={
                **common_env,
                "KG_TRIPLES_READY_TOPIC_ARN": self.kg_triples_ready_topic.topic_arn,
                "NEPTUNE_ENDPOINT": self.neptune_endpoint,
                "NEPTUNE_PORT": "8182"
            }
        )
        
        # 2. UPDATED: KG Triple Loader (now uses v2.0.0 layer)
        self.kg_triple_loader = lambda_.Function(
            self, "KGTripleLoader",
            function_name="solve-global-kr-kg-triple-loader-v2",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/kg-triple-loader"),
            role=self.lambda_role,
            timeout=Duration.minutes(15),
            memory_size=1024,  # Same as before
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[self.neptune_subnet_1, self.neptune_subnet_2]),
            security_groups=[self.lambda_sg],
            layers=common_layers,  # Now includes v2.0.0 layer
            environment={
                **common_env,
                "NEPTUNE_ENDPOINT": self.neptune_endpoint,
                "NEPTUNE_PORT": "8182",
                "TTL_BUCKET": self.kg_bucket.bucket_name
            }
        )

    def _setup_new_nlp_lambda_functions(self):
        """Setup new NLP Lambda functions using v2.0.0 layer"""
        
        # Common environment for NLP functions
        nlp_common_env = {
            "DATABASE_HOST": "solve-global-kr-rag-data-cluster.cluster-cqhsckw0edl1.rds.amazonaws.com",
            "DATABASE_NAME": "climate_risk_rag",
            "DATABASE_USER": "postgres", 
            "DATABASE_PASSWORD_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:861276078413:secret:rds-db-credentials/cluster-ABCDEFGHIJKLMNOP/postgres-AbCdEf",
            "TEXT_BUCKET": self.text_bucket.bucket_name,
            "CHUNKS_BUCKET": self.chunks_bucket.bucket_name,
            "NER_RESULTS_BUCKET": self.ner_results_bucket.bucket_name,
            "KG_BUCKET": self.kg_bucket.bucket_name,
            "ONTOLOGY_BUCKET": self.ontology_bucket.bucket_name,
            "NEPTUNE_ENDPOINT": self.neptune_endpoint,
            "NEPTUNE_PORT": "8182"
        }
        
        # Common layers for NLP functions (includes v2.0.0 with NLP utilities)
        nlp_layers = [self.database_layer, self.database_dependencies_layer, self.knowledge_graph_layer]
        
        # 1. NEW: NLP Entity-Ontology Mapper
        self.nlp_entity_ontology_mapper = lambda_.Function(
            self, "NLPEntityOntologyMapper",
            function_name="solve-global-kr-nlp-entity-ontology-mapper",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/nlp-entity-ontology-mapper"),
            role=self.lambda_role,
            timeout=Duration.minutes(10),
            memory_size=1024,  # Increased for NLP processing
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[self.database_subnet_1, self.database_subnet_2]),
            security_groups=[self.lambda_sg],
            layers=nlp_layers,
            environment={
                **nlp_common_env,
                "MIN_CONFIDENCE_THRESHOLD": "0.6",
                "MAX_CANDIDATES": "5",
                "ENABLE_CACHING": "true"
            }
        )
        
        # 2. NEW: NLP Ontology Term Finder
        self.nlp_ontology_term_finder = lambda_.Function(
            self, "NLPOntologyTermFinder",
            function_name="solve-global-kr-nlp-ontology-term-finder",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/nlp-ontology-term-finder"),
            role=self.lambda_role,
            timeout=Duration.minutes(10),
            memory_size=1024,  # Increased for pattern matching
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[self.database_subnet_1, self.database_subnet_2]),
            security_groups=[self.lambda_sg],
            layers=nlp_layers,
            environment={
                **nlp_common_env,
                "MIN_CONFIDENCE_THRESHOLD": "0.7",
                "MIN_TERM_LENGTH": "3",
                "MAX_TERM_DISTANCE": "100",
                "ENABLE_FUZZY_BOUNDARIES": "true"
            }
        )
        
        # 3. NEW: NLP Concept Reconciler
        self.nlp_concept_reconciler = lambda_.Function(
            self, "NLPConceptReconciler",
            function_name="solve-global-kr-nlp-concept-reconciler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/nlp-concept-reconciler"),
            role=self.lambda_role,
            timeout=Duration.minutes(5),
            memory_size=512,  # Lower memory for reconciliation logic
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[self.database_subnet_1, self.database_subnet_2]),
            security_groups=[self.lambda_sg],
            layers=nlp_layers,
            environment={
                **nlp_common_env,
                "RECONCILIATION_STRATEGY": "confidence_weighted",
                "CONFLICT_RESOLUTION": "highest_confidence",
                "MIN_CONFIDENCE_THRESHOLD": "0.6"
            }
        )
        
        # 4. NEW: NLP-KG Integrator
        self.nlp_kg_integrator = lambda_.Function(
            self, "NLPKGIntegrator",
            function_name="solve-global-kr-nlp-kg-integrator",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/nlp-kg-integrator"),
            role=self.lambda_role,
            timeout=Duration.minutes(10),
            memory_size=1024,  # Increased for RDF processing
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[self.neptune_subnet_1, self.neptune_subnet_2]),
            security_groups=[self.lambda_sg],
            layers=nlp_layers,
            environment={
                **nlp_common_env,
                "ENABLE_VALIDATION": "true",
                "S3_BUCKET": self.kg_bucket.bucket_name
            }
        )

    def _setup_admin_utility_functions(self):
        """Setup administrative utility Lambda functions"""
        
        # Common environment for admin functions
        admin_common_env = {
            "DATABASE_HOST": "solve-global-kr-rag-data-cluster.cluster-cqhsckw0edl1.rds.amazonaws.com",
            "DATABASE_NAME": "climate_risk_rag",
            "DATABASE_USER": "postgres", 
            "DATABASE_PASSWORD_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:861276078413:secret:rds-db-credentials/cluster-ABCDEFGHIJKLMNOP/postgres-AbCdEf",
            "TEXT_BUCKET": self.text_bucket.bucket_name,
            "CHUNKS_BUCKET": self.chunks_bucket.bucket_name,
            "NER_RESULTS_BUCKET": self.ner_results_bucket.bucket_name,
            "KG_BUCKET": self.kg_bucket.bucket_name,
            "ONTOLOGY_BUCKET": self.ontology_bucket.bucket_name,
            "NEPTUNE_ENDPOINT": self.neptune_endpoint,
            "NEPTUNE_PORT": "8182"
        }
        
        # Common layers for admin functions (includes v2.0.0 with ontology management)
        admin_layers = [self.database_layer, self.database_dependencies_layer, self.knowledge_graph_layer]
        
        # ADMIN: Ontology Manager - Administrative utility for ontology operations
        self.admin_ontology_manager = lambda_.Function(
            self, "AdminOntologyManager",
            function_name="solve-global-kr-admin-ontology-manager",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/admin_ontology_manager"),
            role=self.lambda_role,
            timeout=Duration.minutes(15),  # Longer timeout for ontology operations
            memory_size=1024,  # Sufficient for RDFLib operations
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[self.database_subnet_1, self.database_subnet_2]),
            security_groups=[self.lambda_sg],
            layers=admin_layers,
            environment={
                **admin_common_env,
                "LOG_LEVEL": "INFO",
                "ENABLE_DEBUG_LOGGING": "false"
            },
            description="Administrative utility for ontology management operations including loading, validation, and querying"
        )

    def _setup_event_subscriptions_v2(self):
        """Setup event subscriptions for updated and new functions"""
        
        # Existing subscriptions (updated function references)
        self.chunks_ready_topic.add_subscription(
            sns.LambdaSubscription(self.document_structure_kg_processor)
        )
        
        self.kg_triples_ready_topic.add_subscription(
            sns.LambdaSubscription(self.kg_triple_loader)
        )
        
        # NEW: NLP processing subscriptions
        self.nlp_ready_topic.add_subscription(
            sns.LambdaSubscription(self.nlp_entity_ontology_mapper)
        )
        
        self.nlp_ready_topic.add_subscription(
            sns.LambdaSubscription(self.nlp_ontology_term_finder)
        )

    def _setup_outputs_v2(self):
        """Setup CDK outputs for v2.0.0 resources"""
        
        # UPDATED: Layer output
        CfnOutput(
            self, "KnowledgeGraphLayerV2Arn",
            value=self.knowledge_graph_layer.layer_version_arn,
            description="Knowledge Graph Layer v2.0.0 ARN with NLP-Ontology Integration"
        )
        
        # UPDATED: Existing function outputs
        CfnOutput(
            self, "DocumentStructureKGProcessorV2Arn",
            value=self.document_structure_kg_processor.function_arn,
            description="Document Structure KG Processor v2 Function ARN (uses v2.0.0 layer)"
        )
        
        CfnOutput(
            self, "KGTripleLoaderV2Arn",
            value=self.kg_triple_loader.function_arn,
            description="KG Triple Loader v2 Function ARN (uses v2.0.0 layer)"
        )
        
        # NEW: NLP function outputs
        CfnOutput(
            self, "NLPEntityOntologyMapperArn",
            value=self.nlp_entity_ontology_mapper.function_arn,
            description="NLP Entity-Ontology Mapper Function ARN"
        )
        
        CfnOutput(
            self, "NLPOntologyTermFinderArn",
            value=self.nlp_ontology_term_finder.function_arn,
            description="NLP Ontology Term Finder Function ARN"
        )
        
        CfnOutput(
            self, "NLPConceptReconcilerArn",
            value=self.nlp_concept_reconciler.function_arn,
            description="NLP Concept Reconciler Function ARN"
        )
        
        CfnOutput(
            self, "NLPKGIntegratorArn",
            value=self.nlp_kg_integrator.function_arn,
            description="NLP-KG Integrator Function ARN"
        )
        
        # ADMIN: Administrative utility function outputs
        CfnOutput(
            self, "AdminOntologyManagerArn",
            value=self.admin_ontology_manager.function_arn,
            description="Admin Ontology Manager Function ARN - Administrative utility for ontology operations"
        )

# CDK App
app = cdk.App()
ClimateRiskRAGStackV2(app, "ClimateRiskRAGStackV2", 
    env=cdk.Environment(
        account="861276078413",
        region="us-east-1"
    )
)

app.synth()
