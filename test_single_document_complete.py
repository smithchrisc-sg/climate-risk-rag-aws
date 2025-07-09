#!/usr/bin/env python3
"""
Single Document Complete Pipeline Test
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
        
        # Test document - small one
        self.test_document = {
            "key": "documents/006893d2_93170cb9.pdf",
            "size": 34580,
            "est_pages": 3
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
                return []\n            \n            stream_name = streams_response['logStreams'][0]['logStreamName']\n            \n            events_response = self.logs_client.get_log_events(\n                logGroupName=log_group,\n                logStreamName=stream_name,\n                startTime=start_time,\n                endTime=end_time\n            )\n            \n            return [event['message'] for event in events_response['events']]\n            \n        except Exception as e:\n            return []\n    \n    def check_sqs_messages(self, queue_url: str) -> list:\n        \"\"\"Check messages in SQS queue\"\"\"\n        \n        try:\n            response = self.sqs_client.receive_message(\n                QueueUrl=queue_url,\n                MaxNumberOfMessages=10,\n                WaitTimeSeconds=1\n            )\n            \n            return response.get('Messages', [])\n            \n        except Exception as e:\n            print(f\"⚠️  Could not check SQS queue: {e}\")\n            return []\n    \n    def check_s3_artifacts(self, doc_id: str) -> dict:\n        \"\"\"Check if processing artifacts were created\"\"\"\n        \n        artifacts = {}\n        \n        # Check text extraction\n        try:\n            text_key = f\"text/{doc_id}.txt\"\n            self.s3_client.head_object(Bucket=\"solve-global-kr-text-new-861276078413-us-east-1\", Key=text_key)\n            artifacts['text'] = \"✅ Found\"\n        except:\n            artifacts['text'] = \"❌ Missing\"\n        \n        # Check chunks\n        try:\n            chunks_prefix = f\"chunks/{doc_id}/\"\n            response = self.s3_client.list_objects_v2(\n                Bucket=\"solve-global-kr-chunks-861276078413-us-east-1\",\n                Prefix=chunks_prefix,\n                MaxKeys=1\n            )\n            if response.get('KeyCount', 0) > 0:\n                artifacts['chunks'] = \"✅ Found\"\n            else:\n                artifacts['chunks'] = \"❌ Missing\"\n        except:\n            artifacts['chunks'] = \"❌ Missing\"\n        \n        # Check NLP results\n        try:\n            nlp_prefix = f\"nlp/{doc_id}/\"\n            response = self.s3_client.list_objects_v2(\n                Bucket=\"solve-global-kr-ner-results-861276078413-us-east-1\",\n                Prefix=nlp_prefix,\n                MaxKeys=1\n            )\n            if response.get('KeyCount', 0) > 0:\n                artifacts['nlp'] = \"✅ Found\"\n            else:\n                artifacts['nlp'] = \"❌ Missing\"\n        except:\n            artifacts['nlp'] = \"❌ Missing\"\n        \n        return artifacts\n    \n    def run_complete_test(self) -> dict:\n        \"\"\"Run complete pipeline test\"\"\"\n        \n        doc_key = self.test_document['key']\n        doc_id = doc_key.split('/')[-1].replace('.pdf', '')\n        \n        print(f\"\\n🚀 STARTING COMPLETE PIPELINE TEST\")\n        print(f\"📄 Document: {doc_id}\")\n        print(\"=\" * 60)\n        \n        # Step 1: Trigger processing\n        print(f\"\\n1️⃣ Triggering Textract processing...\")\n        if not self.trigger_processing(doc_key):\n            return {\"status\": \"TRIGGER_FAILED\"}\n        \n        print(f\"✅ Processing triggered successfully\")\n        \n        # Step 2: Monitor Textract initiator\n        print(f\"\\n2️⃣ Monitoring Textract initiator (30 seconds)...\")\n        time.sleep(30)\n        \n        initiator_logs = self.check_function_logs('solve-global-kr-textextractor-initiator', minutes_back=2)\n        \n        print(f\"📋 Textract Initiator Logs:\")\n        for log in initiator_logs[-3:]:\n            if \"Started Textract job\" in log:\n                print(f\"  ✅ {log.strip()}\")\n            elif \"ERROR\" in log or \"Exception\" in log:\n                print(f\"  ❌ {log.strip()}\")\n            elif \"Processing complete\" in log:\n                print(f\"  ✅ {log.strip()}\")\n            else:\n                print(f\"  ℹ️  {log.strip()}\")\n        \n        # Step 3: Wait for Textract job completion and monitor processor\n        print(f\"\\n3️⃣ Waiting for Textract completion (3 minutes)...\")\n        time.sleep(180)\n        \n        processor_logs = self.check_function_logs('solve-global-kr-textextractor-processor', minutes_back=5)\n        \n        print(f\"📋 Textract Processor Logs:\")\n        for log in processor_logs[-5:]:\n            if \"Successfully processed\" in log or \"Processing complete\" in log:\n                print(f\"  ✅ {log.strip()}\")\n            elif \"ERROR\" in log or \"Exception\" in log or \"Invalid\" in log:\n                print(f\"  ❌ {log.strip()}\")\n            else:\n                print(f\"  ℹ️  {log.strip()}\")\n        \n        # Step 4: Check SQS queues\n        print(f\"\\n4️⃣ Checking SQS queues...\")\n        \n        # Check text chunker queue\n        chunker_messages = self.check_sqs_messages(\"https://sqs.us-east-1.amazonaws.com/861276078413/text-chunker-queue\")\n        print(f\"📬 Text Chunker Queue: {len(chunker_messages)} messages\")\n        \n        # Step 5: Monitor text chunker\n        if chunker_messages:\n            print(f\"\\n5️⃣ Text chunker has messages, waiting for processing (2 minutes)...\")\n            time.sleep(120)\n            \n            chunker_logs = self.check_function_logs('text-chunker-pipeline', minutes_back=3)\n            \n            print(f\"📋 Text Chunker Logs:\")\n            for log in chunker_logs[-3:]:\n                if \"Successfully processed\" in log or \"Processing complete\" in log:\n                    print(f\"  ✅ {log.strip()}\")\n                elif \"ERROR\" in log or \"Exception\" in log:\n                    print(f\"  ❌ {log.strip()}\")\n                else:\n                    print(f\"  ℹ️  {log.strip()}\")\n        \n        # Step 6: Check final artifacts\n        print(f\"\\n6️⃣ Checking final artifacts...\")\n        artifacts = self.check_s3_artifacts(doc_id)\n        \n        print(f\"📦 Artifacts Status:\")\n        for artifact_type, status in artifacts.items():\n            print(f\"  {artifact_type.upper()}: {status}\")\n        \n        # Step 7: Final assessment\n        print(f\"\\n📊 FINAL ASSESSMENT\")\n        print(\"=\" * 60)\n        \n        successful_artifacts = sum(1 for status in artifacts.values() if \"✅\" in status)\n        total_artifacts = len(artifacts)\n        \n        if successful_artifacts == total_artifacts:\n            overall_status = \"🎉 COMPLETE SUCCESS - Full pipeline working\"\n        elif successful_artifacts >= 1:\n            overall_status = f\"🔄 PARTIAL SUCCESS - {successful_artifacts}/{total_artifacts} stages completed\"\n        else:\n            overall_status = \"❌ FAILED - No artifacts created\"\n        \n        print(f\"🎯 Overall Status: {overall_status}\")\n        print(f\"📈 Success Rate: {successful_artifacts}/{total_artifacts} ({(successful_artifacts/total_artifacts)*100:.1f}%)\")\n        \n        return {\n            \"status\": \"COMPLETE\" if successful_artifacts == total_artifacts else \"PARTIAL\" if successful_artifacts > 0 else \"FAILED\",\n            \"artifacts\": artifacts,\n            \"success_rate\": successful_artifacts / total_artifacts,\n            \"initiator_logs\": initiator_logs[-3:],\n            \"processor_logs\": processor_logs[-5:],\n            \"chunker_messages\": len(chunker_messages)\n        }\n\ndef main():\n    \"\"\"Main test function\"\"\"\n    \n    tester = SingleDocumentTester()\n    results = tester.run_complete_test()\n    \n    return results\n\nif __name__ == \"__main__\":\n    results = main()\n    exit(0 if results['status'] == 'COMPLETE' else 1)"
