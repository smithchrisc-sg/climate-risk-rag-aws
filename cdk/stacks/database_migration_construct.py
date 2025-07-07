"""
Database Migration Construct for Vector Embeddings Schema
"""
from aws_cdk import (
    Duration,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_logs as logs,
    custom_resources as cr,
    CustomResource
)
from constructs import Construct

class DatabaseMigrationConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, 
                 database_url: str, vpc=None, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Database migration Lambda function
        migration_function = lambda_.Function(
            self, "DatabaseMigrationFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="migration_handler.lambda_handler",
            code=lambda_.Code.from_inline(self._get_migration_code()),
            timeout=Duration.minutes(5),
            memory_size=256,
            vpc=vpc,
            environment={
                "DATABASE_URL": database_url
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # Grant RDS permissions if needed
        migration_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "rds:DescribeDBInstances",
                    "rds:DescribeDBClusters"
                ],
                resources=["*"]
            )
        )
        
        # Custom resource provider
        migration_provider = cr.Provider(
            self, "MigrationProvider",
            on_event_handler=migration_function,
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # Custom resource to run migration
        migration_resource = CustomResource(
            self, "VectorEmbeddingsMigration",
            service_token=migration_provider.service_token,
            properties={
                "MigrationVersion": "v1.0.0",
                "Timestamp": str(__import__('time').time())  # Force update on each deploy
            }
        )
        
        self.migration_function = migration_function
        self.migration_resource = migration_resource
    
    def _get_migration_code(self) -> str:
        return '''
import json
import logging
import psycopg2
import os
from urllib.parse import urlparse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Handle database migration for vector embeddings"""
    
    request_type = event.get('RequestType', 'Create')
    logger.info(f"Migration request type: {request_type}")
    
    try:
        if request_type in ['Create', 'Update']:
            run_migration()
            
        return {
            'Status': 'SUCCESS',
            'PhysicalResourceId': 'vector-embeddings-migration-v1',
            'Data': {
                'MigrationStatus': 'Completed',
                'Timestamp': str(__import__('time').time())
            }
        }
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return {
            'Status': 'FAILED',
            'Reason': str(e),
            'PhysicalResourceId': 'vector-embeddings-migration-v1'
        }

def run_migration():
    """Run the vector embeddings database migration"""
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    # Parse database URL
    parsed = urlparse(database_url)
    
    # Connect to database
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path[1:],  # Remove leading slash
        user=parsed.username,
        password=parsed.password,
        sslmode='require'
    )
    
    try:
        with conn.cursor() as cursor:
            logger.info("Running vector embeddings schema migration...")
            
            # Create vector_embeddings_status table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vector_embeddings_status (
                    doc_id VARCHAR(255) PRIMARY KEY,
                    status VARCHAR(50) NOT NULL,
                    embeddings_count INTEGER,
                    titan_cost_estimate DECIMAL(10,6),
                    titan_cost_actual DECIMAL(10,6),
                    opensearch_indexed BOOLEAN DEFAULT FALSE,
                    cache_used BOOLEAN DEFAULT FALSE,
                    model_type VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    processing_duration_seconds INTEGER
                )
            """)
            
            # Add vector embeddings columns to document_processing_status
            cursor.execute("""
                ALTER TABLE document_processing_status 
                ADD COLUMN IF NOT EXISTS vector_embeddings_status VARCHAR(50) DEFAULT 'PENDING',
                ADD COLUMN IF NOT EXISTS vector_embeddings_completed_at TIMESTAMP
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vector_embeddings_status 
                ON vector_embeddings_status(status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_doc_processing_vector_status 
                ON document_processing_status(vector_embeddings_status)
            """)
            
            # Create vector embeddings cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vector_embeddings_cache (
                    chunk_hash VARCHAR(64) PRIMARY KEY,
                    embedding_vector FLOAT8[],
                    model_type VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 1
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vector_cache_model_type 
                ON vector_embeddings_cache(model_type)
            """)
            
            conn.commit()
            logger.info("Vector embeddings schema migration completed successfully")
            
    finally:
        conn.close()
'''
