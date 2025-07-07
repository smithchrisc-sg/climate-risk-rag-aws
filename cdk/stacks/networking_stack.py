"""
Networking Stack for Climate Risk RAG System
Creates VPC, subnets, security groups, and networking components
"""

from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    CfnOutput,
    Tags
)
from constructs import Construct


class NetworkingStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC with public and private subnets across 2 AZs
        self.vpc = ec2.Vpc(
            self, "ClimateRiskVPC",
            vpc_name="solve-global-kr-rag-vpc",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="PublicSubnet",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="PrivateSubnet",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="IsolatedSubnet",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24
                )
            ],
            enable_dns_hostnames=True,
            enable_dns_support=True
        )

        # Security group for Lambda functions
        self.lambda_security_group = ec2.SecurityGroup(
            self, "LambdaSecurityGroup",
            vpc=self.vpc,
            description="Security group for Lambda functions",
            allow_all_outbound=True
        )

        # Security group for OpenSearch
        self.opensearch_security_group = ec2.SecurityGroup(
            self, "OpenSearchSecurityGroup",
            vpc=self.vpc,
            description="Security group for OpenSearch cluster",
            allow_all_outbound=False
        )

        # Allow Lambda to access OpenSearch
        self.opensearch_security_group.add_ingress_rule(
            peer=self.lambda_security_group,
            connection=ec2.Port.tcp(443),
            description="Allow Lambda access to OpenSearch"
        )

        # Security group for Neptune
        self.neptune_security_group = ec2.SecurityGroup(
            self, "NeptuneSecurityGroup",
            vpc=self.vpc,
            description="Security group for Neptune cluster",
            allow_all_outbound=False
        )

        # Allow Lambda to access Neptune
        self.neptune_security_group.add_ingress_rule(
            peer=self.lambda_security_group,
            connection=ec2.Port.tcp(8182),
            description="Allow Lambda access to Neptune"
        )

        # Security group for RDS
        self.rds_security_group = ec2.SecurityGroup(
            self, "RDSSecurityGroup",
            vpc=self.vpc,
            description="Security group for RDS PostgreSQL",
            allow_all_outbound=False
        )

        # Allow Lambda to access RDS
        self.rds_security_group.add_ingress_rule(
            peer=self.lambda_security_group,
            connection=ec2.Port.tcp(5432),
            description="Allow Lambda access to PostgreSQL"
        )

        # VPC Endpoints for AWS services (cost optimization)
        self.s3_endpoint = self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3
        )

        # Interface endpoints for other AWS services
        self.bedrock_endpoint = self.vpc.add_interface_endpoint(
            "BedrockEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.BEDROCK_RUNTIME,
            private_dns_enabled=True,
            security_groups=[self.lambda_security_group]
        )

        self.textract_endpoint = self.vpc.add_interface_endpoint(
            "TextractEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.TEXTRACT,
            private_dns_enabled=True,
            security_groups=[self.lambda_security_group]
        )

        self.comprehend_endpoint = self.vpc.add_interface_endpoint(
            "ComprehendEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.COMPREHEND,
            private_dns_enabled=True,
            security_groups=[self.lambda_security_group]
        )

        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Environment", "Development")

        # Outputs
        CfnOutput(
            self, "VPCId",
            value=self.vpc.vpc_id,
            description="VPC ID"
        )

        CfnOutput(
            self, "PrivateSubnetIds",
            value=",".join([subnet.subnet_id for subnet in self.vpc.private_subnets]),
            description="Private subnet IDs"
        )
