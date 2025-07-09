#!/usr/bin/env python3
"""
Single Document Complete Pipeline Test - FIXED
Test one document through the entire pipeline with detailed monitoring
"""

import boto3
import json
import time
from datetime import datetime

class SingleDocumentTester:
    """Test single document through complete pipeline"""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.logs_client = boto3.client('logs', region_name='us-east-1')
        self.sqs_client = boto3.client('sqs', region_name='us-east-1')
        
        # Test document - use a different one that hasn't been processed
        self.test_document = {
            "key": "documents/0032f6cb_f0caef34.pdf",
            "size": 142850,
            "est_pages": 8
        }
        
        self.bucket_name = "solve-global-kr-documents-861276078413-us-east-1"
        
        print(f"🧪 Single Document Complete Pipeline Tester")
        print(f"📄 Testing: {self.test_document['key']}")
        print(f"📊 Size: {self.test_document['size']:,} bytes (~{self.test_document['est_pages']} pages)")
    
    def create_proper_s3_event(self, document_key: str) -> dict:
        """Create properly formatted S3 event"""
        return {
            "Records": [
                {
                    "eventVersion": "2.1",
                    "eventSource": "aws:s3",
                    "eventTime": datetime.utcnow().isoformat() + "Z",
                    "eventName": "ObjectCreated:Put",
                    "s3": {
                        "s3SchemaVersion": "1.0",
                        "bucket": {
                            "name": self.bucket_name,
                            "arn": f"arn:aws:s3:::{self.bucket_name}"
                        },
                        "object": {
                            "key": document_key,
                            "size": self.test_document['size']
                        }
                    }
                }
            ]
        }
    
    def trigger_processing(self, document_key: str) -> bool:
        """Trigger document processing"""
        
        try:
            payload = self.create_proper_s3_event(document_key)
            
            response = self.lambda_client.invoke(
                FunctionName='solve-global-kr-textextractor-initiator',
                InvocationType='Event',
                Payload=json.dumps(payload)
            )
            
            return response['StatusCode'] == 202
            
        except Exception as e:
            print(f"❌ Error triggering processing: {e}")
            return False
    
    def check_function_logs(self, function_name: str, minutes_back: int = 5) -> list:
        """Check recent logs for a function"""
        
        try:
            log_group = f"/aws/lambda/{function_name}"
            
            end_time = int(time.time() * 1000)
            start_time = end_time - (minutes_back * 60 * 1000)
            
            streams_response = self.logs_client.describe_log_streams(
                logGroupName=log_group,
                orderBy='LastEventTime',
                descending=True,
                limit=1
            )
            
            if not streams_response['logStreams']:
                return []
            
            stream_name = streams_response['logStreams'][0]['logStreamName']
            
            events_response = self.logs_client.get_log_events(
                logGroupName=log_group,
                logStreamName=stream_name,
                startTime=start_time,
                endTime=end_time
            )
            
            return [event['message'] for event in events_response['events']]
            
        except Exception as e:
            return []
    
    def check_s3_artifacts(self, doc_id: str) -> dict:
        """Check if processing artifacts were created"""
        
        artifacts = {}
        
        # Check text extraction
        try:
            text_key = f"text/{doc_id}.txt"
            self.s3_client.head_object(Bucket="solve-global-kr-text-new-861276078413-us-east-1", Key=text_key)
            artifacts['text'] = "✅ Found"
        except:
            artifacts['text'] = "❌ Missing"
        
        # Check chunks
        try:
            chunks_prefix = f"chunks/{doc_id}/"
            response = self.s3_client.list_objects_v2(
                Bucket="solve-global-kr-chunks-861276078413-us-east-1",
                Prefix=chunks_prefix,
                MaxKeys=1
            )
            if response.get('KeyCount', 0) > 0:
                artifacts['chunks'] = "✅ Found"
            else:
                artifacts['chunks'] = "❌ Missing"
        except:
            artifacts['chunks'] = "❌ Missing"
        
        return artifacts
    
    def run_complete_test(self) -> dict:
        """Run complete pipeline test"""
        
        doc_key = self.test_document['key']
        doc_id = doc_key.split('/')[-1].replace('.pdf', '')
        
        print(f"\n🚀 STARTING COMPLETE PIPELINE TEST")
        print(f"📄 Document: {doc_id}")
        print("=" * 60)
        
        # Step 1: Trigger processing
        print(f"\n1️⃣ Triggering Textract processing...")
        if not self.trigger_processing(doc_key):
            return {"status": "TRIGGER_FAILED"}
        
        print(f"✅ Processing triggered successfully")
        
        # Step 2: Monitor Textract initiator
        print(f"\n2️⃣ Monitoring Textract initiator (30 seconds)...")
        time.sleep(30)
        
        initiator_logs = self.check_function_logs('solve-global-kr-textextractor-initiator', minutes_back=2)
        
        print(f"📋 Textract Initiator Logs:")
        for log in initiator_logs[-3:]:
            if "Started Textract job" in log:
                print(f"  ✅ {log.strip()}")
            elif "ERROR" in log or "Exception" in log:
                print(f"  ❌ {log.strip()}")
            elif "Processing complete" in log:
                print(f"  ✅ {log.strip()}")
            else:
                print(f"  ℹ️  {log.strip()}")
        
        # Step 3: Wait for Textract job completion and monitor processor
        print(f"\n3️⃣ Waiting for Textract completion (4 minutes)...")
        time.sleep(240)
        
        processor_logs = self.check_function_logs('solve-global-kr-textextractor-processor', minutes_back=5)
        
        print(f"📋 Textract Processor Logs:")
        for log in processor_logs[-5:]:
            if "Successfully processed" in log or "Processing complete" in log:
                print(f"  ✅ {log.strip()}")
            elif "ERROR" in log or "Exception" in log or "Invalid" in log:
                print(f"  ❌ {log.strip()}")
            else:
                print(f"  ℹ️  {log.strip()}")
        
        # Step 4: Wait for text chunker processing
        print(f"\n4️⃣ Waiting for text chunker processing (2 minutes)...")
        time.sleep(120)
        
        chunker_logs = self.check_function_logs('text-chunker-pipeline', minutes_back=3)
        
        print(f"📋 Text Chunker Logs:")
        for log in chunker_logs[-3:]:
            if "Successfully processed" in log or "Processing complete" in log:
                print(f"  ✅ {log.strip()}")
            elif "ERROR" in log or "Exception" in log:
                print(f"  ❌ {log.strip()}")
            else:
                print(f"  ℹ️  {log.strip()}")
        
        # Step 5: Check final artifacts
        print(f"\n5️⃣ Checking final artifacts...")
        artifacts = self.check_s3_artifacts(doc_id)
        
        print(f"📦 Artifacts Status:")
        for artifact_type, status in artifacts.items():
            print(f"  {artifact_type.upper()}: {status}")
        
        # Step 6: Final assessment
        print(f"\n📊 FINAL ASSESSMENT")
        print("=" * 60)
        
        successful_artifacts = sum(1 for status in artifacts.values() if "✅" in status)
        total_artifacts = len(artifacts)
        
        if successful_artifacts == total_artifacts:
            overall_status = "🎉 COMPLETE SUCCESS - Full pipeline working"
        elif successful_artifacts >= 1:
            overall_status = f"🔄 PARTIAL SUCCESS - {successful_artifacts}/{total_artifacts} stages completed"
        else:
            overall_status = "❌ FAILED - No artifacts created"
        
        print(f"🎯 Overall Status: {overall_status}")
        print(f"📈 Success Rate: {successful_artifacts}/{total_artifacts} ({(successful_artifacts/total_artifacts)*100:.1f}%)")
        
        return {
            "status": "COMPLETE" if successful_artifacts == total_artifacts else "PARTIAL" if successful_artifacts > 0 else "FAILED",
            "artifacts": artifacts,
            "success_rate": successful_artifacts / total_artifacts,
            "doc_id": doc_id
        }

def main():
    """Main test function"""
    
    tester = SingleDocumentTester()
    results = tester.run_complete_test()
    
    return results

if __name__ == "__main__":
    results = main()
    exit(0 if results['status'] == 'COMPLETE' else 1)
