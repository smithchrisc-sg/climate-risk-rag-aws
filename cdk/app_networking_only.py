#!/usr/bin/env python3
"""
Minimal CDK App for Networking Stack Only
Used to deploy VPC endpoints without other stack dependencies
"""

import aws_cdk as cdk
from stacks.networking_stack import NetworkingStack

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account="861276078413",
    region="us-east-1"
)

# Stack naming prefix
project_name = "solve-global-kr-rag"

# Networking stack only (VPC, subnets, security groups, VPC endpoints)
networking_stack = NetworkingStack(
    app, 
    f"{project_name}-networking",
    env=env,
    description="Networking infrastructure for Climate Risk RAG system with VPC endpoints"
)

app.synth()
