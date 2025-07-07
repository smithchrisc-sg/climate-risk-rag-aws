# 🌍 Climate Risk RAG - Selective Migration Guide

This guide walks you through the **selective migration strategy** - migrating a representative sample of documents for cost-effective testing and validation of the new AWS microservices architecture.

## 🎯 **Selective Migration Strategy**

### **Why Selective Migration?**
- **Cost Control:** Test with ~$20/month vs $200+/month for full migration
- **Risk Mitigation:** Validate architecture before full commitment
- **Performance Testing:** Compare POC vs AWS implementation with manageable dataset
- **Iterative Approach:** Learn and optimize before scaling

### **Migration Scope**
```yaml
Selective Migration (Recommended First Step):
  Documents: 1,000 representative documents (~3GB)
  Chunks: ~280,000 text chunks (~8GB)
  Embeddings: ~280,000 vector embeddings (~9GB)
  NER Results: ~1,000 entity extraction files (~3MB)
  Total Storage: ~20GB
  Estimated Cost: $20/month
  Processing Time: 2-4 hours

Full Migration (After Validation):
  Documents: 15,176 documents (~45GB)
  Chunks: 4,244,002 text chunks (~120GB)
  Embeddings: 4,244,002 vector embeddings (~135GB)
  NER Results: ~15,176 entity files (~50MB)
  Total Storage: ~300GB
  Estimated Cost: $200+/month
  Processing Time: 24-48 hours
```

## 📊 **Document Selection Strategy**

### **Representative Sampling Approach**
The selective migration uses stratified sampling to ensure representative coverage:

```python
# Document selection criteria
selection_criteria = {
    'document_types': {
        'climate_reports': 400,      # 40% - Core climate assessments
        'regulatory_docs': 200,      # 20% - Policy and compliance
        'technical_studies': 250,    # 25% - Scientific and technical
        'financial_analysis': 150    # 15% - Economic and financial
    },
    'date_range': {
        'recent': 400,              # 2020-2024
        'historical': 600           # 2015-2019
    },
    'document_size': {
        'small': 200,               # <50 pages
        'medium': 500,              # 50-200 pages
        'large': 300                # >200 pages
    },
    'processing_complexity': {
        'simple_text': 300,         # Mostly text
        'tables_charts': 400,       # Mixed content
        'complex_layout': 300       # Complex formatting
    }
}
```

### **Quality Assurance**
- **Coverage Validation:** Ensure all major climate risk topics are represented
- **Metadata Preservation:** Maintain all original document metadata
- **Chunk Distribution:** Verify representative chunk size and type distribution
- **Entity Coverage:** Ensure diverse entity types and relationships

## 🚀 **Step-by-Step Selective Migration**

### **Prerequisites**
1. **Infrastructure Deployed**: Run CDK deployment first
2. **AWS CLI Configured**: `aws configure` with appropriate permissions
3. **Local Data Accessible**: Verify path to your data lake
4. **Sample Selection**: Generate document selection list

### **Step 1: Generate Document Sample**
```bash
# Run document selection script
cd migration/
python generate_sample_selection.py \
  --sample-size 1000 \
  --strategy stratified \
  --output sample_documents.json

# Verify sample quality
python validate_sample.py \
  --sample-file sample_documents.json \
  --report sample_validation_report.html
```

### **Step 2: Execute Selective Migration**
```bash
# Run selective migration script
./migrate_data_selective.sh

# Monitor progress
tail -f migration_selective.log
```

### **Step 3: Validate Migration**
```bash
# Run validation checks
cd testing/
python validate_migration.py \
  --migration-type selective \
  --sample-file ../migration/sample_documents.json

# Generate validation report
python generate_migration_report.py \
  --type selective \
  --output selective_migration_report.html
```

## 🔧 **Selective Migration Script Analysis**

### **Current Script: `migrate_data_selective.sh`**

The existing selective migration script has the following configuration:

```bash
# Current selective migration scope
SAMPLE_CHUNKS=1000          # Documents to migrate
MAX_WORKERS=8               # Parallel processing

Migration Components:
✅ All documents (15,176 PDFs, ~45GB)     # ⚠️ This should be 1,000 documents
✅ All embeddings (1.02M files, ~32GB)    # ⚠️ This should be sample embeddings
✅ Flair NER results (91 files, ~5MB)     # ✅ Correct
✅ Extracted text (15,155 files, ~2.5GB)  # ⚠️ This should be sample text
✅ Sample chunks (1,000 documents, ~8GB)  # ✅ Correct concept
```

### **⚠️ Script Alignment Issues Identified**

The current `migrate_data_selective.sh` script has some misalignment with the selective strategy:

1. **Documents:** Script migrates ALL 15,176 documents instead of 1,000 sample
2. **Embeddings:** Script migrates ALL embeddings instead of sample embeddings
3. **Text:** Script migrates ALL extracted text instead of sample text
4. **Cost Impact:** Current script would cost ~$88/month, not $20/month

## 🔧 **Corrected Selective Migration Script**

Here's the corrected approach for true selective migration:

