#!/usr/bin/env python3
"""
Text Chunker CDK App - Database Configuration
Phase 1.5: Database integration testing
"""

import aws_cdk as cdk
from aws_cdk import (
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_logs as logs,
    Duration,
    CfnOutput,
    Tags
)
from constructs import Construct

class TextChunkerDatabaseStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Reference existing VPC (from your infrastructure)
        vpc = ec2.Vpc.from_lookup(
            self, "ExistingVpc",
            vpc_id="vpc-051c21d88c7dc3819"  # Your existing VPC ID
        )
        
        # Create lambda layers for shared dependencies
        self._create_lambda_layers()
        
        # Create text chunker lambda function with database access
        self._create_text_chunker_lambda(vpc)
        
        # Create outputs
        self._create_outputs()

        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Component", "TextChunker")
        Tags.of(self).add("Phase", "Phase1-Database")

    def _create_lambda_layers(self):
        """Create lambda layers for shared dependencies"""
        
        # Climate Risk Core Layer (DocumentIDManager, DatabaseManager, etc.)
        self.climate_risk_core_layer = lambda_.LayerVersion(
            self, "ClimateRiskCoreLayer",
            layer_version_name="climate-risk-core-utilities-db",
            code=lambda_.Code.from_asset("../layers/build/climate-risk-core-layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Core application utilities with database support",
        )
        
        # Database Layer (psycopg2-binary)
        self.database_layer = lambda_.LayerVersion(
            self, "DatabaseLayer",
            layer_version_name="database-dependencies",
            code=lambda_.Code.from_asset("../layers/build/database-layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Database dependencies (psycopg2-binary)",
        )

    def _create_text_chunker_lambda(self, vpc):
        """Create the text chunker lambda function with database access"""
        
        # Environment variables for text chunker with database
        text_chunker_env = {
            'CHUNKS_BUCKET': f'solve-global-kr-chunks-{self.account}-{self.region}',
            'TEXT_BUCKET': f'solve-global-kr-text-new-{self.account}-{self.region}',
            'DATABASE_URL': 'postgresql://postgres:-VroWHWQBS5!V)yAcsDC3(3)NHJ5@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require',
            'PHASE': 'PHASE1_DATABASE_TESTING',
            'COORDINATION_TOPIC_ARN': '',
        }
        
        # Create IAM role for text chunker with VPC and database access
        self.text_chunker_role = iam.Role(
            self, "TextChunkerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole")
            ],
            inline_policies={
                "TextChunkerPolicy": iam.PolicyDocument(
                    statements=[
                        # S3 permissions for reading text and storing chunks
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:DeleteObject",
                                "s3:ListBucket"
                            ],
                            resources=[
                                f"arn:aws:s3:::solve-global-kr-text-new-{self.account}-{self.region}",
                                f"arn:aws:s3:::solve-global-kr-text-new-{self.account}-{self.region}/*",
                                f"arn:aws:s3:::solve-global-kr-chunks-{self.account}-{self.region}",
                                f"arn:aws:s3:::solve-global-kr-chunks-{self.account}-{self.region}/*"
                            ]
                        ),
                        # CloudWatch Logs permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents"
                            ],
                            resources=["*"]
                        ),
                        # Secrets Manager for database credentials (if needed)
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "secretsmanager:GetSecretValue"
                            ],
                            resources=[
                                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:rds!db-*"
                            ]
                        )
                    ]
                )
            }
        )
        
        # Get database security group for lambda access
        db_security_group = ec2.SecurityGroup.from_security_group_id(
            self, "DatabaseSecurityGroup",
            security_group_id="sg-09bc56a537bf7ac12"  # PostgreSQL security group
        )
        
        # Create security group for lambda function
        lambda_security_group = ec2.SecurityGroup(
            self, "TextChunkerSecurityGroup",
            vpc=vpc,
            description="Security group for Text Chunker Lambda",
            allow_all_outbound=True
        )
        
        # Allow lambda to connect to database
        db_security_group.add_ingress_rule(
            peer=lambda_security_group,
            connection=ec2.Port.tcp(5432),
            description="Allow Text Chunker Lambda to connect to PostgreSQL"
        )
        
        # Text Chunker Lambda Function with VPC access
        self.text_chunker_function = lambda_.Function(
            self, "TextChunkerFunction",
            function_name="solve-global-kr-text-chunker-db",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="text_chunker_processor.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/text_chunker"),
            timeout=Duration.minutes(10),  # Longer timeout for database operations
            memory_size=1024,  # More memory for database operations
            environment=text_chunker_env,
            role=self.text_chunker_role,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[lambda_security_group],
            layers=[
                self.climate_risk_core_layer,
                self.database_layer
            ],
            description="Text chunker with database integration",
            log_retention=logs.RetentionDays.ONE_WEEK
        )

    def _create_outputs(self):
        """Create CloudFormation outputs"""
        
        CfnOutput(
            self, "TextChunkerFunctionName",
            value=self.text_chunker_function.function_name,
            description="Text Chunker Lambda function name (with database)"
        )
        
        CfnOutput(
            self, "TextChunkerFunctionArn", 
            value=self.text_chunker_function.function_arn,
            description="Text Chunker Lambda function ARN (with database)"
        )
        
        CfnOutput(
            self, "ClimateRiskCoreLayerArn",
            value=self.climate_risk_core_layer.layer_version_arn,
            description="Climate Risk Core Layer ARN (with database support)"
        )
        
        CfnOutput(
            self, "DatabaseLayerArn",
            value=self.database_layer.layer_version_arn,
            description="Database Layer ARN (psycopg2-binary)"
        )

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account="861276078413",
    region="us-east-1"
)

# Text Chunker Stack with Database
text_chunker_db_stack = TextChunkerDatabaseStack(
    app,
    "solve-global-kr-text-chunker-db",
    env=env,
    description="Text Chunker with Database Integration - Phase 1.5"
)

app.synth()
