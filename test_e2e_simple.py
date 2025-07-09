#!/usr/bin/env python3
"""
Simple End-to-End Test for Standardized Messaging
Tests the complete pipeline with a real document
"""

import boto3
import json
import time
from datetime import datetime
from typing import List, Dict

class SimpleE2ETester:
    """Simple end-to-end tester for the pipeline"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        self.logs_client = boto3.client('logs', region_name='us-east-1')
        
        # Use existing POC document (small one for testing)
        self.test_bucket = "solve-global-kr-documents-861276078413-us-east-1"
        self.test_key = "documents/006893d2_93170cb9.pdf"  # Small 34KB document
        
        print(f"🧪 Testing with document: s3://{self.test_bucket}/{self.test_key}")
    
    def check_document_exists(self) -> bool:
        """Check if test document exists"""
        try:
            self.s3_client.head_object(Bucket=self.test_bucket, Key=self.test_key)
            print("✅ Test document exists")
            return True
        except Exception as e:
            print(f"❌ Test document not found: {e}")
            return False
    
    def trigger_textract_processing(self) -> bool:
        """Trigger Textract processing for the test document"""
        
        try:
            # Create test payload
            payload = {
                "Records": [
                    {
                        "s3": {
                            "bucket": {"name": self.test_bucket},
                            "object": {"key": self.test_key}
                        }
                    }
                ]
            }
            
            print("🚀 Triggering Textract initiator...")
            
            # Invoke Textract initiator
            response = self.lambda_client.invoke(
                FunctionName='solve-global-kr-textextractor-initiator',
                InvocationType='Event',  # Async
                Payload=json.dumps(payload)
            )
            
            print(f"✅ Textract initiator triggered (Status: {response['StatusCode']})")
            return True
            
        except Exception as e:
            print(f"❌ Error triggering Textract: {e}")
            return False
    
    def check_lambda_logs(self, function_name: str, minutes_back: int = 5) -> List[str]:
        """Check recent Lambda logs for a function"""
        
        try:
            log_group = f"/aws/lambda/{function_name}"
            
            # Get log streams from the last few minutes
            end_time = int(time.time() * 1000)
            start_time = end_time - (minutes_back * 60 * 1000)
            
            streams_response = self.logs_client.describe_log_streams(
                logGroupName=log_group,
                orderBy='LastEventTime',
                descending=True,
                limit=5
            )
            
            recent_logs = []
            
            for stream in streams_response['logStreams']:
                if stream.get('lastEventTime', 0) >= start_time:
                    events_response = self.logs_client.get_log_events(
                        logGroupName=log_group,
                        logStreamName=stream['logStreamName'],
                        startTime=start_time,
                        endTime=end_time
                    )
                    
                    for event in events_response['events']:
                        recent_logs.append(event['message'])
            
            return recent_logs
            
        except Exception as e:
            print(f"⚠️  Could not retrieve logs for {function_name}: {e}")
            return []
    
    def monitor_pipeline_progress(self, timeout_minutes: int = 10) -> Dict:
        """Monitor the pipeline progress by checking logs"""
        
        functions_to_monitor = [
            'solve-global-kr-textextractor-initiator',
            'solve-global-kr-textextractor-processor', 
            'text-chunker-pipeline',
            'nlp-processor',
            'nlp-worker'
        ]
        
        print(f"📊 Monitoring pipeline progress for {timeout_minutes} minutes...")
        
        start_time = time.time()
        results = {}
        
        while time.time() - start_time < (timeout_minutes * 60):
            print(f"\n⏱️  Checking progress at {datetime.now().strftime('%H:%M:%S')}...")
            
            for function_name in functions_to_monitor:
                if function_name not in results:
                    logs = self.check_lambda_logs(function_name, minutes_back=2)
                    
                    # Look for success indicators in logs
                    success_indicators = [
                        "Successfully processed",
                        "Processing complete",
                        "Message published",
                        "✅",
                        "SUCCESS"
                    ]
                    
                    error_indicators = [
                        "ERROR",
                        "Exception",
                        "Failed",
                        "❌"
                    ]
                    
                    has_success = any(indicator in log for log in logs for indicator in success_indicators)
                    has_error = any(indicator in log for log in logs for indicator in error_indicators)
                    
                    if has_success:
                        results[function_name] = "✅ SUCCESS"
                        print(f"  ✅ {function_name}: Processing successful")
                    elif has_error:
                        results[function_name] = "❌ ERROR"
                        print(f"  ❌ {function_name}: Error detected")
                    elif logs:
                        print(f"  🔄 {function_name}: Processing...")
                    else:
                        print(f"  ⏳ {function_name}: Waiting...")
            
            # Check if we have results for all functions
            if len(results) >= len(functions_to_monitor):
                break
            
            time.sleep(30)  # Wait 30 seconds between checks
        
        return results
    
    def run_end_to_end_test(self) -> bool:
        """Run complete end-to-end test"""
        
        print("🚀 Starting End-to-End Pipeline Test")
        print("=" * 60)
        
        # Step 1: Check test document
        if not self.check_document_exists():
            return False
        
        print("\n" + "=" * 60)
        
        # Step 2: Trigger processing
        if not self.trigger_textract_processing():
            return False
        
        print("\n" + "=" * 60)
        
        # Step 3: Monitor progress
        results = self.monitor_pipeline_progress(timeout_minutes=8)
        
        print("\n" + "=" * 60)
        print("📊 Final Results:")
        
        success_count = 0
        total_count = 0
        
        for function_name, status in results.items():
            print(f"  {status} {function_name}")
            total_count += 1
            if "SUCCESS" in status:
                success_count += 1
        
        print(f"\n📈 Pipeline Success Rate: {success_count}/{total_count}")
        
        if success_count >= 3:  # At least 3 stages successful
            print("\n🎉 End-to-End Test PASSED!")
            print("✅ Standardized messaging pipeline is working")
            return True
        else:
            print("\n⚠️  End-to-End Test PARTIAL SUCCESS")
            print("🔧 Some stages may need attention")
            return False

def main():
    """Main test function"""
    
    tester = SimpleE2ETester()
    success = tester.run_end_to_end_test()
    
    if success:
        print("\n🎯 Ready for production workloads!")
    else:
        print("\n🔧 Pipeline needs debugging")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
