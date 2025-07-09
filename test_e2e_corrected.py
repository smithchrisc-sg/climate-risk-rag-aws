#!/usr/bin/env python3
"""
Corrected End-to-End Testing Script
Tests complete pipeline with proper S3 event format
"""

import boto3
import json
import time
from datetime import datetime
from typing import Dict, List

class E2ECorrectedTester:
    """Corrected end-to-end pipeline tester with proper S3 event format"""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.logs_client = boto3.client('logs', region_name='us-east-1')
        
        # Test configuration
        self.test_session_id = f"e2e-corrected-{int(time.time())}"
        self.bucket_name = "solve-global-kr-documents-861276078413-us-east-1"
        
        # Start with just 2 small documents for initial validation
        self.test_documents = [
            {"key": "documents/006893d2_93170cb9.pdf", "size": 34580, "est_pages": 3},
            {"key": "documents/0068a512_1780336e.pdf", "size": 81776, "est_pages": 5}
        ]
        
        print(f"🧪 E2E Corrected Tester Initialized")
        print(f"📋 Session ID: {self.test_session_id}")
        print(f"📄 Documents: {len(self.test_documents)} (small test batch)")
        print(f"📊 Est. Total Pages: {sum(doc['est_pages'] for doc in self.test_documents)}")
    
    def create_proper_s3_event(self, document_key: str) -> Dict:
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
                            "size": 1024
                        }
                    }
                }
            ]
        }
    
    def trigger_textract_processing(self, document_key: str) -> bool:
        """Trigger Textract processing with proper S3 event format"""
        
        try:
            # Create proper S3 event payload
            payload = self.create_proper_s3_event(document_key)
            
            print(f"🔧 Using proper S3 event format for {document_key}")
            
            # Invoke Textract initiator
            response = self.lambda_client.invoke(
                FunctionName='solve-global-kr-textextractor-initiator',
                InvocationType='Event',  # Async
                Payload=json.dumps(payload)
            )
            
            if response['StatusCode'] == 202:
                print(f"✅ Textract initiated successfully")
                return True
            else:
                print(f"❌ Textract initiation failed: {response['StatusCode']}")
                return False
                
        except Exception as e:
            print(f"❌ Error triggering Textract: {e}")
            return False
    
    def check_textract_initiator_logs(self, minutes_back: int = 2) -> List[str]:
        """Check Textract initiator logs specifically"""
        
        try:
            log_group = "/aws/lambda/solve-global-kr-textextractor-initiator"
            
            # Get recent log events
            end_time = int(time.time() * 1000)
            start_time = end_time - (minutes_back * 60 * 1000)
            
            # Get most recent log stream
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
            print(f"⚠️  Could not retrieve initiator logs: {e}")
            return []
    
    def test_single_document(self, document: Dict) -> Dict:
        """Test processing of a single document"""
        
        doc_key = document['key']
        doc_id = doc_key.split('/')[-1].replace('.pdf', '')
        
        print(f"\n{'='*50}")
        print(f"📄 TESTING: {doc_id}")
        print(f"📊 Size: {document['size']:,} bytes (~{document['est_pages']} pages)")
        print(f"{'='*50}")
        
        result = {
            "doc_id": doc_id,
            "doc_key": doc_key,
            "start_time": time.time(),
            "status": "TESTING"
        }
        
        # Step 1: Verify document exists
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=doc_key)
            print(f"✅ Document verified in S3")
        except Exception as e:
            print(f"❌ Document not found: {e}")
            result.update({"status": "MISSING", "error": str(e)})
            return result
        
        # Step 2: Trigger Textract with proper event format
        print(f"🚀 Triggering Textract processing...")
        if not self.trigger_textract_processing(doc_key):
            result.update({"status": "TRIGGER_FAILED", "error": "Failed to trigger Textract"})
            return result
        
        # Step 3: Wait and check initiator logs
        print(f"⏳ Waiting 30 seconds for initiator processing...")
        time.sleep(30)
        
        initiator_logs = self.check_textract_initiator_logs(minutes_back=2)
        
        # Analyze initiator logs
        success_indicators = ["Processing complete", "success"]
        error_indicators = ["Unsupported event source", "ERROR", "Exception"]
        warning_indicators = ["WARNING"]
        
        has_success = any(indicator in log for log in initiator_logs for indicator in success_indicators)
        has_error = any(indicator in log for log in initiator_logs for indicator in error_indicators)
        has_warning = any(indicator in log for log in initiator_logs for indicator in warning_indicators)
        
        print(f"\n📋 Initiator Log Analysis:")
        for log in initiator_logs[-5:]:  # Show last 5 log entries
            if any(indicator in log for indicator in error_indicators):
                print(f"  ❌ {log.strip()}")
            elif any(indicator in log for indicator in warning_indicators):
                print(f"  ⚠️  {log.strip()}")
            elif any(indicator in log for indicator in success_indicators):
                print(f"  ✅ {log.strip()}")
            else:
                print(f"  ℹ️  {log.strip()}")
        
        # Determine result
        if has_error or has_warning:
            if "Unsupported event source" in str(initiator_logs):
                result.update({
                    "status": "EVENT_FORMAT_ERROR", 
                    "error": "Textract initiator doesn't recognize event format"
                })
            else:
                result.update({
                    "status": "INITIATOR_ERROR", 
                    "error": "Error in Textract initiator processing"
                })
        elif has_success:
            result.update({"status": "INITIATED_SUCCESS"})
            
            # Wait longer and check for downstream processing
            print(f"⏳ Waiting 2 minutes for downstream processing...")
            time.sleep(120)
            
            # Check if text was extracted
            try:
                text_key = f"text/{doc_id}.txt"
                self.s3_client.head_object(Bucket="solve-global-kr-text-new-861276078413-us-east-1", Key=text_key)
                result.update({"status": "TEXT_EXTRACTED", "text_artifact": "✅ Found"})
                print(f"✅ Text extraction successful")
            except:
                result.update({"status": "TEXT_EXTRACTION_PENDING", "text_artifact": "❌ Not found yet"})
                print(f"⏳ Text extraction still in progress or failed")
        else:
            result.update({"status": "NO_CLEAR_RESULT", "error": "Unclear result from logs"})
        
        result['end_time'] = time.time()
        result['processing_time_minutes'] = (result['end_time'] - result['start_time']) / 60
        result['initiator_logs'] = initiator_logs
        
        print(f"\n📊 {doc_id} Test Results:")
        print(f"   Status: {result['status']}")
        print(f"   Processing Time: {result['processing_time_minutes']:.1f} minutes")
        
        return result
    
    def run_corrected_test(self) -> Dict:
        """Run corrected end-to-end test"""
        
        print("🚀 STARTING CORRECTED END-TO-END TEST")
        print("=" * 60)
        print("🎯 Focus: Validate Textract initiator with proper S3 event format")
        print("=" * 60)
        
        all_results = []
        
        for i, document in enumerate(self.test_documents, 1):
            print(f"\n🔄 DOCUMENT {i}/{len(self.test_documents)}")
            
            result = self.test_single_document(document)
            all_results.append(result)
            
            # Short wait between documents
            if i < len(self.test_documents):
                print(f"\n⏳ Waiting 30 seconds before next document...")
                time.sleep(30)
        
        return self.analyze_results(all_results)
    
    def analyze_results(self, all_results: List[Dict]) -> Dict:
        """Analyze test results"""
        
        print("\n" + "=" * 60)
        print("📊 CORRECTED TEST RESULTS ANALYSIS")
        print("=" * 60)
        
        # Count results by status
        status_counts = {}
        for result in all_results:
            status = result.get('status', 'UNKNOWN')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"📄 Total Documents Tested: {len(self.test_documents)}")
        
        for status, count in status_counts.items():
            if "SUCCESS" in status or "EXTRACTED" in status:
                print(f"✅ {status}: {count}")
            elif "ERROR" in status or "FAILED" in status:
                print(f"❌ {status}: {count}")
            else:
                print(f"🔄 {status}: {count}")
        
        # Determine if the core issue is fixed
        event_format_errors = status_counts.get('EVENT_FORMAT_ERROR', 0)
        successful_initiations = sum(count for status, count in status_counts.items() 
                                   if 'SUCCESS' in status or 'EXTRACTED' in status)
        
        if event_format_errors == 0 and successful_initiations > 0:
            overall_status = "🎉 FIXED - Event format issue resolved"
        elif event_format_errors == 0:
            overall_status = "✅ IMPROVED - No event format errors, but processing needs attention"
        else:
            overall_status = "❌ STILL BROKEN - Event format issue persists"
        
        print(f"\n🎯 Overall Assessment: {overall_status}")
        
        # Save results
        self.save_results(all_results)
        
        return {
            'total_documents': len(self.test_documents),
            'status_counts': status_counts,
            'overall_status': overall_status,
            'event_format_fixed': event_format_errors == 0,
            'detailed_results': all_results
        }
    
    def save_results(self, all_results: List[Dict]):
        """Save test results"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"e2e_corrected_test_results_{timestamp}.json"
        
        results_data = {
            'session_id': self.test_session_id,
            'timestamp': timestamp,
            'test_documents': self.test_documents,
            'results': all_results
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")

def main():
    """Main testing function"""
    
    tester = E2ECorrectedTester()
    final_results = tester.run_corrected_test()
    
    return final_results

if __name__ == "__main__":
    results = main()
    # Success if event format is fixed
    exit(0 if results['event_format_fixed'] else 1)
