"""
Data Stack for Climate Risk RAG System
Creates OpenSearch, Neptune, RDS PostgreSQL, and S3 resources
"""

from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_opensearchserverless as opensearchserverless,
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
import json


class DataStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.vpc = vpc

        # S3 Buckets
        self._create_s3_buckets()
        
        # OpenSearch Serverless (cost-effective for your scale)
        self._create_opensearch()
        
        # Neptune for knowledge graph
        self._create_neptune()
        
        # RDS PostgreSQL for metadata
        self._create_rds()

        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Environment", "Development")

    def _create_s3_buckets(self):
        """Import existing S3 buckets for document storage and processing"""
        
        # Import existing document storage bucket
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
        """Create OpenSearch Serverless collection for vector and keyword search"""
        
        # OpenSearch Serverless collection (cost optimized - no standby replicas)
        self.opensearch_collection = opensearchserverless.CfnCollection(
            self, "OpenSearchCollection",
            name="solve-global-kr-search-v2",  # New name to avoid conflicts
            type="SEARCH",  # Optimized for search workloads
            description="Climate Risk RAG search collection - cost optimized"
        )

        # Security policy for the collection
        security_policy = opensearchserverless.CfnSecurityPolicy(
            self, "OpenSearchSecurityPolicy",
            name="solve-global-kr-security-policy",
            type="encryption",
            policy=json.dumps({
                "Rules": [
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/solve-global-kr-search-v2"]
                    }
                ],
                "AWSOwnedKey": True
            })
        )

        # Network policy for VPC access
        network_policy = opensearchserverless.CfnSecurityPolicy(
            self, "OpenSearchNetworkPolicy",
            name="solve-global-kr-network-policy",
            type="network",
            policy=json.dumps([
                {
                    "Rules": [
                        {
                            "ResourceType": "collection",
                            "Resource": [f"collection/solve-global-kr-search-v2"]
                        },
                        {
                            "ResourceType": "dashboard",
                            "Resource": [f"collection/solve-global-kr-search-v2"]
                        }
                    ],
                    "AllowFromPublic": True
                }
            ])
        )

        self.opensearch_collection.add_dependency(security_policy)
        self.opensearch_collection.add_dependency(network_policy)

        # Output
        CfnOutput(
            self, "OpenSearchCollectionEndpoint",
            value=self.opensearch_collection.attr_collection_endpoint
        )

    def _create_neptune(self):
        """Create Neptune cluster for knowledge graph"""
        
        # Neptune subnet group
        subnet_group = neptune.CfnDBSubnetGroup(
            self, "NeptuneSubnetGroup",
            db_subnet_group_description="Subnet group for Neptune cluster",
            subnet_ids=[subnet.subnet_id for subnet in self.vpc.private_subnets],
            db_subnet_group_name="solve-global-kr-neptune-subnet-group"
        )

        # Neptune cluster parameter group
        cluster_param_group = neptune.CfnDBClusterParameterGroup(
            self, "NeptuneClusterParameterGroup",
            family="neptune1.3",
            description="Parameter group for Neptune cluster",
            name="solve-global-kr-neptune-cluster-params",
            parameters={
                "neptune_enable_audit_log": "1",
                "neptune_query_timeout": "120000"
            }
        )

        # Neptune cluster
        self.neptune_cluster = neptune.CfnDBCluster(
            self, "NeptuneCluster",
            db_cluster_identifier="solve-global-kr-neptune",
            engine_version="1.3.1.0",
            db_subnet_group_name=subnet_group.ref,
            vpc_security_group_ids=[self.vpc.vpc_default_security_group],
            backup_retention_period=7,
            preferred_backup_window="03:00-04:00",
            preferred_maintenance_window="sun:04:00-sun:05:00",
            db_cluster_parameter_group_name=cluster_param_group.ref,
            deletion_protection=False,  # Set to True for production
            storage_encrypted=True
        )

        # Neptune instance
        self.neptune_instance = neptune.CfnDBInstance(
            self, "NeptuneInstance",
            db_instance_class="db.t3.medium",
            db_cluster_identifier=self.neptune_cluster.ref,
            db_instance_identifier="solve-global-kr-neptune-instance"
        )

        self.neptune_cluster.add_dependency(subnet_group)
        self.neptune_cluster.add_dependency(cluster_param_group)
        self.neptune_instance.add_dependency(self.neptune_cluster)

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
        
        # Create secret for database credentials
        self.db_secret = secretsmanager.Secret(
            self, "DatabaseSecret",
            description="Climate Risk RAG database credentials",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "postgres"}',
                generate_string_key="password",
                exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/\"\\,@",
                password_length=32
            )
        )

        # RDS subnet group
        subnet_group = rds.SubnetGroup(
            self, "DatabaseSubnetGroup",
            description="Subnet group for RDS PostgreSQL",
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED)
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
            vpc=self.vpc,
            subnet_group=subnet_group,
            credentials=rds.Credentials.from_secret(self.db_secret),
            database_name="climate_risk_rag",
            allocated_storage=20,
            max_allocated_storage=100,
            storage_type=rds.StorageType.GP2,
            backup_retention=Duration.days(7),
            preferred_backup_window="03:00-04:00",
            preferred_maintenance_window="sun:04:00-sun:05:00",
            deletion_protection=False,  # Set to True for production
            delete_automated_backups=True,
            removal_policy=RemovalPolicy.DESTROY  # Change for production
        )

        # Outputs
        CfnOutput(
            self, "DatabaseEndpoint",
            value=self.database.instance_endpoint.hostname
        )
        CfnOutput(
            self, "DatabaseSecretArn",
            value=self.db_secret.secret_arn
        )
