#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup database schema for vector embeddings processing
"""
import os
import sys
sys.path.append('./layers/app-source')

from utils.DatabaseManager import DatabaseManager

def setup_vector_embeddings_schema():
    """Create vector embeddings status table"""
    
    db_manager = DatabaseManager()
    
    # Create vector embeddings status table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS vector_embeddings_status (
        doc_id VARCHAR(255) PRIMARY KEY,
        status VARCHAR(50) NOT NULL,
        embeddings_count INTEGER,
        titan_cost_estimate DECIMAL(10,6),
        titan_cost_actual DECIMAL(10,6),
        opensearch_indexed BOOLEAN DEFAULT FALSE,
        cache_used BOOLEAN DEFAULT FALSE,
        model_type VARCHAR(50),
        model_info JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        error_message TEXT,
        processing_duration_seconds INTEGER,
        
        FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
    );
    """
    
    # Create indexes for efficient querying
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_vector_embeddings_status ON vector_embeddings_status(status);",
        "CREATE INDEX IF NOT EXISTS idx_vector_embeddings_created_at ON vector_embeddings_status(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_vector_embeddings_model_type ON vector_embeddings_status(model_type);"
    ]
    
    # Add columns to existing document_processing_status table
    alter_table_sql = """
    ALTER TABLE document_processing_status 
    ADD COLUMN IF NOT EXISTS vector_embeddings_status VARCHAR(50) DEFAULT 'PENDING',
    ADD COLUMN IF NOT EXISTS vector_embeddings_completed_at TIMESTAMP;
    """
    
    try:
        print("Creating vector embeddings status table...")
        db_manager.execute_query(create_table_sql)
        
        print("Creating indexes...")
        for index_sql in indexes_sql:
            db_manager.execute_query(index_sql)
        
        print("Adding columns to document_processing_status...")
        db_manager.execute_query(alter_table_sql)
        
        print("SUCCESS: Vector embeddings database schema setup complete!")
        
        # Test the setup
        test_query = "SELECT COUNT(*) FROM vector_embeddings_status;"
        result = db_manager.execute_query(test_query)
        print("SUCCESS: Test query successful. Current vector embeddings records: {}".format(result[0][0]))
        
    except Exception as e:
        print("ERROR: Error setting up vector embeddings schema: {}".format(str(e)))
        raise

if __name__ == "__main__":
    setup_vector_embeddings_schema()
