# Knowledge Graph Layer v2.0.0 Deployment Guide

## 🎯 **Overview**

This guide provides step-by-step instructions for deploying Knowledge Graph Layer v2.0.0 with NLP-Ontology integration while maintaining **100% backward compatibility** with existing Lambda functions.

## 🛡️ **Backward Compatibility Guarantee**

- ✅ **All existing Lambda functions continue to work unchanged**
- ✅ **All existing method signatures preserved**
- ✅ **URI patterns remain consistent**
- ✅ **No breaking changes in functionality**

## 📋 **Pre-Deployment Checklist**

### **Prerequisites**
- [ ] AWS CLI configured with appropriate permissions
- [ ] CDK v2 installed and configured
- [ ] Python 3.11 runtime available
- [ ] Access to existing infrastructure (VPC, subnets, security groups)

### **Validation**
- [ ] Current system is working properly
- [ ] All existing Lambda functions are operational
- [ ] Database connectivity is confirmed
- [ ] Neptune cluster is accessible

## 🚀 **Deployment Steps**

### **Step 1: Build Knowledge Graph Layer v2.0.0**

```bash
# Navigate to layer directory
cd /Users/chris/climate-risk-rag-aws/layers/knowledge-graph-layer

# Build the new layer
./build_layer_v2.sh

# Verify build success
ls -la knowledge-graph-layer-v2.0.0.zip
```

**Expected Output:**
```
✅ Layer package created: knowledge-graph-layer-v2.0.0.zip
📊 Package size: ~50-60MB (within Lambda limits)
```

### **Step 2: Backup Existing CDK Files**

```bash
# Navigate to CDK directory
cd /Users/chris/climate-risk-rag-aws/cdk

# Run migration script in dry-run mode first
python3 migrate_to_kg_layer_v2.py --dry-run

# Review what will be changed, then run actual migration
python3 migrate_to_kg_layer_v2.py
```

**Expected Output:**
```
🚀 Starting Knowledge Graph Layer v2.0.0 migration...
📁 Found X files to update
✅ Updated: app_production_ready_fixed.py
✅ Updated: app_document_structure_kg.py
🎉 Migration completed!
```

### **Step 3: Deploy Updated Layer to AWS**

```bash
# Upload layer to AWS Lambda
aws lambda publish-layer-version \
    --layer-name knowledge-graph-layer-v2 \
    --description "Knowledge Graph Layer v2.0.0 with NLP-Ontology Integration" \
    --zip-file fileb://knowledge-graph-layer-v2.0.0.zip \
    --compatible-runtimes python3.11 \
    --region us-east-1

# Note the returned LayerVersionArn for CDK update
```

**Expected Output:**
```json
{
    "LayerArn": "arn:aws:lambda:us-east-1:861276078413:layer:knowledge-graph-layer-v2",
    "LayerVersionArn": "arn:aws:lambda:us-east-1:861276078413:layer:knowledge-graph-layer-v2:1",
    "Version": 1,
    ...
}
```

### **Step 4: Test Existing Functions with New Layer**

```bash
# Deploy updated CDK stack (existing functions with v2.0.0 layer)
cdk deploy ClimateRiskRAGStackV2 --require-approval never

# Test document-structure-kg-processor with new layer
aws lambda invoke \
    --function-name solve-global-kr-document-structure-kg-processor-v2 \
    --payload '{"test_mode": true}' \
    test_response.json

# Verify response
cat test_response.json
```

**Success Criteria:**
- ✅ Function executes without errors
- ✅ Response format unchanged
- ✅ URI patterns consistent
- ✅ Memory usage within expected bounds

### **Step 5: Create New NLP Lambda Functions**

```bash
# Create directories for new Lambda functions
mkdir -p ../lambda/nlp-entity-ontology-mapper
mkdir -p ../lambda/nlp-ontology-term-finder  
mkdir -p ../lambda/nlp-concept-reconciler
mkdir -p ../lambda/nlp-kg-integrator

# Copy handler templates (will be created separately)
# These will use the new NLP utilities from v2.0.0 layer
```

### **Step 6: Deploy New NLP Functions**

```bash
# Deploy new NLP functions
cdk deploy --all

# Verify new functions are created
aws lambda list-functions --query 'Functions[?contains(FunctionName, `nlp`)].FunctionName'
```

**Expected Functions:**
- `solve-global-kr-nlp-entity-ontology-mapper`
- `solve-global-kr-nlp-ontology-term-finder`
- `solve-global-kr-nlp-concept-reconciler`
- `solve-global-kr-nlp-kg-integrator`

### **Step 7: Validate End-to-End Integration**

```bash
# Test complete NLP-ontology pipeline
python3 test_nlp_integration_pipeline.py

# Verify RDF output consistency
python3 validate_rdf_output.py

# Check URI consistency across systems
python3 validate_uri_consistency.py
```

## 🧪 **Testing Strategy**

### **Backward Compatibility Testing**

```bash
# Test 1: Existing function imports
python3 -c "
import sys
sys.path.append('../lambda/document-structure-kg-processor')
from utils import KnowledgeGraphManager
kg = KnowledgeGraphManager()
print('✅ KnowledgeGraphManager import successful')
"

# Test 2: URI consistency
python3 -c "
from utils import KnowledgeGraphManager
kg = KnowledgeGraphManager()
uri1 = kg.mint_document_uri('test123')
uri2 = kg.mint_chunk_uri('test123', 'chunk001')
print(f'✅ URI generation working: {uri1}, {uri2}')
"

# Test 3: Existing method signatures
python3 test_method_signatures.py
```

### **New Functionality Testing**

