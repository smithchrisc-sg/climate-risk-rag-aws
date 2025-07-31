#!/usr/bin/env python3
"""
Refactored KG Integration Deployment with Knowledge Graph Layer
Deploys document-structure-kg-processor and kg-triple-loader using KG Layer v1.0.0
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

class KGRefactoredStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        # Import existing role
        lambda_role = iam.Role.from_role_arn(
            self, "LambdaRole",
            role_arn="arn:aws:iam::861276078413:role/document-processing-lambda-role"
        )
        
        # Import existing database layer
        database_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "DatabaseLayer",
            layer_version_arn="arn:aws:lambda:us-east-1:861276078413:layer:database-core-layer:16"
        )
        
        # Create Knowledge Graph Layer
        knowledge_graph_layer = lambda_.LayerVersion(
            self, "KnowledgeGraphLayer",
            code=lambda_.Code.from_asset("../layers/knowledge-graph-layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Knowledge Graph Layer v2.0.0 with NLP-Ontology Integration with Neptune bulk load support"
        )
        
        # Import VPC and networking
        vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_name="solve-global-kr-rag-vpc")
        
        # Import security groups
        lambda_security_group = ec2.SecurityGroup.from_security_group_id(
            self, "LambdaSecurityGroup",
            security_group_id="sg-0c9e10b9cfb4c9eb0"
        )
        
        # Database subnets for Lambda functions requiring database access
        database_subnets = ec2.SubnetSelection(subnets=[
            ec2.Subnet.from_subnet_id(self, "DatabaseSubnet1", subnet_id="subnet-0e9efc5fdf29e9da0"),
            ec2.Subnet.from_subnet_id(self, "DatabaseSubnet2", subnet_id="subnet-00efdcc220a613ae3")
        ])
        
        # Neptune subnets for Lambda functions requiring Neptune access
        neptune_subnets = ec2.SubnetSelection(subnets=[
            ec2.Subnet.from_subnet_id(self, "NeptuneSubnet1", subnet_id="subnet-03d8bd6cf3491f38c"),
            ec2.Subnet.from_subnet_id(self, "NeptuneSubnet2", subnet_id="subnet-0c0be1dd59f70f70e")
        ])
        
        # KG Triples Ready Topic
        kg_triples_ready_topic = sns.Topic(
            self, "KGTriplesReadyTopic",
            topic_name="kg-triples-ready-refactored",
            display_name="Knowledge Graph Triples Ready for Neptune Loading (Refactored)"
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
        
        # Neptune environment variables
        neptune_env = {
            "NEPTUNE_ENDPOINT": "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com",
            "NEPTUNE_PORT": "8182",
            "AWS_REGION": "us-east-1",
            "NEPTUNE_TIMEOUT": "60",
            "NEPTUNE_MAX_RETRIES": "3"
        }
        
        # S3 bucket environment variables
        s3_env = {
            "CHUNKS_BUCKET": "solve-global-kr-dl-chunks-861276078413-us-east-1",
            "TEXT_BUCKET": "solve-global-kr-dl-text-861276078413-us-east-1",
            "TTL_BUCKET": "solve-global-kr-dl-neptune-ttl-861276078413-us-east-1",
            "ONTOLOGY_BUCKET": "solve-global-kr-dl-ontology-861276078413-us-east-1"
        }
        
        # Document Structure KG Processor (Refactored)
        document_structure_kg_processor = lambda_.Function(
            self, "DocumentStructureKGProcessorRefactored",
            function_name="document-structure-kg-processor-refactored",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/document-structure-kg-processor"),
            role=lambda_role,
            timeout=Duration.minutes(10),  # Increased for bulk load operations
            memory_size=1024,
            layers=[database_layer, knowledge_graph_layer],
            environment={
                **standard_env,
                **neptune_env,
                **s3_env,
                "KG_TRIPLES_READY_TOPIC_ARN": kg_triples_ready_topic.topic_arn
            },
            vpc=vpc,
            vpc_subnets=database_subnets,  # Needs database access
            security_groups=[lambda_security_group]
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
        
        # Grant permission to publish to KG triples ready topic
        kg_triples_ready_topic.grant_publish(document_structure_kg_processor)
        
        # KG Triple Loader (Refactored)
        kg_triple_loader = lambda_.Function(
            self, "KGTripleLoaderRefactored",
            function_name="kg-triple-loader-refactored",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/kg-triple-loader"),
            role=lambda_role,
            timeout=Duration.minutes(15),  # Increased for bulk load monitoring
            memory_size=1024,
            layers=[database_layer, knowledge_graph_layer],
            environment={
                **standard_env,
                **neptune_env,
                **s3_env
            },
            vpc=vpc,
            vpc_subnets=neptune_subnets,  # Needs Neptune access
            security_groups=[lambda_security_group]
        )
        
        # Subscribe to KG triples ready topic
        kg_triples_ready_topic.add_subscription(
            sns_subscriptions.LambdaSubscription(kg_triple_loader)
        )
        
        # Grant permission for SNS to invoke
        kg_triple_loader.add_permission(
            "AllowKGTriplesReadySNSInvoke",
            principal=iam.ServicePrincipal("sns.amazonaws.com"),
            source_arn=kg_triples_ready_topic.topic_arn
        )
        
        # Enhanced IAM permissions for KG Layer operations
        enhanced_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                # Neptune bulk load permissions
                "neptune-db:*",
                # S3 permissions for bulk load
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket",
                "s3:DeleteObject",
                # Enhanced SNS permissions
                "sns:Publish",
                "sns:Subscribe",
                "sns:Unsubscribe"
            ],
            resources=[
                # Neptune cluster
                f"arn:aws:neptune-db:us-east-1:861276078413:cluster/solve-global-kr-neptune/*",
                # S3 buckets
                "arn:aws:s3:::solve-global-kr-*",
                "arn:aws:s3:::solve-global-kr-*/*",
                # SNS topics
                kg_triples_ready_topic.topic_arn,
                "arn:aws:sns:us-east-1:861276078413:text-chunking-complete"
            ]
        )
        
        # Add enhanced permissions to both Lambda functions
        document_structure_kg_processor.add_to_role_policy(enhanced_policy)
        kg_triple_loader.add_to_role_policy(enhanced_policy)
        
        # Output important information
        from aws_cdk import CfnOutput
        
        CfnOutput(
            self, "KnowledgeGraphLayerArn",
            value=knowledge_graph_layer.layer_version_arn,
            description="Knowledge Graph Layer ARN for use in other stacks"
        )
        
        CfnOutput(
            self, "KGTriplesReadyTopicArn",
            value=kg_triples_ready_topic.topic_arn,
            description="KG Triples Ready Topic ARN"
        )
        
        CfnOutput(
            self, "DocumentStructureKGProcessorArn",
            value=document_structure_kg_processor.function_arn,
            description="Refactored Document Structure KG Processor ARN"
        )
        
        CfnOutput(
            self, "KGTripleLoaderArn",
            value=kg_triple_loader.function_arn,
            description="Refactored KG Triple Loader ARN"
        )

app = App()
KGRefactoredStack(app, "KGRefactoredStack")
app.synth()
