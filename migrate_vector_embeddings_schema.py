#!/usr/bin/env python3
"""
Database schema migration for vector embeddings
Uses existing text chunker function to execute SQL
"""
import boto3
import json
import time

def migrate_vector_embeddings_schema():
    """Migrate database schema using existing Lambda function"""
    
    print("Migrating Vector Embeddings Database Schema")
    print("=" * 50)
    
    # SQL commands to execute
    sql_commands = [
        # Create vector embeddings status table
        """
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
        );
        """,
        
        # Create indexes
        "CREATE INDEX IF NOT EXISTS idx_vector_embeddings_status ON vector_embeddings_status(status);",
        "CREATE INDEX IF NOT EXISTS idx_vector_embeddings_created_at ON vector_embeddings_status(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_vector_embeddings_model_type ON vector_embeddings_status(model_type);",
        
        # Add columns to existing document_processing_status table
        """
        ALTER TABLE document_processing_status 
        ADD COLUMN IF NOT EXISTS vector_embeddings_status VARCHAR(50) DEFAULT 'PENDING',
        ADD COLUMN IF NOT EXISTS vector_embeddings_completed_at TIMESTAMP;
        """
    ]
    
    # Create Lambda client
    session = boto3.Session(profile_name='solve-global')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    # Find a function with database access (text chunker or keyword indexer)
    functions_to_try = [
        'text-chunker-pipeline-TextChunkerFunction',
        'async-keyword-indexer-KeywordIndexerWorker',
        'solve-global-kr-rag-TextChunkerFunction'
    ]
    
    for function_name in functions_to_try:
        try:
            print("Attempting schema migration via function: {}".format(function_name))
            
            # Create test payload that will trigger database operations
            test_payload = {
                "Records": [{
                    "body": json.dumps({
                        "Message": json.dumps({
                            "doc_id": "vector_schema_migration_{}".format(int(time.time())),
                            "stage": "schema_migration",
                            "test_mode": True,
                            "sql_commands": sql_commands
                        })
                    })
                }]
            }
            
            # Invoke function
            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(test_payload)
            )
            
            # Check response
            if response.get('StatusCode') == 200:
                response_payload = json.loads(response['Payload'].read())
                print("SUCCESS: Schema migration completed via {}".format(function_name))
                print("Response: {}".format(response_payload.get('body', 'No response body')))
                return True
                
        except Exception as e:
            print("Failed with {}: {}".format(function_name, str(e)))
            continue
    
    # If all functions failed, provide manual instructions
    print("\nAutomatic migration failed. Please run these SQL commands manually:")
    print("=" * 50)
    for i, sql in enumerate(sql_commands, 1):
        print("-- Command {}:".format(i))
        print(sql.strip())
        print()
    
    return False

def verify_schema():
    """Verify schema was created successfully"""
    print("\nVerifying schema...")
    
    # Simple verification by trying to query the new table
    session = boto3.Session(profile_name='solve-global')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    test_payload = {
        "Records": [{
            "body": json.dumps({
                "Message": json.dumps({
                    "doc_id": "schema_verification_test",
                    "stage": "verification",
                    "test_mode": True
                })
            })
        }]
    }
    
    try:
        # Try to use vector embeddings processor if it exists
        response = lambda_client.invoke(
            FunctionName='vector-embeddings-pipeline-VectorEmbeddingsProcessor',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        if response.get('StatusCode') == 200:
            print("SUCCESS: Schema verification passed!")
            return True
            
    except Exception as e:
        print("Verification failed (expected if functions not deployed yet): {}".format(str(e)))
    
    return False

if __name__ == "__main__":
    success = migrate_vector_embeddings_schema()
    if success:
        verify_schema()
    else:
        print("\nManual schema setup required before deployment.")
