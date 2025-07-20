#!/usr/bin/env python3
"""
Simple PostgreSQL connection test
"""

import psycopg2
import getpass
import sys
import os

def test_connection():
    """Test PostgreSQL connection"""
    
    # Database details
    host = "solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com"
    port = "5432"
    database = "climate_risk_rag"
    username = "postgres"
    
    print("🔑 PostgreSQL Connection Test")
    print("=" * 40)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Database: {database}")
    print(f"Username: {username}")
    print()
    
    # Get password
    password = getpass.getpass("Enter database password: ")
    
    if not password:
        print("❌ Password required")
        return False
    
    try:
        print("🔌 Connecting...")
        
        # Try connection with SSL (default for RDS)
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password,
            sslmode='require'  # RDS typically requires SSL
        )
        
        cursor = conn.cursor()
        
        # Test queries
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        cursor.execute("SELECT current_database(), current_user;")
        db_info = cursor.fetchone()
        
        # Check if database has tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        print("✅ Connection successful!")
        print(f"📊 Version: {version.split(',')[0]}")
        print(f"📁 Database: {db_info[0]}")
        print(f"👤 User: {db_info[1]}")
        print(f"📋 Tables: {len(tables)}")
        
        if tables:
            print("   Existing tables:")
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print("   No tables found (empty database)")
        
        # Save working connection string
        database_url = f"postgresql://{username}:{password}@{host}:{port}/{database}?sslmode=require"
        
        with open('/tmp/database_url.sh', 'w') as f:
            f.write(f"export DATABASE_URL='{database_url}'\n")
        
        print(f"\n💾 DATABASE_URL saved to: /tmp/database_url.sh")
        print("   Source with: source /tmp/database_url.sh")
        
        return True
        
    except psycopg2.OperationalError as e:
        error_msg = str(e).lower()
        print(f"❌ Connection failed: {e}")
        
        if "password authentication failed" in error_msg:
            print("\n💡 Authentication failed - check password")
            
        elif "ssl connection has been closed unexpectedly" in error_msg:
            print("\n💡 SSL issue - trying without SSL requirement...")
            return test_connection_no_ssl(host, port, database, username, password)
            
        elif "connection timed out" in error_msg:
            print("\n💡 Connection timeout - check network/security groups")
            
        elif "could not connect to server" in error_msg:
            print("\n💡 Cannot reach server - check if database is running")
            
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_connection_no_ssl(host, port, database, username, password):
    """Test connection without SSL requirement"""
    try:
        print("🔌 Trying connection without SSL...")
        
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password,
            sslmode='prefer'  # Try SSL but don't require it
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        print("✅ Connection successful (without SSL requirement)!")
        print(f"📊 Version: {version.split(',')[0]}")
        
        # Save working connection string
        database_url = f"postgresql://{username}:{password}@{host}:{port}/{database}?sslmode=prefer"
        
        with open('/tmp/database_url.sh', 'w') as f:
            f.write(f"export DATABASE_URL='{database_url}'\n")
        
        print(f"💾 DATABASE_URL saved to: /tmp/database_url.sh")
        
        return True
        
    except Exception as e:
        print(f"❌ Still failed: {e}")
        return False

if __name__ == "__main__":
    try:
        success = test_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 Cancelled")
        sys.exit(1)
