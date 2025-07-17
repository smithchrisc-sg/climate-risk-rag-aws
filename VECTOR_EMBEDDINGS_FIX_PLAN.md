# Vector Embeddings Stage Fix Plan

## Current Issues

1. **Import Errors**: Functions can't import `utils.DatabaseManager` from lambda layers
2. **Layer Version Mismatch**: Using `climate-risk-core-utilities-pipeline:16` instead of latest
3. **Missing Dependencies**: Vector embeddings need additional ML libraries
4. **VPC Configuration**: May cause timeouts for Bedrock API calls

## Step-by-Step Fix Plan

### Phase 1: Update Lambda Layers (Immediate)

1. **Update Vector Embeddings Functions to Use Latest Layers**:
   - Update processor to use `climate-risk-core-utilities:12` (latest)
   - Update worker to use `climate-risk-core-utilities:12` (latest)
   - Ensure both have `database-dependencies-pipeline:3`

2. **Add Missing Dependencies Layer**:
   - Create or update layer with vector embeddings dependencies:
     - `sentence-transformers`
     - `torch` (CPU version for Lambda)
     - `transformers`
     - `opensearch-py`
     - `numpy` (Lambda-compatible version)

### Phase 2: Fix Code Issues (High Priority)

1. **Update Import Statements**:
   - Ensure proper import paths for shared utilities
   - Add fallback imports for missing modules
   - Fix standardized messaging imports

2. **Fix Database Integration**:
   - Ensure DatabaseManager is properly imported
   - Add error handling for database connection issues
   - Update table creation scripts

3. **Fix OpenSearch Integration**:
   - Verify OpenSearch client configuration
   - Test vector index creation
   - Ensure proper authentication

### Phase 3: VPC and Network Configuration (Medium Priority)

1. **Review VPC Configuration**:
   - Ensure NAT Gateway access for Bedrock API calls
   - Verify security group rules
   - Consider removing VPC for worker function if not needed

2. **Add VPC Endpoints** (if needed):
   - Bedrock VPC endpoint for embeddings API
   - S3 VPC endpoint for chunk access

### Phase 4: Testing and Validation (High Priority)

1. **Unit Testing**:
   - Test each component individually
   - Verify embeddings generation
   - Test OpenSearch indexing

2. **Integration Testing**:
   - End-to-end pipeline test
   - Verify message flow between functions
   - Test error handling

## Implementation Steps

### Step 1: Create Updated Lambda Layer

```bash
# Create layer with vector embeddings dependencies
./create_vector_embeddings_layer.py
```

### Step 2: Update Lambda Function Configurations

```bash
# Update both functions to use latest layers
./update_vector_embeddings_layers.py
```

### Step 3: Fix Code Issues

```bash
# Update function code with fixes
./update_vector_embeddings_code.py
```

### Step 4: Test the Pipeline

```bash
# Run end-to-end test
./run_test_with_cleanup.py
```

## Expected Outcomes

1. **Vector Embeddings Processor**: Should successfully receive chunks-ready messages and delegate to worker
2. **Vector Embeddings Worker**: Should generate embeddings and index them in OpenSearch
3. **Database Updates**: Should properly track processing status
4. **Message Flow**: Should publish completion messages for next stage

## Risk Mitigation

1. **Backup Current Configuration**: Save current function configurations before changes
2. **Gradual Rollout**: Test with single document first
3. **Monitoring**: Add CloudWatch alarms for function errors
4. **Rollback Plan**: Keep previous working versions available

## Success Criteria

- [ ] Functions can import all required modules
- [ ] Database connections work properly
- [ ] Embeddings are generated successfully
- [ ] Vectors are indexed in OpenSearch
- [ ] Processing status is updated correctly
- [ ] Completion messages are published
- [ ] End-to-end pipeline test passes