```bash
#!/bin/bash
# Corrected Climate Risk RAG Selective Data Migration Script

set -e

echo "🌍 Climate Risk RAG - Selective Data Migration (Corrected)"
echo "========================================================="

# Configuration
LOCAL_DATA_PATH="/Volumes/G-RAID Photo 24TB/climate_risk_rag"
AWS_REGION="us-east-1"
SAMPLE_SIZE=1000            # Number of documents to migrate
MAX_WORKERS=4               # Reduced for selective migration

# Sample selection file (generated by generate_sample_selection.py)
SAMPLE_FILE="migration/sample_documents.json"

echo "📍 Selective Migration Configuration:"
echo "  Sample Size: $SAMPLE_SIZE documents"
echo "  Sample File: $SAMPLE_FILE"
echo "  Estimated Storage: ~20GB"
echo "  Estimated Cost: ~$20/month"
echo ""

# Migration steps for SAMPLE documents only
migrate_sample_documents() {
    echo "📄 Migrating sample documents..."
    python migration/migrate_sample_documents.py \
        --sample-file "$SAMPLE_FILE" \
        --source-path "$LOCAL_DATA_PATH/data/raw" \
        --bucket "$DOCUMENTS_BUCKET" \
        --max-workers $MAX_WORKERS
}

migrate_sample_chunks() {
    echo "🧩 Migrating sample chunks..."
    python migration/migrate_sample_chunks.py \
        --sample-file "$SAMPLE_FILE" \
        --source-path "$LOCAL_DATA_PATH/data/chunks" \
        --bucket "$ARTIFACTS_BUCKET" \
        --prefix "chunks/" \
        --max-workers $MAX_WORKERS
}

migrate_sample_embeddings() {
    echo "🔢 Migrating sample embeddings..."
    python migration/migrate_sample_embeddings.py \
        --sample-file "$SAMPLE_FILE" \
        --source-path "$LOCAL_DATA_PATH/data/embeddings" \
        --bucket "$ARTIFACTS_BUCKET" \
        --prefix "embeddings/" \
        --max-workers $MAX_WORKERS
}

migrate_sample_ner() {
    echo "🏷️ Migrating sample NER results..."
    python migration/migrate_sample_ner.py \
        --sample-file "$SAMPLE_FILE" \
        --source-path "$LOCAL_DATA_PATH/data/ner_results" \
        --bucket "$ARTIFACTS_BUCKET" \
        --prefix "ner_results/" \
        --max-workers $MAX_WORKERS
}
```

## 📊 **Migration Validation Framework**

### **Validation Checks**
```python
# Selective migration validation
validation_checks = {
    'document_count': {
        'expected': 1000,
        'tolerance': 0  # Exact match required
    },
    'chunk_distribution': {
        'expected_avg': 280,
        'tolerance': 50  # ±50 chunks per document
    },
    'storage_usage': {
        'expected_gb': 20,
        'tolerance': 5   # ±5GB acceptable
    },
    'processing_artifacts': {
        'chunks': True,
        'embeddings': True,
        'ner_results': True,
        'metadata': True
    },
    'data_integrity': {
        'file_corruption': 0,
        'missing_files': 0,
        'metadata_consistency': True
    }
}
```

### **Performance Benchmarks**
```yaml
Selective Migration Performance Targets:
  Migration Time: <4 hours
  Data Transfer Rate: >5GB/hour
  Error Rate: <0.1%
  Validation Success: 100%
  
Comparison Testing Targets:
  Query Response Time: <3 seconds
  Search Precision: >85%
  Processing Accuracy: >95%
  Cost per Query: <$0.05
```

## 🧪 **Testing & Validation Process**

### **Phase 1: Migration Validation**
```bash
# 1. Pre-migration checks
python testing/pre_migration_checks.py \
  --sample-file migration/sample_documents.json

# 2. Execute selective migration
./migrate_data_selective.sh

# 3. Post-migration validation
python testing/post_migration_validation.py \
  --migration-type selective \
  --expected-count 1000

# 4. Data integrity checks
python testing/data_integrity_checks.py \
  --sample-file migration/sample_documents.json \
  --check-all-artifacts
```

### **Phase 2: Performance Testing**
```bash
# 1. System functionality tests
python testing/system_functionality_tests.py \
  --test-suite selective_migration

# 2. Query performance tests
python testing/query_performance_tests.py \
  --sample-queries testing/sample_queries.json \
  --iterations 100

# 3. Comparison tests (POC vs AWS)
python testing/comparison_tests.py \
  --poc-endpoint "http://localhost:8000" \
  --aws-endpoint "https://api.climate-risk.com" \
  --test-queries testing/comparison_queries.json
```

### **Phase 3: Quality Assessment**
```bash
# 1. Search quality assessment
python testing/search_quality_assessment.py \
  --test-queries testing/quality_test_queries.json \
  --ground-truth testing/ground_truth_results.json

# 2. Response quality evaluation
python testing/response_quality_evaluation.py \
  --evaluation-criteria testing/quality_criteria.json

# 3. Generate comprehensive report
python testing/generate_test_report.py \
  --migration-type selective \
  --output reports/selective_migration_test_report.html
```

