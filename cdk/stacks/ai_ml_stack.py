"""
AI/ML Stack for Climate Risk RAG System
Creates IAM roles and policies for Bedrock, Textract, Comprehend, and Titan
"""

from aws_cdk import (
    Stack,
    aws_iam as iam,
    # aws_bedrock as bedrock,  # Temporarily commented out - import issue
    CfnOutput,
    Tags
)
from constructs import Construct


class AiMlStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create IAM role for Lambda functions to access AI/ML services
        self._create_ai_ml_role()
        
        # Enable Bedrock model access
        self._enable_bedrock_models()

        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Environment", "Development")

    def _create_ai_ml_role(self):
        """Create IAM role with permissions for AI/ML services"""
        
        self.ai_ml_role = iam.Role(
            self, "AiMlServiceRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Role for Lambda functions to access AI/ML services",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole")
            ]
        )

        # Bedrock permissions
        bedrock_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:ListFoundationModels",
                "bedrock:GetFoundationModel"
            ],
            resources=[
                f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v1",
                f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-text-lite-v1",
                f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-text-express-v1",
                f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
                f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
            ]
        )

        # Textract permissions
        textract_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "textract:DetectDocumentText",
                "textract:AnalyzeDocument",
                "textract:StartDocumentAnalysis",
                "textract:GetDocumentAnalysis",
                "textract:StartDocumentTextDetection",
                "textract:GetDocumentTextDetection"
            ],
            resources=["*"]
        )

        # Comprehend permissions
        comprehend_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "comprehend:DetectEntities",
                "comprehend:DetectKeyPhrases",
                "comprehend:DetectSentiment",
                "comprehend:DetectSyntax",
                "comprehend:DetectPiiEntities",
                "comprehend:ClassifyDocument"
            ],
            resources=["*"]
        )

        # S3 permissions for AI/ML services
        s3_ai_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            resources=[
                "arn:aws:s3:::solve-global-kr-documents-*/*",
                "arn:aws:s3:::solve-global-kr-chunks-*/*"
            ]
        )

        # CloudWatch Logs permissions
        logs_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            resources=[f"arn:aws:logs:{self.region}:{self.account}:*"]
        )

        # Add policies to role
        self.ai_ml_role.add_to_policy(bedrock_policy)
        self.ai_ml_role.add_to_policy(textract_policy)
        self.ai_ml_role.add_to_policy(comprehend_policy)
        self.ai_ml_role.add_to_policy(s3_ai_policy)
        self.ai_ml_role.add_to_policy(logs_policy)

        # Output
        CfnOutput(
            self, "AiMlRoleArn",
            value=self.ai_ml_role.role_arn,
            description="IAM role ARN for AI/ML services"
        )

    def _enable_bedrock_models(self):
        """Enable access to Bedrock foundation models"""
        
        # Note: Model access needs to be enabled manually in the Bedrock console
        # or via AWS CLI for the first time. This is a one-time setup.
        
        # Create a custom resource to document required models
        models_to_enable = [
            "amazon.titan-embed-text-v1",      # For embeddings
            "amazon.titan-text-lite-v1",       # For lightweight text generation
            "amazon.titan-text-express-v1",    # For more capable text generation
            "anthropic.claude-3-haiku-20240307-v1:0",   # Fast, cost-effective
            "anthropic.claude-3-sonnet-20240229-v1:0"   # More capable reasoning
        ]

        # Output the models that need to be enabled
        CfnOutput(
            self, "BedrockModelsToEnable",
            value=",".join(models_to_enable),
            description="Bedrock models that need to be enabled manually"
        )

        # Create a policy document for reference
        self.bedrock_model_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["bedrock:InvokeModel"],
                    resources=[
                        f"arn:aws:bedrock:{self.region}::foundation-model/{model}"
                        for model in models_to_enable
                    ]
                )
            ]
        )
