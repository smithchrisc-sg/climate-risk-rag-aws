#!/usr/bin/env python3
"""
Update Lambda functions to use OpenSearch Managed Service instead of Serverless
"""
import boto3
import json

def get_opensearch_endpoint():
    """Get the OpenSearch managed domain endpoint"""
    client = boto3.client('opensearch', region_name='us-east-1')
    
    try:
        response = client.describe_domain(DomainName='climate-risk-opensearch')
        endpoint = response['DomainStatus'].get('Endpoint')
        
        if endpoint:
            return f"https://{endpoint}"
        else:
            print("❌ OpenSearch domain not ready yet")
            return None
            
    except Exception as e:
        print(f"❌ Error getting OpenSearch endpoint: {e}")
        return None

def update_lambda_function(function_name, new_env_vars):
    """Update a Lambda function's environment variables"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # Get current configuration
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        current_env = response.get('Environment', {}).get('Variables', {})
        
        # Merge with new variables
        updated_env = {**current_env, **new_env_vars}
        
        # Update the function
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={'Variables': updated_env}
        )
        
        print(f"✅ Updated {function_name}")
        return True
        
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"⚠️  Function {function_name} not found - skipping")
        return False
    except Exception as e:
        print(f"❌ Failed to update {function_name}: {e}")
        return False

def update_all_lambda_functions():
    """Update all Lambda functions that use OpenSearch"""
    
    # Get the managed OpenSearch endpoint
    opensearch_endpoint = get_opensearch_endpoint()
    if not opensearch_endpoint:
        print("❌ Cannot proceed without OpenSearch endpoint")
        return False
    
    print(f"Using OpenSearch endpoint: {opensearch_endpoint}")
    
    # Environment variables for managed service
    managed_opensearch_config = {
        'OPENSEARCH_ENDPOINT': opensearch_endpoint,
        'OPENSEARCH_VECTOR_INDEX': 'climate-risk-vectors',
        'OPENSEARCH_SEARCH_INDEX': 'climate-risk-search',
        'OPENSEARCH_USE_SERVERLESS': 'false',
        'OPENSEARCH_AUTH_TYPE': 'aws4auth',
        'OPENSEARCH_SERVICE': 'es'  # 'es' for managed, 'aoss' for serverless
    }
    
    # Lambda functions that need updating
    functions_to_update = [
        'vector-embeddings-worker',
        'keyword-indexer-processor',
        # Add other functions that use OpenSearch
    ]
    
    success_count = 0
    
    for function_name in functions_to_update:
        if update_lambda_function(function_name, managed_opensearch_config):
            success_count += 1
    
    print(f"\n✅ Successfully updated {success_count}/{len(functions_to_update)} functions")
    
    if success_count < len(functions_to_update):
        print("⚠️  Some functions were not updated. Check the logs above.")
    
    return success_count == len(functions_to_update)

def create_index_templates():
    """Create index templates for the managed OpenSearch cluster"""
    from opensearchpy import OpenSearch, RequestsHttpConnection
    from requests_aws4auth import AWS4Auth
    
    # Get endpoint
    opensearch_endpoint = get_opensearch_endpoint()
    if not opensearch_endpoint:
        return False
    
    # Remove https:// for client
    endpoint_host = opensearch_endpoint.replace('https://', '')
    
    # Set up authentication
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        'us-east-1',
        'es'
    )
    
    # Create client
    client = OpenSearch(
        hosts=[{'host': endpoint_host, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )
    
    try:
        # Test connection
        info = client.info()
        print(f"✅ Connected to OpenSearch {info['version']['number']}")
        
        # Vector index template
        vector_template = {
            "index_patterns": ["climate-risk-vectors*"],
            "template": {
                "settings": {
                    "number_of_shards": 2,  # Split across 2 data nodes
                    "number_of_replicas": 1,
                    "index.knn": True,
                    "index.knn.algo_param.ef_search": 100
                },
                "mappings": {
                    "properties": {
                        "doc_id": {"type": "keyword"},
                        "chunk_id": {"type": "keyword"},
                        "content": {"type": "text"},
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": 1536,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "nmslib",
                                "parameters": {
                                    "ef_construction": 128,
                                    "m": 24
                                }
                            }
                        },
                        "metadata": {
                            "properties": {
                                "page_number": {"type": "integer"},
                                "chunk_index": {"type": "integer"},
                                "created_at": {"type": "date"}
                            }
                        }
                    }
                }
            }
        }
        
        # Search index template
        search_template = {
            "index_patterns": ["climate-risk-search*"],
            "template": {
                "settings": {
                    "number_of_shards": 2,
                    "number_of_replicas": 1,
                    "analysis": {
                        "analyzer": {
                            "climate_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "stop", "snowball"]
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "doc_id": {"type": "keyword"},
                        "chunk_id": {"type": "keyword"},
                        "content": {
                            "type": "text",
                            "analyzer": "climate_analyzer"
                        },
                        "keywords": {"type": "keyword"},
                        "metadata": {
                            "properties": {
                                "page_number": {"type": "integer"},
                                "chunk_index": {"type": "integer"},
                                "created_at": {"type": "date"}
                            }
                        }
                    }
                }
            }
        }
        
        # Create templates
        client.indices.put_index_template(
            name="climate-risk-vectors-template",
            body=vector_template
        )
        print("✅ Created vector index template")
        
        client.indices.put_index_template(
            name="climate-risk-search-template", 
            body=search_template
        )
        print("✅ Created search index template")
        
        # Create initial indices
        client.indices.create(index="climate-risk-vectors", ignore=400)
        client.indices.create(index="climate-risk-search", ignore=400)
        print("✅ Created initial indices")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up indices: {e}")
        return False

def show_migration_status():
    """Show the current migration status"""
    print("OpenSearch Migration Status")
    print("=" * 40)
    
    # Check domain status
    opensearch_client = boto3.client('opensearch', region_name='us-east-1')
    try:
        response = opensearch_client.describe_domain(DomainName='climate-risk-opensearch')
        status = response['DomainStatus']
        
        if status.get('Processing'):
            print("🟡 OpenSearch Domain: Creating...")
        elif status.get('Endpoint'):
            print(f"🟢 OpenSearch Domain: Ready")
            print(f"   Endpoint: https://{status['Endpoint']}")
        else:
            print("🔴 OpenSearch Domain: Unknown status")
            
    except opensearch_client.exceptions.ResourceNotFoundException:
        print("🔴 OpenSearch Domain: Not created")
    
    # Check serverless collections (should be cleaned up after migration)
    aoss_client = boto3.client('opensearchserverless', region_name='us-east-1')
    try:
        collections = aoss_client.list_collections()
        if collections['collectionSummaries']:
            print(f"⚠️  Serverless Collections: {len(collections['collectionSummaries'])} still active")
            print("   (Clean up after migration is complete)")
        else:
            print("🟢 Serverless Collections: Cleaned up")
    except Exception as e:
        print(f"⚠️  Could not check serverless collections: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == 'status':
            show_migration_status()
        elif command == 'update-lambdas':
            update_all_lambda_functions()
        elif command == 'setup-indices':
            create_index_templates()
        elif command == 'all':
            print("Running complete migration setup...")
            if update_all_lambda_functions():
                create_index_templates()
                show_migration_status()
        else:
            print("Usage: python script.py [status|update-lambdas|setup-indices|all]")
    else:
        print("Usage: python script.py [status|update-lambdas|setup-indices|all]")
