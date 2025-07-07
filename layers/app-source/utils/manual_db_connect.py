#!/usr/bin/env python3
"""
Manual database connection script
Bypasses AWS CLI limitations by using known database details
"""

import psycopg2
import getpass
import sys

def test_database_connection():
    """Test database connection with manual password entry"""
    
    # Known database details
    host = "solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com"
    port = "5432"
    database = "climate_risk_rag"
    username = "postgres"
    
    print("🔑 Climate Risk RAG Database Connection Test")
    print("=" * 50)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Database: {database}")
    print(f"Username: {username}")
    print()
    
    # Get password from user
    password = getpass.getpass("Enter database password: ")
    
    if not password:
        print("❌ Password is required")
        return False
    
    # Construct connection string
    database_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    try:
        print("🔌 Testing connection...")
        
        # Test connection
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test basic queries
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        cursor.execute("SELECT current_database();")
        current_db = cursor.fetchone()[0]
        
        cursor.execute("SELECT current_user;")
        current_user = cursor.fetchone()[0]
        
        # List tables
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
        print(f"📊 PostgreSQL version: {version.split(',')[0]}")
        print(f"📁 Database: {current_db}")
        print(f"👤 User: {current_user}")
        print(f"📋 Tables found: {len(tables)}")
        
        if tables:
            print("   Tables:")
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print("   No tables found (database is empty)")
        
        # Save working DATABASE_URL
        with open('/tmp/database_url.sh', 'w') as f:
            f.write(f"export DATABASE_URL='{database_url}'\n")
        
        print(f"\n💾 DATABASE_URL saved to: /tmp/database_url.sh")
        print(f"   Source it with: source /tmp/database_url.sh")
        
        # Also save to environment file
        with open('/Users/chris/climate-risk-rag-aws/.env', 'w') as f:
            f.write(f"DATABASE_URL={database_url}\n")
        
        print(f"💾 Also saved to: /Users/chris/climate-risk-rag-aws/.env")
        
        return True
        
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        print(f"❌ Connection failed: {error_msg}")
        
        if "password authentication failed" in error_msg:
            print("\n💡 Password authentication failed. Please check:")
            print("1. The password is correct")
            print("2. The master username is 'postgres'")
            
        elif "could not connect to server" in error_msg:
            print("\n💡 Connection timeout. Please check:")
            print("1. Database is running and accessible")
            print("2. Security groups allow connections from your IP")
            print("3. Database is in a public subnet or you have VPN access")
            
        elif "database" in error_msg and "does not exist" in error_msg:
            print("\n💡 Database doesn't exist. Try connecting to 'postgres' database first:")
            print("   Then create the 'climate_risk_rag' database")
            
        return False
        
    except ImportError:
        print("❌ psycopg2 not installed. Install with:")
        print("   pip install psycopg2-binary")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

def main():
    """Main function"""
    try:
        success = test_database_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user")
        sys.exit(1)

if __name__ == "__main__":
    main()
