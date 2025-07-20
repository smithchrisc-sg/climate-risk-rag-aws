#!/usr/bin/env python3
"""
Quick connection test with SSL and better error handling
"""

import psycopg2
import getpass
import json
import sys

def test_connection():
    host = "solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com"
    port = "5432"
    database = "climate_risk_rag"
    username = "postgres"
    
    print("🔑 PostgreSQL Connection Test with SSL")
    print("=" * 50)
    print(f"Host: {host}")
    print(f"Database: {database}")
    print(f"Username: {username}")
    print()
    
    password = getpass.getpass("Enter database password: ")
    
    if not password.strip():
        print("❌ Empty password detected")
        return False
    
    print(f"🔐 Password length: {len(password)} characters")
    print(f"🔐 Password starts with: {password[:3]}...")
    
    # Test different connection methods
    connection_methods = [
        ("SSL Required", {"sslmode": "require"}),
        ("SSL Preferred", {"sslmode": "prefer"}),
        ("SSL Disabled", {"sslmode": "disable"}),
    ]
    
    for method_name, ssl_params in connection_methods:
        print(f"\n🔌 Testing {method_name}...")
        
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                connect_timeout=10,
                **ssl_params
            )
            
            cursor = conn.cursor()
            cursor.execute("SELECT version(), current_user, current_database();")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            print(f"✅ {method_name} - SUCCESS!")
            print(f"📊 Version: {result[0].split(',')[0]}")
            print(f"👤 User: {result[1]}")
            print(f"📁 Database: {result[2]}")
            
            # Save working connection
            database_url = f"postgresql://{username}:{password}@{host}:{port}/{database}?sslmode={ssl_params['sslmode']}"
            
            with open('/tmp/database_url.sh', 'w') as f:
                f.write(f"export DATABASE_URL='{database_url}'\n")
            
            print(f"\n💾 Working DATABASE_URL saved to /tmp/database_url.sh")
            return True
            
        except psycopg2.OperationalError as e:
            error_msg = str(e)
            print(f"❌ {method_name} - FAILED")
            
            if "password authentication failed" in error_msg:
                print("   → Password authentication failed")
            elif "no pg_hba.conf entry" in error_msg:
                print("   → SSL/encryption required")
            elif "connection timed out" in error_msg:
                print("   → Connection timeout")
            else:
                print(f"   → {error_msg}")
        
        except Exception as e:
            print(f"❌ {method_name} - ERROR: {e}")
    
    print("\n💡 All connection methods failed")
    print("💡 Most likely issue: Incorrect password")
    return False

def suggest_password_retrieval():
    print("\n🔍 How to get the correct password:")
    print("1. AWS Console → Secrets Manager")
    print("2. Find secret: DatabaseSecret86DBB7B3-Z8CSRvy8A8bp")
    print("3. Click 'Retrieve secret value'")
    print("4. Copy the 'password' field value")
    print("\nOR")
    print("1. AWS Console → CloudFormation")
    print("2. Stack: solve-global-kr-rag-data")
    print("3. Outputs tab → Look for DatabaseSecretArn")
    print("4. Click the ARN link to go to Secrets Manager")

if __name__ == "__main__":
    try:
        success = test_connection()
        if not success:
            suggest_password_retrieval()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 Cancelled")
        sys.exit(1)
