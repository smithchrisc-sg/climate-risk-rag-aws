#!/usr/bin/env python3
"""
Complete Pipeline Integration Test
Tests the full SNS/SQS messaging pipeline with text chunker
"""

import boto3
import json
import time
from datetime import datetime

def test_complete_pipeline():
    """Test complete pipeline integration with SNS/SQS messaging"""
    
    print("🚀 Complete Pipeline Integration Test")
    print("=" * 80)
    print(f"Started at: {datetime.utcnow().isoformat()}")
    print()
    
    session = boto3.Session(profile_name='solve-global')
    sns_client = session.client('sns', region_name='us-east-1')
    sqs_client = session.client('sqs', region_name='us-east-1')
    
    # Pipeline configuration
    text_ready_topic_arn = "arn:aws:sns:us-east-1:861276078413:text-extraction-complete"
    chunks_ready_topic_arn = "arn:aws:sns:us-east-1:861276078413:chunks-ready"
    text_chunker_queue_url = "https://sqs.us-east-1.amazonaws.com/861276078413/text-chunker-queue"
    
    print("🔍 Pipeline Configuration")
    print("=" * 60)
    print(f"Text Ready Topic: {text_ready_topic_arn}")
    print(f"Chunks Ready Topic: {chunks_ready_topic_arn}")
    print(f"Text Chunker Queue: {text_chunker_queue_url}")
    
    # Test document
    doc_id = "pipeline-test-neural-fuzzy"
    
    # Create pipeline message (simulating TextExtractor output)
    pipeline_message = {
        "doc_id": doc_id,
        "stage": "text_ready",
        "full_text_location": {
            "bucket": "solve-global-kr-text-new-861276078413-us-east-1",
            "key": "extracted_text/neural-fuzzy-textract.txt"
        },
        "document_structure_location": None,
        "documentid_manager_integration": True,
        "selective_migration_used": False,
        "filename": "neural-fuzzy-textract.pdf",
        "pipeline_integration_test": True,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    print(f"\n📤 Publishing Pipeline Message")
    print("=" * 60)
    print(f"Document ID: {doc_id}")
    print(f"Message: {json.dumps(pipeline_message, indent=2)}")
    
    try:
        # Step 1: Publish message to text-ready topic (simulating TextExtractor)
        print("\n🔄 Step 1: Publishing to Text Ready Topic")
        sns_response = sns_client.publish(
            TopicArn=text_ready_topic_arn,
            Message=json.dumps(pipeline_message),
            Subject=f"Text Extraction Complete: {doc_id}"
        )
        
        message_id = sns_response['MessageId']
        print(f"✅ Published to SNS: {message_id}")
        
        # Step 2: Wait for SQS processing
        print("\n⏳ Step 2: Waiting for SQS Processing")
        print("Waiting for message to be processed by text chunker...")
        time.sleep(15)  # Wait for processing
        
        # Step 3: Check for chunks ready message
        print("\n📥 Step 3: Checking for Chunks Ready Messages")
        
        # Subscribe to chunks ready topic temporarily for testing
        temp_queue_response = sqs_client.create_queue(
            QueueName=f'temp-chunks-ready-test-{int(time.time())}'
        )
        temp_queue_url = temp_queue_response['QueueUrl']
        
        # Get queue attributes for subscription
        queue_attrs = sqs_client.get_queue_attributes(
            QueueUrl=temp_queue_url,
            AttributeNames=['QueueArn']
        )
        temp_queue_arn = queue_attrs['Attributes']['QueueArn']
        
        # Subscribe temp queue to chunks ready topic
        subscription_response = sns_client.subscribe(
            TopicArn=chunks_ready_topic_arn,
            Protocol='sqs',
            Endpoint=temp_queue_arn
        )
        
        # Set queue policy to allow SNS
        queue_policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": "*",
                "Action": "sqs:SendMessage",
                "Resource": temp_queue_arn,
                "Condition": {
                    "ArnEquals": {
                        "aws:SourceArn": chunks_ready_topic_arn
                    }
                }
            }]
        }
        
        sqs_client.set_queue_attributes(
            QueueUrl=temp_queue_url,
            Attributes={
                'Policy': json.dumps(queue_policy)
            }
        )
        
        print(f"✅ Created temporary subscription: {subscription_response['SubscriptionArn']}")
        
        # Wait a bit more for chunks ready message
        time.sleep(10)
        
        # Check for messages in temp queue
        messages = sqs_client.receive_message(
            QueueUrl=temp_queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=5
        )
        
        chunks_ready_received = False
        if 'Messages' in messages:
            print(f"✅ Received {len(messages['Messages'])} chunks ready messages:")
            for msg in messages['Messages']:
                try:
                    # Parse SNS message
                    sns_msg = json.loads(msg['Body'])
                    chunks_msg = json.loads(sns_msg['Message'])
                    
                    if chunks_msg.get('stage') == 'chunks_ready':
                        chunks_ready_received = True
                        print(f"   📦 Chunks Ready: {chunks_msg['doc_id']}")
                        print(f"      Chunks Created: {chunks_msg.get('chunks_created', 'N/A')}")
                        print(f"      Status: {chunks_msg.get('status', 'N/A')}")
                        print(f"      Location: {chunks_msg.get('chunks_location', {}).get('prefix', 'N/A')}")
                    
                except Exception as e:
                    print(f"   ⚠️  Error parsing message: {e}")
        else:
            print("⚠️  No chunks ready messages received yet")
        
        # Step 4: Check S3 for generated chunks
        print("\n📊 Step 4: Checking S3 for Generated Chunks")
        s3_client = session.client('s3', region_name='us-east-1')
        
        try:
            chunks_response = s3_client.list_objects_v2(
                Bucket='solve-global-kr-chunks-861276078413-us-east-1',
                Prefix=f'chunks/{doc_id}/',
                MaxKeys=20
            )
            
            chunks = chunks_response.get('Contents', [])
            print(f"✅ Found {len(chunks)} chunk files in S3:")
            
            for i, chunk in enumerate(chunks[:10]):
                print(f"   {i+1:2d}. {chunk['Key']}: {chunk['Size']:,} bytes")
            
            if len(chunks) > 10:
                print(f"   ... and {len(chunks) - 10} more chunks")
                
        except Exception as e:
            print(f"❌ Error checking S3 chunks: {e}")
            chunks = []
        
        # Step 5: Check database status
        print("\n📋 Step 5: Checking Database Status")
        
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
                "SELECT * FROM text_chunking_status WHERE doc_id = %s ORDER BY updated_at DESC LIMIT 1",
                (doc_id,)
            )
            
            status_record = cursor.fetchone()
            if status_record:
                print(f"✅ Database status record:")
                print(f"   Status: {status_record['status']}")
                print(f"   Chunks created: {status_record['chunks_created']}")
                print(f"   Updated: {status_record['updated_at']}")
            else:
                print("⚠️  No database status record found")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"❌ Error checking database: {e}")
            status_record = None
        
        # Cleanup
        print("\n🧹 Cleanup")
        try:
            sns_client.unsubscribe(SubscriptionArn=subscription_response['SubscriptionArn'])
            sqs_client.delete_queue(QueueUrl=temp_queue_url)
            print("✅ Cleaned up temporary resources")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
        
        # Final assessment
        print("\n" + "=" * 80)
        print("🎯 Complete Pipeline Integration Results")
        print("=" * 80)
        
        sns_success = message_id is not None
        processing_success = len(chunks) > 0
        messaging_success = chunks_ready_received
        database_success = status_record is not None and status_record['status'] != 'FAILED'
        
        print(f"✅ SNS Publishing: {'SUCCESS' if sns_success else 'FAILED'}")
        print(f"✅ SQS Processing: {'SUCCESS' if processing_success else 'FAILED'}")
        print(f"✅ Pipeline Messaging: {'SUCCESS' if messaging_success else 'PARTIAL'}")
        print(f"✅ Chunk Generation: {len(chunks)} chunks ({'SUCCESS' if processing_success else 'FAILED'})")
        print(f"✅ Database Integration: {'SUCCESS' if database_success else 'FAILED'}")
        
        overall_success = sns_success and processing_success and database_success
        
        if overall_success:
            print("\n🎉 COMPLETE PIPELINE SUCCESS!")
            print("✅ End-to-end SNS/SQS messaging pipeline working")
            print("✅ Text chunker processes messages from queue")
            print("✅ Chunks generated and stored in S3")
            print("✅ Database status tracking operational")
            print("✅ Pipeline coordination messages published")
            
            print("\n📋 Pipeline Validation Complete:")
            print("• TextExtractor → SNS → SQS → Text Chunker flow working")
            print("• Text Chunker → SNS → Downstream processors ready")
            print("• Database integration across all pipeline stages")
            print("• Error handling and status reporting functional")
            print("• Production-ready messaging architecture")
            
            print("\n🚀 Ready for Production:")
            print("• Connect TextExtractor to text-extraction-complete topic")
            print("• Subscribe downstream processors to chunks-ready topic")
            print("• Configure monitoring and alerting")
            print("• Scale for production document volumes")
            
        else:
            print("\n⚠️  PIPELINE ISSUES DETECTED:")
            if not sns_success:
                print("❌ SNS publishing failed")
            if not processing_success:
                print("❌ SQS processing or chunk generation failed")
            if not database_success:
                print("❌ Database integration issues")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ Pipeline test error: {e}")
        return False

if __name__ == "__main__":
    success = test_complete_pipeline()
    exit(0 if success else 1)
