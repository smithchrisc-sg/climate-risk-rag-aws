"""
AI/ML Stack for Climate Risk RAG System
Creates IAM roles and policies for AI/ML services
"""

from aws_cdk import (
    Stack,
    aws_iam as iam,
    CfnOutput,
    Tags
)
from constructs import Construct


class AiMlStack(Stack):
    def __init__(self, scope, construct_id, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Create IAM role for Lambda functions to access AI/ML services
        self._create_ai_ml_role()

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
            resources=["*"]  # Simplified - avoid f-string issues
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
                "arn:aws:s3:::solve-global-kr-chunks-*/*",
                "arn:aws:s3:::solve-global-kr-ner-results-*/*"
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
            resources=["*"]  # Simplified
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
