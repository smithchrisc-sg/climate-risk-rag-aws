#!/usr/bin/env python3
"""
Text Chunker CDK App - Phase 1 Deployment
"""

import aws_cdk as cdk
from stacks.text_chunker_stack import TextChunkerStack

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account="861276078413",
    region="us-east-1"
)

# For Phase 1, we'll create a minimal deployment without full messaging integration
# This allows us to test the lambda function deployment and layer access

# Create a minimal VPC reference (assuming existing VPC)
# In production, this would reference the actual networking stack
class MockVpc:
    def __init__(self):
        pass

mock_vpc = MockVpc()

# Create a minimal messaging stack reference
class MockMessagingStack:
    def __init__(self):
        pass

mock_messaging = MockMessagingStack()

# Text Chunker Stack
text_chunker_stack = TextChunkerStack(
    app,
    "solve-global-kr-text-chunker-phase1",
    vpc=mock_vpc,
    messaging_stack=mock_messaging,
    env=env,
    description="Text Chunker Phase 1 - Lambda deployment testing"
)

app.synth()
