#!/usr/bin/env python3
"""
CDK App for Entity Resolution Service
Deploys Lambda function for resolving entities from NLP results and generating RDF

This CDK app creates:
1. Entity Resolution Service Lambda
2. SNS topic subscriptions for NLP completion events
3. Integration with existing KG pipeline
4. IAM roles and policies
5. VPC configuration for database access

Architecture: Integrates with existing NLP and KG pipelines
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

class EntityResolutionServiceStack(Stack):
    """Stack for Entity Resolution Service"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Environment configuration
        account_id = "861276078413"  # Correct current account
        region = "us-east-1"
        
        # S3 buckets (existing)
        chunks_bucket_name = f"solve-global-kr-dl-chunks-{account_id}-{region}"
        text_bucket_name = f"solve-global-kr-dl-text-{account_id}-{region}"
        ner_results_bucket_name = f"solve-global-kr-dl-ner-results-{account_id}-{region}"
        ttl_bucket_name = f"solve-global-kr-dl-neptune-ttl-{account_id}-{region}"
        
        # VPC configuration (existing)
        vpc_id = "vpc-051c21d88c7dc3819"
        vpc = ec2.Vpc.from_lookup(self, "ExistingVPC", vpc_id=vpc_id)
        
        # Security groups (existing)
        lambda_security_group = ec2.SecurityGroup.from_security_group_id(
            self, "LambdaSecurityGroup", "sg-099296a5c809e8d9d"
        )
        
        # Neptune endpoint
        neptune_endpoint = "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
        
        # Lambda layers (existing)
        core_utilities_layer = _lambda.LayerVersion.from_layer_version_arn(
            self, "CoreUtilitiesLayer",
            layer_version_arn=f"arn:aws:lambda:{region}:{account_id}:layer:climate-risk-core-utilities-pipeline:2"
        )
        
        database_layer = _lambda.LayerVersion.from_layer_version_arn(
            self, "DatabaseLayer", 
            layer_version_arn=f"arn:aws:lambda:{region}:{account_id}:layer:database-dependencies-pipeline:2"
        )
        
        # SNS Topics (existing - reference them)
        nlp_completion_topic_arn = f"arn:aws:sns:{region}:{account_id}:nlp-processing-complete"
        kg_integration_topic_arn = f"arn:aws:sns:{region}:{account_id}:kg-integration-processing"
        
        # Reference existing topics
        nlp_completion_topic = sns.Topic.from_topic_arn(
            self, "NLPCompletionTopic", nlp_completion_topic_arn
        )
        
        kg_integration_topic = sns.Topic.from_topic_arn(
            self, "KGIntegrationTopic", kg_integration_topic_arn
        )
        
        # Create entities resolved topic for completion notifications
        entities_resolved_topic = sns.Topic(
            self, "EntitiesResolvedTopic",
            topic_name="entities-resolved",
            display_name="Entities Resolved Completion"
        )
        
        # IAM role for Entity Resolution Lambda
        entity_resolver_role = iam.Role(
            self, "EntityResolverRole",
            role_name="entity-resolution-service-lambda-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        
        # S3 permissions for Entity Resolution
        entity_resolver_role.add_to_policy(iam.PolicyStatement(
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
                f"arn:aws:s3:::{ner_results_bucket_name}",
                f"arn:aws:s3:::{ner_results_bucket_name}/*",
                f"arn:aws:s3:::{ttl_bucket_name}",
                f"arn:aws:s3:::{ttl_bucket_name}/*"
            ]
        ))
        
        # SNS permissions for Entity Resolution
        entity_resolver_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "sns:Publish"
            ],
            resources=[
                kg_integration_topic_arn,
                entities_resolved_topic.topic_arn
            ]
        ))
        
        # RDS permissions for status updates
        entity_resolver_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "rds-data:ExecuteStatement",
                "rds-data:BatchExecuteStatement"
            ],
            resources=[f"arn:aws:rds:{region}:{account_id}:cluster:*"]
        ))
        
        # Entity Resolution Service Lambda
        entity_resolution_service = _lambda.Function(
            self, "EntityResolutionService",
            function_name="entity-resolution-service",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="entity_resolver.lambda_handler",
            code=_lambda.Code.from_asset("../lambda/entity_resolver"),
            layers=[core_utilities_layer, database_layer],
            role=entity_resolver_role,
            vpc=vpc,
            security_groups=[lambda_security_group],
            timeout=Duration.minutes(10),
            memory_size=1024,
            environment={
                "CHUNKS_BUCKET": chunks_bucket_name,
                "TEXT_BUCKET": text_bucket_name,
                "NER_RESULTS_BUCKET": ner_results_bucket_name,
                "TTL_BUCKET": ttl_bucket_name,
                "KG_INTEGRATION_TOPIC_ARN": kg_integration_topic_arn,
                "ENTITIES_RESOLVED_TOPIC_ARN": entities_resolved_topic.topic_arn,
                "NEPTUNE_ENDPOINT": neptune_endpoint,
                "DATABASE_URL": "postgresql://postgres:c0xfd_t#PBUqV(pLM-9IqM59G:>c@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require",
                "ENTITY_NAMESPACE": "kr:",
                "ENTITY_BASE_URI": "http://solve.global/knowledge-commons/schema#"
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # SNS subscription: NLP completion → Entity Resolution Service
        nlp_completion_topic.add_subscription(
            subscriptions.LambdaSubscription(entity_resolution_service)
        )
        
        # Outputs
        cdk.CfnOutput(self, "EntityResolutionServiceArn",
            value=entity_resolution_service.function_arn,
            description="Entity Resolution Service Lambda ARN"
        )
        
        cdk.CfnOutput(self, "EntitiesResolvedTopicArn",
            value=entities_resolved_topic.topic_arn,
            description="Entities Resolved Topic ARN"
        )

# CDK App
app = cdk.App()
EntityResolutionServiceStack(app, "EntityResolutionServiceStack",
    env=cdk.Environment(
        account="861276078413",
        region="us-east-1"
    )
)

app.synth()
