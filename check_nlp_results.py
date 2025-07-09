#!/usr/bin/env python3
"""
Check NLP Processing Results
"""

import boto3

def check_nlp_results():
    """Check NLP processing results for all test documents"""
    
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    test_documents = [
        "01eef8c1_a403b295",
        "01dd077e_86ce1ac2", 
        "0249c7aa_ae155247",
        "00f79db3_73eecd13",
        "01487dbe_a6e69b7a",
        "004e17a3_3bb90d8e",
        "007f21ed_c25a961d"
    ]
    
    print("🧠 CHECKING NLP PROCESSING RESULTS")
    print("=" * 50)
    
    nlp_success_count = 0
    
    for doc_id in test_documents:
        try:
            nlp_prefix = f"nlp/{doc_id}/"
            response = s3_client.list_objects_v2(
                Bucket="solve-global-kr-ner-results-861276078413-us-east-1",
                Prefix=nlp_prefix,
                MaxKeys=5
            )
            
            if response.get('KeyCount', 0) > 0:
                print(f"   ✅ {doc_id}: {response['KeyCount']} NLP result files")
                nlp_success_count += 1
                
                # Show file details
                for obj in response.get('Contents', [])[:3]:
                    file_name = obj['Key'].split('/')[-1]
                    file_size = obj['Size']
                    print(f"      📄 {file_name} ({file_size:,} bytes)")
            else:
                print(f"   ❌ {doc_id}: No NLP results")
                
        except Exception as e:
            print(f"   ❌ {doc_id}: Error checking NLP results - {e}")
    
    total_docs = len(test_documents)
    success_rate = (nlp_success_count / total_docs) * 100
    
    print(f"\n📊 NLP PROCESSING SUMMARY:")
    print(f"   Success: {nlp_success_count}/{total_docs} ({success_rate:.1f}%)")
    
    if nlp_success_count == total_docs:
        print(f"   🎉 COMPLETE SUCCESS: All documents processed!")
        return True
    elif nlp_success_count >= total_docs * 0.7:
        print(f"   ✅ GOOD SUCCESS: Most documents processed")
        return True
    else:
        print(f"   ⚠️  PARTIAL SUCCESS: Some documents processed")
        return False

if __name__ == "__main__":
    success = check_nlp_results()
    exit(0 if success else 1)
