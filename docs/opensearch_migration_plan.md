# OpenSearch Migration Plan: Serverless → AWS Managed

## Phase 1: Preparation (1-2 hours)

### 1. Update CDK Stack
- Replace `data_stack.py` with `data_stack_managed_opensearch.py`
- Update imports: `aws_opensearchserverless` → `aws_opensearch`
- Update Lambda IAM policies: `aoss:*` → `es:*`

### 2. Update Lambda Environment Variables
```python
# In CDK Lambda definitions, change:
# OLD:
"OPENSEARCH_COLLECTION_ENDPOINT": collection.attr_collection_endpoint

# NEW:
"OPENSEARCH_ENDPOINT": domain.domain_endpoint
```

### 3. Update Lambda Code
- Change auth service from `'aoss'` to `'es'`
- Update connection logic (see example above)
- Test locally if possible

## Phase 2: Deployment (30 minutes)

### 1. Deploy New Infrastructure
```bash
# Deploy new managed OpenSearch domain
cdk deploy DataStack --require-approval never

# Wait for domain to be ready (10-15 minutes)
aws opensearch describe-domain --domain-name solve-global-kr-search
```

### 2. Update Lambda Functions
```bash
# Update Lambda functions with new code
cdk deploy ComputeStack --require-approval never
```

### 3. Test Connectivity
```bash
# Test from Lambda
aws lambda invoke --function-name test-opensearch-connection response.json
```

## Phase 3: Data Migration (if needed)

### Option A: Fresh Start (Recommended)
- Let pipeline rebuild indices naturally
- Faster and cleaner than migration
- Good for development/testing

### Option B: Data Migration (if preserving data)
```python
# Export from serverless
def export_from_serverless():
    # Connect to old serverless collection
    # Export all indices and documents
    pass

# Import to managed domain  
def import_to_managed():
    # Connect to new managed domain
    # Recreate indices and import documents
    pass
```

## Phase 4: Cleanup (15 minutes)

### 1. Verify New System
- Test vector search functionality
- Test keyword search functionality
- Verify all Lambda functions work

### 2. Remove Old Resources
```bash
# Delete serverless collection
aws opensearchserverless delete-collection --id <collection-id>

# Remove old CDK resources
cdk destroy OldDataStack
```

## Cost Comparison

### Before (Serverless)
- Minimum 2 OCUs = $748/month
- Scales automatically but expensive

### After (Managed - Year 1)
- Single m6g.medium.search = $43/month
- 20GB storage = $3/month
- **Total: $46/month (94% savings)**

### After (Managed - Production)
- 3x m6g.large.search = $255/month
- 100GB storage = $14/month
- **Total: $269/month (64% savings vs serverless)**

## Rollback Plan

If issues arise:
1. Keep old serverless collection during testing
2. Switch Lambda environment variables back
3. Redeploy old Lambda code
4. Delete new managed domain

## Timeline
- **Preparation**: 1-2 hours
- **Deployment**: 30 minutes
- **Testing**: 30 minutes
- **Cleanup**: 15 minutes
- **Total**: 2-3 hours

## Benefits
- 90%+ cost reduction
- Better performance (dedicated resources)
- More control over scaling
- Standard OpenSearch features
- Easier monitoring and troubleshooting
