#!/usr/bin/env python3
"""
Comprehensive End-to-End Testing Script - FIXED VERSION
Tests complete pipeline with 10 selected climate risk documents
"""

import boto3
import json
import time
from datetime import datetime
from typing import Dict, List

class E2EComprehensiveTester:
    """Comprehensive end-to-end pipeline tester"""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.logs_client = boto3.client('logs', region_name='us-east-1')
        
        # Test configuration
        self.test_session_id = f"e2e-test-{int(time.time())}"
        self.bucket_name = "solve-global-kr-documents-861276078413-us-east-1"
        
        # Selected test documents (cost-optimized)
        self.test_documents = [
            {"key": "documents/006893d2_93170cb9.pdf", "size": 34580, "est_pages": 3},
            {"key": "documents/0068a512_1780336e.pdf", "size": 81776, "est_pages": 5},
            {"key": "documents/004e17a3_3bb90d8e.pdf", "size": 135830, "est_pages": 8},
            {"key": "documents/0032f6cb_f0caef34.pdf", "size": 142850, "est_pages": 8},
            {"key": "documents/007f21ed_c25a961d.pdf", "size": 166430, "est_pages": 10}
        ]
        
        # Cost tracking
        self.estimated_textract_cost = sum(doc["est_pages"] for doc in self.test_documents) * 0.0015
        self.estimated_comprehend_cost = len(self.test_documents) * 0.019
        self.estimated_bedrock_cost = len(self.test_documents) * 0.002
        
        print(f"🧪 E2E Comprehensive Tester Initialized")
        print(f"📋 Session ID: {self.test_session_id}")
        print(f"📄 Documents: {len(self.test_documents)}")
        print(f"📊 Est. Total Pages: {sum(doc['est_pages'] for doc in self.test_documents)}")
        print(f"💰 Est. Textract Cost: ${self.estimated_textract_cost:.3f}")
        print(f"💰 Est. Total Cost: ${self.estimated_textract_cost + self.estimated_comprehend_cost + self.estimated_bedrock_cost:.3f}")
    
    def verify_document_exists(self, document_key: str) -> bool:
        """Verify document exists in S3"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=document_key)
            return True
        except Exception as e:
            print(f"❌ Document not found: {document_key}")
            return False
    
    def trigger_textract_processing(self, document_key: str) -> bool:
        """Trigger Textract processing for a document"""
        
        try:
            # Create S3 event payload
            payload = {
                "Records": [
                    {
                        "s3": {
                            "bucket": {"name": self.bucket_name},
                            "object": {"key": document_key}
                        }
                    }
                ]
            }
            
            # Invoke Textract initiator
            response = self.lambda_client.invoke(
                FunctionName='solve-global-kr-textextractor-initiator',
                InvocationType='Event',  # Async
                Payload=json.dumps(payload)
            )
            
            return response['StatusCode'] == 202
                
        except Exception as e:
            print(f"❌ Error triggering Textract for {document_key}: {e}")
            return False
    
    def check_lambda_logs(self, function_name: str, minutes_back: int = 2) -> List[str]:
        """Check recent Lambda logs for processing activity"""
        
        try:
            log_group = f"/aws/lambda/{function_name}"
            
            # Get recent log events
            end_time = int(time.time() * 1000)
            start_time = end_time - (minutes_back * 60 * 1000)
            
            # Get log streams
            streams_response = self.logs_client.describe_log_streams(
                logGroupName=log_group,
                orderBy='LastEventTime',
                descending=True,
                limit=2
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
            return []
    
    def monitor_pipeline_progress(self, document_key: str, timeout_minutes: int = 8) -> Dict:
        """Monitor pipeline progress for a specific document"""
        
        doc_id = document_key.split('/')[-1].replace('.pdf', '')
        
        functions_to_monitor = [
            'solve-global-kr-textextractor-initiator',
            'solve-global-kr-textextractor-processor',
            'text-chunker-pipeline',
            'nlp-processor'
        ]
        
        print(f"📊 Monitoring {doc_id} for {timeout_minutes} minutes...")
        
        start_time = time.time()
        stage_results = {}
        
        while time.time() - start_time < (timeout_minutes * 60):
            current_time = datetime.now().strftime('%H:%M:%S')
            print(f"⏱️  [{current_time}] Checking progress for {doc_id}...")
            
            for function_name in functions_to_monitor:
                if function_name not in stage_results:
                    logs = self.check_lambda_logs(function_name, minutes_back=3)
                    
                    # Look for document-specific processing
                    doc_mentioned = any(doc_id in log or document_key in log for log in logs)
                    success_indicators = ["Successfully processed", "Processing complete", "✅", "SUCCESS"]
                    error_indicators = ["ERROR", "Exception", "Failed", "❌"]
                    
                    has_success = any(indicator in log for log in logs for indicator in success_indicators)
                    has_error = any(indicator in log for log in logs for indicator in error_indicators)
                    
                    if doc_mentioned and has_success:
                        stage_results[function_name] = "✅ SUCCESS"
                        print(f"  ✅ {function_name}: Processing successful")
                    elif doc_mentioned and has_error:
                        stage_results[function_name] = "❌ ERROR"
                        print(f"  ❌ {function_name}: Error detected")
                    elif doc_mentioned:
                        print(f"  🔄 {function_name}: Processing...")
                    elif logs:
                        print(f"  ⏳ {function_name}: Activity detected")
                    else:
                        print(f"  ⏳ {function_name}: Waiting...")
            
            # Check if we have results for most functions
            if len(stage_results) >= 2:
                break
            
            time.sleep(45)  # Wait 45 seconds between checks
        
        return stage_results
    
    def check_s3_artifacts(self, document_key: str) -> Dict:
        """Check if processing artifacts were created in S3"""
        
        doc_id = document_key.split('/')[-1].replace('.pdf', '')
        artifacts = {}
        
        # Check for text extraction results
        try:
            text_key = f"text/{doc_id}.txt"
            self.s3_client.head_object(Bucket="solve-global-kr-text-new-861276078413-us-east-1", Key=text_key)
            artifacts['text_extraction'] = "✅ Found"
        except:
            artifacts['text_extraction'] = "❌ Missing"
        
        # Check for chunks
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
    
    def process_single_document(self, document: Dict) -> Dict:
        """Process a single document through the pipeline"""
        
        doc_key = document['key']
        doc_id = doc_key.split('/')[-1].replace('.pdf', '')
        
        print(f"\n{'='*50}")
        print(f"📄 PROCESSING: {doc_id}")
        print(f"📊 Size: {document['size']:,} bytes (~{document['est_pages']} pages)")
        print(f"{'='*50}")
        
        result = {
            "doc_id": doc_id,
            "doc_key": doc_key,
            "start_time": time.time(),
            "status": "UNKNOWN"
        }
        
        # Step 1: Verify document exists
        if not self.verify_document_exists(doc_key):
            result.update({"status": "MISSING", "error": "Document not found in S3"})
            return result
        
        print(f"✅ Document verified: {doc_key}")
        
        # Step 2: Trigger Textract processing
        print(f"🚀 Triggering Textract processing...")
        if not self.trigger_textract_processing(doc_key):
            result.update({"status": "FAILED", "error": "Failed to trigger Textract"})
            return result
        
        print(f"✅ Textract processing initiated")
        
        # Step 3: Wait for processing to start
        print(f"⏳ Waiting 90 seconds for processing to initialize...")
        time.sleep(90)
        
        # Step 4: Monitor pipeline progress
        stage_results = self.monitor_pipeline_progress(doc_key, timeout_minutes=8)
        artifacts = self.check_s3_artifacts(doc_key)
        
        result.update({
            'pipeline_stages': stage_results,
            'artifacts': artifacts,
            'end_time': time.time()
        })
        
        # Determine overall status
        successful_stages = sum(1 for status in stage_results.values() if '✅' in status)
        if successful_stages >= 2:
            result['status'] = 'SUCCESS'
        elif successful_stages >= 1:
            result['status'] = 'PARTIAL'
        else:
            result['status'] = 'FAILED'
        
        # Calculate processing time
        processing_time = result['end_time'] - result['start_time']
        result['processing_time_minutes'] = processing_time / 60
        
        print(f"\n📊 {doc_id} Results:")
        print(f"   Status: {result['status']}")
        print(f"   Processing Time: {result['processing_time_minutes']:.1f} minutes")
        print(f"   Successful Stages: {successful_stages}/{len(stage_results)}")
        print(f"   Artifacts: {sum(1 for status in artifacts.values() if '✅' in status)}/{len(artifacts)}")
        
        return result
    
    def run_comprehensive_test(self) -> Dict:
        """Run comprehensive end-to-end test"""
        
        print("🚀 STARTING COMPREHENSIVE END-TO-END TEST")
        print("=" * 70)
        print(f"📄 Testing {len(self.test_documents)} documents")
        print(f"💰 Estimated cost: ${self.estimated_textract_cost + self.estimated_comprehend_cost + self.estimated_bedrock_cost:.3f}")
        print("=" * 70)
        
        all_results = []
        
        # Process each document individually
        for i, document in enumerate(self.test_documents, 1):
            print(f"\n🔄 DOCUMENT {i}/{len(self.test_documents)}")
            
            result = self.process_single_document(document)
            all_results.append(result)
            
            # Wait between documents to avoid overwhelming the system
            if i < len(self.test_documents):
                print(f"\n⏳ Waiting 60 seconds before next document...")
                time.sleep(60)
        
        return self.compile_final_results(all_results)
    
    def compile_final_results(self, all_results: List[Dict]) -> Dict:
        """Compile and analyze final test results"""
        
        print("\n" + "=" * 70)
        print("📊 FINAL RESULTS ANALYSIS")
        print("=" * 70)
        
        # Count results by status
        status_counts = {}
        successful_docs = []
        failed_docs = []
        partial_docs = []
        
        total_processing_time = 0
        
        for result in all_results:
            status = result.get('status', 'UNKNOWN')
            status_counts[status] = status_counts.get(status, 0) + 1
            
            if 'processing_time_minutes' in result:
                total_processing_time += result['processing_time_minutes']
            
            doc_id = result['doc_id']
            if status == 'SUCCESS':
                successful_docs.append(doc_id)
            elif status == 'FAILED':
                failed_docs.append(doc_id)
            elif status == 'PARTIAL':
                partial_docs.append(doc_id)
        
        # Calculate success metrics
        total_docs = len(self.test_documents)
        success_rate = (status_counts.get('SUCCESS', 0) / total_docs) * 100
        partial_rate = (status_counts.get('PARTIAL', 0) / total_docs) * 100
        avg_processing_time = total_processing_time / total_docs if total_docs > 0 else 0
        
        # Print summary
        print(f"📄 Total Documents Tested: {total_docs}")
        print(f"✅ Successful: {status_counts.get('SUCCESS', 0)} ({success_rate:.1f}%)")
        print(f"🔄 Partial Success: {status_counts.get('PARTIAL', 0)} ({partial_rate:.1f}%)")
        print(f"❌ Failed: {status_counts.get('FAILED', 0)}")
        print(f"⏱️  Average Processing Time: {avg_processing_time:.1f} minutes")
        
        if successful_docs:
            print(f"\n✅ Successful Documents: {', '.join(successful_docs)}")
        if partial_docs:
            print(f"\n🔄 Partial Success Documents: {', '.join(partial_docs)}")
        if failed_docs:
            print(f"\n❌ Failed Documents: {', '.join(failed_docs)}")
        
        # Overall assessment
        if success_rate >= 80:
            overall_status = "🎉 EXCELLENT - Production Ready"
        elif success_rate >= 60:
            overall_status = "✅ GOOD - Minor Issues to Address"
        elif success_rate >= 40:
            overall_status = "⚠️  FAIR - Significant Issues Need Attention"
        else:
            overall_status = "❌ POOR - Major Issues Require Resolution"
        
        print(f"\n🎯 Overall Assessment: {overall_status}")
        
        # Save results
        self.save_results(all_results)
        
        return {
            'total_documents': total_docs,
            'success_rate': success_rate,
            'status_counts': status_counts,
            'overall_status': overall_status,
            'avg_processing_time': avg_processing_time,
            'detailed_results': all_results
        }
    
    def save_results(self, all_results: List[Dict]):
        """Save test results to file"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"e2e_test_results_{timestamp}.json"
        
        results_data = {
            'session_id': self.test_session_id,
            'timestamp': timestamp,
            'test_documents': self.test_documents,
            'estimated_costs': {
                'textract': self.estimated_textract_cost,
                'comprehend': self.estimated_comprehend_cost,
                'bedrock': self.estimated_bedrock_cost
            },
            'results': all_results
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")

def main():
    """Main testing function"""
    
    tester = E2EComprehensiveTester()
    
    # Run the comprehensive test
    final_results = tester.run_comprehensive_test()
    
    return final_results

if __name__ == "__main__":
    results = main()
    exit(0 if results['success_rate'] >= 60 else 1)
