# Knowledge Graph Layer

**Version**: 1.0.0  
**Compatible with**: Python 3.11, AWS Lambda, Neptune  

## Overview

The Knowledge Graph Layer provides a consistent abstraction for Neptune/SPARQL operations across all Lambda functions in the Climate Risk RAG system. Similar to the DatabaseManager layer for PostgreSQL operations, this layer ensures consistent URI generation, query patterns, and error handling for all knowledge graph operations.

## Components

### Core Classes

- **KnowledgeGraphManager**: Main interface for all KG operations
- **URIManager**: Consistent URI generation and namespace management
- **SPARQLQueryBuilder**: Safe SPARQL query construction with injection prevention
- **OntologyManager**: Ontology concept retrieval and management
- **TripleManager**: Triple insertion and manipulation operations
- **BulkLoadManager**: Neptune bulk load operations from S3 for large datasets

### Exception Classes

- **KGConnectionError**: Neptune connection failures
- **KGQueryError**: SPARQL query execution failures
- **KGInsertError**: Triple insertion failures
- **KGValidationError**: Data validation failures
- **KGAuthenticationError**: Neptune authentication failures
- **KGTimeoutError**: Operation timeout failures

## Usage

### Basic Initialization

```python
from utils.KnowledgeGraphManager import KnowledgeGraphManager

# Initialize in Lambda function
kg_manager = KnowledgeGraphManager()
```

### Environment Variables Required

```bash
NEPTUNE_ENDPOINT=your-neptune-cluster-endpoint
NEPTUNE_PORT=8182
AWS_REGION=us-east-1
NEPTUNE_TIMEOUT=30
NEPTUNE_MAX_RETRIES=3
```

### Common Operations

#### Ontology Operations

```python
# Get all concepts
concepts = kg_manager.get_ontology_concepts()

# Get domain concepts only
domain_concepts = kg_manager.get_ontology_concepts(concept_type="domain")

# Search concepts by label
climate_concepts = kg_manager.search_concepts_by_label("climate", fuzzy=True)

# Get concept details
concept_details = kg_manager.get_concept_by_uri("http://ontology.org/climate/ClimateChange")

# Get concept relationships
relationships = kg_manager.get_concept_relationships("http://ontology.org/climate/ClimateChange")
```

#### URI Generation

```python
# Generate consistent URIs
doc_uri = kg_manager.mint_document_uri("doc123")
chunk_uri = kg_manager.mint_chunk_uri("doc123", "chunk456")
mention_uri = kg_manager.mint_concept_mention_uri("chunk456", "http://ontology.org/climate/ClimateChange", 45)
```

#### Triple Operations

```python
# Insert document metadata
metadata = {
    'title': 'Climate Report',
    'creator': 'Author Name',
    'subject': 'Climate Change'
}
kg_manager.insert_document_triples("doc123", metadata)

# Insert concept mentions
mentions = [
    {
        'concept_uri': 'http://ontology.org/climate/ClimateChange',
        'text': 'climate change',
        'start_position': 45,
        'end_position': 58,
        'confidence': 0.95,
        'concept_type': 'domain',
        'source': 'comprehend'
    }
]
kg_manager.insert_concept_mentions("chunk456", mentions)

# Insert co-occurrences
co_occurrences = [
    {
        'concept1_uri': 'http://ontology.org/climate/ClimateChange',
        'concept2_uri': 'http://ontology.org/emissions/CarbonEmissions',
        'confidence': 0.85,
        'distance': 12
    }
]
kg_manager.insert_co_occurrences("chunk456", co_occurrences)

# Bulk insert TTL
ttl_content = '''
kcc:doc123 a dcterms:Document ;
    dcterms:title "Climate Report" ;
    dcterms:creator "Author Name" .
'''
kg_manager.bulk_insert_ttl(ttl_content)

# Optimized insertion (automatically chooses best method)
result = kg_manager.triple_manager.insert_triples_optimized(large_ttl_content)
if result['method'] == 'bulk_load':
    print(f"Used bulk load, loaded {result['records_loaded']} records")
else:
    print(f"Used SPARQL insert, estimated {result['estimated_records']} records")
```

#### Bulk Load Operations

```python
# Upload TTL to S3 and bulk load into Neptune
s3_uri = kg_manager.upload_ttl_to_s3(large_ttl_content, "bulk-data/dataset.ttl")
load_result = kg_manager.bulk_load_from_s3(s3_uri, format='turtle', wait=True)

# Asynchronous bulk load
load_id = kg_manager.bulk_load_from_s3("s3://bucket/large-dataset.ttl", wait=False)
status = kg_manager.get_bulk_load_status(load_id)

# List recent bulk loads
recent_loads = kg_manager.list_recent_bulk_loads(limit=5)

# Cancel a running load
kg_manager.cancel_bulk_load(load_id)
```

#### Query Operations

```python
# Find documents with specific concepts
concept_uris = ["http://ontology.org/climate/ClimateChange"]
documents = kg_manager.find_documents_with_concepts(concept_uris, limit=50)

# Find co-occurring concepts
co_occurrences = kg_manager.find_concept_co_occurrences("http://ontology.org/climate/ClimateChange")

# Get document concept summary
summary = kg_manager.get_document_concept_summary("doc123")

# Search chunks by concept
chunks = kg_manager.search_chunks_by_concept("http://ontology.org/climate/ClimateChange", confidence_threshold=0.7)
```

## Integration with Existing Lambda Functions

### Document Structure KG Processor

