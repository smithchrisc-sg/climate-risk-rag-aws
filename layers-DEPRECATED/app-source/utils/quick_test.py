#!/usr/bin/env python3
"""
Quick connection test with timeout
"""

import psycopg2
import getpass
import signal
import sys

def timeout_handler(signum, frame):
    print("\n⏰ Connection timed out after 10 seconds")
    print("This suggests a network connectivity issue")
    sys.exit(1)

def quick_test():
    host = "solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com"
    port = "5432"
    database = "climate_risk_rag"
    username = "postgres"
    
    print("🔑 Quick Connection Test (10 second timeout)")
    print("=" * 50)
    
    password = getpass.getpass("Enter database password: ")
    
    # Set 10 second timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(10)
    
    try:
        print("🔌 Testing connection...")
        
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password,
            connect_timeout=10
        )
        
        signal.alarm(0)  # Cancel timeout
        print("✅ Connected successfully!")
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        signal.alarm(0)
        print(f"❌ Connection failed: {e}")
        return False
    except Exception as e:
        signal.alarm(0)
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    quick_test()
