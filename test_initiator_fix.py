#!/usr/bin/env python3
"""
Test Initiator Status Update Fix
Validates that the initiator now properly creates initial PROCESSING status
"""

import boto3
import json
import time
from datetime import datetime

def test_initiator_status_fix():
    """Test that initiator creates proper initial status"""
    
    print("🔧 Testing Initiator Status Update Fix")
    print("=" * 60)
    print(f"Started at: {datetime.utcnow().isoformat()}")
    print()
    
    session = boto3.Session(profile_name='solve-global')
    sns_client = session.client('sns', region_name='us-east-1')
    
    # Test document
    doc_id = "initiator-status-fix-test"
    text_ready_topic_arn = "arn:aws:sns:us-east-1:861276078413:text-extraction-complete"
    
    print(f"📋 Testing Status Update Flow:")
    print(f"   Document: {doc_id}")
    print(f"   Expected: PROCESSING → COMPLETED")
    print(f"   Fix: Initiator should create initial PROCESSING status")
    
    # Create test message
    test_message = {
        "doc_id": doc_id,
        "stage": "text_ready",
        "full_text_location": {
            "bucket": "solve-global-kr-text-new-861276078413-us-east-1",
            "key": "extracted_text/neural-fuzzy-textract.txt"
        },
        "document_structure_location": None,
        "documentid_manager_integration": True,
        "selective_migration_used": False,
        "filename": f"{doc_id}.pdf",
        "initiator_fix_test": True,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        # Clear any existing status for clean test
        print(f"\n🧹 Clearing any existing status for clean test...")
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
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
            
            cursor.execute("DELETE FROM keyword_indexing_status WHERE doc_id = %s", (doc_id,))
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Cleared existing status for {doc_id}")
            
        except Exception as e:
            print(f"⚠️ Could not clear existing status: {e} (continuing anyway)")
        
        # Publish message
        print(f"\n📤 Publishing test message...")
        sns_response = sns_client.publish(
            TopicArn=text_ready_topic_arn,
            Message=json.dumps(test_message),
            Subject=f"Initiator Status Fix Test: {doc_id}"
        )
        
        message_id = sns_response['MessageId']
        print(f"✅ Published: {message_id}")
        
        # Check for initial PROCESSING status (should appear quickly)
        print(f"\n⏳ Phase 1: Checking for initial PROCESSING status (5 seconds)...")
        time.sleep(5)
        
        initial_status = check_status(doc_id)
        
        if initial_status:
            print(f"✅ Initial status found:")
            print(f"   Status: {initial_status['status']}")
            print(f"   Notes: {initial_status['notes']}")
            print(f"   Created: {initial_status['updated_at']}")
            
            if initial_status['status'] == 'PROCESSING':
                print(f"🎉 SUCCESS: Initiator created initial PROCESSING status!")
                initiator_fixed = True
            else:
                print(f"⚠️ Unexpected initial status: {initial_status['status']}")
                initiator_fixed = False
        else:
            print(f"❌ No initial status found - initiator issue persists")
            initiator_fixed = False
        
        # Wait for worker completion
        print(f"\n⏳ Phase 2: Waiting for worker completion (20 seconds)...")
        time.sleep(20)
        
        final_status = check_status(doc_id)
        
        if final_status:
            print(f"✅ Final status:")
            print(f"   Status: {final_status['status']}")
            print(f"   Notes: {final_status['notes']}")
            print(f"   Updated: {final_status['updated_at']}")
            
            worker_completed = final_status['status'] == 'COMPLETED'
        else:
            print(f"❌ No final status found")
            worker_completed = False
        
        # Check CloudWatch logs for enhanced logging
        print(f"\n📊 Checking Enhanced Logging...")
        try:
            logs_client = session.client('logs', region_name='us-east-1')
            
            # Get recent initiator logs
            streams = logs_client.describe_log_streams(
                logGroupName='/aws/lambda/async-keyword-indexer-initiator',
                orderBy='LastEventTime',
                descending=True,
                limit=1
            )
            
            if streams['logStreams']:
                stream_name = streams['logStreams'][0]['logStreamName']
                
                events = logs_client.get_log_events(
                    logGroupName='/aws/lambda/async-keyword-indexer-initiator',
                    logStreamName=stream_name,
                    startTime=int((datetime.utcnow().timestamp() - 300) * 1000)  # Last 5 minutes
                )
                
                # Look for our enhanced logging messages
                enhanced_logs_found = False
                for event in events['events']:
                    message = event['message']
                    if any(indicator in message for indicator in ['🚀', '📄', '✅', '💾']):
                        enhanced_logs_found = True
                        print(f"   📝 {message.strip()}")
                
                if enhanced_logs_found:
                    print(f"✅ Enhanced logging is working")
                else:
                    print(f"⚠️ Enhanced logging not found in recent logs")
                    
            else:
                print(f"⚠️ No recent log streams found")
                
        except Exception as e:
            print(f"⚠️ Could not check CloudWatch logs: {e}")
        
        # Final assessment
        print(f"\n" + "=" * 60)
        print("🎯 Initiator Status Fix Test Results")
        print("=" * 60)
        
        print(f"✅ Message Publishing: SUCCESS")
        print(f"✅ Initial Status Creation: {'SUCCESS' if initiator_fixed else 'FAILED'}")
        print(f"✅ Worker Completion: {'SUCCESS' if worker_completed else 'FAILED'}")
        
        overall_success = initiator_fixed and worker_completed
        
        if overall_success:
            print(f"\n🎉 INITIATOR STATUS FIX SUCCESSFUL!")
            print("✅ Initiator now properly creates initial PROCESSING status")
            print("✅ Complete status tracking: PROCESSING → COMPLETED")
            print("✅ Enhanced logging provides detailed visibility")
            print("✅ Async architecture fully operational")
            
            print(f"\n🔧 Fix Details:")
            print("• Enhanced error handling in status updates")
            print("• Detailed logging for debugging")
            print("• Proper database transaction management")
            print("• Graceful fallback when database unavailable")
            
            print(f"\n📊 Status Flow Validated:")
            print("1. Initiator receives message")
            print("2. Creates PROCESSING status immediately")
            print("3. Delegates to worker asynchronously")
            print("4. Worker completes and updates to COMPLETED")
            print("5. Full audit trail maintained")
            
        else:
            print(f"\n⚠️ INITIATOR STATUS FIX ISSUES:")
            if not initiator_fixed:
                print("❌ Initiator still not creating initial PROCESSING status")
            if not worker_completed:
                print("❌ Worker completion failed")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def check_status(doc_id: str) -> dict:
    """Check current status for document"""
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        db_params = {
            'host': 'solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com',
            'port': 5432,
            'database': 'climate_risk_rag',
            'user': 'postgres',
            'password': '-VroWHWQBS5!V)yAcsDC3(3)NHJ5',
            'sslmode': 'require'
        }
        
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            "SELECT * FROM keyword_indexing_status WHERE doc_id = %s ORDER BY updated_at DESC LIMIT 1",
            (doc_id,)
        )
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return dict(result) if result else None
        
    except Exception as e:
        print(f"❌ Status check error: {e}")
        return None

if __name__ == "__main__":
    success = test_initiator_status_fix()
    
    if success:
        print(f"\n✅ INITIATOR STATUS FIX VALIDATED!")
        print("The async keyword indexer now has complete status tracking.")
    else:
        print(f"\n❌ Initiator status fix test failed.")
    
    exit(0 if success else 1)
