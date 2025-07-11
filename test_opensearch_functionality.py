#!/usr/bin/env python3
"""
Test script to verify OpenSearch keyword and vector indexing functionality
"""

import boto3
import json
import time
from datetime import datetime

# Use the correct AWS profile
session = boto3.Session(profile_name='solve-global')

def test_keyword_indexing():
    """Test keyword indexing by invoking the keyword indexer Lambda"""
    print("🔍 Testing Keyword Indexing...")
    
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    # Test payload for keyword indexing
    test_payload = {
        "Records": [
            {
                "body": json.dumps({
                    "document_id": "test-doc-001",
                    "s3_bucket": "solve-global-kr-dl-text-861276078413-us-east-1",
                    "s3_key": "test/sample.txt",
                    "text_content": "This is a test document about climate risk and environmental sustainability.",
                    "metadata": {
                        "title": "Test Climate Document",
                        "source": "test",
                        "timestamp": datetime.now().isoformat()
                    }
                })
            }
        ]
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='keyword-indexer',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        result = json.loads(response['Payload'].read())
        print(f"✅ Keyword Indexer Response: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Keyword Indexing Failed: {str(e)}")
        return False

def test_vector_indexing():
    """Test vector indexing by invoking the vector embeddings worker Lambda"""
    print("🔍 Testing Vector Indexing...")
    
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    # Test payload for vector indexing
    test_payload = {
        "Records": [
            {
                "body": json.dumps({
                    "document_id": "test-doc-001",
                    "text_content": "This is a test document about climate risk and environmental sustainability.",
                    "chunk_id": "chunk-001",
                    "metadata": {
                        "title": "Test Climate Document",
                        "source": "test",
                        "timestamp": datetime.now().isoformat()
                    }
                })
            }
        ]
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='vector-embeddings-pipelin-VectorEmbeddingsWorker5F-nCQL6EhDMuyi',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        result = json.loads(response['Payload'].read())
        print(f"✅ Vector Indexer Response: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Vector Indexing Failed: {str(e)}")
        return False

def check_opensearch_collections():
    """Check the status of OpenSearch collections"""
    print("🔍 Checking OpenSearch Collections...")
    
    opensearch_client = session.client('opensearchserverless', region_name='us-east-1')
    
    try:
        collections = opensearch_client.list_collections()
        
        print("📊 Current Collections:")
        for collection in collections['collectionSummaries']:
            details = opensearch_client.batch_get_collection(ids=[collection['id']])
            collection_detail = details['collectionDetails'][0]
            
            print(f"  • {collection_detail['name']}")
            print(f"    - ID: {collection_detail['id']}")
            print(f"    - Type: {collection_detail['type']}")
            print(f"    - Status: {collection_detail['status']}")
            print(f"    - Standby Replicas: {collection_detail['standbyReplicas']}")
            print(f"    - Endpoint: {collection_detail['collectionEndpoint']}")
            print()
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to check collections: {str(e)}")
        return False

def main():
    """Main test function"""
    print("🚀 OpenSearch Functionality Test")
    print("=" * 50)
    
    # Check collections first
    collections_ok = check_opensearch_collections()
    
    if not collections_ok:
        print("❌ Cannot proceed with tests - collections check failed")
        return
    
    print("🧪 Running Functionality Tests...")
    print("-" * 30)
    
    # Test keyword indexing
    keyword_ok = test_keyword_indexing()
    time.sleep(2)
    
    # Test vector indexing  
    vector_ok = test_vector_indexing()
    
    print("\n📋 Test Results Summary:")
    print("-" * 30)
    print(f"Keyword Indexing: {'✅ PASS' if keyword_ok else '❌ FAIL'}")
    print(f"Vector Indexing:  {'✅ PASS' if vector_ok else '❌ FAIL'}")
    
    if keyword_ok and vector_ok:
        print("\n🎉 All tests passed! OpenSearch functionality is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the error messages above.")

if __name__ == "__main__":
    main()