```bash
# Test 1: NLP utilities import
python3 -c "
from utils import EntityAligner, OntologyTermMatcher, ConceptReconciler
print('✅ New NLP utilities import successful')
"

# Test 2: Entity alignment
python3 test_entity_alignment.py

# Test 3: Term matching
python3 test_term_matching.py

# Test 4: Reconciliation
python3 test_reconciliation.py
```

### **Performance Testing**

```bash
# Test memory usage
python3 test_memory_usage.py

# Test cold start times
python3 test_cold_start.py

# Test processing speed
python3 test_processing_speed.py
```

## 🔧 **Configuration Updates**

### **Environment Variables**

Add these environment variables to new NLP functions:

```python
# Entity-Ontology Mapper
"MIN_CONFIDENCE_THRESHOLD": "0.6"
"MAX_CANDIDATES": "5"
"ENABLE_CACHING": "true"

# Ontology Term Finder
"MIN_CONFIDENCE_THRESHOLD": "0.7"
"MIN_TERM_LENGTH": "3"
"MAX_TERM_DISTANCE": "100"
"ENABLE_FUZZY_BOUNDARIES": "true"

# Concept Reconciler
"RECONCILIATION_STRATEGY": "confidence_weighted"
"CONFLICT_RESOLUTION": "highest_confidence"

# NLP-KG Integrator
"ENABLE_VALIDATION": "true"
"S3_BUCKET": "solve-global-kr-dl-kg-861276078413-us-east-1"
```

### **Memory and Timeout Settings**

```python
# Existing functions (unchanged)
memory_size=1024
timeout=Duration.minutes(15)

# New NLP functions (increased for ML processing)
memory_size=1024  # For NLP processing
timeout=Duration.minutes(10)  # For complex operations
```

## 🚨 **Troubleshooting**

### **Common Issues**

#### **Import Errors**
```python
# ❌ Wrong
from utils.EntityAligner import EntityAligner

# ✅ Correct
from utils import EntityAligner
```

#### **Memory Issues**
```bash
# Increase memory for NLP functions
memory_size=1536  # Up from 1024
```

#### **Cold Start Issues**
```bash
# Use provisioned concurrency for frequently used functions
aws lambda put-provisioned-concurrency-config \
    --function-name solve-global-kr-nlp-entity-ontology-mapper \
    --provisioned-concurrency-config ProvisionedConcurrencyConfig=2
```

#### **Layer Size Issues**
```bash
# Check layer size
aws lambda get-layer-version \
    --layer-name knowledge-graph-layer-v2 \
    --version-number 1 \
    --query 'CodeSize'

# If too large, optimize dependencies
pip install --no-deps <package>
```

### **Validation Commands**

```bash
# Check layer contents
aws lambda get-layer-version \
    --layer-name knowledge-graph-layer-v2 \
    --version-number 1

# Test function with new layer
aws lambda invoke \
    --function-name solve-global-kr-document-structure-kg-processor-v2 \
    --payload '{}' \
    response.json

# Check CloudWatch logs
aws logs describe-log-groups \
    --log-group-name-prefix "/aws/lambda/solve-global-kr"
```

## 🔄 **Rollback Procedure**

If issues occur, rollback using these steps:

### **Step 1: Restore CDK Files**
```bash
cd /Users/chris/climate-risk-rag-aws/cdk
cp backups_kg_v2_migration/*.backup .
```

### **Step 2: Revert to Previous Layer**
```bash
# Update CDK to use previous layer version
# Edit CDK files to reference v1.0.6 layer

# Redeploy
cdk deploy --all
```

### **Step 3: Verify Rollback**
```bash
# Test existing functions
aws lambda invoke \
    --function-name solve-global-kr-document-structure-kg-processor \
    --payload '{}' \
    response.json
```

## 📊 **Success Metrics**

### **Deployment Success**
- ✅ Layer v2.0.0 deployed successfully
- ✅ All existing functions updated without errors
- ✅ New NLP functions created and operational
- ✅ No breaking changes in existing functionality

### **Performance Metrics**
- ✅ Memory usage within expected bounds (<1.5GB)
- ✅ Cold start times <10 seconds
- ✅ Processing speed maintained or improved
- ✅ Error rates <5%

### **Functional Metrics**
- ✅ Entity-ontology alignment accuracy >80%
- ✅ Pattern matching performance >1000 terms/second
- ✅ Reconciliation success rate >90%
- ✅ RDF integration generates valid TTL

## 📚 **Post-Deployment Tasks**

### **Documentation Updates**
- [ ] Update API documentation
- [ ] Update architecture diagrams
- [ ] Update troubleshooting guides
- [ ] Update monitoring dashboards

### **Monitoring Setup**
- [ ] Configure CloudWatch alarms for new functions
- [ ] Set up performance monitoring
- [ ] Configure error rate alerts
- [ ] Set up cost monitoring

### **Team Communication**
- [ ] Notify team of successful deployment
- [ ] Share updated documentation
- [ ] Schedule knowledge transfer sessions
- [ ] Update runbooks and procedures

## 🎯 **Next Steps**

After successful deployment:

1. **Monitor Performance**: Watch CloudWatch metrics for 24-48 hours
2. **Validate Accuracy**: Test NLP-ontology integration with real documents
3. **Optimize Configuration**: Tune confidence thresholds and memory settings
4. **Plan Search Integration**: Prepare for future search system development
5. **Document Lessons Learned**: Update deployment procedures based on experience

---

**This deployment maintains complete backward compatibility while adding powerful NLP-ontology integration capabilities. All existing functionality continues to work unchanged, with new capabilities available for advanced document processing.**
