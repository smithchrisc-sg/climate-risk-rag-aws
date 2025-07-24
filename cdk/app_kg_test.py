#!/usr/bin/env python3
"""
Simple KG Integration Test Deployment
"""

from aws_cdk import (
    App, Stack, Duration,
    aws_lambda as lambda_,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
    aws_iam as iam,
    aws_ec2 as ec2
)
from constructs import Construct

class KGTestStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        # Import existing role
        lambda_role = iam.Role.from_role_arn(
            self, "LambdaRole",
            role_arn="arn:aws:iam::861276078413:role/document-processing-lambda-role"
        )
        
        # Import existing layer
        database_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "DatabaseLayer",
            layer_version_arn="arn:aws:lambda:us-east-1:861276078413:layer:database-core-layer:16"
        )
        
        # Import VPC
        vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_name="solve-global-kr-rag-vpc")
        
        # Import security group
        security_group = ec2.SecurityGroup.from_security_group_id(
            self, "SecurityGroup",
            security_group_id="sg-0c9e10b9cfb4c9eb0"
        )
        
        # KG Triples Ready Topic
        kg_triples_ready_topic = sns.Topic(
            self, "KGTriplesReadyTopic",
            topic_name="kg-triples-ready",
            display_name="Knowledge Graph Triples Ready for Neptune Loading"
        )
        
        # Reference existing text-chunking-complete topic
        text_chunking_complete_topic = sns.Topic.from_topic_arn(
            self, "TextChunkingCompleteTopic",
            topic_arn="arn:aws:sns:us-east-1:861276078413:text-chunking-complete"
        )
        
        # Standard environment variables
        standard_env = {
            "DATABASE_SECRET_NAME": "rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863",
            "DB_PORT": "5432",
            "DB_NAME": "climate_risk_rag",
            "DB_HOST": "solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com"
        }
        
        # Document Structure KG Processor
        document_structure_kg_processor = lambda_.Function(
            self, "DocumentStructureKGProcessor",
            function_name="document-structure-kg-processor",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/document-structure-kg-processor"),
            role=lambda_role,
            timeout=Duration.minutes(5),
            memory_size=1024,
            layers=[database_layer],
            environment={
                **standard_env,
                "CHUNKS_BUCKET": "solve-global-kr-dl-chunks-861276078413-us-east-1",
                "TEXT_BUCKET": "solve-global-kr-dl-text-861276078413-us-east-1",
                "TTL_BUCKET": "solve-global-kr-dl-neptune-ttl-861276078413-us-east-1",
                "NEPTUNE_ENDPOINT": "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com",
                "NEPTUNE_PORT": "8182",
                "KG_TRIPLES_READY_TOPIC_ARN": kg_triples_ready_topic.topic_arn
            },
            vpc=vpc,
            security_groups=[security_group]
        )
        
        # Subscribe to text-chunking-complete topic
        text_chunking_complete_topic.add_subscription(
            sns_subscriptions.LambdaSubscription(document_structure_kg_processor)
        )
        
        # Grant permission for SNS to invoke
        document_structure_kg_processor.add_permission(
            "AllowSNSInvoke",
            principal=iam.ServicePrincipal("sns.amazonaws.com"),
            source_arn="arn:aws:sns:us-east-1:861276078413:text-chunking-complete"
        )
        
        # KG Integration Worker
        kg_integration_worker = lambda_.Function(
            self, "KGIntegrationWorker",
            function_name="kg-integration-worker",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/kg-integration-worker"),
            role=lambda_role,
            timeout=Duration.minutes(10),
            memory_size=512,
            layers=[database_layer],
            environment={
                **standard_env,
                "NEPTUNE_ENDPOINT": "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com",
                "NEPTUNE_PORT": "8182",
                "TTL_BUCKET": "solve-global-kr-dl-neptune-ttl-861276078413-us-east-1"
            },
            vpc=vpc,
            security_groups=[security_group]
        )
        
        # Subscribe to kg-triples-ready topic
        kg_triples_ready_topic.add_subscription(
            sns_subscriptions.LambdaSubscription(kg_integration_worker)
        )
        
        # Grant permission for SNS to invoke
        kg_integration_worker.add_permission(
            "AllowKGTriplesReadySNSInvoke",
            principal=iam.ServicePrincipal("sns.amazonaws.com"),
            source_arn=kg_triples_ready_topic.topic_arn
        )

# CDK App
app = App()
KGTestStack(app, "kg-test-stack")
app.synth()
