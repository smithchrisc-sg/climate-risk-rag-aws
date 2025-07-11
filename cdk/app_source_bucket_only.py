#!/usr/bin/env python3
"""
Standalone CDK App for Source Documents Bucket
Simple deployment to add the source documents bucket without complex dependencies
"""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_iam as iam,
    RemovalPolicy,
    CfnOutput,
    Tags,
    Duration
)
from constructs import Construct


class SourceDocumentsBucketStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create the source documents bucket
        self.source_documents_bucket = s3.Bucket(
            self, "SourceDocumentsBucket",
            bucket_name=f"solve-global-kr-dl-source-documents-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.RETAIN,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            # Enable event notifications for Lambda triggers
            event_bridge_enabled=True,
            # CORS configuration for potential web uploads
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                    max_age=3000
                )
            ],
            # Lifecycle configuration to manage costs
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteIncompleteMultipartUploads",
                    abort_incomplete_multipart_upload_after=Duration.days(7)
                )
            ]
        )
        
        # Add bucket policy for Lambda access
        self.source_documents_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="LambdaAccess",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("lambda.amazonaws.com")],
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBucket"
                ],
                resources=[
                    self.source_documents_bucket.bucket_arn,
                    f"{self.source_documents_bucket.bucket_arn}/*"
                ]
            )
        )
        
        # Output the bucket name
        CfnOutput(
            self, "SourceDocumentsBucketName", 
            value=self.source_documents_bucket.bucket_name,
            description="Name of the source documents bucket for end-state testing"
        )
        
        CfnOutput(
            self, "SourceDocumentsBucketArn",
            value=self.source_documents_bucket.bucket_arn,
            description="ARN of the source documents bucket"
        )
        
        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Environment", "Development")
        Tags.of(self).add("Purpose", "EndStateTesting")


# Create the CDK app
app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account="861276078413",
    region="us-east-1"
)

# Create the source documents bucket stack
source_bucket_stack = SourceDocumentsBucketStack(
    app,
    "solve-global-kr-source-documents-bucket",
    env=env,
    description="Source documents bucket for end-state pipeline testing"
)

app.synth()
