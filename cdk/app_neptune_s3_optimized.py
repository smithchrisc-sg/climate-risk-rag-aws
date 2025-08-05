#!/usr/bin/env python3
"""
Neptune Cluster with S3-Optimized Routing CDK App

Creates a new Neptune cluster with dedicated subnets that have S3 VPC endpoint routing only,
eliminating the routing ambiguity that prevents bulk loading from working.

Key Features:
- New Neptune cluster with proper subnet group
- S3-only routing (no NAT gateway conflicts)
- Proper IAM roles and security groups
- Compatible with existing infrastructure
"""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_neptune as neptune,
    aws_iam as iam,
    Duration,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct

class NeptuneS3OptimizedStack(Stack):
    """Neptune cluster with S3-optimized routing for bulk loading"""
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Import existing VPC
        self.vpc = ec2.Vpc.from_lookup(self, "ExistingVPC", vpc_id="vpc-051c21d88c7dc3819")
        
        # Import the new S3-optimized subnets we created
        self.neptune_s3_subnet_1 = ec2.Subnet.from_subnet_id(
            self, "NeptuneS3Subnet1", 
            subnet_id="subnet-0a487c41b9eef90f7"  # 10.0.101.0/24, us-east-1a
        )
        self.neptune_s3_subnet_2 = ec2.Subnet.from_subnet_id(
            self, "NeptuneS3Subnet2", 
            subnet_id="subnet-0e7befb231398ba54"  # 10.0.102.0/24, us-east-1b
        )
        
        # Create Neptune security group
        self.neptune_sg = ec2.SecurityGroup(
            self, "NeptuneS3SecurityGroup",
            vpc=self.vpc,
            description="Security group for Neptune cluster with S3-optimized routing",
            allow_all_outbound=False
        )
        
        # Import existing Lambda security group for access
        self.lambda_sg = ec2.SecurityGroup.from_security_group_id(
            self, "LambdaSecurityGroup", 
            security_group_id="sg-0c9e10b9cfb4c9eb0"
        )
        
        # Add ingress rule for Lambda access to Neptune
        self.neptune_sg.add_ingress_rule(
            peer=self.lambda_sg,
            connection=ec2.Port.tcp(8182),
            description="Allow Lambda access to Neptune SPARQL/Gremlin endpoint"
        )
        
        # Create Neptune subnet group with S3-optimized subnets
        self.neptune_subnet_group = neptune.CfnDBSubnetGroup(
            self, "NeptuneS3SubnetGroup",
            db_subnet_group_name="solve-global-kr-neptune-s3-optimized",
            db_subnet_group_description="Neptune subnet group with S3 VPC endpoint routing only (no NAT conflicts)",
            subnet_ids=[
                self.neptune_s3_subnet_1.subnet_id,
                self.neptune_s3_subnet_2.subnet_id
            ],
            tags=[
                cdk.CfnTag(key="Project", value="ClimateRiskRAG"),
                cdk.CfnTag(key="Environment", value="Development"),
                cdk.CfnTag(key="Purpose", value="S3-optimized Neptune routing")
            ]
        )
        
        # Create Neptune cluster parameter group for optimization
        self.neptune_cluster_param_group = neptune.CfnDBClusterParameterGroup(
            self, "NeptuneS3ClusterParamGroup",
            family="neptune1.3",
            description="Neptune cluster parameters optimized for bulk loading",
            name="solve-global-kr-neptune-s3-cluster-params",
            parameters={
                "neptune_enable_audit_log": "0",  # Disable audit logging for performance
                "neptune_query_timeout": "120000",  # 2 minutes query timeout
                "neptune_result_cache": "1"  # Enable result caching
            },
            tags=[
                cdk.CfnTag(key="Project", value="ClimateRiskRAG"),
                cdk.CfnTag(key="Environment", value="Development")
            ]
        )
        
        # Import existing Neptune service role
        self.neptune_service_role = iam.Role.from_role_arn(
            self, "NeptuneServiceRole",
            role_arn="arn:aws:iam::861276078413:role/NeptuneLoadFromS3Role"
        )
        
        # Create Neptune cluster with S3-optimized configuration
        self.neptune_cluster = neptune.CfnDBCluster(
            self, "NeptuneS3Cluster",
            db_cluster_identifier="solve-global-kr-neptune-s3",
            engine_version="1.3.2.1",
            db_subnet_group_name=self.neptune_subnet_group.db_subnet_group_name,
            vpc_security_group_ids=[self.neptune_sg.security_group_id],
            db_cluster_parameter_group_name=self.neptune_cluster_param_group.name,
            backup_retention_period=7,
            preferred_backup_window="03:00-04:00",
            preferred_maintenance_window="sun:04:00-sun:05:00",
            storage_encrypted=True,
            associated_roles=[
                neptune.CfnDBCluster.DBClusterRoleProperty(
                    role_arn=self.neptune_service_role.role_arn
                )
            ],
            deletion_protection=False,  # Allow deletion for development
            tags=[
                cdk.CfnTag(key="Project", value="ClimateRiskRAG"),
                cdk.CfnTag(key="Environment", value="Development"),
                cdk.CfnTag(key="Purpose", value="S3-optimized bulk loading")
            ]
        )
        
        # Add dependency on subnet group and parameter group
        self.neptune_cluster.add_dependency(self.neptune_subnet_group)
        self.neptune_cluster.add_dependency(self.neptune_cluster_param_group)
        
        # Create Neptune instance
        self.neptune_instance = neptune.CfnDBInstance(
            self, "NeptuneS3Instance",
            db_instance_class="db.t3.medium",
            db_instance_identifier="solve-global-kr-neptune-s3-instance",
            db_cluster_identifier=self.neptune_cluster.db_cluster_identifier,
            tags=[
                cdk.CfnTag(key="Project", value="ClimateRiskRAG"),
                cdk.CfnTag(key="Environment", value="Development")
            ]
        )
        
        # Add dependency on cluster
        self.neptune_instance.add_dependency(self.neptune_cluster)
        
        # Outputs for easy reference
        CfnOutput(
            self, "NeptuneClusterEndpoint",
            value=self.neptune_cluster.attr_endpoint,
            description="Neptune cluster endpoint for S3-optimized bulk loading"
        )
        
        CfnOutput(
            self, "NeptuneClusterReadEndpoint", 
            value=self.neptune_cluster.attr_read_endpoint,
            description="Neptune cluster read endpoint"
        )
        
        CfnOutput(
            self, "NeptuneInstanceEndpoint",
            value=self.neptune_instance.attr_endpoint,
            description="Neptune instance endpoint"
        )
        
        CfnOutput(
            self, "NeptuneSubnetGroup",
            value=self.neptune_subnet_group.db_subnet_group_name,
            description="Neptune subnet group with S3-optimized routing"
        )
        
        CfnOutput(
            self, "NeptuneSecurityGroup",
            value=self.neptune_sg.security_group_id,
            description="Neptune security group ID"
        )

# CDK App
app = cdk.App()

# Deploy Neptune with S3-optimized routing
NeptuneS3OptimizedStack(
    app, 
    "solve-global-kr-neptune-s3",
    env=cdk.Environment(
        account="861276078413",
        region="us-east-1"
    ),
    description="Neptune cluster with S3-optimized routing for bulk loading"
)

app.synth()
