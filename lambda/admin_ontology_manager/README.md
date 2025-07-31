# Admin Ontology Manager Lambda

Administrative utility Lambda function for managing ontology operations in the Climate Risk RAG system. This function provides a programmatic interface to the OntologyManager class from the knowledge-graph-layer v2.0.0.

## Purpose

This Lambda serves as an administrative utility (not part of the main processing pipeline) to:
- Load ontology data from S3 or direct content
- Query and validate ontology concepts
- Manage ontology cache
- Provide ontology statistics and diagnostics

## Supported Operations

### 1. `load_ontology_from_s3`
Load ontology from an S3 key in the configured ontology bucket.

**Parameters:**
- `s3_key` (required): S3 key for the ontology file
- `format` (optional): RDF format ('turtle', 'xml', 'n3', 'json-ld'), defaults to 'turtle'
- `force_reload` (optional): Force reload even if already loaded, defaults to false

**Example:**
```json
{
  "operation": "load_ontology_from_s3",
  "parameters": {
    "s3_key": "climate-risk-ontology.ttl",
    "format": "turtle",
    "force_reload": true
  }
}
```

### 2. `load_ontology_from_content`
Load ontology from provided TTL content.

**Parameters:**
- `ttl_content` (required): TTL content as string
- `force_reload` (optional): Force reload even if already loaded, defaults to false

**Example:**
```json
{
  "operation": "load_ontology_from_content",
  "parameters": {
    "ttl_content": "@prefix kr: <https://solve.global/ontology/climate-risk/> .\n...",
    "force_reload": true
  }
}
```

### 3. `get_concepts`
Retrieve ontology concepts, optionally filtered by type.

**Parameters:**
- `concept_type` (optional): Filter by specific concept type

**Example:**
```json
{
  "operation": "get_concepts",
  "parameters": {
    "concept_type": "DomainConcept"
  }
}
```

### 4. `get_concept_details`
Get detailed information about a specific concept.

**Parameters:**
- `concept_uri` (required): URI of the concept

**Example:**
```json
{
  "operation": "get_concept_details",
  "parameters": {
    "concept_uri": "https://solve.global/ontology/climate-risk/ClimateRisk"
  }
}
```

### 5. `find_concepts_by_label`
Search for concepts by label with optional fuzzy matching.

**Parameters:**
- `label` (required): Label to search for
- `fuzzy` (optional): Enable fuzzy matching, defaults to true

**Example:**
```json
{
  "operation": "find_concepts_by_label",
  "parameters": {
    "label": "climate",
    "fuzzy": true
  }
}
```

### 6. `validate_concept`
Validate that a concept exists and optionally matches expected type.

**Parameters:**
- `concept_uri` (required): URI of the concept to validate
- `ontology_concept` (optional): Expected concept type

**Example:**
```json
{
  "operation": "validate_concept",
  "parameters": {
    "concept_uri": "https://solve.global/ontology/climate-risk/ClimateRisk",
    "ontology_concept": "DomainConcept"
  }
}
```

### 7. `get_concept_relationships`
Get all relationships for a specific concept.

**Parameters:**
- `concept_uri` (required): URI of the concept

**Example:**
```json
{
  "operation": "get_concept_relationships",
  "parameters": {
    "concept_uri": "https://solve.global/ontology/climate-risk/ClimateRisk"
  }
}
```

### 8. `get_ontology_stats`
Get ontology manager statistics and diagnostics.

**Parameters:** None

**Example:**
```json
{
  "operation": "get_ontology_stats"
}
```

### 9. `clear_cache`
Clear the ontology cache.

**Parameters:** None

**Example:**
```json
{
  "operation": "clear_cache"
}
```

## Response Format

All operations return a standardized response:

```json
{
  "statusCode": 200,
  "body": {
    "operation": "operation_name",
    "success": true,
    "result": {
      // Operation-specific result data
    }
  }
}
```

Error responses:
```json
{
  "statusCode": 400,
  "body": {
    "operation": "operation_name",
    "success": false,
    "error": "Error message",
    "error_type": "KnowledgeGraphError"
  }
}
```

## Usage

### Via AWS CLI
```bash
aws lambda invoke \
  --function-name solve-global-kr-admin-ontology-manager \
  --payload '{"operation":"get_ontology_stats"}' \
  response.json
```

### Via Python (boto3)
```python
import boto3
import json

lambda_client = boto3.client('lambda')

response = lambda_client.invoke(
    FunctionName='solve-global-kr-admin-ontology-manager',
    InvocationType='RequestResponse',
    Payload=json.dumps({
        'operation': 'get_concepts',
        'parameters': {'concept_type': 'DomainConcept'}
    })
)

result = json.loads(response['Payload'].read())
print(json.dumps(result, indent=2))
```

### Using the Test Script
Run the provided test script to test all operations:

```bash
python test_admin_ontology_manager.py
```

## Dependencies

This Lambda uses the knowledge-graph-layer v2.0.0 which provides:
- RDFLib for ontology processing
- OntologyManager class
- Knowledge graph utilities and exceptions
- AWS SDK (boto3)

## Environment Variables

The Lambda inherits standard environment variables from the CDK deployment:
- `ONTOLOGY_BUCKET`: S3 bucket for ontology files
- `DATABASE_HOST`, `DATABASE_NAME`, etc.: Database connection details
- `NEPTUNE_ENDPOINT`, `NEPTUNE_PORT`: Neptune graph database details

## Error Handling

The Lambda handles three types of errors:
1. **KnowledgeGraphError**: Ontology-specific errors (400 status)
2. **ValidationError**: Parameter validation errors (400 status)  
3. **InternalError**: Unexpected system errors (500 status)

All errors are logged with full stack traces for debugging.

## Security

This Lambda runs with the same IAM role as other pipeline functions, providing access to:
- S3 buckets for ontology data
- RDS database for metadata
- Neptune graph database
- CloudWatch for logging

## Monitoring

Monitor the Lambda through:
- CloudWatch Logs: `/aws/lambda/solve-global-kr-admin-ontology-manager`
- CloudWatch Metrics: Function duration, errors, invocations
- X-Ray tracing (if enabled)

## Development

To modify this Lambda:
1. Update the code in `lambda_function.py`
2. Test locally using the test script
3. Deploy via CDK: `cdk deploy ClimateRiskRAGStackV2`
4. Verify deployment using the test script
