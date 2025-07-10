#!/usr/bin/env python3
"""
Deploy only the data stack for OpenSearch optimization
"""

import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2
from stacks.data_stack import DataStack

app = cdk.App()

# Environment
env = cdk.Environment(
    account="861276078413",
    region="us-east-1"
)

# Create a temporary stack to lookup VPC
class VpcLookupStack(cdk.Stack):
    def __init__(self, scope, construct_id, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        self.vpc = ec2.Vpc.from_lookup(
            self, "ExistingVpc",
            vpc_id="vpc-051c21d88c7dc3819"
        )

# Create VPC lookup stack
vpc_stack = VpcLookupStack(app, "vpc-lookup", env=env)

# Data stack only
data_stack = DataStack(
    app,
    "solve-global-kr-rag-data",
    vpc=vpc_stack.vpc,
    env=env,
    description="Data layer infrastructure (OpenSearch, Neptune, RDS) - Cost Optimized"
)

app.synth()
