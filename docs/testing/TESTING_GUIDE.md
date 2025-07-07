# 🔬 Climate Risk RAG - Testing & Comparison Guide

This guide walks you through comprehensive testing and comparison between your POC implementation and the new AWS serverless architecture.

## 🎯 **Testing Strategy Overview**

### **Selective Migration Approach**
- **All documents** (15,176 PDFs) - Essential baseline
- **All embeddings** (1.02M files, 32GB) - Compare vs Titan
- **Flair NER results** (91 files) - Your best NER model
- **Extracted text** (15,155 files) - Validation reference
- **Sample chunks** (1,000 documents) - Chunking comparison

### **Comparison Dimensions**
1. **Text Extraction**: Your parsing vs AWS Textract
2. **Named Entity Recognition**: Flair vs AWS Comprehend
3. **Embeddings**: Your vectors vs AWS Titan
4. **Chunking**: 5-sentence approach vs AWS structured
5. **End-to-end RAG**: Overall system performance

## 🚀 **Step-by-Step Testing Process**

### **Phase 1: Selective Migration** (2-3 hours)

```bash
# Execute selective migration
./migrate_data_selective.sh
```

**What this does:**
- Uploads all 15,176 documents to S3
- Migrates your processed embeddings (32GB)
- Uploads Flair NER results (your best model)
- Migrates extracted text for validation
- Samples 1,000 documents' chunks for comparison
- **Cost**: ~$20/month during testing period

### **Phase 2: Infrastructure Deployment**

```bash
# Deploy AWS infrastructure
./deploy.sh
```

**What this creates:**
- Lambda functions with structured chunking
- OpenSearch Serverless for vector/keyword search
- Neptune for knowledge graph
- API Gateway for testing interface
- Step Functions for document processing

### **Phase 3: Comparison Testing** (1-2 hours)

```bash
# Install testing dependencies
cd testing
pip install -r requirements.txt

# Run comprehensive comparison
python3 run_comparison.py \
  --documents-bucket climate-risk-documents-{ACCOUNT}-{REGION} \
  --artifacts-bucket climate-risk-artifacts-{ACCOUNT}-{REGION} \
  --sample-size 100

# Quick test (smaller sample)
python3 run_comparison.py \
  --documents-bucket climate-risk-documents-{ACCOUNT}-{REGION} \
  --artifacts-bucket climate-risk-artifacts-{ACCOUNT}-{REGION} \
  --quick-test
```

## 📊 **Comparison Framework Details**

### **1. Text Extraction Comparison**
```
POC Method vs AWS Textract
├── Content similarity (Jaccard index)
├── Length comparison
├── Word overlap analysis
└── Quality scoring
```

**Metrics:**
- Jaccard similarity coefficient
- Content length ratio
- Word overlap percentage
- Overall quality score

### **2. NER Comparison**
```
Flair NER vs AWS Comprehend
├── Entity count comparison
├── Entity type distribution
├── Common entity detection
└── Precision/Recall/F1 analysis
```

**Metrics:**
- Precision, Recall, F1-score
- Entity type coverage
- Climate-specific entity detection
- Processing speed comparison

### **3. Embedding Comparison**
```
Your Embeddings vs AWS Titan
├── Dimension analysis
├── Cosine similarity comparison
├── Clustering quality
└── Downstream task performance
```

**Metrics:**
- Vector similarity scores
- Dimension efficiency
- Semantic coherence
- Search relevance quality

### **4. Chunking Comparison**
```
5-Sentence Chunks vs AWS Structured
├── Chunk size distribution
├── Content overlap analysis
├── Boundary quality assessment
└── Context preservation
```

**Metrics:**
- Average chunk size
- Size variance
- Content overlap
- Semantic coherence

### **5. RAG Performance**
```
End-to-End System Comparison
├── Query response quality
├── Source attribution accuracy
├── Response time analysis
└── Cost per query
```

**Test Queries:**
- "What are the main physical climate risks?"
- "How do carbon emissions affect climate change?"
- "What adaptation strategies exist for sea level rise?"
- "How can businesses assess climate risk?"
- And 6 more domain-specific queries

## 📈 **Expected Results & Analysis**

### **Text Extraction**
- **Expected**: AWS Textract likely superior for complex PDFs
- **Key Metric**: Jaccard similarity > 0.8 indicates high agreement
- **Decision Point**: If similarity > 0.7, use Textract for consistency

### **NER Performance**
- **Expected**: Flair may outperform on climate-specific entities
- **Key Metric**: F1-score comparison
- **Decision Point**: If Flair F1 > Comprehend + 0.1, keep Flair

