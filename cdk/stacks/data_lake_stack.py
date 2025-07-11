"""
Data Lake Stack for Climate Risk RAG System
Creates S3 buckets with proper structure for microservices data lake architecture
"""

from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    RemovalPolicy,
    CfnOutput,
    Tags,
    Duration
)
from constructs import Construct


class DataLakeStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create S3 buckets for data lake architecture
        self._create_data_lake_buckets()
        
        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Environment", "Development")
        Tags.of(self).add("Architecture", "DataLake")

    def _create_data_lake_buckets(self):
        """Create S3 buckets for data lake"""
        
        # Source documents bucket (end-state simulation)
        self.source_documents_bucket = s3.Bucket(
            self, "SourceDocumentsBucket",
            bucket_name=f"solve-global-kr-dl-source-documents-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.RETAIN,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            # Enable event notifications for Lambda triggers
            event_bridge_enabled=True
        )
        
        # Documents bucket (legacy/existing)
        self.documents_bucket = s3.Bucket(
            self, "DocumentsBucket",
            bucket_name=f"solve-global-kr-documents-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.RETAIN,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        # Extracted text bucket
        self.extracted_text_bucket = s3.Bucket(
            self, "ExtractedTextBucket",
            bucket_name=f"solve-global-kr-text-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.RETAIN,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        # Chunks bucket
        self.chunks_bucket = s3.Bucket(
            self, "ChunksBucket",
            bucket_name=f"solve-global-kr-chunks-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.RETAIN,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        # Embeddings bucket
        self.embeddings_bucket = s3.Bucket(
            self, "EmbeddingsBucket",
            bucket_name=f"solve-global-kr-embeddings-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.RETAIN,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        # NER results bucket
        self.ner_results_bucket = s3.Bucket(
            self, "NERResultsBucket",
            bucket_name=f"solve-global-kr-ner-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.RETAIN,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        # Knowledge graph bucket
        self.knowledge_graph_bucket = s3.Bucket(
            self, "KnowledgeGraphBucket",
            bucket_name=f"solve-global-kr-kg-data-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.RETAIN,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        # Processing metadata bucket
        self.processing_metadata_bucket = s3.Bucket(
            self, "ProcessingMetadataBucket",
            bucket_name=f"solve-global-kr-cache-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.RETAIN,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED
        )
        
        # Outputs
        CfnOutput(self, "SourceDocumentsBucketName", value=self.source_documents_bucket.bucket_name)
        CfnOutput(self, "DocumentsBucketName", value=self.documents_bucket.bucket_name)
        CfnOutput(self, "ExtractedTextBucketName", value=self.extracted_text_bucket.bucket_name)
        CfnOutput(self, "ChunksBucketName", value=self.chunks_bucket.bucket_name)
        CfnOutput(self, "EmbeddingsBucketName", value=self.embeddings_bucket.bucket_name)
        CfnOutput(self, "NERResultsBucketName", value=self.ner_results_bucket.bucket_name)
        CfnOutput(self, "KnowledgeGraphBucketName", value=self.knowledge_graph_bucket.bucket_name)
        CfnOutput(self, "ProcessingMetadataBucketName", value=self.processing_metadata_bucket.bucket_name)
