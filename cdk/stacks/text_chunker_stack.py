"""
Text Chunker Stack - Phase 1 Deployment
Simplified version for lambda deployment testing without full VPC integration
"""

import json
from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_logs as logs,
    Duration,
    CfnOutput,
    Tags
)
from constructs import Construct


class TextChunkerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
                 vpc, messaging_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create lambda layers for shared dependencies
        self._create_lambda_layers()
        
        # Create text chunker lambda function (simplified for Phase 1)
        self._create_text_chunker_lambda()
        
        # Create outputs
        self._create_outputs()

        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Component", "TextChunker")
        Tags.of(self).add("Phase", "Phase1-Testing")

    def _create_lambda_layers(self):
        """Create lambda layers for shared dependencies"""
        
        # Climate Risk Core Layer (DocumentIDManager, DatabaseManager, etc.)
        self.climate_risk_core_layer = lambda_.LayerVersion(
            self, "ClimateRiskCoreLayer",
            layer_version_name="climate-risk-core-utilities",
            code=lambda_.Code.from_asset("../layers/build/climate-risk-core-layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Core application utilities (DocumentIDManager, DatabaseManager, etc.)",
        )

    def _create_text_chunker_lambda(self):
        """Create the text chunker lambda function for Phase 1 testing"""
        
        # Environment variables for text chunker
        text_chunker_env = {
            'CHUNKS_BUCKET': f'solve-global-kr-chunks-{self.account}-{self.region}',
            'TEXT_BUCKET': f'solve-global-kr-text-new-{self.account}-{self.region}',
            'DATABASE_URL': 'postgresql://postgres:-VroWHWQBS5!V)yAcsDC3(3)NHJ5@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require',
            'PHASE': 'PHASE1_TESTING',
            'COORDINATION_TOPIC_ARN': '',  # Empty for Phase 1
        }
        
        # Create IAM role for text chunker
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
                        )
                    ]
                )
            }
        )
        
        # Text Chunker Lambda Function
        self.text_chunker_function = lambda_.Function(
            self, "TextChunkerFunction",
            function_name="solve-global-kr-text-chunker-phase1",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="text_chunker_processor.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/text_chunker"),
            timeout=Duration.minutes(5),  # Shorter timeout for Phase 1 testing
            memory_size=512,  # Lower memory for Phase 1 testing
            environment=text_chunker_env,
            role=self.text_chunker_role,
            layers=[
                self.climate_risk_core_layer
            ],
            description="Text chunker Phase 1 - Lambda deployment testing",
            log_retention=logs.RetentionDays.ONE_WEEK
        )

    def _create_outputs(self):
        """Create CloudFormation outputs"""
        
        CfnOutput(
            self, "TextChunkerFunctionName",
            value=self.text_chunker_function.function_name,
            description="Text Chunker Lambda function name"
        )
        
        CfnOutput(
            self, "TextChunkerFunctionArn", 
            value=self.text_chunker_function.function_arn,
            description="Text Chunker Lambda function ARN"
        )
        
        CfnOutput(
            self, "ClimateRiskCoreLayerArn",
            value=self.climate_risk_core_layer.layer_version_arn,
            description="Climate Risk Core Layer ARN"
        )
