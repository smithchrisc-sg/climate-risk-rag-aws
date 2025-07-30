#!/usr/bin/env python3
"""
Fix Database Schema - Add Missing chunks_count Column
"""

import psycopg2
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_database_schema():
    """Add missing chunks_count column to text_chunking_status table"""
    
    # Database connection string
    database_url = "postgresql://postgres:c0xfd_t#PBUqV(pLM-9IqM59G:>c@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require"
    
    try:
        # Connect to database
        logger.info("Connecting to database...")
        conn = psycopg2.connect(database_url)
        
        with conn.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'text_chunking_status'
                );
            """)
            
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                logger.info("Creating text_chunking_status table...")
                cursor.execute("""
                    CREATE TABLE text_chunking_status (
                        doc_id VARCHAR(255) PRIMARY KEY,
                        status VARCHAR(50) NOT NULL,
                        chunks_count INTEGER DEFAULT 0,
                        message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                logger.info("✅ Created text_chunking_status table with chunks_count column")
            else:
                # Check if chunks_count column exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'text_chunking_status' 
                        AND column_name = 'chunks_count'
                    );
                """)
                
                column_exists = cursor.fetchone()[0]
                
                if not column_exists:
                    logger.info("Adding missing chunks_count column...")
                    cursor.execute("""
                        ALTER TABLE text_chunking_status 
                        ADD COLUMN chunks_count INTEGER DEFAULT 0;
                    """)
                    logger.info("✅ Added chunks_count column to text_chunking_status table")
                else:
                    logger.info("✅ chunks_count column already exists")
            
            # Commit changes
            conn.commit()
            logger.info("✅ Database schema fix completed successfully")
            
    except Exception as e:
        logger.error(f"❌ Database schema fix failed: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    fix_database_schema()
