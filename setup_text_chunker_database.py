#!/usr/bin/env python3
"""
Setup Text Chunker Database Schema
Creates required tables for text chunker status tracking
"""

import psycopg2
import sys
from datetime import datetime

def setup_text_chunker_schema():
    """Setup database schema for text chunker"""
    
    print("🔧 Setting Up Text Chunker Database Schema")
    print("=" * 60)
    
    # Database connection parameters
    db_params = {
        'host': 'solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com',
        'port': 5432,
        'database': 'climate_risk_rag',
        'user': 'postgres',
        'password': '-VroWHWQBS5!V)yAcsDC3(3)NHJ5',
        'sslmode': 'require'
    }
    
    try:
        # Connect to database
        print("Connecting to PostgreSQL database...")
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        print("✅ Connected to database successfully")
        
        # Create text chunking status table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS text_chunking_status (
            id SERIAL PRIMARY KEY,
            doc_id VARCHAR(255) UNIQUE NOT NULL,
            status VARCHAR(50) NOT NULL,
            chunks_created INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_text_chunking_status_doc_id ON text_chunking_status(doc_id);
        CREATE INDEX IF NOT EXISTS idx_text_chunking_status_status ON text_chunking_status(status);
        CREATE INDEX IF NOT EXISTS idx_text_chunking_status_updated_at ON text_chunking_status(updated_at);
        """
        
        print("Creating text_chunking_status table...")
        cursor.execute(create_table_sql)
        
        # Create trigger for updated_at
        trigger_sql = """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        DROP TRIGGER IF EXISTS update_text_chunking_status_updated_at ON text_chunking_status;
        CREATE TRIGGER update_text_chunking_status_updated_at
            BEFORE UPDATE ON text_chunking_status
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
        
        print("Creating updated_at trigger...")
        cursor.execute(trigger_sql)
        
        # Commit changes
        conn.commit()
        print("✅ Database schema created successfully")
        
        # Test the schema
        print("\nTesting database schema...")
        test_sql = """
        INSERT INTO text_chunking_status (doc_id, status, chunks_created, notes)
        VALUES ('test_schema_setup', 'TESTING', 0, 'Schema setup test')
        ON CONFLICT (doc_id) 
        DO UPDATE SET 
            status = EXCLUDED.status,
            notes = EXCLUDED.notes,
            updated_at = CURRENT_TIMESTAMP;
        """
        
        cursor.execute(test_sql)
        
        # Verify the test record
        cursor.execute("SELECT * FROM text_chunking_status WHERE doc_id = 'test_schema_setup'")
        result = cursor.fetchone()
        
        if result:
            print("✅ Schema test successful")
            print(f"   Test record: doc_id={result[1]}, status={result[2]}, chunks={result[3]}")
            
            # Clean up test record
            cursor.execute("DELETE FROM text_chunking_status WHERE doc_id = 'test_schema_setup'")
            conn.commit()
            print("✅ Test record cleaned up")
        else:
            print("❌ Schema test failed")
            return False
        
        # Check existing DocumentIDManager tables
        print("\nChecking existing DocumentIDManager tables...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%document%'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        if tables:
            print("✅ Found DocumentIDManager tables:")
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print("⚠️  No DocumentIDManager tables found - may need migration")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 Database setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def test_database_connection():
    """Test basic database connectivity"""
    
    print("\n🧪 Testing Database Connection")
    print("=" * 60)
    
    db_params = {
        'host': 'solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com',
        'port': 5432,
        'database': 'climate_risk_rag',
        'user': 'postgres',
        'password': '-VroWHWQBS5!V)yAcsDC3(3)NHJ5',
        'sslmode': 'require'
    }
    
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ PostgreSQL Version: {version[0]}")
        
        # Test database name
        cursor.execute("SELECT current_database();")
        db_name = cursor.fetchone()
        print(f"✅ Connected to database: {db_name[0]}")
        
        # Test current user
        cursor.execute("SELECT current_user;")
        user = cursor.fetchone()
        print(f"✅ Connected as user: {user[0]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Text Chunker Database Configuration")
    print("=" * 80)
    print(f"Started at: {datetime.utcnow().isoformat()}")
    print()
    
    # Test connection first
    if not test_database_connection():
        print("❌ Database connection failed. Check credentials and network access.")
        sys.exit(1)
    
    # Setup schema
    if setup_text_chunker_schema():
        print("\n🎉 Database configuration completed successfully!")
        print("Text chunker is ready for database integration testing.")
        sys.exit(0)
    else:
        print("\n❌ Database configuration failed.")
        sys.exit(1)
