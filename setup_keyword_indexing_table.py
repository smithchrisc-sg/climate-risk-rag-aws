#!/usr/bin/env python3
"""
Setup keyword indexing status table in the database
"""

import psycopg2
from psycopg2.extras import RealDictCursor

def setup_keyword_indexing_table():
    """Create keyword indexing status table"""
    
    db_params = {
        'host': 'solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com',
        'port': 5432,
        'database': 'climate_risk_rag',
        'user': 'postgres',
        'password': '-VroWHWQBS5!V)yAcsDC3(3)NHJ5',
        'sslmode': 'require'
    }
    
    print("🗄️ Setting up keyword indexing status table...")
    
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Create keyword indexing status table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keyword_indexing_status (
                doc_id VARCHAR(255) PRIMARY KEY,
                status VARCHAR(50) NOT NULL,
                notes TEXT,
                indexed_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        
        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_keyword_indexing_status_status 
            ON keyword_indexing_status(status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_keyword_indexing_updated_at 
            ON keyword_indexing_status(updated_at)
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Keyword indexing status table created successfully")
        
    except Exception as e:
        print(f"❌ Error setting up table: {e}")
        raise

if __name__ == "__main__":
    setup_keyword_indexing_table()
