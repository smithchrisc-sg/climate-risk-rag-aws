"""
Audit-First Database Schema Migration Construct
Replaces complex multi-column schema with simplified 2-table audit design
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

class AuditSchemaMigrationConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, 
                 database_url: str, vpc=None, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Database migration Lambda function
        migration_function = lambda_.Function(
            self, "AuditSchemaMigrationFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="migration_handler.lambda_handler",
            code=lambda_.Code.from_inline(self._get_migration_code()),
            timeout=Duration.minutes(10),
            memory_size=512,
            vpc=vpc,
            environment={
                "DATABASE_URL": database_url
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # Grant RDS permissions
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
            self, "AuditSchemaMigrationProvider",
            on_event_handler=migration_function,
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # Custom resource to run migration
        migration_resource = CustomResource(
            self, "AuditSchemaMigration",
            service_token=migration_provider.service_token,
            properties={
                "MigrationVersion": "audit-v1.0.0",
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
    """Handle database migration to audit-first 2-table schema"""
    
    request_type = event.get('RequestType', 'Create')
    logger.info(f"Audit schema migration request type: {request_type}")
    
    try:
        if request_type in ['Create', 'Update']:
            run_audit_schema_migration()
            
        return {
            'Status': 'SUCCESS',
            'PhysicalResourceId': 'audit-schema-migration-v1',
            'Data': {
                'MigrationStatus': 'Completed',
                'SchemaVersion': 'audit-v1.0.0',
                'Timestamp': str(__import__('time').time())
            }
        }
        
    except Exception as e:
        logger.error(f"Audit schema migration failed: {str(e)}")
        return {
            'Status': 'FAILED',
            'Reason': str(e),
            'PhysicalResourceId': 'audit-schema-migration-v1'
        }

def run_audit_schema_migration():
    """Execute the audit-first schema migration"""
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    # Parse database URL
    parsed = urlparse(database_url)
    
    connection = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path[1:],  # Remove leading slash
        user=parsed.username,
        password=parsed.password
    )
    
    try:
        with connection.cursor() as cursor:
            logger.info("Starting audit-first schema migration...")
            
            # Create backup of existing documents table if it exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'documents'
                );
            """)
            
            if cursor.fetchone()[0]:
                logger.info("Creating backup of existing documents table...")
                cursor.execute("CREATE TABLE documents_backup AS SELECT * FROM documents;")
            
            # Drop existing tables to start clean
            logger.info("Dropping existing tables...")
            cursor.execute("DROP TABLE IF EXISTS document_processing_status CASCADE;")
            cursor.execute("DROP TABLE IF EXISTS documents CASCADE;")
            cursor.execute("DROP TABLE IF EXISTS chunks CASCADE;")
            cursor.execute("DROP TABLE IF EXISTS document_metadata CASCADE;")
            
            # Create new audit-first schema
            logger.info("Creating new documents table...")
            cursor.execute("""
                CREATE TABLE documents (
                    doc_id VARCHAR(32) PRIMARY KEY,
                    source_url TEXT NOT NULL,
                    original_filename TEXT,
                    file_size_bytes BIGINT,
                    file_hash VARCHAR(64),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create indexes for documents table
            cursor.execute("CREATE INDEX idx_documents_source_url ON documents(source_url);")
            cursor.execute("CREATE INDEX idx_documents_created_at ON documents(created_at);")
            cursor.execute("CREATE INDEX idx_documents_file_hash ON documents(file_hash);")
            
            logger.info("Creating document_processing_status table...")
            cursor.execute("""
                CREATE TABLE document_processing_status (
                    id SERIAL PRIMARY KEY,
                    doc_id VARCHAR(32) REFERENCES documents(doc_id) ON DELETE CASCADE,
                    stage VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT,
                    system_id VARCHAR(100),
                    retry_count INTEGER DEFAULT 0,
                    metadata JSONB,
                    
                    CONSTRAINT valid_status CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'skipped')),
                    CONSTRAINT valid_stage CHECK (stage IN (
                        'download', 'textract_initiate', 'textract_complete', 'chunking',
                        'vector_embedding', 'vector_indexing', 'indexing', 'nlp_initiate',
                        'nlp_complete', 'kg_doc_structure', 'kg_entities', 'validation'
                    ))
                );
            """)
            
            # Create indexes for document_processing_status table
            cursor.execute("CREATE INDEX idx_processing_doc_stage_time ON document_processing_status(doc_id, stage, timestamp);")
            cursor.execute("CREATE INDEX idx_processing_stage_status_time ON document_processing_status(stage, status, timestamp);")
            cursor.execute("CREATE INDEX idx_processing_timestamp ON document_processing_status(timestamp);")
            cursor.execute("CREATE INDEX idx_processing_system_id ON document_processing_status(system_id);")
            cursor.execute("""
                CREATE INDEX idx_processing_status_pending ON document_processing_status(status, timestamp) 
                WHERE status IN ('pending', 'in_progress');
            """)
            
            # Insert sample data for verification
            logger.info("Inserting sample data for verification...")
            cursor.execute("""
                INSERT INTO documents (doc_id, source_url, original_filename, file_size_bytes, file_hash) 
                VALUES (
                    'sample123456789abcdef', 
                    'https://example.com/sample.pdf', 
                    'sample.pdf', 
                    1024000, 
                    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
                );
            """)
            
            cursor.execute("""
                INSERT INTO document_processing_status (doc_id, stage, status) 
                VALUES ('sample123456789abcdef', 'download', 'completed');
            """)
            
            connection.commit()
            logger.info("Audit-first schema migration completed successfully!")
            
    finally:
        connection.close()
'''
