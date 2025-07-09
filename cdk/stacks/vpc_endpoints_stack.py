"""
VPC Endpoints Stack for Climate Risk RAG System
Adds missing SNS and SQS VPC endpoints to existing VPC infrastructure
"""

from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    CfnOutput,
    Tags
)
from constructs import Construct


class VpcEndpointsStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Import existing VPC by ID
        vpc = ec2.Vpc.from_lookup(self, "ExistingVPC", 
                                  vpc_id="vpc-051c21d88c7dc3819")
        
        # Import existing Lambda security group by ID
        lambda_security_group = ec2.SecurityGroup.from_security_group_id(
            self, "LambdaSecurityGroup",
            security_group_id="sg-0c043bcb40f656321"
        )

        # SNS VPC Endpoint - Critical for pipeline messaging
        self.sns_endpoint = vpc.add_interface_endpoint(
            "SNSEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SNS,
            private_dns_enabled=True,
            security_groups=[lambda_security_group],
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            )
        )

        # SQS VPC Endpoint - Critical for pipeline messaging
        self.sqs_endpoint = vpc.add_interface_endpoint(
            "SQSEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SQS,
            private_dns_enabled=True,
            security_groups=[lambda_security_group],
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            )
        )

        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Environment", "Development")
        Tags.of(self).add("Purpose", "Pipeline messaging automation")

        # Outputs
        CfnOutput(
            self, "SNSEndpointId",
            value=self.sns_endpoint.vpc_endpoint_id,
            description="SNS VPC Endpoint ID for pipeline messaging"
        )

        CfnOutput(
            self, "SQSEndpointId", 
            value=self.sqs_endpoint.vpc_endpoint_id,
            description="SQS VPC Endpoint ID for pipeline messaging"
        )

        CfnOutput(
            self, "VpcEndpointsStatus",
            value="SNS and SQS VPC endpoints deployed for full pipeline automation",
            description="VPC endpoints deployment status"
        )
