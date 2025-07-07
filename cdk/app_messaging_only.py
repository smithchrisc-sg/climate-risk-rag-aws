#!/usr/bin/env python3
"""
Temporary CDK App for TextExtractor Messaging Only
Deploy messaging infrastructure first to avoid circular dependencies
"""

import aws_cdk as cdk
from constructs import Construct
from stacks.textextractor_messaging_stack import TextExtractorMessagingStack

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region") or "us-east-1"
)

# Stack naming prefix
project_name = "solve-global-kr-rag"

# TextExtractor Messaging stack (SNS/SQS for async processing)
textextractor_messaging_stack = TextExtractorMessagingStack(
    app,
    f"{project_name}-textextractor-messaging",
    env=env,
    description="SNS/SQS messaging infrastructure for TextExtractor async processing"
)

app.synth()
