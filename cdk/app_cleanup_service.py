#!/usr/bin/env python3
"""
CDK App for Climate Risk RAG Cleanup Service
Deploys a centralized cleanup Lambda function with VPC access
"""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_logs as logs
)
from constructs import Construct

class CleanupServiceStack(Stack):
    """Stack for the cleanup service Lambda function"""

    def __init__(self, scope, construct_id, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Import existing VPC
        vpc = ec2.Vpc.from_lookup(self, "ExistingVPC", vpc_id="vpc-051c21d88c7dc3819")
        
        # Import database subnets for VPC access
        subnet1 = ec2.Subnet.from_subnet_id(
            self, "DatabaseSubnet1", 
            subnet_id="subnet-0e9efc5fdf29e9da0"
        )
        subnet2 = ec2.Subnet.from_subnet_id(
            self, "DatabaseSubnet2", 
            subnet_id="subnet-00efdcc220a613ae3"
        )
        
        # Create security group for cleanup service
        cleanup_sg = ec2.SecurityGroup(
            self, "CleanupServiceSecurityGroup",
            vpc=vpc,
            description="Security group for cleanup service with database access",
            allow_all_outbound=True
        )
        
        # Add egress rule for PostgreSQL database access
        cleanup_sg.add_egress_rule(
            peer=ec2.SecurityGroup.from_security_group_id(
                self, "DatabaseSG", 
                security_group_id="sg-09bc56a537bf7ac12"
            ),
            connection=ec2.Port.tcp(5432),
            description="Allow PostgreSQL access to database"
        )
        
        # Add inbound rule to database security group
        database_sg = ec2.SecurityGroup.from_security_group_id(
            self, "DatabaseSecurityGroup",
            security_group_id="sg-09bc56a537bf7ac12"
        )
        
        database_sg.add_ingress_rule(
            peer=cleanup_sg,
            connection=ec2.Port.tcp(5432),
            description="Allow cleanup service to connect to PostgreSQL"
        )
        
        # Create IAM role for cleanup service
        cleanup_role = iam.Role(
            self, "CleanupServiceRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "CleanupServicePolicy": iam.PolicyDocument(
                    statements=[
                        # S3 permissions for all project buckets
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:DeleteObject",
                                "s3:ListBucket",
                                "s3:GetObjectMetadata",
                                "s3:ListBucketVersions",
                                "s3:DeleteObjectVersion"
                            ],
                            resources=[
                                "arn:aws:s3:::solve-global-kr-*",
                                "arn:aws:s3:::solve-global-kr-*/*"
                            ]
                        ),
                        # OpenSearch permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "es:ESHttpGet",
                                "es:ESHttpPost",
                                "es:ESHttpPut",
                                "es:ESHttpDelete",
                                "es:ESHttpHead"
                            ],
                            resources=[
                                f"arn:aws:es:{self.region}:{self.account}:domain/*"
                            ]
                        ),
                        # Neptune permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "neptune-db:connect",
                                "neptune-db:ReadDataViaQuery",
                                "neptune-db:WriteDataViaQuery",
                                "neptune-db:DeleteDataViaQuery"
                            ],
                            resources=[
                                f"arn:aws:neptune-db:{self.region}:{self.account}:cluster/*",
                                f"arn:aws:neptune-db:{self.region}:{self.account}:cluster/*/*"
                            ]
                        ),
                        # RDS permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "rds:DescribeDBInstances",
                                "rds:DescribeDBClusters"
                            ],
                            resources=["*"]
                        ),
                        # Secrets Manager permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["secretsmanager:GetSecretValue"],
                            resources=[f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:*"]
                        ),
                        # STS permissions for account identity
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["sts:GetCallerIdentity"],
                            resources=["*"]
                        )
                    ]
                )
            }
        )
        
        # Create Lambda function
        self.cleanup_function = lambda_.Function(
            self, "CleanupServiceFunction",
            function_name="solve-global-kr-cleanup-service",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="cleanup_service.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/cleanup_service"),
            role=cleanup_role,
            timeout=Duration.minutes(15),
            memory_size=1024,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[subnet1, subnet2]),
            security_groups=[cleanup_sg],
            layers=[
                # Use existing layers
                lambda_.LayerVersion.from_layer_version_arn(
                    self, "CoreUtilitiesLayer",
                    layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:climate-risk-core-utilities:2"
                ),
                lambda_.LayerVersion.from_layer_version_arn(
                    self, "DatabaseDependenciesLayer",
                    layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:database-dependencies:2"
                )
            ],
            environment={
                "DATABASE_URL": "postgresql://postgres:c0xfd_t#PBUqV(pLM-9IqM59G:>c@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require",
                "OPENSEARCH_VECTOR_ENDPOINT": "https://search-climate-risk-vectorsearch-collection.us-east-1.aoss.amazonaws.com",
                "OPENSEARCH_KEYWORD_ENDPOINT": "https://search-climate-risk-keyword-index.us-east-1.es.amazonaws.com",
                "NEPTUNE_ENDPOINT": "solve-global-kr-rag-data-neptunedbcluster-1234567890.cluster-abcdefghij.us-east-1.neptune.amazonaws.com",
                "NEPTUNE_PORT": "8182",
                "AWS_ACCOUNT_ID": "861276078413",
                "LAMBDA_ENVIRONMENT": "true"
            }
        )
        
        # Output the function ARN
        cdk.CfnOutput(
            self, "CleanupServiceFunctionArn",
            value=self.cleanup_function.function_arn,
            description="ARN of the cleanup service Lambda function"
        )
        
        # Output the function name
        cdk.CfnOutput(
            self, "CleanupServiceFunctionName",
            value=self.cleanup_function.function_name,
            description="Name of the cleanup service Lambda function"
        )


# CDK App
app = cdk.App()

# Deploy cleanup service stack
cleanup_stack = CleanupServiceStack(
    app, "CleanupServiceStack",
    env=cdk.Environment(
        account="861276078413",
        region="us-east-1"
    ),
    description="Climate Risk RAG Cleanup Service - Centralized cleanup of test artifacts"
)

# Add tags
cdk.Tags.of(cleanup_stack).add("Project", "ClimateRiskRAG")
cdk.Tags.of(cleanup_stack).add("Component", "CleanupService")
cdk.Tags.of(cleanup_stack).add("Environment", "Development")

app.synth()
