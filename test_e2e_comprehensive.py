#!/usr/bin/env python3
"""
Comprehensive End-to-End Testing Script
Tests complete pipeline with 10 selected climate risk documents
"""

import boto3
import json
import time
import csv
from datetime import datetime
from typing import Dict, List

class E2EComprehensiveTester:
    """Comprehensive end-to-end pipeline tester"""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.logs_client = boto3.client('logs', region_name='us-east-1')
        self.sns_client = boto3.client('sns', region_name='us-east-1')
        
        # Test configuration
        self.test_session_id = f"e2e-test-{int(time.time())}"
        self.bucket_name = "solve-global-kr-documents-861276078413-us-east-1"
        
        # Selected test documents (cost-optimized)
        self.test_documents = [
            {"key": "documents/006893d2_93170cb9.pdf", "size": 34580, "est_pages": 3},
            {"key": "documents/0068a512_1780336e.pdf", "size": 81776, "est_pages": 5},
            {"key": "documents/004e17a3_3bb90d8e.pdf", "size": 135830, "est_pages": 8},
            {"key": "documents/0032f6cb_f0caef34.pdf", "size": 142850, "est_pages": 8},
            {"key": "documents/007f21ed_c25a961d.pdf", "size": 166430, "est_pages": 10},
            {"key": "documents/0004ad39_4285ab3d.pdf", "size": 458718, "est_pages": 25},
            {"key": "documents/002328de_230b4003.pdf", "size": 602461, "est_pages": 30},
            {"key": "documents/00eb3286_a3572ad0.pdf", "size": 783647, "est_pages": 35},
            {"key": "documents/00dc6a68_6a5bc5a9.pdf", "size": 1181179, "est_pages": 50},
            {"key": "documents/00f00dd5_35c93ca5.pdf", "size": 1369827, "est_pages": 55}
        ]
        
        # Cost tracking
        self.estimated_textract_cost = sum(doc["est_pages"] for doc in self.test_documents) * 0.0015
        self.estimated_comprehend_cost = len(self.test_documents) * 0.019
        self.estimated_bedrock_cost = len(self.test_documents) * 0.002
        
        # Results tracking
        self.results = {
            "session_id": self.test_session_id,
            "start_time": datetime.now().isoformat(),
            "documents": {},
            "pipeline_stages": {},
            "costs": {},
            "performance": {},
            "errors": []
        }
        
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
            print(f"❌ Document not found: {document_key} - {e}")
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
            
            if response['StatusCode'] == 202:
                print(f"✅ Textract initiated for {document_key}")
                return True
            else:
                print(f"❌ Textract initiation failed for {document_key}: {response['StatusCode']}")
                return False
                
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
                limit=3
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
    
    def monitor_pipeline_progress(self, document_key: str, timeout_minutes: int = 15) -> Dict:
        """Monitor pipeline progress for a specific document"""
        
        doc_id = document_key.split('/')[-1].replace('.pdf', '')
        
        functions_to_monitor = [
            'solve-global-kr-textextractor-initiator',
            'solve-global-kr-textextractor-processor',
            'text-chunker-pipeline',
            'nlp-processor',
            'nlp-worker'
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
                    else:
                        print(f"  ⏳ {function_name}: Waiting...")
            
            # Check if we have results for most functions
            if len(stage_results) >= 3:
                break
            
            time.sleep(30)  # Wait 30 seconds between checks
        
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
        
        # Check for NLP results
        try:
            nlp_prefix = f"nlp/{doc_id}/"
            response = self.s3_client.list_objects_v2(
                Bucket="solve-global-kr-ner-results-861276078413-us-east-1",
                Prefix=nlp_prefix,
                MaxKeys=1
            )
            if response.get('KeyCount', 0) > 0:
                artifacts['nlp_results'] = "✅ Found"
            else:
                artifacts['nlp_results'] = "❌ Missing"
        except:
            artifacts['nlp_results'] = "❌ Missing"
        
        return artifacts
    
    def process_document_batch(self, batch_documents: List[Dict], batch_number: int) -> Dict:
        """Process a batch of documents"""
        
        print(f"\n{'='*60}")
        print(f"📦 PROCESSING BATCH {batch_number}")
        print(f"📄 Documents: {len(batch_documents)}")
        print(f"{'='*60}")
        
        batch_results = {}
        
        # Step 1: Verify all documents exist
        for doc in batch_documents:
            doc_key = doc['key']
            doc_id = doc_key.split('/')[-1].replace('.pdf', '')
            
            print(f"\n🔍 Verifying {doc_id}...")
            if self.verify_document_exists(doc_key):
                print(f"✅ Document exists: {doc_key}")
            else:
                print(f"❌ Document missing: {doc_key}")
                batch_results[doc_id] = {"status": "MISSING", "error": "Document not found in S3"}
                continue
        
        # Step 2: Trigger processing for all documents in batch
        for doc in batch_documents:
            doc_key = doc['key']
            doc_id = doc_key.split('/')[-1].replace('.pdf', '')\n            \n            if doc_id not in batch_results:  # Skip if already failed\n                print(f\"\\n🚀 Triggering processing for {doc_id}...\")\n                if self.trigger_textract_processing(doc_key):\n                    batch_results[doc_id] = {\"status\": \"PROCESSING\", \"start_time\": time.time()}\n                else:\n                    batch_results[doc_id] = {\"status\": \"FAILED\", \"error\": \"Failed to trigger Textract\"}\n        \n        # Step 3: Wait for initial processing to start\n        print(f\"\\n⏳ Waiting 60 seconds for processing to initialize...\")\n        time.sleep(60)\n        \n        # Step 4: Monitor each document's progress\n        for doc in batch_documents:\n            doc_key = doc['key']\n            doc_id = doc_key.split('/')[-1].replace('.pdf', '')\n            \n            if batch_results.get(doc_id, {}).get('status') == 'PROCESSING':\n                print(f\"\\n📊 Monitoring {doc_id} pipeline progress...\")\n                stage_results = self.monitor_pipeline_progress(doc_key, timeout_minutes=10)\n                artifacts = self.check_s3_artifacts(doc_key)\n                \n                batch_results[doc_id].update({\n                    'pipeline_stages': stage_results,\n                    'artifacts': artifacts,\n                    'end_time': time.time()\n                })\n                \n                # Determine overall status\n                successful_stages = sum(1 for status in stage_results.values() if '✅' in status)\n                if successful_stages >= 3:\n                    batch_results[doc_id]['status'] = 'SUCCESS'\n                elif successful_stages >= 1:\n                    batch_results[doc_id]['status'] = 'PARTIAL'\n                else:\n                    batch_results[doc_id]['status'] = 'FAILED'\n        \n        return batch_results\n    \n    def run_comprehensive_test(self) -> Dict:\n        \"\"\"Run comprehensive end-to-end test\"\"\"\n        \n        print(\"🚀 STARTING COMPREHENSIVE END-TO-END TEST\")\n        print(\"=\" * 70)\n        \n        # Process documents in batches of 3 to manage load and costs\n        batch_size = 3\n        all_results = {}\n        \n        for i in range(0, len(self.test_documents), batch_size):\n            batch = self.test_documents[i:i+batch_size]\n            batch_number = (i // batch_size) + 1\n            \n            batch_results = self.process_document_batch(batch, batch_number)\n            all_results.update(batch_results)\n            \n            # Wait between batches to avoid overwhelming the system\n            if i + batch_size < len(self.test_documents):\n                print(f\"\\n⏳ Waiting 120 seconds before next batch...\")\n                time.sleep(120)\n        \n        # Final results compilation\n        self.results['end_time'] = datetime.now().isoformat()\n        self.results['documents'] = all_results\n        \n        return self.compile_final_results()\n    \n    def compile_final_results(self) -> Dict:\n        \"\"\"Compile and analyze final test results\"\"\"\n        \n        print(\"\\n\" + \"=\" * 70)\n        print(\"📊 FINAL RESULTS ANALYSIS\")\n        print(\"=\" * 70)\n        \n        # Count results by status\n        status_counts = {}\n        successful_docs = []\n        failed_docs = []\n        partial_docs = []\n        \n        for doc_id, result in self.results['documents'].items():\n            status = result.get('status', 'UNKNOWN')\n            status_counts[status] = status_counts.get(status, 0) + 1\n            \n            if status == 'SUCCESS':\n                successful_docs.append(doc_id)\n            elif status == 'FAILED':\n                failed_docs.append(doc_id)\n            elif status == 'PARTIAL':\n                partial_docs.append(doc_id)\n        \n        # Calculate success metrics\n        total_docs = len(self.test_documents)\n        success_rate = (status_counts.get('SUCCESS', 0) / total_docs) * 100\n        partial_rate = (status_counts.get('PARTIAL', 0) / total_docs) * 100\n        \n        # Print summary\n        print(f\"📄 Total Documents Tested: {total_docs}\")\n        print(f\"✅ Successful: {status_counts.get('SUCCESS', 0)} ({success_rate:.1f}%)\")\n        print(f\"🔄 Partial Success: {status_counts.get('PARTIAL', 0)} ({partial_rate:.1f}%)\")\n        print(f\"❌ Failed: {status_counts.get('FAILED', 0)}\")\n        print(f\"⚠️  Missing: {status_counts.get('MISSING', 0)}\")\n        \n        if successful_docs:\n            print(f\"\\n✅ Successful Documents: {', '.join(successful_docs)}\")\n        if partial_docs:\n            print(f\"\\n🔄 Partial Success Documents: {', '.join(partial_docs)}\")\n        if failed_docs:\n            print(f\"\\n❌ Failed Documents: {', '.join(failed_docs)}\")\n        \n        # Overall assessment\n        if success_rate >= 80:\n            overall_status = \"🎉 EXCELLENT - Production Ready\"\n        elif success_rate >= 60:\n            overall_status = \"✅ GOOD - Minor Issues to Address\"\n        elif success_rate >= 40:\n            overall_status = \"⚠️  FAIR - Significant Issues Need Attention\"\n        else:\n            overall_status = \"❌ POOR - Major Issues Require Resolution\"\n        \n        print(f\"\\n🎯 Overall Assessment: {overall_status}\")\n        \n        # Save results\n        self.save_results()\n        \n        return {\n            'total_documents': total_docs,\n            'success_rate': success_rate,\n            'status_counts': status_counts,\n            'overall_status': overall_status,\n            'detailed_results': self.results\n        }\n    \n    def save_results(self):\n        \"\"\"Save test results to file\"\"\"\n        \n        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')\n        filename = f\"e2e_test_results_{timestamp}.json\"\n        \n        with open(filename, 'w') as f:\n            json.dump(self.results, f, indent=2)\n        \n        print(f\"\\n💾 Results saved to: {filename}\")\n\ndef main():\n    \"\"\"Main testing function\"\"\"\n    \n    tester = E2EComprehensiveTester()\n    \n    # Confirm before starting\n    print(f\"\\n⚠️  COST ESTIMATE: ~${tester.estimated_textract_cost + tester.estimated_comprehend_cost + tester.estimated_bedrock_cost:.3f}\")\n    print(\"📋 This will process 10 documents through the complete pipeline\")\n    \n    # Run the comprehensive test\n    final_results = tester.run_comprehensive_test()\n    \n    return final_results\n\nif __name__ == \"__main__\":\n    results = main()\n    exit(0 if results['success_rate'] >= 60 else 1)"
