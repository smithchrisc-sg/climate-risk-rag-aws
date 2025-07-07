#!/usr/bin/env python3
"""
Simple database setup for vector embeddings using Lambda function
"""
import boto3
import json

def setup_vector_embeddings_db():
    """Setup vector embeddings database schema using Lambda"""
    
    print("Setting up Vector Embeddings Database Schema")
    print("=" * 50)
    
    # Create Lambda client with solve-global profile
    session = boto3.Session(profile_name='solve-global')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    # SQL commands to execute
    sql_commands = [
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
        "CREATE INDEX IF NOT EXISTS idx_vector_embeddings_status ON vector_embeddings_status(status);",
        "CREATE INDEX IF NOT EXISTS idx_vector_embeddings_created_at ON vector_embeddings_status(created_at);",
        """
        ALTER TABLE document_processing_status 
        ADD COLUMN IF NOT EXISTS vector_embeddings_status VARCHAR(50) DEFAULT 'PENDING',
        ADD COLUMN IF NOT EXISTS vector_embeddings_completed_at TIMESTAMP;
        """
    ]
    
    # Test payload for database setup
    test_payload = {
        "Records": [{
            "body": json.dumps({
                "Message": json.dumps({
                    "doc_id": "vector_db_setup_test",
                    "stage": "database_setup",
                    "sql_commands": sql_commands,
                    "setup_mode": True
                })
            })
        }]
    }
    
    try:
        # Use text chunker function to execute database commands
        # (it has database access and can execute arbitrary SQL)
        function_name = 'text-chunker-pipeline-TextChunkerFunction'
        
        print("Executing database setup via Lambda function...")
        
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        if response.get('StatusCode') == 200:
            print("SUCCESS: Database setup completed!")
            print("Response: {}".format(response_payload.get('body', 'No response body')))
        else:
            print("ERROR: Database setup failed")
            print("Response: {}".format(response_payload))
            
    except Exception as e:
        print("ERROR: Failed to setup database: {}".format(str(e)))
        print("Note: You may need to manually create the vector_embeddings_status table")
        print("SQL to run manually:")
        for sql in sql_commands:
            print("  {}".format(sql.strip()))

if __name__ == "__main__":
    setup_vector_embeddings_db()