### **Embeddings**
- **Expected**: Titan may have better general performance
- **Key Metric**: Downstream task performance
- **Decision Point**: Cost vs performance trade-off analysis

### **Chunking**
- **Expected**: AWS structured better for complex documents
- **Key Metric**: Content overlap and boundary quality
- **Decision Point**: Hybrid approach may be optimal

## 🎯 **Sample Test Results**

```
🔬 COMPARISON SUMMARY
============================================================

📝 TEXT EXTRACTION:
  Average quality score: 0.847
  Jaccard similarity: 0.782
  Recommendation: AWS Textract shows high similarity - recommended

🏷️  NAMED ENTITY RECOGNITION:
  Average F1 score: 0.734
  Average precision: 0.801
  Average recall: 0.678
  Recommendation: Flair NER shows superior performance for climate entities

🔢 EMBEDDINGS:
  Average cosine similarity: 0.823
  Documents compared: 15
  Recommendation: Both perform well, consider cost implications

✂️  CHUNKING:
  Average content overlap: 0.691
  Documents compared: 10
  Recommendation: AWS structured chunking preserves hierarchy better

🤖 RAG PERFORMANCE:
  Test queries: 10
  Performance analysis available in detailed results

💡 KEY RECOMMENDATIONS:
  1. AWS Textract recommended for production consistency
  2. Keep Flair NER for specialized climate entity detection
  3. Implement A/B testing for production deployment
  4. Consider hybrid approaches for optimal results
  5. Monitor performance metrics continuously
```

## 🔧 **Customizing Tests**

### **Add Custom Test Queries**
Edit `testing/comparison_framework.py`:
```python
test_queries = [
    "Your custom climate risk question?",
    "Another domain-specific query?",
    # Add more queries relevant to your use case
]
```

### **Adjust Sample Sizes**
```bash
# Test with different sample sizes
python3 run_comparison.py --sample-size 50   # Smaller, faster
python3 run_comparison.py --sample-size 200  # Larger, more comprehensive
```

### **Focus on Specific Comparisons**
Modify the framework to run only specific comparisons:
- Text extraction only
- NER comparison only
- Embedding analysis only

## 📊 **Results Analysis**

### **Automated Reports**
The framework generates:
- **JSON results**: Detailed metrics and comparisons
- **Visualizations**: Charts and graphs
- **Recommendations**: Actionable insights
- **Cost analysis**: Performance vs cost trade-offs

### **Manual Analysis**
Review results for:
- **Domain-specific performance**: Climate risk entity detection
- **Document type variations**: Reports vs papers vs presentations
- **Language patterns**: Technical vs general climate content
- **Edge cases**: Complex tables, charts, multi-column layouts

## 💰 **Cost Management During Testing**

### **Testing Period Costs** (~3-6 months)
- **Storage**: ~$20/month (selective migration)
- **Compute**: ~$10-20/month (testing queries)
- **AI/ML Services**: ~$5-15/month (comparison testing)
- **Total**: ~$35-55/month

### **Post-Testing Cleanup**
```bash
# Keep only documents, remove test artifacts
aws s3 rm s3://climate-risk-artifacts-{ACCOUNT}-{REGION}/processed_embeddings/ --recursive
aws s3 rm s3://climate-risk-artifacts-{ACCOUNT}-{REGION}/sample_chunks/ --recursive
# Reduces cost to ~$10/month
```

## 🎯 **Decision Framework**

### **Go with AWS if:**
- Textract similarity > 0.8
- Comprehend F1-score within 0.1 of Flair
- Titan embeddings perform well on test queries
- Cost savings > 30%
- Maintenance reduction is priority

### **Keep POC approach if:**
- Flair significantly outperforms Comprehend (F1 > 0.1 difference)
- Your embeddings show superior domain performance
- Custom chunking provides better results
- You have specialized requirements

### **Hybrid approach if:**
- Mixed results across different components
- Different approaches excel in different areas
- Cost vs performance trade-offs vary by component

## 🚀 **Next Steps After Testing**

1. **Analyze Results**: Review all comparison metrics
2. **Make Decisions**: Choose approach for each component
3. **Implement Production**: Deploy chosen architecture
4. **Monitor Performance**: Set up ongoing monitoring
5. **Iterate**: Continuously improve based on real usage

---

**Ready to discover which approach works best for your climate risk RAG system!** 🔬📊

The testing framework provides comprehensive, data-driven insights to make informed decisions about your production architecture.
