#!/usr/bin/env python3
"""
CDK App for Neptune Connectivity Test Lambda - FIXED
Deploy a Lambda function in the VPC to test Neptune connectivity
"""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_ec2 as ec2,
    aws_iam as iam,
    Duration,
    Environment
)
from constructs import Construct

class NeptuneTestStack(Stack):
    """Stack for Neptune connectivity test Lambda"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Use existing VPC
        vpc = ec2.Vpc.from_lookup(
            self, "ExistingVPC",
            vpc_id="vpc-051c21d88c7dc3819"
        )

        # Use existing Lambda security group
        lambda_security_group = ec2.SecurityGroup.from_security_group_id(
            self, "LambdaSecurityGroup",
            security_group_id="sg-0c043bcb40f656321"
        )

        # Create Lambda function for Neptune testing
        neptune_test_lambda = _lambda.Function(
            self, "NeptuneTestLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="neptune_test_lambda.lambda_handler",
            code=_lambda.Code.from_asset("../src/knowledge_graph"),
            timeout=Duration.minutes(5),
            memory_size=256,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[lambda_security_group],
            environment={
                "NEPTUNE_ENDPOINT": "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
            }
        )

        # Add permissions for Neptune access (if needed)
        neptune_test_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "neptune-db:*"
                ],
                resources=["*"]
            )
        )

        # Output the Lambda function name
        cdk.CfnOutput(
            self, "NeptuneTestLambdaName",
            value=neptune_test_lambda.function_name,
            description="Name of the Neptune test Lambda function"
        )

# Create app with proper environment
app = cdk.App()

# Define environment
env = Environment(
    account="861276078413",
    region="us-east-1"
)

NeptuneTestStack(
    app, 
    "neptune-test-stack",
    env=env,
    description="Lambda function to test Neptune connectivity from within VPC"
)

app.synth()
