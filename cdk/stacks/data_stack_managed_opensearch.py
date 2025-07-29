"""
Data Stack for Climate Risk RAG System - AWS Managed OpenSearch Version
Creates AWS Managed OpenSearch, Neptune, RDS PostgreSQL, and S3 resources
"""

import json
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_opensearch as opensearch,  # Changed from opensearchserverless
    aws_neptune as neptune,
    aws_rds as rds,
    aws_ec2 as ec2,
    aws_secretsmanager as secretsmanager,
    RemovalPolicy,
    CfnOutput,
    Tags,
    Duration
)
from constructs import Construct

class DataStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.vpc = vpc

        # S3 Buckets
        self._create_s3_buckets()
        
        # AWS Managed OpenSearch (cost-effective for your scale)
        self._create_opensearch()
        
        # Neptune for knowledge graph
        self._create_neptune()
        
        # RDS PostgreSQL for metadata
        self._create_rds()

        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Environment", "Development")

    def _create_s3_buckets(self):
        """Create S3 buckets for document storage"""
        
        # Import existing documents bucket
        self.documents_bucket = s3.Bucket.from_bucket_name(
            self, "DocumentsBucket", 
            bucket_name=f"solve-global-kr-documents-{self.account}-{self.region}"
        )
        
        # Import existing chunks bucket (used as artifacts bucket)
        self.artifacts_bucket = s3.Bucket.from_bucket_name(
            self, "ArtifactsBucket", 
            bucket_name=f"solve-global-kr-chunks-{self.account}-{self.region}"
        )

        # Outputs
        CfnOutput(self, "DocumentsBucketName", value=self.documents_bucket.bucket_name)
        CfnOutput(self, "ArtifactsBucketName", value=self.artifacts_bucket.bucket_name)

    def _create_opensearch(self):
        """Create AWS Managed OpenSearch domain for vector and keyword search"""
        
        # Security group for OpenSearch
        self.opensearch_sg = ec2.SecurityGroup(
            self, "OpenSearchSecurityGroup",
            vpc=self.vpc,
            description="Security group for OpenSearch domain",
            allow_all_outbound=True
        )
        
        # Allow HTTPS access from Lambda security group (will be created later)
        self.opensearch_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(443),
            description="HTTPS access from VPC"
        )
        
        # OpenSearch domain configuration
        # Start small for year 1, can scale up for production
        domain_config = {
            "instance_type": "m6g.medium.search",  # Start small: 2 vCPU, 4GB RAM
            "instance_count": 1,  # Single node for year 1
            "dedicated_master_enabled": False,  # No dedicated master for small setup
            "zone_awareness_enabled": False  # Single AZ for cost savings
        }
        
        # For production (100K docs), uncomment this configuration:
        # domain_config = {
        #     "instance_type": "m6g.large.search",  # 2 vCPU, 8GB RAM
        #     "instance_count": 3,  # 3 nodes for HA
        #     "dedicated_master_enabled": True,
        #     "master_instance_type": "m6g.medium.search",
        #     "master_instance_count": 3,
        #     "zone_awareness_enabled": True,
        #     "availability_zone_count": 2
        # }
        
        self.opensearch_domain = opensearch.Domain(
            self, "OpenSearchDomain",
            domain_name="solve-global-kr-search",
            version=opensearch.EngineVersion.OPENSEARCH_2_11,
            
            # Capacity configuration
            capacity=opensearch.CapacityConfig(
                data_node_instance_type=domain_config["instance_type"],
                data_nodes=domain_config["instance_count"],
                master_node_instance_type=domain_config.get("master_instance_type"),
                master_nodes=domain_config.get("master_instance_count", 0) if domain_config.get("dedicated_master_enabled") else 0
            ),
            
            # EBS configuration
            ebs=opensearch.EbsOptions(
                enabled=True,
                volume_type=ec2.EbsDeviceVolumeType.GP3,
                volume_size=20,  # Start with 20GB, auto-scales as needed
                iops=3000,
                throughput=125
            ),
            
            # Network configuration
            vpc=self.vpc,
            vpc_subnets=[ec2.SubnetSelection(
                subnets=self.vpc.private_subnets[:2] if domain_config.get("zone_awareness_enabled") else [self.vpc.private_subnets[0]]
            )],
            security_groups=[self.opensearch_sg],
            
            # Access configuration
            fine_grained_access_control=opensearch.AdvancedSecurityOptions(
                master_user_name="admin",
                master_user_password=secretsmanager.Secret(
                    self, "OpenSearchMasterPassword",
                    description="OpenSearch master user password",
                    generate_secret_string=secretsmanager.SecretStringGenerator(
                        exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/\"\\",
                        include_space=False,
                        password_length=32
                    )
                ).secret_value
            ),
            
            # Encryption
            encryption_at_rest=opensearch.EncryptionAtRestOptions(enabled=True),
            node_to_node_encryption=True,
            enforce_https=True,
            
            # Logging
            logging=opensearch.LoggingOptions(
                slow_search_log_enabled=True,
                app_log_enabled=True,
                slow_index_log_enabled=True
            ),
            
            # Automated snapshots
            automated_snapshot_start_hour=2,  # 2 AM UTC
            
            # Removal policy
            removal_policy=RemovalPolicy.DESTROY  # Change to RETAIN for production
        )
        
        # Output the domain endpoint
        CfnOutput(
            self, "OpenSearchDomainEndpoint",
            value=f"https://{self.opensearch_domain.domain_endpoint}",
            description="OpenSearch domain endpoint"
        )
        
        CfnOutput(
            self, "OpenSearchDomainArn",
            value=self.opensearch_domain.domain_arn,
            description="OpenSearch domain ARN"
        )

    def _create_neptune(self):
        """Create Neptune cluster for knowledge graph"""
        
        # Neptune subnet group
        subnet_group = neptune.CfnDBSubnetGroup(
            self, "NeptuneSubnetGroup",
            db_subnet_group_description="Subnet group for Neptune cluster",
            subnet_ids=[subnet.subnet_id for subnet in self.vpc.private_subnets],
            tags=[
                {"Key": "Name", "Value": "solve-global-kr-neptune-subnet-group"}
            ]
        )

        # Neptune security group
        neptune_sg = ec2.SecurityGroup(
            self, "NeptuneSecurityGroup",
            vpc=self.vpc,
            description="Security group for Neptune cluster",
            allow_all_outbound=False
        )

        # Allow access from Lambda functions (port 8182)
        neptune_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(8182),
            description="Neptune access from VPC"
        )

        # Neptune cluster
        self.neptune_cluster = neptune.CfnDBCluster(
            self, "NeptuneCluster",
            engine="neptune",
            db_subnet_group_name=subnet_group.ref,
            vpc_security_group_ids=[neptune_sg.security_group_id],
            backup_retention_period=7,
            preferred_backup_window="03:00-04:00",
            preferred_maintenance_window="sun:04:00-sun:05:00",
            tags=[
                {"Key": "Name", "Value": "solve-global-kr-neptune-cluster"}
            ]
        )

        # Neptune instance
        self.neptune_instance = neptune.CfnDBInstance(
            self, "NeptuneInstance",
            db_instance_class="db.t3.medium",
            db_cluster_identifier=self.neptune_cluster.ref,
            tags=[
                {"Key": "Name", "Value": "solve-global-kr-neptune-instance"}
            ]
        )

        # Outputs
        CfnOutput(
            self, "NeptuneClusterEndpoint",
            value=self.neptune_cluster.attr_endpoint
        )
        CfnOutput(
            self, "NeptuneClusterReadEndpoint", 
            value=self.neptune_cluster.attr_read_endpoint
        )

    def _create_rds(self):
        """Create RDS PostgreSQL for metadata storage"""
        
        # RDS subnet group
        db_subnet_group = rds.SubnetGroup(
            self, "DatabaseSubnetGroup",
            description="Subnet group for RDS PostgreSQL",
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=self.vpc.private_subnets)
        )

        # RDS security group
        db_sg = ec2.SecurityGroup(
            self, "DatabaseSecurityGroup",
            vpc=self.vpc,
            description="Security group for RDS PostgreSQL",
            allow_all_outbound=False
        )

        # Allow PostgreSQL access from Lambda functions
        db_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(5432),
            description="PostgreSQL access from VPC"
        )

        # RDS PostgreSQL instance
        self.database = rds.DatabaseInstance(
            self, "PostgreSQLDatabase",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15_4
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3, 
                ec2.InstanceSize.MICRO
            ),
            allocated_storage=20,
            storage_type=rds.StorageType.GP2,
            database_name="climate_risk_rag",
            credentials=rds.Credentials.from_generated_secret(
                "postgres",
                secret_name="solve-global-kr-db-credentials"
            ),
            vpc=self.vpc,
            subnet_group=db_subnet_group,
            security_groups=[db_sg],
            backup_retention=Duration.days(7),
            deletion_protection=False,  # Set to True for production
            delete_automated_backups=True,
            removal_policy=RemovalPolicy.DESTROY  # Change to RETAIN for production
        )

        # Output
        CfnOutput(
            self, "DatabaseEndpoint",
            value=self.database.instance_endpoint.hostname
        )
        CfnOutput(
            self, "DatabaseSecretArn",
            value=self.database.secret.secret_arn
        )
