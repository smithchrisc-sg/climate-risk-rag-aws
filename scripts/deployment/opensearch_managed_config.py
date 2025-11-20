#!/usr/bin/env python3
"""
OpenSearch Managed Service configuration and client setup
"""
import boto3
import os
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

class OpenSearchManagedClient:
    """OpenSearch client for managed service"""
    
    def __init__(self, endpoint=None, region='us-east-1'):
        """Initialize OpenSearch client for managed service"""
        self.region = region
        self.endpoint = endpoint or os.environ.get('OPENSEARCH_ENDPOINT')
        
        if not self.endpoint:
            raise ValueError("OpenSearch endpoint must be provided")
        
        # Remove https:// if present
        if self.endpoint.startswith('https://'):
            self.endpoint = self.endpoint[8:]
        
        # Set up AWS authentication
        credentials = boto3.Session().get_credentials()
        self.awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            'es',  # Note: 'es' for managed service, not 'aoss'
            session_token=credentials.token
        )
        
        # Create OpenSearch client
        self.client = OpenSearch(
            hosts=[{'host': self.endpoint, 'port': 443}],
            http_auth=self.awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            pool_maxsize=20,
            timeout=30
        )
    
    def get_client(self):
        """Get the OpenSearch client"""
        return self.client
    
    def test_connection(self):
        """Test connection to OpenSearch"""
        try:
            info = self.client.info()
            print(f"✅ Connected to OpenSearch {info['version']['number']}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def create_vector_index(self, index_name="climate-risk-vectors"):
        """Create vector index with proper mapping"""
        mapping = {
            "settings": {
                "index": {
                    "number_of_shards": 1,
                    "number_of_replicas": 1,
                    "knn": True,
                    "knn.algo_param.ef_search": 100
                }
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
        
        try:
            if self.client.indices.exists(index=index_name):
                print(f"Index {index_name} already exists")
                return True
                
            response = self.client.indices.create(index=index_name, body=mapping)
            print(f"✅ Created vector index: {index_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to create vector index: {e}")
            return False
    
    def create_search_index(self, index_name="climate-risk-search"):
        """Create keyword search index"""
        mapping = {
            "settings": {
                "index": {
                    "number_of_shards": 1,
                    "number_of_replicas": 1
                },
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
                        "analyzer": "climate_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "title": {
                        "type": "text",
                        "analyzer": "climate_analyzer",
                        "boost": 2.0
                    },
                    "keywords": {"type": "keyword"},
                    "metadata": {
                        "properties": {
                            "page_number": {"type": "integer"},
                            "chunk_index": {"type": "integer"},
                            "created_at": {"type": "date"},
                            "document_type": {"type": "keyword"}
                        }
                    }
                }
            }
        }
        
        try:
            if self.client.indices.exists(index=index_name):
                print(f"Index {index_name} already exists")
                return True
                
            response = self.client.indices.create(index=index_name, body=mapping)
            print(f"✅ Created search index: {index_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to create search index: {e}")
            return False

def update_lambda_environment_variables():
    """Update Lambda functions with new OpenSearch endpoint"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Get the OpenSearch domain endpoint
    opensearch_client = boto3.client('opensearch', region_name='us-east-1')
    domain = opensearch_client.describe_domain(DomainName='climate-risk-opensearch')
    endpoint = f"https://{domain['DomainStatus']['Endpoint']}"
    
    # Lambda functions that need updating
    functions_to_update = [
        'vector-embeddings-worker',
        'keyword-indexer-processor',
        # Add other functions that use OpenSearch
    ]
    
    for function_name in functions_to_update:
        try:
            # Get current environment variables
            response = lambda_client.get_function_configuration(FunctionName=function_name)
            env_vars = response.get('Environment', {}).get('Variables', {})
            
            # Update OpenSearch configuration
            env_vars.update({
                'OPENSEARCH_ENDPOINT': endpoint,
                'OPENSEARCH_VECTOR_INDEX': 'climate-risk-vectors',
                'OPENSEARCH_SEARCH_INDEX': 'climate-risk-search',
                'OPENSEARCH_USE_SERVERLESS': 'false'
            })
            
            # Update the function
            lambda_client.update_function_configuration(
                FunctionName=function_name,
                Environment={'Variables': env_vars}
            )
            
            print(f"✅ Updated {function_name} environment variables")
            
        except Exception as e:
            print(f"❌ Failed to update {function_name}: {e}")

if __name__ == "__main__":
    # Test the configuration
    try:
        # This would be set after domain creation
        endpoint = "search-climate-risk-opensearch-xxx.us-east-1.es.amazonaws.com"
        
        client = OpenSearchManagedClient(endpoint=endpoint)
        
        if client.test_connection():
            client.create_vector_index()
            client.create_search_index()
            print("✅ OpenSearch managed service setup complete")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
