#!/usr/bin/env python3
"""
Pipeline Test Lambda CDK App
Deploys the pipeline test Lambda function with VPC access and proper permissions
"""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_logs as logs,
    Duration,
    CfnOutput,
    Tags
)
from constructs import Construct


class PipelineTestLambdaStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Import existing VPC
        vpc = ec2.Vpc.from_lookup(
            self, "ExistingVPC",
            vpc_id="vpc-0123456789abcdef0"  # Replace with actual VPC ID
        )
        
        # Create Lambda execution role with comprehensive permissions
        lambda_role = iam.Role(
            self, "PipelineTestLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "PipelineTestPolicy": iam.PolicyDocument(
                    statements=[
                        # S3 permissions for all buckets
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:ListBucket",
                                "s3:CopyObject",
                                "s3:GetObjectMetadata",
                                "s3:PutObjectMetadata"
                            ],
                            resources=[
                                "arn:aws:s3:::solve-global-kr-*",
                                "arn:aws:s3:::solve-global-kr-*/*"
                            ]
                        ),
                        # Lambda invoke permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "lambda:InvokeFunction"
                            ],
                            resources=[
                                f"arn:aws:lambda:{self.region}:{self.account}:function:solve-global-kr-*"
                            ]
                        ),
                        # RDS permissions for database access
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
                            actions=[
                                "secretsmanager:GetSecretValue"
                            ],
                            resources=[
                                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:*"
                            ]
                        )
                    ]
                )
            }
        )
        
        # Import existing Lambda layer (if available)
        try:
            shared_layer = lambda_.LayerVersion.from_layer_version_arn(
                self, "SharedLayer",
                layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:solve-global-kr-shared-layer:1"
            )
            layers = [shared_layer]
        except:
            # Create a minimal layer or use none
            layers = []
        
        # Create the pipeline test Lambda function
        self.pipeline_test_function = lambda_.Function(
            self, "PipelineTestFunction",
            function_name="solve-global-kr-pipeline-test-function",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="pipeline_test_handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/pipeline_test_function"),
            role=lambda_role,
            timeout=Duration.minutes(15),  # Long timeout for document processing
            memory_size=1024,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            layers=layers,
            environment={
                # S3 bucket names
                "EXISTING_DOCUMENTS_BUCKET": f"solve-global-kr-documents-{self.account}-{self.region}",
                "SOURCE_DOCUMENTS_BUCKET": f"solve-global-kr-dl-source-documents-{self.account}-{self.region}",
                "TEXT_BUCKET": f"solve-global-kr-dl-text-{self.account}-{self.region}",
                "CHUNKS_BUCKET": f"solve-global-kr-dl-chunks-{self.account}-{self.region}",
                
                # SQLite database configuration (stored in S3)
                "SQLITE_S3_BUCKET": f"solve-global-kr-cache-{self.account}-{self.region}",
                "SQLITE_S3_KEY": "database/corpus_document_ids.db",
                "SQLITE_DB_PATH": "/tmp/corpus_document_ids.db",
                
                # Database connection
                "DATABASE_URL": "postgresql://postgres:-VroWHWQBS5!V)yAcsDC3(3)NHJ5@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require",
                
                # Other configuration
                "AWS_DEFAULT_REGION": self.region,
                "LAMBDA_ENVIRONMENT": "true"
            },
            description="Pipeline test function for parameterized document processing tests",
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # Output the function ARN
        CfnOutput(
            self, "PipelineTestFunctionArn",
            value=self.pipeline_test_function.function_arn,
            description="ARN of the pipeline test Lambda function"
        )
        
        CfnOutput(
            self, "PipelineTestFunctionName",
            value=self.pipeline_test_function.function_name,
            description="Name of the pipeline test Lambda function"
        )
        
        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Environment", "Development")
        Tags.of(self).add("Purpose", "PipelineTesting")


# Create the CDK app
app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account="861276078413",
    region="us-east-1"
)

# Create the pipeline test Lambda stack
pipeline_test_stack = PipelineTestLambdaStack(
    app,
    "solve-global-kr-pipeline-test-lambda",
    env=env,
    description="Pipeline test Lambda function for parameterized document processing tests"
)

app.synth()