## 💰 **Cost Analysis & Monitoring**

### **Selective Migration Costs**
```yaml
Storage Costs (Monthly):
  S3 Standard: ~$0.46 (20GB × $0.023/GB)
  S3 Intelligent Tiering: ~$0.40 (with lifecycle)
  
Processing Costs (One-time):
  Lambda Executions: ~$2.00 (text processing)
  Textract: ~$15.00 (1,000 documents)
  Comprehend: ~$5.00 (NER processing)
  Bedrock: ~$3.00 (embedding generation)
  
Database Costs (Monthly):
  OpenSearch Serverless: ~$8.00
  Neptune: ~$7.00 (t3.medium)
  RDS: ~$3.00 (t3.micro)
  
Total Monthly Cost: ~$20-25
Total Setup Cost: ~$25
```

### **Cost Monitoring**
```bash
# Set up cost alerts for selective migration
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget '{
    "BudgetName": "ClimateRiskRAG-Selective",
    "BudgetLimit": {
      "Amount": "30",
      "Unit": "USD"
    },
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }'

# Monitor costs
python monitoring/cost_monitor.py \
  --budget-name "ClimateRiskRAG-Selective" \
  --alert-threshold 25
```

## 🔄 **Migration Path: Selective → Full**

### **Decision Criteria for Full Migration**
```yaml
Proceed to Full Migration When:
  Technical Validation:
    - Query response time: <3 seconds ✅
    - Search precision: >85% ✅
    - System stability: >99% uptime ✅
    - Cost per query: <$0.05 ✅
  
  Business Validation:
    - Stakeholder approval ✅
    - Budget approval for $200/month ✅
    - Timeline approval for 24-48 hour migration ✅
    - Risk acceptance for production deployment ✅
```

### **Full Migration Preparation**
```bash
# 1. Scale up infrastructure for full migration
python infrastructure/scale_for_full_migration.py

# 2. Generate full migration plan
python migration/generate_full_migration_plan.py \
  --based-on-selective-results \
  --optimization-level high

# 3. Execute full migration
./migrate_data.sh  # Full migration script

# 4. Comprehensive validation
python testing/full_migration_validation.py
```

## 📋 **Selective Migration Checklist**

### **Pre-Migration**
- [ ] Infrastructure deployed and validated
- [ ] Sample document selection generated and validated
- [ ] Migration scripts updated for selective approach
- [ ] Cost monitoring and alerts configured
- [ ] Backup and rollback procedures documented

### **During Migration**
- [ ] Monitor migration progress and performance
- [ ] Track costs and resource utilization
- [ ] Validate data integrity at each stage
- [ ] Document any issues or optimizations needed

### **Post-Migration**
- [ ] Complete data integrity validation
- [ ] Performance testing and benchmarking
- [ ] Comparison testing with POC system
- [ ] Cost analysis and optimization
- [ ] Generate migration report and recommendations

### **Decision Point**
- [ ] Technical validation successful
- [ ] Business case confirmed
- [ ] Stakeholder approval for full migration
- [ ] Budget and timeline approved
- [ ] Risk assessment completed

## 🎯 **Success Metrics**

### **Technical Success Criteria**
- **Migration Completion:** 100% of selected documents migrated successfully
- **Data Integrity:** 0% data corruption or loss
- **Performance:** Query response time <3 seconds for 90% of queries
- **Accuracy:** Search precision >85% compared to POC
- **Reliability:** System uptime >99% during testing period

### **Business Success Criteria**
- **Cost Control:** Monthly costs <$25 for selective migration
- **Timeline:** Migration completed within 4 hours
- **Quality:** Stakeholder satisfaction with system performance
- **Risk Mitigation:** No critical issues identified
- **Scalability:** Clear path to full migration validated

## 📞 **Support & Troubleshooting**

### **Common Issues**
1. **Sample Selection Problems:** Use `validate_sample.py` to verify representativeness
2. **Migration Script Errors:** Check AWS permissions and bucket access
3. **Performance Issues:** Monitor Lambda memory and timeout settings
4. **Cost Overruns:** Verify sample size and check for unexpected data transfer

### **Getting Help**
- **Documentation:** Refer to [INFRASTRUCTURE_STACKS_GUIDE.md](INFRASTRUCTURE_STACKS_GUIDE.md)
- **Troubleshooting:** See [TRIGGER_MAPPING.md](TRIGGER_MAPPING.md) for event debugging
- **Performance:** Review [STEP_FUNCTIONS_DESIGN.md](STEP_FUNCTIONS_DESIGN.md) for optimization

---

## 🚀 **Next Steps After Selective Migration**

1. **Validate Results:** Complete all testing and validation procedures
2. **Analyze Performance:** Compare with POC system and document improvements
3. **Optimize Configuration:** Fine-tune based on selective migration learnings
4. **Business Review:** Present results to stakeholders for full migration approval
5. **Plan Full Migration:** Use selective migration insights to optimize full migration approach

This selective migration approach provides a cost-effective, low-risk path to validate the new AWS microservices architecture before committing to the full migration of all 15,176 documents.
