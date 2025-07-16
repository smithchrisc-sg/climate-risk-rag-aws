#!/usr/bin/env python3
"""
CDK App for Source Document Events
Deploy SNS/SQS infrastructure for source document events
"""

import aws_cdk as cdk
from constructs import Construct
from stacks.source_document_events_stack import SourceDocumentEventsStack

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account="861276078413",
    region="us-east-1"
)

# Stack naming prefix
project_name = "solve-global-kr-rag"

# Source Document Events stack (SNS/SQS for source document events)
source_document_events_stack = SourceDocumentEventsStack(
    app,
    f"{project_name}-source-document-events",
    env=env,
    description="SNS/SQS infrastructure for source document events"
)

app.synth()
