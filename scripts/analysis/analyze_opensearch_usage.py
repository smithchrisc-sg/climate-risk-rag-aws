#!/usr/bin/env python3
"""
Analyze current OpenSearch Serverless usage to inform managed service sizing
"""
import boto3
import json
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import os

def get_opensearch_client(endpoint, region='us-east-1'):
    """Create OpenSearch client with AWS auth"""
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        region,
        'aoss',
        session_token=credentials.token
    )
    
    client = OpenSearch(
        hosts=[{'host': endpoint.replace('https://', ''), 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=20
    )
    return client

def analyze_collection(client, collection_name, collection_type):
    """Analyze a single collection"""
    print(f"\n=== Analyzing {collection_name} ({collection_type}) ===")
    
    try:
        # Get cluster stats
        stats = client.cluster.stats()
        print(f"Cluster Status: {stats.get('status', 'unknown')}")
        
        # Get indices info
        indices = client.indices.stats()
        total_docs = 0
        total_size_bytes = 0
        
        for index_name, index_stats in indices.get('indices', {}).items():
            docs = index_stats.get('total', {}).get('docs', {}).get('count', 0)
            size_bytes = index_stats.get('total', {}).get('store', {}).get('size_in_bytes', 0)
            
            print(f"Index: {index_name}")
            print(f"  Documents: {docs:,}")
            print(f"  Size: {size_bytes / (1024*1024):.2f} MB")
            
            total_docs += docs
            total_size_bytes += size_bytes
        
        print(f"\nTotal Documents: {total_docs:,}")
        print(f"Total Size: {total_size_bytes / (1024*1024):.2f} MB")
        
        return {
            'collection_name': collection_name,
            'collection_type': collection_type,
            'total_documents': total_docs,
            'total_size_mb': total_size_bytes / (1024*1024),
            'indices_count': len(indices.get('indices', {}))
        }
        
    except Exception as e:
        print(f"Error analyzing {collection_name}: {e}")
        return None

def main():
    """Main analysis function"""
    print("OpenSearch Serverless Usage Analysis")
    print("=" * 50)
    
    # Collection endpoints (from AWS CLI output)
    collections = [
        {
            'name': 'solve-global-kr-vectors-v2',
            'endpoint': 'rui72a7agqnqo77vk34b.us-east-1.aoss.amazonaws.com',
            'type': 'VECTORSEARCH'
        },
        {
            'name': 'solve-global-kr-search-v2', 
            'endpoint': 'i7dzyfap1fe42z9delui.us-east-1.aoss.amazonaws.com',
            'type': 'SEARCH'
        }
    ]
    
    analysis_results = []
    
    for collection in collections:
        try:
            client = get_opensearch_client(f"https://{collection['endpoint']}")
            result = analyze_collection(client, collection['name'], collection['type'])
            if result:
                analysis_results.append(result)
        except Exception as e:
            print(f"Failed to connect to {collection['name']}: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("MIGRATION SIZING RECOMMENDATIONS")
    print("=" * 50)
    
    total_docs = sum(r['total_documents'] for r in analysis_results)
    total_size = sum(r['total_size_mb'] for r in analysis_results)
    
    print(f"Total Documents: {total_docs:,}")
    print(f"Total Data Size: {total_size:.2f} MB")
    print(f"Recommended Storage: {max(100, int(total_size * 2))} GB")
    
    if total_size < 1000:  # Less than 1GB
        print("Recommended Instance: t3.small.search")
    elif total_size < 5000:  # Less than 5GB
        print("Recommended Instance: t3.medium.search")
    else:
        print("Recommended Instance: t3.large.search")
    
    # Save results
    with open('/tmp/opensearch_analysis.json', 'w') as f:
        json.dump(analysis_results, f, indent=2)
    
    print(f"\nDetailed results saved to: /tmp/opensearch_analysis.json")

if __name__ == "__main__":
    main()
