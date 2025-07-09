#!/usr/bin/env python3
"""
Process 10 Documents End-to-End
Uses the current working pipeline without modifications
"""

import boto3
import json
import time
from datetime import datetime
from typing import List, Dict

class TenDocumentProcessor:
    """Process 10 documents through the complete pipeline"""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        
        # Selected 10 documents (mix of sizes, cost-optimized)
        self.documents = [
            {"key": "documents/006893d2_93170cb9.pdf", "size": 34580, "est_pages": 3},
            {"key": "documents/0068a512_1780336e.pdf", "size": 81776, "est_pages": 5},
            {"key": "documents/004e17a3_3bb90d8e.pdf", "size": 135830, "est_pages": 8},
            {"key": "documents/0032f6cb_f0caef34.pdf", "size": 142850, "est_pages": 8},
            {"key": "documents/007f21ed_c25a961d.pdf", "size": 166430, "est_pages": 10},
            {"key": "documents/01fa2bbb_aa94d139.pdf", "size": 112035, "est_pages": 6},
            {"key": "documents/0297eeee_0e55d7a3.pdf", "size": 36401, "est_pages": 3},
            {"key": "documents/023951b5_be6da2bf.pdf", "size": 316498, "est_pages": 15},
            {"key": "documents/0249c7aa_ae155247.pdf", "size": 2000756, "est_pages": 80},
            {"key": "documents/024c99ee_031172fe.pdf", "size": 1595933, "est_pages": 65}
        ]
        
        self.bucket_name = "solve-global-kr-documents-861276078413-us-east-1"
        
        # Cost estimation
        total_pages = sum(doc["est_pages"] for doc in self.documents)
        self.estimated_textract_cost = total_pages * 0.0015
        self.estimated_comprehend_cost = len(self.documents) * 0.019
        self.estimated_bedrock_cost = len(self.documents) * 0.002
        self.estimated_total_cost = self.estimated_textract_cost + self.estimated_comprehend_cost + self.estimated_bedrock_cost
        
        print(f"🚀 Ten Document Processor Initialized")
        print(f"📄 Documents: {len(self.documents)}")
        print(f"📊 Total Est. Pages: {total_pages}")
        print(f"💰 Est. Total Cost: ${self.estimated_total_cost:.3f}")
    
    def create_s3_event(self, document_key: str, document_size: int) -> dict:
        """Create proper S3 event for document processing"""
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
                            "size": document_size
                        }
                    }
                }
            ]
        }
    
    def trigger_document_processing(self, document: Dict) -> bool:
        """Trigger processing for a single document"""
        
        try:
            payload = self.create_s3_event(document['key'], document['size'])
            
            response = self.lambda_client.invoke(
                FunctionName='solve-global-kr-textextractor-initiator',
                InvocationType='Event',
                Payload=json.dumps(payload)
            )
            
            return response['StatusCode'] == 202
            
        except Exception as e:
            print(f"❌ Error triggering {document['key']}: {e}")
            return False
    
    def check_processing_results(self, documents: List[Dict], wait_minutes: int = 15) -> Dict:
        """Check processing results for all documents"""
        
        print(f"\n⏳ Waiting {wait_minutes} minutes for processing to complete...")
        time.sleep(wait_minutes * 60)
        
        results = {}
        
        for doc in documents:
            doc_id = doc['key'].split('/')[-1].replace('.pdf', '')
            
            result = {
                'doc_id': doc_id,
                'original_key': doc['key'],
                'size': doc['size'],
                'est_pages': doc['est_pages']
            }
            
            # Check text extraction
            try:
                text_key = f"text/{doc_id}.txt"
                response = self.s3_client.head_object(
                    Bucket="solve-global-kr-text-new-861276078413-us-east-1", 
                    Key=text_key
                )
                result['text_extraction'] = "✅ Success"
                result['text_size'] = response.get('ContentLength', 0)
            except:
                result['text_extraction'] = "❌ Missing"
                result['text_size'] = 0
            
            # Check chunks
            try:
                chunks_prefix = f"chunks/{doc_id}/"
                response = self.s3_client.list_objects_v2(
                    Bucket="solve-global-kr-chunks-861276078413-us-east-1",
                    Prefix=chunks_prefix,
                    MaxKeys=1
                )
                chunk_count = response.get('KeyCount', 0)
                if chunk_count > 0:
                    result['chunking'] = "✅ Success"
                    # Get actual chunk count
                    full_response = self.s3_client.list_objects_v2(
                        Bucket="solve-global-kr-chunks-861276078413-us-east-1",
                        Prefix=chunks_prefix
                    )
                    result['chunk_count'] = full_response.get('KeyCount', 0)
                else:
                    result['chunking'] = "❌ Missing"
                    result['chunk_count'] = 0
            except:
                result['chunking'] = "❌ Missing"
                result['chunk_count'] = 0
            
            # Check NLP results
            try:
                nlp_prefix = f"nlp/{doc_id}/"
                response = self.s3_client.list_objects_v2(
                    Bucket="solve-global-kr-ner-results-861276078413-us-east-1",
                    Prefix=nlp_prefix,
                    MaxKeys=1
                )
                if response.get('KeyCount', 0) > 0:
                    result['nlp_processing'] = "✅ Success"
                else:
                    result['nlp_processing'] = "❌ Missing"
            except:
                result['nlp_processing'] = "❌ Missing"
            
            results[doc_id] = result
        
        return results
    
    def process_batch(self, batch_documents: List[Dict], batch_number: int) -> Dict:
        """Process a batch of documents"""
        
        print(f"\n{'='*60}")
        print(f"📦 PROCESSING BATCH {batch_number}")
        print(f"📄 Documents: {len(batch_documents)}")
        print(f"{'='*60}")
        
        # Trigger processing for all documents in batch
        successful_triggers = 0
        for i, doc in enumerate(batch_documents, 1):
            doc_id = doc['key'].split('/')[-1].replace('.pdf', '')
            print(f"\n🚀 [{i}/{len(batch_documents)}] Triggering: {doc_id}")
            print(f"   Size: {doc['size']:,} bytes (~{doc['est_pages']} pages)")
            
            if self.trigger_document_processing(doc):
                print(f"   ✅ Successfully triggered")
                successful_triggers += 1
            else:
                print(f"   ❌ Failed to trigger")
        
        print(f"\n📊 Batch {batch_number} Summary:")
        print(f"   Triggered: {successful_triggers}/{len(batch_documents)}")
        
        return self.check_processing_results(batch_documents)
    
    def run_ten_document_processing(self) -> Dict:
        """Run complete 10-document processing"""
        
        print("🚀 STARTING 10-DOCUMENT END-TO-END PROCESSING")
        print("=" * 70)
        print(f"💰 Estimated Cost: ${self.estimated_total_cost:.3f}")
        print("=" * 70)
        
        # Process in batches of 3 to manage load
        batch_size = 3
        all_results = {}
        
        for i in range(0, len(self.documents), batch_size):
            batch = self.documents[i:i+batch_size]
            batch_number = (i // batch_size) + 1
            
            batch_results = self.process_batch(batch, batch_number)
            all_results.update(batch_results)
            
            # Wait between batches (except for last batch)
            if i + batch_size < len(self.documents):
                print(f"\n⏳ Waiting 3 minutes before next batch...")
                time.sleep(180)
        
        return self.analyze_final_results(all_results)
    
    def analyze_final_results(self, all_results: Dict) -> Dict:
        """Analyze and report final results"""
        
        print("\n" + "=" * 70)
        print("📊 FINAL 10-DOCUMENT PROCESSING RESULTS")
        print("=" * 70)
        
        # Count successes by stage
        text_success = sum(1 for r in all_results.values() if "✅" in r.get('text_extraction', ''))
        chunk_success = sum(1 for r in all_results.values() if "✅" in r.get('chunking', ''))
        nlp_success = sum(1 for r in all_results.values() if "✅" in r.get('nlp_processing', ''))
        
        total_docs = len(all_results)
        
        print(f"📄 Total Documents: {total_docs}")
        print(f"📝 Text Extraction: {text_success}/{total_docs} ({(text_success/total_docs)*100:.1f}%)")
        print(f"🔗 Text Chunking: {chunk_success}/{total_docs} ({(chunk_success/total_docs)*100:.1f}%)")
        print(f"🧠 NLP Processing: {nlp_success}/{total_docs} ({(nlp_success/total_docs)*100:.1f}%)")
        
        # Detailed results
        print(f"\n📋 DETAILED RESULTS:")
        for doc_id, result in all_results.items():
            print(f"\n📄 {doc_id}:")
            print(f"   Size: {result['size']:,} bytes (~{result['est_pages']} pages)")
            print(f"   Text: {result['text_extraction']} ({result.get('text_size', 0):,} chars)")
            print(f"   Chunks: {result['chunking']} ({result.get('chunk_count', 0)} chunks)")
            print(f"   NLP: {result['nlp_processing']}")
        
        # Overall assessment
        if text_success == total_docs and chunk_success >= total_docs * 0.8:
            overall_status = "🎉 EXCELLENT - Production Ready"
        elif text_success >= total_docs * 0.8:
            overall_status = "✅ GOOD - Minor Issues"
        elif text_success >= total_docs * 0.6:
            overall_status = "⚠️  FAIR - Needs Attention"
        else:
            overall_status = "❌ POOR - Major Issues"
        
        print(f"\n🎯 Overall Assessment: {overall_status}")
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f"ten_document_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'total_documents': total_docs,
                'success_rates': {
                    'text_extraction': text_success / total_docs,
                    'chunking': chunk_success / total_docs,
                    'nlp_processing': nlp_success / total_docs
                },
                'estimated_cost': self.estimated_total_cost,
                'detailed_results': all_results
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {results_file}")
        
        return {
            'total_documents': total_docs,
            'text_success_rate': text_success / total_docs,
            'chunk_success_rate': chunk_success / total_docs,
            'nlp_success_rate': nlp_success / total_docs,
            'overall_status': overall_status
        }

def main():
    """Main processing function"""
    
    processor = TenDocumentProcessor()
    results = processor.run_ten_document_processing()
    
    return results

if __name__ == "__main__":
    results = main()
    success_rate = results['text_success_rate']
    exit(0 if success_rate >= 0.8 else 1)
