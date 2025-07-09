#!/usr/bin/env python3
"""
CDK App for VPC Endpoints Deployment
Deploys missing SNS and SQS VPC endpoints to complete infrastructure
"""

import aws_cdk as cdk
from stacks.vpc_endpoints_stack import VpcEndpointsStack

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account="861276078413",
    region="us-east-1"
)

# VPC Endpoints stack - adds missing endpoints for full automation
vpc_endpoints_stack = VpcEndpointsStack(
    app, 
    "solve-global-kr-rag-vpc-endpoints",
    env=env,
    description="VPC endpoints for SNS and SQS to enable full pipeline automation"
)

app.synth()
