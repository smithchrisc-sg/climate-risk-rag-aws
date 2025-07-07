"""
Microservices Compute Stack for Climate Risk RAG System
Creates individual Lambda functions for each processing stage with proper event triggers
"""

import json
from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_events as events,
    aws_events_targets as targets,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_logs as logs,
    Duration,
    CfnOutput,
    Tags
)
from constructs import Construct


class MicroservicesComputeStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
                 vpc: ec2.Vpc, bucket_names, data_resources, ai_ml_resources, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.vpc = vpc
        self.bucket_names = bucket_names
        self.data_resources = data_resources
        self.ai_ml_resources = ai_ml_resources

        # Create shared Lambda layer for common dependencies
        self.shared_layer = lambda_.LayerVersion(
            self, "SharedLayer",
            code=lambda_.Code.from_asset("../lambda/shared_layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_9],
            description="Shared dependencies for Climate Risk RAG microservices"
        )
        
        # Create all Lambda functions first
        self._create_document_processing_lambdas()
        self._create_query_processing_lambdas()
        self._create_knowledge_graph_lambdas()
        
        # Grant permissions after all functions are created
        self._grant_data_lake_permissions()
        
        # Create API Gateway for external access
        self._create_api_gateway()
        
        # Create monitoring and orchestration
        self._create_monitoring_resources()

        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Environment", "Development")
        Tags.of(self).add("Architecture", "Microservices")

    def _create_document_processing_lambdas(self):
        """Create Lambda functions for document processing pipeline"""
        
        # Common environment variables for document processing
        doc_processing_env = {
            'DOCUMENTS_BUCKET': self.bucket_names["documents"],
            'EXTRACTED_TEXT_BUCKET': self.bucket_names["extracted_text"],
            'CHUNKS_BUCKET': self.bucket_names["chunks"],
            'EMBEDDINGS_BUCKET': self.bucket_names["embeddings"],
            'NER_RESULTS_BUCKET': self.bucket_names["ner_results"],
            'PROCESSING_METADATA_BUCKET': self.bucket_names["processing_metadata"],
            'OPENSEARCH_ENDPOINT': self.data_resources.opensearch_collection.attr_collection_endpoint
        }
        
        # Text Extractor Lambda
        self.text_extractor = lambda_.Function(
            self, "TextExtractor",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="text_extractor.handler",
            code=lambda_.Code.from_asset("../lambda/text_extractor"),
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment=doc_processing_env,
            role=self.ai_ml_resources.ai_ml_role,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            layers=[self.shared_layer],
            description="Extracts text from PDF documents using AWS Textract",
            log_retention=logs.RetentionDays.ONE_MONTH
        )
        
        # Text Chunker Lambda
        self.text_chunker = lambda_.Function(
            self, "TextChunker",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="text_chunker.handler",
            code=lambda_.Code.from_asset("../lambda/text_chunker"),
            timeout=Duration.minutes(10),
            memory_size=512,
            environment=doc_processing_env,
            role=self.ai_ml_resources.ai_ml_role,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            description="Creates structured chunks from extracted text",
            log_retention=logs.RetentionDays.ONE_MONTH
        )
        
        # Embedding Generator Lambda
        self.embedding_generator = lambda_.Function(
            self, "EmbeddingGenerator",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="embedding_generator.handler",
            code=lambda_.Code.from_asset("../lambda/embedding_generator"),
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment=doc_processing_env,
            role=self.ai_ml_resources.ai_ml_role,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            description="Generates embeddings using AWS Titan and indexes in OpenSearch",
            log_retention=logs.RetentionDays.ONE_MONTH
        )
        
        # NER Processor Lambda
        self.ner_processor = lambda_.Function(
            self, "NERProcessor",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="ner_processor.handler",
            code=lambda_.Code.from_asset("../lambda/ner_processor"),
            timeout=Duration.minutes(10),
            memory_size=512,
            environment=doc_processing_env,
            role=self.ai_ml_resources.ai_ml_role,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            description="Processes text chunks for named entity recognition",
            log_retention=logs.RetentionDays.ONE_MONTH
        )

    def _create_query_processing_lambdas(self):
        """Create Lambda functions for query processing pipeline"""
        
        # Query processing environment variables
        query_env = {
            'OPENSEARCH_ENDPOINT': self.data_resources.opensearch_collection.attr_collection_endpoint,
            'NEPTUNE_ENDPOINT': self.data_resources.neptune_cluster.attr_endpoint,
            'EMBEDDINGS_BUCKET': self.bucket_names["embeddings"],
            'NER_RESULTS_BUCKET': self.bucket_names["ner_results"],
            'KNOWLEDGE_GRAPH_BUCKET': self.bucket_names["knowledge_graph"]
        }
        
        # Query Analyzer Lambda
        self.query_analyzer = lambda_.Function(
            self, "QueryAnalyzer",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="query_analyzer.handler",
            code=lambda_.Code.from_asset("../lambda/query_analyzer"),
            timeout=Duration.minutes(2),
            memory_size=256,
            environment=query_env,
            role=self.ai_ml_resources.ai_ml_role,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            description="Analyzes user queries and extracts intent/entities",
            log_retention=logs.RetentionDays.ONE_MONTH
        )
        
        # Vector Search Lambda
        self.vector_searcher = lambda_.Function(
            self, "VectorSearcher",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="vector_searcher.handler",
            code=lambda_.Code.from_asset("../lambda/vector_searcher"),
            timeout=Duration.minutes(3),
            memory_size=512,
            environment=query_env,
            role=self.ai_ml_resources.ai_ml_role,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            description="Performs vector similarity search using OpenSearch",
            log_retention=logs.RetentionDays.ONE_MONTH
        )
        
        # Knowledge Graph Searcher Lambda
        self.kg_searcher = lambda_.Function(
            self, "KnowledgeGraphSearcher",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="kg_searcher.handler",
            code=lambda_.Code.from_asset("../lambda/kg_searcher"),
            timeout=Duration.minutes(3),
            memory_size=512,
            environment=query_env,
            role=self.ai_ml_resources.ai_ml_role,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            description="Searches knowledge graph using Neptune",
            log_retention=logs.RetentionDays.ONE_MONTH
        )
        
        # Response Generator Lambda
        self.response_generator = lambda_.Function(
            self, "ResponseGenerator",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="response_generator.handler",
            code=lambda_.Code.from_asset("../lambda/response_generator"),
            timeout=Duration.minutes(5),
            memory_size=1024,
            environment=query_env,
            role=self.ai_ml_resources.ai_ml_role,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            description="Generates responses using AWS Bedrock LLMs",
            log_retention=logs.RetentionDays.ONE_MONTH
        )

    def _create_knowledge_graph_lambdas(self):
        """Create Lambda functions for knowledge graph pipeline"""
        
        kg_env = {
            'NEPTUNE_ENDPOINT': self.data_resources.neptune_cluster.attr_endpoint,
            'NER_RESULTS_BUCKET': self.bucket_names["ner_results"],
            'KNOWLEDGE_GRAPH_BUCKET': self.bucket_names["knowledge_graph"]
        }
        
        # Entity Extractor Lambda
        self.entity_extractor = lambda_.Function(
            self, "EntityExtractor",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="entity_extractor.handler",
            code=lambda_.Code.from_asset("../lambda/entity_extractor"),
            timeout=Duration.minutes(5),
            memory_size=512,
            environment=kg_env,
            role=self.ai_ml_resources.ai_ml_role,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            description="Extracts entities from NER results for knowledge graph",
            log_retention=logs.RetentionDays.ONE_MONTH
        )
        
        # Relationship Miner Lambda
        self.relationship_miner = lambda_.Function(
            self, "RelationshipMiner",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="relationship_miner.handler",
            code=lambda_.Code.from_asset("../lambda/relationship_miner"),
            timeout=Duration.minutes(10),
            memory_size=1024,
            environment=kg_env,
            role=self.ai_ml_resources.ai_ml_role,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            description="Mines relationships between entities using LLMs",
            log_retention=logs.RetentionDays.ONE_MONTH
        )
        
        # Graph Updater Lambda
        self.graph_updater = lambda_.Function(
            self, "GraphUpdater",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="graph_updater.handler",
            code=lambda_.Code.from_asset("../lambda/graph_updater"),
            timeout=Duration.minutes(10),
            memory_size=512,
            environment=kg_env,
            role=self.ai_ml_resources.ai_ml_role,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            description="Updates Neptune knowledge graph with new entities and relationships",
            log_retention=logs.RetentionDays.ONE_MONTH
        )

    def _create_api_gateway(self):
        """Create API Gateway for external access"""
        
        # REST API
        self.api = apigateway.RestApi(
            self, "ClimateRiskMicroservicesAPI",
            rest_api_name="Climate Risk RAG Microservices API",
            description="API for Climate Risk RAG microservices system",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            )
        )
        
        # Query endpoint (orchestrates the query processing pipeline)
        query_resource = self.api.root.add_resource("query")
        
        # Create a Step Functions workflow for query processing
        query_workflow = self._create_query_processing_workflow()
        
        # API Gateway integration with Step Functions
        query_integration = apigateway.Integration(
            type=apigateway.IntegrationType.AWS,
            integration_http_method="POST",
            uri=f"arn:aws:apigateway:{self.region}:states:action/StartExecution",
            options=apigateway.IntegrationOptions(
                credentials_role=iam.Role(
                    self, "APIGatewayStepFunctionsRole",
                    assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
                    inline_policies={
                        "StepFunctionsStartExecution": iam.PolicyDocument(
                            statements=[
                                iam.PolicyStatement(
                                    actions=["states:StartExecution"],
                                    resources=[query_workflow.state_machine_arn]
                                )
                            ]
                        )
                    }
                ),
                request_templates={
                    "application/json": json.dumps({
                        "input": "$util.escapeJavaScript($input.json('$'))",
                        "stateMachineArn": query_workflow.state_machine_arn
                    })
                },
                integration_responses=[{
                    "statusCode": "200",
                    "responseTemplates": {
                        "application/json": json.dumps({
                            "executionArn": "$util.parseJson($input.json('$')).executionArn"
                        })
                    }
                }]
            )
        )
        
        query_resource.add_method("POST", query_integration)
        
        # Health check endpoint
        health_resource = self.api.root.add_resource("health")
        health_integration = apigateway.LambdaIntegration(self.query_analyzer)
        health_resource.add_method("GET", health_integration)
        
        # Output
        CfnOutput(
            self, "MicroservicesAPIURL",
            value=self.api.url,
            description="Microservices API Gateway URL"
        )

    def _create_query_processing_workflow(self):
        """Create Step Functions workflow for query processing"""
        
        # Define tasks
        analyze_query_task = sfn_tasks.LambdaInvoke(
            self, "AnalyzeQueryTask",
            lambda_function=self.query_analyzer,
            payload=sfn.TaskInput.from_object({
                "query": sfn.JsonPath.string_at("$.query"),
                "options": sfn.JsonPath.string_at("$.options")
            })
        )
        
        # Parallel search tasks
        vector_search_task = sfn_tasks.LambdaInvoke(
            self, "VectorSearchTask",
            lambda_function=self.vector_searcher,
            payload=sfn.TaskInput.from_object({
                "query_analysis": sfn.JsonPath.string_at("$.Payload"),
                "search_params": sfn.JsonPath.string_at("$.search_params")
            })
        )
        
        kg_search_task = sfn_tasks.LambdaInvoke(
            self, "KGSearchTask",
            lambda_function=self.kg_searcher,
            payload=sfn.TaskInput.from_object({
                "query_analysis": sfn.JsonPath.string_at("$.Payload"),
                "kg_params": sfn.JsonPath.string_at("$.kg_params")
            })
        )
        
        # Parallel execution of searches
        parallel_search = sfn.Parallel(self, "ParallelSearch")
        parallel_search.branch(vector_search_task)
        parallel_search.branch(kg_search_task)
        
        # Generate response
        generate_response_task = sfn_tasks.LambdaInvoke(
            self, "GenerateResponseTask",
            lambda_function=self.response_generator,
            payload=sfn.TaskInput.from_object({
                "query_analysis": sfn.JsonPath.string_at("$[0].Payload"),
                "search_results": sfn.JsonPath.string_at("$[1]"),
                "kg_results": sfn.JsonPath.string_at("$[2]")
            })
        )
        
        # Define workflow
        definition = analyze_query_task.next(
            parallel_search.next(generate_response_task)
        )
        
        # Create state machine
        query_workflow = sfn.StateMachine(
            self, "QueryProcessingWorkflow",
            definition=definition,
            timeout=Duration.minutes(10),
            state_machine_name="solve-global-kr-query-processing"
        )
        
        return query_workflow

    def _create_monitoring_resources(self):
        """Create monitoring and alerting resources"""
        
        # CloudWatch dashboard for monitoring
        # This would include metrics for all Lambda functions
        
        # EventBridge rules for processing orchestration
        # Daily processing summary
        daily_summary_rule = events.Rule(
            self, "DailyProcessingSummary",
            schedule=events.Schedule.cron(
                minute="0",
                hour="8",
                day="*",
                month="*"
            ),
            description="Daily processing summary and health check"
        )
        
        # Add targets for monitoring functions
        # (These would be additional Lambda functions for monitoring)
        
        # Output important function ARNs
        CfnOutput(self, "TextExtractorArn", value=self.text_extractor.function_arn)
        CfnOutput(self, "TextChunkerArn", value=self.text_chunker.function_arn)
        CfnOutput(self, "EmbeddingGeneratorArn", value=self.embedding_generator.function_arn)
        CfnOutput(self, "NERProcessorArn", value=self.ner_processor.function_arn)

    def _grant_data_lake_permissions(self):
        """Grant Lambda functions permissions to access data lake buckets"""
        
        # Document processing Lambdas
        doc_processing_lambdas = [
            self.text_extractor,
            self.text_chunker,
            self.embedding_generator,
            self.ner_processor
        ]
        
        for lambda_func in doc_processing_lambdas:
            # Grant access to all data lake buckets
            lambda_func.add_to_role_policy(iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket"
                ],
                resources=[
                    f"arn:aws:s3:::{self.bucket_names['documents']}",
                    f"arn:aws:s3:::{self.bucket_names['documents']}/*",
                    f"arn:aws:s3:::{self.bucket_names['extracted_text']}",
                    f"arn:aws:s3:::{self.bucket_names['extracted_text']}/*",
                    f"arn:aws:s3:::{self.bucket_names['chunks']}",
                    f"arn:aws:s3:::{self.bucket_names['chunks']}/*",
                    f"arn:aws:s3:::{self.bucket_names['embeddings']}",
                    f"arn:aws:s3:::{self.bucket_names['embeddings']}/*",
                    f"arn:aws:s3:::{self.bucket_names['ner_results']}",
                    f"arn:aws:s3:::{self.bucket_names['ner_results']}/*",
                    f"arn:aws:s3:::{self.bucket_names['processing_metadata']}",
                    f"arn:aws:s3:::{self.bucket_names['processing_metadata']}/*"
                ]
            ))
        
        # Query processing Lambdas
        query_processing_lambdas = [
            self.query_analyzer,
            self.vector_searcher,
            self.kg_searcher,
            self.response_generator
        ]
        
        for lambda_func in query_processing_lambdas:
            # Grant read access to processed data
            lambda_func.add_to_role_policy(iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                resources=[
                    f"arn:aws:s3:::{self.bucket_names['embeddings']}",
                    f"arn:aws:s3:::{self.bucket_names['embeddings']}/*",
                    f"arn:aws:s3:::{self.bucket_names['ner_results']}",
                    f"arn:aws:s3:::{self.bucket_names['ner_results']}/*",
                    f"arn:aws:s3:::{self.bucket_names['knowledge_graph']}",
                    f"arn:aws:s3:::{self.bucket_names['knowledge_graph']}/*"
                ]
            ))
        
        # Knowledge graph Lambdas
        kg_lambdas = [
            self.entity_extractor,
            self.relationship_miner,
            self.graph_updater
        ]
        
        for lambda_func in kg_lambdas:
            lambda_func.add_to_role_policy(iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                resources=[
                    f"arn:aws:s3:::{self.bucket_names['ner_results']}",
                    f"arn:aws:s3:::{self.bucket_names['ner_results']}/*"
                ]
            ))
            lambda_func.add_to_role_policy(iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket"
                ],
                resources=[
                    f"arn:aws:s3:::{self.bucket_names['knowledge_graph']}",
                    f"arn:aws:s3:::{self.bucket_names['knowledge_graph']}/*"
                ]
            ))
        
        # OpenSearch permissions
        opensearch_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["aoss:APIAccessAll"],
            resources=[self.data_resources.opensearch_collection.attr_arn]
        )
        
        # Add OpenSearch permissions to relevant functions
        opensearch_functions = [
            self.embedding_generator,
            self.vector_searcher
        ]
        
        for lambda_func in opensearch_functions:
            lambda_func.add_to_role_policy(opensearch_policy)

    @property
    def text_extractor_function(self):
        return self.text_extractor

    @property
    def text_chunker_function(self):
        return self.text_chunker

    @property
    def embedding_generator_function(self):
        return self.embedding_generator

    @property
    def ner_processor_function(self):
        return self.ner_processor

    @property
    def entity_extractor_function(self):
        return self.entity_extractor
