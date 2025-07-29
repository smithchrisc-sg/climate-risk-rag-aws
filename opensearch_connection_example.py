"""
Example showing the minimal changes needed in Lambda code 
to switch from OpenSearch Serverless to AWS Managed OpenSearch
"""

# BEFORE (OpenSearch Serverless):
# from opensearchpy import OpenSearch, RequestsHttpConnection
# from aws_requests_auth.aws_auth import AWSRequestsAuth

# client = OpenSearch(
#     hosts=[{'host': collection_endpoint, 'port': 443}],
#     http_auth=AWSRequestsAuth(aws_access_key, aws_secret_key, aws_region, 'aoss'),
#     use_ssl=True,
#     verify_certs=True,
#     connection_class=RequestsHttpConnection
# )

# AFTER (AWS Managed OpenSearch):
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.aws_auth import AWSRequestsAuth
import boto3

def get_opensearch_client():
    """Get OpenSearch client for AWS Managed domain"""
    
    # Get domain endpoint from environment or parameter store
    domain_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')  # e.g., search-solve-global-kr-search-abc123.us-east-1.es.amazonaws.com
    
    # Get AWS credentials
    session = boto3.Session()
    credentials = session.get_credentials()
    
    # Create auth object - note 'es' service instead of 'aoss'
    auth = AWSRequestsAuth(
        credentials.access_key,
        credentials.secret_key,
        session.region_name,
        'es'  # Changed from 'aoss' to 'es'
    )
    
    # Create client - same API as before!
    client = OpenSearch(
        hosts=[{'host': domain_endpoint, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30
    )
    
    return client

# All your existing OpenSearch operations remain exactly the same:
def create_vector_index(client, index_name):
    """Create vector index - no changes needed"""
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
                "metadata": {"type": "object"}
            }
        }
    }
    
    client.indices.create(index=index_name, body=index_body)

def search_vectors(client, index_name, query_vector, size=10):
    """Vector search - no changes needed"""
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
    
    return client.search(index=index_name, body=search_body)

# Environment variable changes needed in CDK:
# OLD: OPENSEARCH_COLLECTION_ENDPOINT
# NEW: OPENSEARCH_ENDPOINT