```python
# Before (direct Neptune operations)
# Direct SPARQL construction and execution

# After (using KG layer)
from utils.KnowledgeGraphManager import KnowledgeGraphManager

class DocumentStructureKGProcessor:
    def __init__(self):
        self.kg_manager = KnowledgeGraphManager()
    
    def generate_document_ttl(self, doc_data):
        doc_uri = self.kg_manager.mint_document_uri(doc_data['doc_id'])
        return self.kg_manager.insert_document_triples(doc_data['doc_id'], doc_data['metadata'])
```

### KG Integration Worker

```python
# Before (manual TTL parsing and Neptune loading)
# Custom SPARQL construction and AWS4Auth setup

# After (using KG layer)
from utils.KnowledgeGraphManager import KnowledgeGraphManager

class KGIntegrationWorker:
    def __init__(self):
        self.kg_manager = KnowledgeGraphManager()
    
    def load_ttl_to_neptune(self, ttl_content):
        return self.kg_manager.bulk_insert_ttl(ttl_content)
```

## URI Namespace Structure

The layer uses consistent URI namespaces:

- **Base**: `http://solve.global/knowledge-commons/`
- **Documents**: `http://solve.global/knowledge-commons/document/{doc_id}`
- **Chunks**: `http://solve.global/knowledge-commons/chunk/{doc_id}/{chunk_id}`
- **Mentions**: `http://solve.global/knowledge-commons/mention/{hash}`
- **Co-occurrences**: `http://solve.global/knowledge-commons/co-occurrence/{hash}`

## Error Handling

All operations use consistent error handling:

```python
from utils.kg_exceptions import KGConnectionError, KGQueryError, KGInsertError

try:
    results = kg_manager.execute_sparql_query(query)
except KGConnectionError as e:
    logger.error(f"Neptune connection failed: {e}")
except KGQueryError as e:
    logger.error(f"SPARQL query failed: {e}")
except KGInsertError as e:
    logger.error(f"Triple insertion failed: {e}")
```

## Performance Features

- **Connection Pooling**: Reuses connections across operations
- **Caching**: Caches ontology concepts and relationships
- **Retry Logic**: Automatic retry with exponential backoff
- **Timeout Handling**: Configurable timeouts for operations
- **Query Validation**: Basic SPARQL injection prevention

## Deployment

### Building the Layer

```bash
cd layers/knowledge-graph-layer
pip install -r requirements.txt -t python/
zip -r knowledge-graph-layer.zip python/
```

### CDK Deployment

```python
knowledge_graph_layer = lambda_.LayerVersion(
    self, "KnowledgeGraphLayer",
    code=lambda_.Code.from_asset("../layers/knowledge-graph-layer"),
    compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
    description="Knowledge Graph operations layer v1.0.0"
)
```

### Lambda Function Usage

```python
# In Lambda function
import sys
sys.path.append('/opt/python')

from utils.KnowledgeGraphManager import KnowledgeGraphManager

def lambda_handler(event, context):
    kg_manager = KnowledgeGraphManager()
    # Use kg_manager for all KG operations
```

## Version Management

**IMPORTANT**: Like the DatabaseManager layer, version consistency is critical:

1. **Layer Versioning**: Use semantic versioning (1.0.0, 1.1.0, etc.)
2. **Compatibility**: Test all Lambda functions when updating the layer
3. **Deployment**: Deploy layer updates before Lambda function updates
4. **Documentation**: Update this README with any breaking changes

## Testing

### Unit Tests

```python
import unittest
from unittest.mock import Mock, patch
from utils.KnowledgeGraphManager import KnowledgeGraphManager

class TestKnowledgeGraphManager(unittest.TestCase):
    @patch('boto3.Session')
    def setUp(self, mock_session):
        # Mock AWS credentials
        mock_creds = Mock()
        mock_creds.access_key = 'test_key'
        mock_creds.secret_key = 'test_secret'
        mock_creds.token = 'test_token'
        mock_session.return_value.get_credentials.return_value = mock_creds
        
        # Set environment variables
        os.environ['NEPTUNE_ENDPOINT'] = 'test-neptune.amazonaws.com'
        
        self.kg_manager = KnowledgeGraphManager()
    
    def test_uri_generation(self):
        doc_uri = self.kg_manager.mint_document_uri('test_doc')
        self.assertTrue(doc_uri.startswith('http://solve.global/knowledge-commons/document/'))
```

### Integration Tests

Test against actual Neptune instance in development environment.

## Troubleshooting

### Common Issues

1. **Connection Timeout**: Increase `NEPTUNE_TIMEOUT` environment variable
2. **Authentication Errors**: Verify Lambda has Neptune access permissions
3. **Query Failures**: Check SPARQL syntax and URI validity
4. **Memory Issues**: Monitor Lambda memory usage with large TTL files

### Debugging

```python
# Get connection info
conn_info = kg_manager.get_connection_info()
logger.info(f"Connection info: {conn_info}")

# Get health status
health = kg_manager.get_health_status()
logger.info(f"Health status: {health}")

# Get cache statistics
cache_stats = kg_manager.get_cache_stats()
logger.info(f"Cache stats: {cache_stats}")
```

## Migration Guide

When migrating existing Lambda functions to use this layer:

1. **Install Layer**: Add knowledge-graph-layer to Lambda function
2. **Update Imports**: Replace direct Neptune/SPARQL imports
3. **Replace Operations**: Use KG manager methods instead of direct SPARQL
4. **Update Error Handling**: Use KG-specific exceptions
5. **Test Thoroughly**: Verify all operations work correctly
6. **Update Documentation**: Document any function-specific changes
