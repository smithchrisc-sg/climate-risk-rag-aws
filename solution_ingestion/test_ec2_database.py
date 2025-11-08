#!/usr/bin/env python3
"""
EC2 database connectivity test using AWS Secrets Manager.
"""

import sys
import os
from pathlib import Path
import boto3
import json
import psycopg2

# Setup paths
sys.path.append(str(Path(__file__).parent))

def get_database_credentials():
    """Get database credentials from AWS Secrets Manager."""
    try:
        # Try common secret names for this project
        secret_names = [
            'solve-global-kr-rag-data/postgres',
            'rds-db-credentials/solve-global-kr-rag-data-postgresqldatabase03fc658',
            'solve-global-kr-rag/database'
        ]
        
        secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        
        for secret_name in secret_names:
            try:
                print(f"Trying secret: {secret_name}")
                response = secrets_client.get_secret_value(SecretId=secret_name)
                secret = json.loads(response['SecretString'])
                print(f"[OK] Found secret: {secret_name}")
                return secret
            except Exception as e:
                print(f"Secret {secret_name} not found: {e}")
                continue
        
        raise Exception("No database secrets found")
        
    except Exception as e:
        print(f"Failed to get database credentials: {e}")
        return None

def test_database_with_secrets():
    """Test database connection using Secrets Manager."""
    print("Testing database connection with Secrets Manager...")
    
    try:
        # Get credentials from Secrets Manager
        creds = get_database_credentials()
        if not creds:
            print("❌ Could not retrieve database credentials")
            return False
        
        # Connect to database
        conn_params = {
            'host': creds.get('host', 'solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com'),
            'port': creds.get('port', 5432),
            'database': creds.get('dbname', 'climate_risk_rag'),
            'user': creds.get('username', 'postgres'),
            'password': creds['password'],
            'sslmode': 'require'
        }
        
        print(f"Connecting to: {conn_params['host']}:{conn_params['port']}/{conn_params['database']}")
        
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        # Test queries
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"[OK] Database connected: {version[:50]}...")
        
        cursor.execute("SELECT current_database(), current_user;")
        db_info = cursor.fetchone()
        print(f"[OK] Database: {db_info[0]}, User: {db_info[1]}")
        
        # Check if tables exist
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"[OK] Found {len(tables)} tables: {[t[0] for t in tables[:5]]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_solution_model():
    """Test solution model with correct fields."""
    print("\nTesting solution model...")
    
    try:
        from models.solution import Solution
        
        # Create solution with correct fields
        solution = Solution(
            id="test_001",
            source_file="test.csv",
            row_number=1,
            number="001", 
            name="Test Solution",
            country="Test Country",
            public_organisations="Test Public Org",
            international_organisations="Test Intl Org",
            private_organisations="Test Private Org",
            type_of_risk="Climate Risk",
            type_of_solution="Adaptation",
            ppp="Public",
            theme="Water Management", 
            year_of_implementation="2024",
            description="Test description",
            key_highlights="Test highlights",
            results="Test results",
            organization_sources="Test org sources",
            other_sources="Test other sources",
            contact_information="test@example.com",
            date_added="2024-11-05",
            last_updated="2024-11-05",
            most_recent_changes="Initial creation"
        )
        
        print(f"[OK] Solution created: {solution.name}")
        print(f"[OK] Document ID: {solution.doc_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Solution model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== EC2 Database Test with Secrets Manager ===\n")
    
    db_success = test_database_with_secrets()
    model_success = test_solution_model()
    
    if db_success and model_success:
        print("\n🎉 All tests passed! Database connectivity working.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)
