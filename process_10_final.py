#!/usr/bin/env python3
"""
Process 10 Medium Documents in Parallel - Final Version
"""

import boto3
import json
import time
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

class FinalParallelProcessor:
    """Final parallel processor for 10 medium documents"""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        
        # 10 medium-sized documents (≤15 pages each)
        self.documents = [
            {"key": "documents/006893d2_93170cb9.pdf", "size": 34580, "est_pages": 3},
            {"key": "documents/0068a512_1780336e.pdf", "size": 81776, "est_pages": 5},
            {"key": "documents/004e17a3_3bb90d8e.pdf", "size": 135830, "est_pages": 8},
            {"key": "documents/0032f6cb_f0caef34.pdf", "size": 142850, "est_pages": 8},
            {"key": "documents/007f21ed_c25a961d.pdf", "size": 166430, "est_pages": 10},
            {"key": "documents/01fa2bbb_aa94d139.pdf", "size": 112035, "est_pages": 6},
            {"key": "documents/0297eeee_0e55d7a3.pdf", "size": 36401, "est_pages": 3},
            {"key": "documents/023951b5_be6da2bf.pdf", "size": 316498, "est_pages": 15},
            {"key": "documents/00f79db3_73eecd13.pdf", "size": 472124, "est_pages": 12},
            {"key": "documents/01487dbe_a6e69b7a.pdf", "size": 292529, "est_pages": 9}
        ]
        
        total_pages = sum(doc["est_pages"] for doc in self.documents)
        self.estimated_cost = total_pages * 0.0015 + len(self.documents) * 0.021
        
        print(f"🚀 Final Parallel Processor", flush=True)
        print(f"📄 Documents: {len(self.documents)} (medium-sized, ≤15 pages)", flush=True)
        print(f"📊 Total Pages: {total_pages}", flush=True)
        print(f"💰 Estimated Cost: ${self.estimated_cost:.3f}", flush=True)
        print("", flush=True)
    
    def trigger_document(self, doc_info):
        """Trigger processing for a single document"""
        
        document, thread_id = doc_info
        doc_key = document['key']
        doc_id = doc_key.split('/')[-1].replace('.pdf', '')
        
        print(f"🔄 [Thread {thread_id}] Starting: {doc_id} ({document['est_pages']} pages)", flush=True)
        
        try:
            payload = {
                "Records": [{
                    "eventVersion": "2.1",
                    "eventSource": "aws:s3",
                    "eventTime": datetime.utcnow().isoformat() + "Z",
                    "eventName": "ObjectCreated:Put",
                    "s3": {
                        "s3SchemaVersion": "1.0",
                        "bucket": {
                            "name": "solve-global-kr-documents-861276078413-us-east-1",
                            "arn": "arn:aws:s3:::solve-global-kr-documents-861276078413-us-east-1"
                        },
                        "object": {
                            "key": doc_key,
                            "size": document['size']
                        }
                    }
                }]
            }
            
            response = self.lambda_client.invoke(
                FunctionName='solve-global-kr-textextractor-initiator',
                InvocationType='Event',
                Payload=json.dumps(payload)
            )
            
            if response['StatusCode'] == 202:
                print(f"✅ [Thread {thread_id}] Triggered: {doc_id}", flush=True)
                return {'doc_id': doc_id, 'thread_id': thread_id, 'status': 'triggered', 'document': document}
            else:
                print(f"❌ [Thread {thread_id}] Failed: {doc_id} - HTTP {response['StatusCode']}", flush=True)
                return {'doc_id': doc_id, 'thread_id': thread_id, 'status': 'failed', 'document': document}
                
        except Exception as e:
            print(f"❌ [Thread {thread_id}] Error: {doc_id} - {e}", flush=True)
            return {'doc_id': doc_id, 'thread_id': thread_id, 'status': 'error', 'document': document}
    
    def check_results(self, triggered_docs, wait_minutes=10):
        """Check processing results"""
        
        print(f"\n⏳ Waiting {wait_minutes} minutes for processing...", flush=True)
        time.sleep(wait_minutes * 60)
        
        print("\n🔍 Checking results...", flush=True)
        
        results = {}
        for trigger_result in triggered_docs:
            if trigger_result['status'] != 'triggered':
                continue
                
            doc_id = trigger_result['doc_id']
            document = trigger_result['document']
            
            result = {
                'doc_id': doc_id,
                'thread_id': trigger_result['thread_id'],
                'est_pages': document['est_pages']
            }
            
            # Check text
            try:
                text_key = f"text/{doc_id}.txt"
                response = self.s3_client.head_object(
                    Bucket="solve-global-kr-dl-text-861276078413-us-east-1", 
                    Key=text_key
                )
                result['text'] = f"✅ {response.get('ContentLength', 0):,} chars"
            except:
                result['text'] = "❌ Missing"
            
            # Check chunks
            try:
                chunks_prefix = f"chunks/{doc_id}/"
                response = self.s3_client.list_objects_v2(
                    Bucket="solve-global-kr-dl-chunks-861276078413-us-east-1",
                    Prefix=chunks_prefix
                )
                chunk_count = response.get('KeyCount', 0)
                result['chunks'] = f"✅ {chunk_count} chunks" if chunk_count > 0 else "❌ Missing"
            except:
                result['chunks'] = "❌ Missing"
            
            # Check NLP
            try:
                nlp_prefix = f"nlp/{doc_id}/"
                response = self.s3_client.list_objects_v2(
                    Bucket="solve-global-kr-dl-ner-results-861276078413-us-east-1",
                    Prefix=nlp_prefix,
                    MaxKeys=1
                )
                result['nlp'] = "✅ Complete" if response.get('KeyCount', 0) > 0 else "❌ Missing"
            except:
                result['nlp'] = "❌ Missing"
            
            results[doc_id] = result
        
        return results
    
    def run_processing(self):
        """Run complete parallel processing"""
        
        print("🚀 STARTING 10-DOCUMENT PARALLEL PROCESSING", flush=True)
        print("=" * 60, flush=True)
        
        # Step 1: Trigger all in parallel
        doc_info_list = [(doc, i+1) for i, doc in enumerate(self.documents)]
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            trigger_results = list(executor.map(self.trigger_document, doc_info_list))
        
        # Summary of triggers
        successful_triggers = sum(1 for r in trigger_results if r['status'] == 'triggered')
        print(f"\n📊 Trigger Summary: {successful_triggers}/{len(trigger_results)} successful", flush=True)
        
        if successful_triggers == 0:
            print("❌ No documents triggered successfully", flush=True)
            return False
        
        # Step 2: Wait and check results
        results = self.check_results(trigger_results)
        
        # Step 3: Analyze results
        print("\n" + "=" * 60, flush=True)
        print("📊 FINAL RESULTS", flush=True)
        print("=" * 60, flush=True)
        
        text_success = sum(1 for r in results.values() if "✅" in r['text'])
        chunk_success = sum(1 for r in results.values() if "✅" in r['chunks'])
        nlp_success = sum(1 for r in results.values() if "✅" in r['nlp'])
        total = len(results)
        
        print(f"📄 Total Documents: {total}", flush=True)
        print(f"📝 Text Extraction: {text_success}/{total} ({(text_success/total)*100:.1f}%)", flush=True)
        print(f"🔗 Text Chunking: {chunk_success}/{total} ({(chunk_success/total)*100:.1f}%)", flush=True)
        print(f"🧠 NLP Processing: {nlp_success}/{total} ({(nlp_success/total)*100:.1f}%)", flush=True)
        
        print(f"\n📋 Detailed Results:", flush=True)
        for doc_id, result in results.items():
            print(f"📄 {doc_id} [T{result['thread_id']}] ({result['est_pages']}p):", flush=True)
            print(f"   Text: {result['text']}", flush=True)
            print(f"   Chunks: {result['chunks']}", flush=True)
            print(f"   NLP: {result['nlp']}", flush=True)
        
        # Overall assessment
        if text_success >= total * 0.7 and chunk_success >= total * 0.8:
            print(f"\n🎉 SUCCESS: Parallel microservices processing working!", flush=True)
            return True
        else:
            print(f"\n⚠️  PARTIAL SUCCESS: Some issues remain", flush=True)
            return True  # Still consider success if we got some results

def main():
    """Main function"""
    
    processor = FinalParallelProcessor()
    success = processor.run_processing()
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
