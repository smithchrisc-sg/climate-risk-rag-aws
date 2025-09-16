# Neptune Stream Poller Lambda Function

## Overview

The Neptune Stream Poller Lambda function processes Neptune Streams and indexes RDF data to OpenSearch for full-text search capabilities. This enables the `neptune-fts:query()` function in SPARQL queries.

## Architecture

```
Neptune Cluster (Streams) → Lambda Poller → OpenSearch Domain
                                ↓
                         DynamoDB (Lease Table)
```

## Key Components

### Core Processing Modules
- **`neptune_to_es/neptune_sparql_es_handler.py`** - SPARQL stream processing
- **`neptune_to_es/neptune_gremlin_es_handler.py`** - Gremlin stream processing  
- **`neptune_to_es/es_helper.py`** - OpenSearch indexing utilities
- **`aggregator/es_aggregator.py`** - Record aggregation for efficiency

### Configuration
- **Handler**: `lambda_function.lambda_handler`
- **Runtime**: Python 3.9
- **Memory**: 1024 MB
- **Timeout**: 600 seconds (10 minutes)
- **VPC**: Enabled for Neptune and OpenSearch access

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `StreamRecordsHandler` | Handler class for processing | `neptune_to_es.neptune_sparql_es_handler.ElasticSearchSparqlHandler` |
| `NeptuneStreamEndpoint` | Neptune stream URL | `https://cluster.neptune.amazonaws.com:8182/sparql/stream` |
| `AdditionalParams` | JSON config for OpenSearch | `{"ElasticSearchEndpoint": "domain.es.amazonaws.com"}` |
| `LeaseTable` | DynamoDB table for coordination | `NeptuneOntologyFTS-LeaseTable` |
| `StreamRecordsBatchSize` | Records per batch | `5000` |
| `MaxPollingWaitTime` | Polling interval (seconds) | `600` |
| `LoggingLevel` | Log level | `INFO` |

## Current Configuration

### Optimized Settings
- **Application Name**: `NeptuneOntologyFTS`
- **Batch Size**: 5000 records (maximum efficiency)
- **Polling Interval**: 10 minutes (cost-optimized)
- **Query Engine**: SPARQL
- **OpenSearch Shards**: 2 (reduced from default 5)

### Network Configuration
- **VPC**: `vpc-051c21d88c7dc3819`
- **Subnets**: Database subnets for OpenSearch access
- **Security Groups**: Lambda, OpenSearch, and HTTPS access

## Customization for Ontology Filtering

### Current State
The Lambda processes **all** Neptune data and indexes it to OpenSearch.

### Planned Enhancement
Add filtering logic to only index ontology data:

```python
# Proposed filtering logic
ONTOLOGY_GRAPHS = [
    'http://climate-risk-ontology',
    'http://geonames-ontology',
    'http://www.w3.org/2000/01/rdf-schema',
    'http://www.w3.org/2004/02/skos/core'
]

def should_index_record(record):
    graph_uri = record.get('eventData', {}).get('stmt', {}).get('graph', '')
    return any(ontology in graph_uri for ontology in ONTOLOGY_GRAPHS)
```

### Benefits of Filtering
- **60-80% cost reduction** in DynamoDB operations
- **Smaller OpenSearch indices** (faster queries)
- **Ontology-focused results** (no document noise)
- **Reduced Lambda execution time**

## Deployment

### Via CloudFormation
The Lambda is deployed as part of the `NeptuneQuickStart` CloudFormation stack.

### Manual Updates
```bash
# Create deployment package
cd /Users/chris/climate-risk-rag-aws/lambda/neptune-stream-poller
zip -r neptune-stream-poller.zip . -x "*.zip" "*.md" "__pycache__/*"

# Update Lambda function
aws lambda update-function-code \
    --function-name "NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3" \
    --zip-file fileb://neptune-stream-poller.zip
```

## Monitoring

### CloudWatch Logs
- **Log Group**: `/aws/lambda/NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3`
- **Log Level**: INFO (configurable via `LoggingLevel`)

### CloudWatch Dashboard
- **URL**: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=neptune-stream-poller-NeptuneOntologyFTS
- **Metrics**: Processing rate, errors, DynamoDB usage

### Key Metrics to Monitor
- **Records processed per minute**
- **Lambda execution duration**
- **DynamoDB read/write capacity**
- **OpenSearch indexing rate**
- **Error rates and types**

## Troubleshooting

### Common Issues
1. **Stream connectivity**: Check Neptune Streams are enabled
2. **OpenSearch access**: Verify VPC and security group configuration
3. **DynamoDB throttling**: Monitor lease table capacity
4. **Lambda timeout**: Increase timeout if processing large batches

### Debug Commands
```bash
# Check Lambda logs
aws logs tail /aws/lambda/NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3 --follow

# Check DynamoDB lease table
aws dynamodb scan --table-name NeptuneOntologyFTS-LeaseTable

# Check OpenSearch indices
curl -X GET "https://opensearch-domain/_cat/indices" -u admin:password
```

## Integration with Climate Risk RAG System

### Purpose
Enables full-text search within SPARQL queries for:
- **Climate risk ontology** concepts and relationships
- **Geonames ontology** location data
- **Entity alignment** between NLP results and ontologies

### Usage in OntologyManager
```python
# SPARQL query with FTS
query = """
PREFIX neptune-fts: <http://aws.amazon.com/neptune/vocab/v01/services/fts#>

SELECT ?concept ?label ?score
WHERE {
    ?concept rdfs:label ?label .
    FILTER(neptune-fts:query(neptune-fts:field('object'), 'climate adaptation'))
    BIND(neptune-fts:score() AS ?score)
}
ORDER BY DESC(?score)
"""
```

## Future Enhancements

### Phase 1: Ontology Filtering
- Add filtering logic to process only ontology graphs
- Reduce costs and improve performance
- Maintain backward compatibility

### Phase 2: Advanced Features
- Custom analyzers for climate terminology
- Multilanguage support for geographic names
- Real-time indexing optimization

### Phase 3: Integration
- Direct integration with OntologyManager methods
- Automated ontology updates
- Performance monitoring and alerting

---

**Status**: Deployed and operational  
**Last Updated**: August 7, 2025  
**CloudFormation Stack**: `NeptuneQuickStart`
