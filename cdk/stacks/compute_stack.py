"""
Compute Stack for Climate Risk RAG System
Creates Lambda functions, API Gateway, Step Functions, and EventBridge rules
"""

from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_events as events,
    aws_events_targets as targets,
    aws_s3_notifications as s3n,
    aws_iam as iam,
    aws_ec2 as ec2,
    Duration,
    CfnOutput,
    Tags
)
from constructs import Construct


class ComputeStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.Vpc, 
                 data_resources, ai_ml_resources, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.vpc = vpc
        self.data_resources = data_resources
        self.ai_ml_resources = ai_ml_resources

        # Create Lambda functions
        self._create_lambda_functions()
        
        # Create API Gateway
        self._create_api_gateway()
        
        # Create Step Functions workflow
        self._create_step_functions()
        
        # Create EventBridge rules
        self._create_event_rules()
        
        # Create S3 triggers
        self._create_s3_triggers()

        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Environment", "Development")

    def _create_lambda_functions(self):
        """Create Lambda functions for different components"""
        
        # Common environment variables
        common_env = {
            "OPENSEARCH_ENDPOINT": self.data_resources.opensearch_collection.attr_collection_endpoint,
            "NEPTUNE_ENDPOINT": self.data_resources.neptune_cluster.attr_endpoint,
            "DATABASE_SECRET_ARN": self.data_resources.db_secret.secret_arn,
            "DOCUMENTS_BUCKET": self.data_resources.documents_bucket.bucket_name,
            "ARTIFACTS_BUCKET": self.data_resources.artifacts_bucket.bucket_name,
            "AWS_REGION": self.region
        }

        # Document Processing Lambda
        self.document_processor = lambda_.Function(
            self, "DocumentProcessor",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="document_processor.handler",
            code=lambda_.Code.from_asset("../lambda/document_processor"),
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment=common_env,
            role=self.ai_ml_resources.ai_ml_role,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            description="Processes documents using Textract, Comprehend, and Titan"
        )

        # Query Handler Lambda
        self.query_handler = lambda_.Function(
            self, "QueryHandler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="query_handler.handler",
            code=lambda_.Code.from_asset("../lambda/query_handler"),
            timeout=Duration.minutes(5),
            memory_size=512,
            environment=common_env,
            role=self.ai_ml_resources.ai_ml_role,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            description="Handles RAG queries using OpenSearch, Neptune, and Bedrock"
        )

        # Knowledge Graph Manager Lambda
        self.kg_manager = lambda_.Function(
            self, "KnowledgeGraphManager",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="kg_manager.handler",
            code=lambda_.Code.from_asset("../lambda/kg_manager"),
            timeout=Duration.minutes(10),
            memory_size=1024,
            environment=common_env,
            role=self.ai_ml_resources.ai_ml_role,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            description="Manages knowledge graph operations in Neptune"
        )

        # Bulk Processing Lambda (for periodic rescans)
        self.bulk_processor = lambda_.Function(
            self, "BulkProcessor",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="bulk_processor.handler",
            code=lambda_.Code.from_asset("../lambda/bulk_processor"),
            timeout=Duration.minutes(15),
            memory_size=2048,
            environment=common_env,
            role=self.ai_ml_resources.ai_ml_role,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            description="Handles bulk document processing and periodic rescans"
        )

        # Grant permissions to access data resources
        self._grant_data_permissions()

    def _grant_data_permissions(self):
        """Grant Lambda functions permissions to access data resources"""
        
        # S3 permissions
        self.data_resources.documents_bucket.grant_read_write(self.document_processor)
        self.data_resources.documents_bucket.grant_read(self.query_handler)
        self.data_resources.artifacts_bucket.grant_read_write(self.document_processor)
        self.data_resources.artifacts_bucket.grant_read_write(self.bulk_processor)

        # Secrets Manager permissions
        self.data_resources.db_secret.grant_read(self.document_processor)
        self.data_resources.db_secret.grant_read(self.query_handler)
        self.data_resources.db_secret.grant_read(self.kg_manager)
        self.data_resources.db_secret.grant_read(self.bulk_processor)

        # OpenSearch permissions (handled via IAM policies in the functions)
        opensearch_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "aoss:APIAccessAll"  # OpenSearch Serverless permission
            ],
            resources=[self.data_resources.opensearch_collection.attr_arn]
        )

        for func in [self.document_processor, self.query_handler, self.kg_manager, self.bulk_processor]:
            func.add_to_role_policy(opensearch_policy)

    def _create_api_gateway(self):
        """Create API Gateway for the web interface"""
        
        # REST API
        self.api = apigateway.RestApi(
            self, "ClimateRiskAPI",
            rest_api_name="Climate Risk RAG API",
            description="API for Climate Risk RAG system",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            )
        )

        # Query endpoint
        query_resource = self.api.root.add_resource("query")
        query_integration = apigateway.LambdaIntegration(
            self.query_handler,
            request_templates={"application/json": '{"statusCode": "200"}'}
        )
        query_resource.add_method("POST", query_integration)

        # Document upload endpoint
        documents_resource = self.api.root.add_resource("documents")
        upload_integration = apigateway.LambdaIntegration(self.document_processor)
        documents_resource.add_method("POST", upload_integration)

        # Knowledge graph endpoint
        kg_resource = self.api.root.add_resource("knowledge-graph")
        kg_integration = apigateway.LambdaIntegration(self.kg_manager)
        kg_resource.add_method("GET", kg_integration)
        kg_resource.add_method("POST", kg_integration)

        # Output
        CfnOutput(
            self, "APIGatewayURL",
            value=self.api.url,
            description="API Gateway URL"
        )

    def _create_step_functions(self):
        """Create Step Functions workflow for document processing"""
        
        # Define tasks
        extract_text_task = sfn_tasks.LambdaInvoke(
            self, "ExtractTextTask",
            lambda_function=self.document_processor,
            payload=sfn.TaskInput.from_object({
                "action": "extract_text",
                "bucket": sfn.JsonPath.string_at("$.bucket"),
                "key": sfn.JsonPath.string_at("$.key")
            })
        )

        analyze_entities_task = sfn_tasks.LambdaInvoke(
            self, "AnalyzeEntitiesTask",
            lambda_function=self.document_processor,
            payload=sfn.TaskInput.from_object({
                "action": "analyze_entities",
                "text": sfn.JsonPath.string_at("$.Payload.text"),
                "document_id": sfn.JsonPath.string_at("$.Payload.document_id")
            })
        )

        generate_embeddings_task = sfn_tasks.LambdaInvoke(
            self, "GenerateEmbeddingsTask",
            lambda_function=self.document_processor,
            payload=sfn.TaskInput.from_object({
                "action": "generate_embeddings",
                "chunks": sfn.JsonPath.string_at("$.Payload.chunks"),
                "document_id": sfn.JsonPath.string_at("$.Payload.document_id"),
                "structured_chunks": sfn.JsonPath.string_at("$.Payload.structured_chunks")
            })
        )

        update_knowledge_graph_task = sfn_tasks.LambdaInvoke(
            self, "UpdateKnowledgeGraphTask",
            lambda_function=self.kg_manager,
            payload=sfn.TaskInput.from_object({
                "action": "update_graph",
                "entities": sfn.JsonPath.string_at("$.Payload.entities"),
                "document_id": sfn.JsonPath.string_at("$.Payload.document_id")
            })
        )

        # Define workflow
        definition = extract_text_task.next(
            analyze_entities_task.next(
                generate_embeddings_task.next(
                    update_knowledge_graph_task
                )
            )
        )

        # Create state machine
        self.document_processing_workflow = sfn.StateMachine(
            self, "DocumentProcessingWorkflow",
            definition=definition,
            timeout=Duration.minutes(30),
            state_machine_name="solve-global-kr-document-processing"
        )

        # Output
        CfnOutput(
            self, "StepFunctionsArn",
            value=self.document_processing_workflow.state_machine_arn,
            description="Step Functions workflow ARN"
        )

    def _create_event_rules(self):
        """Create EventBridge rules for scheduled tasks"""
        
        # Weekly bulk processing rule
        weekly_rule = events.Rule(
            self, "WeeklyBulkProcessing",
            schedule=events.Schedule.cron(
                minute="0",
                hour="2",
                day="*",
                month="*",
                week_day="SUN"
            ),
            description="Weekly bulk processing and document rescan"
        )

        weekly_rule.add_target(
            targets.LambdaFunction(self.bulk_processor)
        )

        # Daily health check rule
        daily_rule = events.Rule(
            self, "DailyHealthCheck",
            schedule=events.Schedule.cron(
                minute="0",
                hour="1",
                day="*",
                month="*",
                week_day="*"
            ),
            description="Daily system health check"
        )

        daily_rule.add_target(
            targets.LambdaFunction(
                self.query_handler,
                event=events.RuleTargetInput.from_object({"action": "health_check"})
            )
        )

    def _create_s3_triggers(self):
        """Create S3 event triggers for document processing"""
        
        # Trigger Step Functions workflow when documents are uploaded
        self.data_resources.documents_bucket.add_event_notification(
            s3n.EventType.OBJECT_CREATED,
            s3n.SfnDestination(self.document_processing_workflow),
            s3n.NotificationKeyFilter(suffix=".pdf")
        )

        self.data_resources.documents_bucket.add_event_notification(
            s3n.EventType.OBJECT_CREATED,
            s3n.SfnDestination(self.document_processing_workflow),
            s3n.NotificationKeyFilter(suffix=".docx")
        )

        self.data_resources.documents_bucket.add_event_notification(
            s3n.EventType.OBJECT_CREATED,
            s3n.SfnDestination(self.document_processing_workflow),
            s3n.NotificationKeyFilter(suffix=".txt")
        )
