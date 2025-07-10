#!/usr/bin/env python3
"""
CDK App for Document Structure Knowledge Graph Integration
Deploys Lambda functions for integrating document structure into Neptune KG

This CDK app creates:
1. Document Structure KG Processor Lambda
2. KG Integration Worker Lambda  
3. SNS topics for messaging
4. IAM roles and policies
5. VPC configuration for Neptune access

Architecture: Designed for extensibility to support future entity processing
"""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ec2 as ec2,
    aws_logs as logs
)
from constructs import Construct

class DocumentStructureKGStack(Stack):
    """Stack for Document Structure Knowledge Graph Integration"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Environment configuration
        account_id = "861276078413"
        region = "us-east-1"
        
        # S3 buckets (existing)
        chunks_bucket_name = f"solve-global-kr-chunks-{account_id}-{region}"
        text_bucket_name = f"solve-global-kr-text-new-{account_id}-{region}"
        ttl_bucket_name = f"solve-global-kr-neptune-ttl-{account_id}-{region}"
        
        # VPC configuration (existing)
        vpc_id = "vpc-051c21d88c7dc3819"
        vpc = ec2.Vpc.from_lookup(self, "ExistingVPC", vpc_id=vpc_id)
        
        # Security groups (existing)
        lambda_security_group = ec2.SecurityGroup.from_security_group_id(
            self, "LambdaSecurityGroup", "sg-0c043bcb40f656321"
        )
        
        # Neptune endpoint
        neptune_endpoint = "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
        
        # Lambda layers (existing)
        core_utilities_layer = _lambda.LayerVersion.from_layer_version_arn(
            self, "CoreUtilitiesLayer",
            layer_version_arn=f"arn:aws:lambda:{region}:{account_id}:layer:climate-risk-core-utilities:2"
        )
        
        database_layer = _lambda.LayerVersion.from_layer_version_arn(
            self, "DatabaseLayer", 
            layer_version_arn=f"arn:aws:lambda:{region}:{account_id}:layer:database-dependencies:2"
        )
        
        # SNS Topics for KG processing pipeline
        kg_integration_topic = sns.Topic(
            self, "KGIntegrationTopic",
            topic_name="kg-integration-processing",
            display_name="Knowledge Graph Integration Processing"
        )
        
        kg_completion_topic = sns.Topic(
            self, "KGCompletionTopic", 
            topic_name="kg-processing-completion",
            display_name="Knowledge Graph Processing Completion"
        )
        
        # Future: Entity processing topic (architecture ready)
        entity_processing_topic = sns.Topic(
            self, "EntityProcessingTopic",
            topic_name="entity-processing",
            display_name="Entity Processing for Knowledge Graph"
        )
        
        # IAM role for KG Lambda functions
        kg_lambda_role = iam.Role(
            self, "KGLambdaRole",
            role_name="document-structure-kg-lambda-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        
        # S3 permissions for KG functions
        kg_lambda_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetObject",
                "s3:PutObject", 
                "s3:ListBucket",
                "s3:GetObjectMetadata"
            ],
            resources=[
                f"arn:aws:s3:::{chunks_bucket_name}",
                f"arn:aws:s3:::{chunks_bucket_name}/*",
                f"arn:aws:s3:::{text_bucket_name}",
                f"arn:aws:s3:::{text_bucket_name}/*",
                f"arn:aws:s3:::{ttl_bucket_name}",
                f"arn:aws:s3:::{ttl_bucket_name}/*"
            ]
        ))
        
        # SNS permissions for KG functions
        kg_lambda_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "sns:Publish"
            ],
            resources=[
                kg_integration_topic.topic_arn,
                kg_completion_topic.topic_arn,
                entity_processing_topic.topic_arn
            ]
        ))
        
        # RDS permissions for status updates
        kg_lambda_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "rds-data:ExecuteStatement",
                "rds-data:BatchExecuteStatement"
            ],
            resources=[f"arn:aws:rds:{region}:{account_id}:cluster:*"]
        ))
        
        # Neptune permissions (for future direct access if needed)
        kg_lambda_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "neptune-db:connect",
                "neptune-db:ReadDataViaQuery",
                "neptune-db:WriteDataViaQuery"
            ],
            resources=[f"arn:aws:neptune-db:{region}:{account_id}:cluster-*/*"]
        ))
        
        # Document Structure KG Processor Lambda
        document_structure_kg_processor = _lambda.Function(
            self, "DocumentStructureKGProcessor",
            function_name="document-structure-kg-processor",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="document_structure_kg_processor.lambda_handler",
            code=_lambda.Code.from_asset("../lambda/document_structure_kg_processor"),
            layers=[core_utilities_layer, database_layer],
            role=kg_lambda_role,
            vpc=vpc,
            security_groups=[lambda_security_group],
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={
                "CHUNKS_BUCKET": chunks_bucket_name,
                "TEXT_BUCKET": text_bucket_name,
                "TTL_BUCKET": ttl_bucket_name,
                "KG_INTEGRATION_TOPIC_ARN": kg_integration_topic.topic_arn,
                "ENTITY_PROCESSING_TOPIC_ARN": entity_processing_topic.topic_arn,
                "NEPTUNE_ENDPOINT": neptune_endpoint
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # KG Integration Worker Lambda
        kg_integration_worker = _lambda.Function(
            self, "KGIntegrationWorker",
            function_name="kg-integration-worker",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="kg_integration_worker.lambda_handler", 
            code=_lambda.Code.from_asset("../lambda/kg_integration_worker"),
            layers=[core_utilities_layer, database_layer],
            role=kg_lambda_role,
            vpc=vpc,
            security_groups=[lambda_security_group],
            timeout=Duration.minutes(10),
            memory_size=1024,
            environment={
                "NEPTUNE_ENDPOINT": neptune_endpoint,
                "KG_COMPLETION_TOPIC_ARN": kg_completion_topic.topic_arn,
                "TTL_BUCKET": ttl_bucket_name
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # SNS subscriptions
        kg_integration_topic.add_subscription(
            subscriptions.LambdaSubscription(kg_integration_worker)
        )
        
        # Future: Text chunker completion → Document Structure KG Processor
        # This will be connected to existing text chunker completion topic
        
        # Outputs
        cdk.CfnOutput(self, "DocumentStructureKGProcessorArn",
            value=document_structure_kg_processor.function_arn,
            description="Document Structure KG Processor Lambda ARN"
        )
        
        cdk.CfnOutput(self, "KGIntegrationWorkerArn", 
            value=kg_integration_worker.function_arn,
            description="KG Integration Worker Lambda ARN"
        )
        
        cdk.CfnOutput(self, "KGIntegrationTopicArn",
            value=kg_integration_topic.topic_arn,
            description="KG Integration Topic ARN"
        )
        
        cdk.CfnOutput(self, "KGCompletionTopicArn",
            value=kg_completion_topic.topic_arn,
            description="KG Completion Topic ARN"
        )
        
        cdk.CfnOutput(self, "EntityProcessingTopicArn",
            value=entity_processing_topic.topic_arn,
            description="Entity Processing Topic ARN (Future Use)"
        )

# CDK App
app = cdk.App()
DocumentStructureKGStack(app, "DocumentStructureKGStack",
    env=cdk.Environment(
        account="861276078413",
        region="us-east-1"
    )
)

app.synth()
