# OpenSearch Migration Guide: Serverless → AWS Managed

## Overview

This guide walks through migrating from OpenSearch Serverless to AWS Managed OpenSearch, achieving **90%+ cost savings** while maintaining full functionality.

## Cost Impact

| Configuration | Monthly Cost | Use Case |
|---------------|--------------|----------|
| **Current (Serverless)** | $1,500-2,200 | 10K-100K docs |
| **New (Managed - Year 1)** | $44 | 10K docs, single node |
| **New (Managed - Production)** | $277 | 100K docs, 3-node cluster |
| **Savings** | **94% reduction** | Massive cost optimization |

## Pre-Migration Checklist

- [ ] AWS SSO credentials refreshed
- [ ] CDK dependencies installed (`pip install -r cdk/requirements.txt`)
- [ ] Virtual environment activated
- [ ] Current OpenSearch data backed up (if needed)

## Step 1: Deploy New Infrastructure

```bash
# Run the deployment script
./deploy_managed_opensearch.sh
```

This creates:
- AWS Managed OpenSearch domain (`solve-global-kr-search`)
- Security groups with proper VPC access
- IAM permissions for Lambda functions
- Secrets Manager entry for master password
- All existing infrastructure remains intact

## Step 2: Update Lambda Functions

### Required Changes

The changes are minimal - only the connection method changes:

#### Before (Serverless):
```python
from aws_requests_auth.aws_auth import AWSRequestsAuth

auth = AWSRequestsAuth(access_key, secret_key, region, 'aoss')  # aoss service
client = OpenSearch(
    hosts=[{'host': collection_endpoint, 'port': 443}],
    http_auth=auth,
    # ... rest same
)
```

#### After (Managed):
```python
from aws_requests_auth.aws_auth import AWSRequestsAuth

auth = AWSRequestsAuth(access_key, secret_key, region, 'es')  # es service
client = OpenSearch(
    hosts=[{'host': domain_endpoint, 'port': 443}],
    http_auth=auth,
    # ... rest same
)
```

### Environment Variables Added

The CDK stack automatically adds these to all Lambda functions:
- `OPENSEARCH_ENDPOINT`: Domain endpoint
- `OPENSEARCH_MASTER_SECRET_ARN`: Master password secret ARN

### Functions to Update

1. **Vector Embeddings Worker** (`lambda/vector-embeddings-worker/`)
2. **Keyword Indexer** (`lambda/keyword-indexer/`)
3. Any custom search functions

### Update Script

```bash
# Copy the example code
cp lambda_opensearch_updates.py lambda/vector-embeddings-worker/opensearch_client.py
cp lambda_opensearch_updates.py lambda/keyword-indexer/opensearch_client.py

# Update your handler files to import the new client
# Replace get_opensearch_client() calls with the new implementation
```

## Step 3: Test Connectivity

### Test OpenSearch Domain

```bash
# Check domain status
aws opensearch describe-domain --domain-name solve-global-kr-search

# Test from Lambda (create a test function)
aws lambda invoke --function-name test-opensearch-connection response.json
```

### Verify Indices

```python
# Test script to verify OpenSearch is working
from lambda_opensearch_updates import get_opensearch_client

client = get_opensearch_client()
print("Cluster health:", client.cluster.health())
print("Indices:", client.indices.get_alias("*"))
```

## Step 4: Data Migration (Optional)

### Option A: Fresh Start (Recommended)
- Let the pipeline rebuild indices naturally
- Faster and cleaner than migration
- Good for development/testing environments

### Option B: Data Migration
If you need to preserve existing data:

```python
# Export from serverless (if needed)
def export_indices():
    # Connect to old serverless collection
    # Use scroll API to export all documents
    pass

# Import to managed domain
def import_indices():
    # Connect to new managed domain
    # Recreate indices and bulk import documents
    pass
```

## Step 5: Update Lambda Deployments

```bash
# Update Lambda functions with new code
cd cdk
cdk deploy -a "python app_production_ready_managed_opensearch.py" \
    --require-approval never
```

## Step 6: Validation

### Test Vector Search
```python
# Test vector search functionality
vectors = get_test_vectors()
results = search_vectors(vectors[0], size=5)
print(f"Found {len(results['hits']['hits'])} results")
```

### Test Keyword Search
```python
# Test keyword search functionality
results = search_keywords("climate risk", size=10)
print(f"Found {len(results['hits']['hits'])} results")
```

### Test Pipeline Integration
```bash
# Upload a test document to trigger the pipeline
aws s3 cp test_document.pdf s3://solve-global-kr-dl-source-documents-861276078413-us-east-1/documents/

# Monitor pipeline execution
aws logs tail /aws/lambda/solve-global-kr-vector-embeddings-worker --follow
```

## Step 7: Cleanup (After Validation)

### Remove Old Serverless Collection
```bash
# List serverless collections
aws opensearchserverless list-collections

# Delete old collection (after confirming new system works)
aws opensearchserverless delete-collection --id <collection-id>
```

### Update Documentation
- Update any hardcoded endpoints in documentation
- Update monitoring dashboards
- Update backup procedures

## Rollback Plan

If issues arise:

1. **Keep old serverless collection** during testing period
2. **Switch environment variables** back to old endpoints
3. **Redeploy old Lambda code** if needed
4. **Delete new managed domain** to avoid costs

```bash
# Emergency rollback
aws opensearch delete-domain --domain-name solve-global-kr-search
# Redeploy old stack
cdk deploy -a "python app_production_ready.py"
```

## Monitoring & Maintenance

### CloudWatch Metrics
- Monitor OpenSearch cluster health
- Track search latency and throughput
- Set up alarms for disk usage

### Cost Monitoring
- Set up billing alerts
- Monitor EBS storage growth
- Track query costs

### Scaling Guidelines

#### Year 1 (10K docs):
- Single `m6g.medium.search` node
- 20GB EBS storage
- ~$44/month

#### Production (100K docs):
- 3x `m6g.large.search` nodes
- 50GB EBS storage per node
- Multi-AZ deployment
- ~$277/month

#### Scaling Up:
```bash
# Update domain configuration
aws opensearch update-domain-config \
    --domain-name solve-global-kr-search \
    --cluster-config InstanceType=m6g.large.search,InstanceCount=3
```

## Troubleshooting

### Common Issues

1. **Connection Timeout**
   - Check security group rules
   - Verify VPC configuration
   - Ensure Lambda is in correct subnets

2. **Authentication Errors**
   - Verify IAM permissions
   - Check auth service ('es' not 'aoss')
   - Ensure session token is included

3. **Index Creation Fails**
   - Check domain status
   - Verify master credentials
   - Review CloudWatch logs

### Debug Commands

```bash
# Check domain status
aws opensearch describe-domain --domain-name solve-global-kr-search

# View Lambda logs
aws logs tail /aws/lambda/solve-global-kr-vector-embeddings-worker

# Test connectivity from Lambda
aws lambda invoke --function-name test-opensearch-connection response.json
```

## Success Criteria

- [ ] OpenSearch domain is healthy and accessible
- [ ] Vector search returns relevant results
- [ ] Keyword search functions correctly
- [ ] Pipeline processes documents end-to-end
- [ ] Cost reduced by 90%+
- [ ] No functionality regression

## Support

For issues during migration:
1. Check CloudWatch logs for detailed error messages
2. Verify security group and IAM configurations
3. Test connectivity step-by-step
4. Use rollback plan if needed

The migration provides massive cost savings while maintaining full functionality. The OpenSearch APIs remain identical, so your search logic doesn't change at all.
