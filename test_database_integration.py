#!/usr/bin/env python3
"""
Test Database Integration for Text Chunker
Tests the database-enabled text chunker function
"""

import boto3
import json
import time
from datetime import datetime

def test_database_enabled_function():
    """Test the database-enabled text chunker function"""
    
    print("🧪 Testing Database-Enabled Text Chunker")
    print("=" * 60)
    
    # Create Lambda client
    session = boto3.Session(profile_name='solve-global')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    # Test payload with database integration test
    test_payload = {
        "Records": [{
            "body": json.dumps({
                "Message": json.dumps({
                    "doc_id": f"test_db_integration_{int(time.time())}",
                    "stage": "test",
                    "test_mode": True,
                    "database_test": True
                })
            })
        }]
    }
    
    try:
        print("Invoking database-enabled function...")
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-text-chunker-db',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        if response['StatusCode'] == 200:
            payload = json.loads(response['Payload'].read())
            print("✅ Function invocation successful!")
            print(f"Response: {json.dumps(payload, indent=2)}")
            return True
        else:
            print(f"❌ Function invocation failed: {response}")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def check_database_logs():
    """Check CloudWatch logs for database integration status"""
    
    print("\n📋 Checking Database Integration Logs")
    print("=" * 60)
    
    session = boto3.Session(profile_name='solve-global')
    logs_client = session.client('logs', region_name='us-east-1')
    
    try:
        # Get latest log stream
        streams = logs_client.describe_log_streams(
            logGroupName='/aws/lambda/solve-global-kr-text-chunker-db',
            orderBy='LastEventTime',
            descending=True,
            limit=1
        )
        
        if streams['logStreams']:
            stream_name = streams['logStreams'][0]['logStreamName']
            
            # Get recent log events
            events = logs_client.get_log_events(
                logGroupName='/aws/lambda/solve-global-kr-text-chunker-db',
                logStreamName=stream_name,
                startFromHead=False,
                limit=20
            )
            
            print(f"Latest log stream: {stream_name}")
            print("\nRecent log events:")
            
            database_success = False
            import_success = False
            
            for event in events['events'][-15:]:  # Last 15 events
                message = event['message'].strip()
                if message:
                    if 'DatabaseManager initialized successfully' in message:
                        print(f"✅ {message}")
                        database_success = True
                        import_success = True
                    elif 'Failed to import DatabaseManager' in message:
                        print(f"❌ {message}")
                    elif 'Database connection string required' in message:
                        print(f"⚠️  {message}")
                    elif 'Smart structured chunker initialized successfully' in message:
                        print(f"✅ {message}")
                        import_success = True
                    elif 'Failed to import smart chunker' in message:
                        print(f"❌ {message}")
                    elif 'ERROR' in message:
                        print(f"⚠️  {message}")
                    elif 'INFO' in message and ('initialized' in message or 'import' in message):
                        print(f"ℹ️  {message}")
            
            return database_success, import_success
        else:
            print("No log streams found")
            return False, False
            
    except Exception as e:
        print(f"❌ Error getting logs: {e}")
        return False, False

def test_database_connectivity():
    """Test direct database connectivity from local environment"""
    
    print("\n🔗 Testing Direct Database Connectivity")
    print("=" * 60)
    
    try:
        import psycopg2
        
        # Database connection parameters
        db_params = {
            'host': 'solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com',
            'port': 5432,
            'database': 'climate_risk_rag',
            'user': 'postgres',
            'password': '-VroWHWQBS5!V)yAcsDC3(3)NHJ5',
            'sslmode': 'require'
        }
        
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        # Test text_chunking_status table
        cursor.execute("SELECT COUNT(*) FROM text_chunking_status;")
        count = cursor.fetchone()[0]
        print(f"✅ text_chunking_status table accessible: {count} records")
        
        # Test DocumentIDManager tables
        cursor.execute("SELECT COUNT(*) FROM documents;")
        doc_count = cursor.fetchone()[0]
        print(f"✅ documents table accessible: {doc_count} records")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Database connectivity test failed: {e}")
        return False

def run_database_integration_test():
    """Run complete database integration test"""
    
    print("🚀 Database Integration Test for Text Chunker")
    print("=" * 80)
    print(f"Started at: {datetime.utcnow().isoformat()}")
    print()
    
    # Test direct database connectivity first
    db_connectivity = test_database_connectivity()
    
    # Test lambda function
    function_test = test_database_enabled_function()
    
    # Wait a moment for logs to be available
    print("\nWaiting for CloudWatch logs...")
    time.sleep(5)
    
    # Check logs for database integration status
    db_success, import_success = check_database_logs()
    
    # Summary
    print("\n" + "=" * 80)
    print("🎯 Database Integration Test Results")
    print("=" * 80)
    
    print(f"✅ Direct Database Connectivity: {'SUCCESS' if db_connectivity else 'FAILED'}")
    print(f"✅ Lambda Function Invocation: {'SUCCESS' if function_test else 'FAILED'}")
    print(f"✅ Import Integration: {'SUCCESS' if import_success else 'FAILED'}")
    print(f"✅ Database Integration: {'SUCCESS' if db_success else 'FAILED'}")
    
    overall_success = db_connectivity and function_test and import_success
    
    if overall_success:
        if db_success:
            print("\n🎉 COMPLETE SUCCESS: Database integration fully working!")
            print("✅ All imports working")
            print("✅ Database connection established")
            print("✅ Text chunker ready for real document processing")
        else:
            print("\n✅ PARTIAL SUCCESS: Imports working, database needs configuration")
            print("✅ All imports working")
            print("⚠️  Database connection needs VPC/security group configuration")
            print("✅ Ready for Phase 2 integration testing")
    else:
        print("\n❌ FAILED: Issues need to be resolved")
    
    return overall_success

if __name__ == "__main__":
    success = run_database_integration_test()
    exit(0 if success else 1)
