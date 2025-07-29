"""
Lambda Code Updates for AWS Managed OpenSearch Migration
This file shows the minimal changes needed in Lambda functions
"""

import os
import boto3
import json
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.aws_auth import AWSRequestsAuth

def get_opensearch_client():
    """
    Updated OpenSearch client for AWS Managed domain
    Replace the serverless connection code with this
    """
    
    # Get domain endpoint from environment variable
    domain_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
    if not domain_endpoint:
        raise ValueError("OPENSEARCH_ENDPOINT environment variable not set")
    
    # Remove https:// prefix if present
    if domain_endpoint.startswith('https://'):
        domain_endpoint = domain_endpoint[8:]
    
    # Get AWS credentials
    session = boto3.Session()
    credentials = session.get_credentials()
    region = session.region_name or 'us-east-1'
    
    # Create auth object for AWS Managed OpenSearch (note: 'es' not 'aoss')
    auth = AWSRequestsAuth(
        credentials.access_key,
        credentials.secret_key,
        region,
        'es'  # Changed from 'aoss' to 'es'
    )
    
    # Add session token if present (for temporary credentials)
    if credentials.token:
        auth.session_token = credentials.token
    
    # Create OpenSearch client
    client = OpenSearch(
        hosts=[{'host': domain_endpoint, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30,
        max_retries=3,
        retry_on_timeout=True
    )
    
    return client

def get_master_credentials():
    """
    Get OpenSearch master credentials from Secrets Manager
    Only needed for initial setup/admin operations
    """
    secret_arn = os.environ.get('OPENSEARCH_MASTER_SECRET_ARN')
    if not secret_arn:
        return None
    
    secrets_client = boto3.client('secretsmanager')
    try:
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response['SecretValue'])
        return {
            'username': secret.get('username', 'admin'),
            'password': secret.get('password')
        }
    except Exception as e:
        print(f"Warning: Could not retrieve master credentials: {e}")
        return None

# Example usage in vector embeddings Lambda
def lambda_handler_vector_embeddings_example(event, context):
    """
    Example: Updated vector embeddings Lambda handler
    """
    
    try:
        # Get OpenSearch client (same API as before!)
        opensearch_client = get_opensearch_client()
        
        # All your existing OpenSearch operations work the same
        index_name = "vector-embeddings"
        
        # Create index if it doesn't exist
        if not opensearch_client.indices.exists(index=index_name):
            index_body = {
                "settings": {
                    "index": {
                        "knn": True,
                        "knn.algo_param.ef_search": 100
                    }
                },
                "mappings": {
                    "properties": {
                        "vector": {
                            "type": "knn_vector",
                            "dimension": 1536,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimilarity",
                                "engine": "nmslib"
                            }
                        },
                        "text": {"type": "text"},
                        "document_id": {"type": "keyword"},
                        "chunk_id": {"type": "keyword"},
                        "metadata": {"type": "object"}
                    }
                }
            }
            opensearch_client.indices.create(index=index_name, body=index_body)
        
        # Process embeddings (your existing logic)
        # ... existing code remains the same ...
        
        return {
            'statusCode': 200,
            'body': json.dumps('Vector embeddings processed successfully')
        }
        
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

# Example usage in keyword indexer Lambda
def lambda_handler_keyword_indexer_example(event, context):
    """
    Example: Updated keyword indexer Lambda handler
    """
    
    try:
        # Get OpenSearch client
        opensearch_client = get_opensearch_client()
        
        # Keyword search index
        index_name = "keyword-search"
        
        # Create index if it doesn't exist
        if not opensearch_client.indices.exists(index=index_name):
            index_body = {
                "settings": {
                    "analysis": {
                        "analyzer": {
                            "climate_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "stop", "stemmer"]
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "text": {
                            "type": "text",
                            "analyzer": "climate_analyzer"
                        },
                        "keywords": {"type": "keyword"},
                        "document_id": {"type": "keyword"},
                        "chunk_id": {"type": "keyword"},
                        "metadata": {"type": "object"}
                    }
                }
            }
            opensearch_client.indices.create(index=index_name, body=index_body)
        
        # Process keywords (your existing logic)
        # ... existing code remains the same ...
        
        return {
            'statusCode': 200,
            'body': json.dumps('Keywords indexed successfully')
        }
        
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

# Search functions remain exactly the same!
def search_vectors(query_vector, size=10, filters=None):
    """Vector search - no changes needed"""
    client = get_opensearch_client()
    
    search_body = {
        "size": size,
        "query": {
            "knn": {
                "vector": {
                    "vector": query_vector,
                    "k": size
                }
            }
        }
    }
    
    if filters:
        search_body["query"] = {
            "bool": {
                "must": [search_body["query"]],
                "filter": filters
            }
        }
    
    return client.search(index="vector-embeddings", body=search_body)

def search_keywords(query_text, size=10, filters=None):
    """Keyword search - no changes needed"""
    client = get_opensearch_client()
    
    search_body = {
        "size": size,
        "query": {
            "multi_match": {
                "query": query_text,
                "fields": ["text", "keywords"],
                "type": "best_fields"
            }
        }
    }
    
    if filters:
        search_body["query"] = {
            "bool": {
                "must": [search_body["query"]],
                "filter": filters
            }
        }
    
    return client.search(index="keyword-search", body=search_body)

# Summary of changes needed:
"""
CHANGES REQUIRED IN EXISTING LAMBDA FUNCTIONS:

1. Update connection code:
   - Change auth service from 'aoss' to 'es'
   - Use OPENSEARCH_ENDPOINT instead of collection endpoint
   - Add session token handling for temporary credentials

2. Environment variables (already added in CDK):
   - OPENSEARCH_ENDPOINT: Domain endpoint
   - OPENSEARCH_MASTER_SECRET_ARN: Master password secret

3. All OpenSearch operations remain exactly the same:
   - Index creation
   - Document indexing
   - Search queries
   - Index management

4. No changes needed to:
   - Search logic
   - Index mappings
   - Query structures
   - Response handling
"""
