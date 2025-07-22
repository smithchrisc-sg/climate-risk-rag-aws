#!/usr/bin/env python3
"""
Climate Risk RAG System - Main CDK Application
Updated to reflect current standardized architecture with proper layers and IAM roles
"""

import aws_cdk as cdk
from stacks.data_stack import DataStack
from stacks.networking_stack import NetworkingStack
from stacks.compute_stack import ComputeStack
from stacks.ai_ml_stack import AiMlStack

# Import our new standardized stacks
from app_complete_standardized import (
    DocumentProcessingLambdaRoleConstruct,
    StandardizedLambdaLayersConstruct,
    MessagingInfrastructureStack,
    DocumentProcessingStack,
    S3NotificationStack
)

class ClimateRiskRAGStandardizedApp(cdk.App):
    """
    Main CDK application for Climate Risk RAG system
    Uses standardized layers and proper IAM roles
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Environment configuration
        env = cdk.Environment(
            account="861276078413",
            region="us-east-1"
        )
        
        # VPC configuration (from existing infrastructure)
        vpc_config = {
            "vpc_id": "vpc-0123456789abcdef0",  # Update with actual VPC ID
            "subnet_ids": [
                "subnet-03d8bd6cf3491f38c",
                "subnet-0c0be1dd59f70f70e"
            ],
            "security_group_id": "sg-0c9e10b9cfb4c9eb0"
        }
        
        # Core infrastructure stacks (existing)
        data_stack = DataStack(
            self, "ClimateRiskRAGDataStack",
            env=env,
            description="RDS PostgreSQL and Neptune databases for Climate Risk RAG"
        )
        
        networking_stack = NetworkingStack(
            self, "ClimateRiskRAGNetworkingStack", 
            env=env,
            description="VPC, subnets, and networking for Climate Risk RAG"
        )
        
        ai_ml_stack = AiMlStack(
            self, "ClimateRiskRAGAiMlStack",
            env=env,
            description="OpenSearch domain for vector search"
        )
        
        # New standardized messaging infrastructure
        messaging_stack = MessagingInfrastructureStack(
            self, "ClimateRiskRAGMessaging",
            env=env,
            description="SNS topics and SQS queues for document processing pipeline"
        )
        
        # New standardized document processing stack
        document_processing_stack = DocumentProcessingStack(
            self, "ClimateRiskRAGDocumentProcessing",
            messaging_stack=messaging_stack,
            env=env,
            description="Lambda functions for document processing with standardized layers",
            **vpc_config
        )
        
        # S3 notification configuration
        s3_notification_stack = S3NotificationStack(
            self, "ClimateRiskRAGS3Notifications",
            messaging_stack=messaging_stack,
            env=env,
            description="S3 bucket notifications for document processing triggers"
        )
        
        # Legacy compute stack (for remaining functions not yet migrated)
        compute_stack = ComputeStack(
            self, "ClimateRiskRAGComputeStack",
            data_stack=data_stack,
            networking_stack=networking_stack,
            ai_ml_stack=ai_ml_stack,
            env=env,
            description="Legacy Lambda functions (to be migrated to standardized approach)"
        )
        
        # Stack dependencies
        messaging_stack.add_dependency(networking_stack)
        document_processing_stack.add_dependency(messaging_stack)
        document_processing_stack.add_dependency(data_stack)
        s3_notification_stack.add_dependency(messaging_stack)
        compute_stack.add_dependency(data_stack)
        compute_stack.add_dependency(networking_stack)
        compute_stack.add_dependency(ai_ml_stack)
        
        # Add tags to all stacks
        cdk.Tags.of(self).add("Project", "ClimateRiskRAG")
        cdk.Tags.of(self).add("Environment", "Production")
        cdk.Tags.of(self).add("Architecture", "Standardized")
        cdk.Tags.of(self).add("DeploymentMethod", "CDK")

if __name__ == "__main__":
    app = ClimateRiskRAGStandardizedApp()
    app.synth()
