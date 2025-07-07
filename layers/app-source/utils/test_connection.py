#!/usr/bin/env python3
"""
Simple database connection test script
"""

import os
import sys

def test_connection(database_url):
    """Test PostgreSQL connection"""
    try:
        import psycopg2
        print(f"🔌 Testing connection to: {database_url.split('@')[1] if '@' in database_url else 'database'}")
        
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Connection successful!")
        print(f"📊 PostgreSQL version: {version}")
        
        # Test database list
        cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        databases = [row[0] for row in cursor.fetchall()]
        print(f"📁 Available databases: {', '.join(databases)}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except ImportError:
        print("❌ psycopg2 not installed. Run: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

def main():
    """Main function"""
    print("🧪 PostgreSQL Connection Test")
    print("=" * 40)
    
    # Check for DATABASE_URL
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        print("\nPlease set it with:")
        print("export DATABASE_URL='postgresql://username:password@host:port/database'")
        print("\nFor your database:")
        print("export DATABASE_URL='postgresql://postgres:YOUR_PASSWORD@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/postgres'")
        return False
    
    return test_connection(database_url)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
