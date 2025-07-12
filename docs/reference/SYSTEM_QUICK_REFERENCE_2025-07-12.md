# Climate Risk RAG - Quick Reference Guide
**Last Updated**: July 12, 2025

## 🚀 System Status
- **Status**: ✅ FULLY OPERATIONAL
- **Total Lambda Functions**: 16 (all configured)
- **Database Status**: ✅ All functions have correct credentials
- **Processing Capacity**: 1000+ documents/day
- **Cost per Document**: ~$0.039

---

## 🔑 Critical Information

### Database Connection (All Functions)
```
postgresql://postgres:c0xfd_t#PBUqV(pLM-9IqM59G:>c@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require
```

### AWS Account Details
- **Account ID**: 861276078413
- **Region**: us-east-1
- **VPC ID**: vpc-051c21d88c7dc3819

---

## 📋 Lambda Functions (16 Total)

### Text Extraction (3 functions)
- `solve-global-kr-textextractor-initiator` - Starts Textract jobs
- `solve-global-kr-textextractor-processor` - Processes results
- `solve-global-kr-textextractor-trigger` - Manual testing

### Text Processing (3 functions)  
- `text-chunker-pipeline` - Main chunking (PRODUCTION)
- `solve-global-kr-text-chunker-db` - DB integration
- `solve-global-kr-text-chunker-phase1` - Testing version

### NLP Processing (2 functions)
- `nlp-processor` - NLP initiator
- `nlp-worker` - NLP background worker

### Vector Embeddings (2 functions)
- `vector-embeddings-pipelin-VectorEmbeddingsProcesso-YU1t1iUbDEkA` - Processor
- `vector-embeddings-pipelin-VectorEmbeddingsWorker5F-nCQL6EhDMuyi` - Worker

### Keyword Indexing (3 functions)
- `keyword-indexer` - Synchronous indexer
- `async-keyword-indexer-initiator` - Async initiator
- `async-keyword-indexer-worker` - Async worker

### Knowledge Graph (3 functions)
- `document-structure-kg-processor` - Document structure
- `entity-resolution-service` - Entity resolution
- `kg-integration-worker` - KG integration

---

## 🗄️ Storage Locations

### S3 Buckets
```bash
# Source documents
solve-global-kr-dl-source-documents-861276078413-us-east-1

# Processed text
solve-global-kr-dl-text-861276078413-us-east-1

# Text chunks
solve-global-kr-dl-chunks-861276078413-us-east-1

# Working buckets
solve-global-kr-text-new-861276078413-us-east-1
solve-global-kr-chunks-861276078413-us-east-1
```

### OpenSearch Collections
```bash
# Vector search
https://rui72a7agqnqo77vk34b.us-east-1.aoss.amazonaws.com

# Keyword search  
https://i7dzyfap1fe42z9delui.us-east-1.aoss.amazonaws.com
```

### Neptune Knowledge Graph
```bash
solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com
```

---

## 🔧 Common Commands

### Check Function Status
```bash
aws lambda get-function-configuration --function-name [FUNCTION_NAME] --region us-east-1
```

### Verify Database Config
```bash
aws lambda get-function-configuration --function-name [FUNCTION_NAME] --region us-east-1 --query 'Environment.Variables.DATABASE_URL'
```

### List Documents
```bash
aws s3 ls s3://solve-global-kr-dl-source-documents-861276078413-us-east-1/
```

### Trigger Manual Test
```bash
aws lambda invoke --function-name solve-global-kr-textextractor-trigger --region us-east-1 --payload '{"bucket":"solve-global-kr-dl-source-documents-861276078413-us-east-1","key":"filename.pdf"}' response.json
```

---

## 🚨 Recently Fixed (July 12, 2025)

### Functions Updated Today
1. `vector-embeddings-pipelin-VectorEmbeddingsProcesso-YU1t1iUbDEkA` - Database URL fixed
2. `async-keyword-indexer-initiator` - Database URL fixed  
3. `async-keyword-indexer-worker` - Database URL fixed

### Previous Fixes (From Conversation History)
- IAM permissions for S3 data lake buckets
- Database credentials for 7 core pipeline functions
- End-to-end Textract processing validation
- Cost analysis and optimization

---

## 📊 Processing Pipeline Flow

```
Documents (S3) 
    ↓
Textract Extraction
    ↓
Text Chunking
    ↓
┌─────────────────┬─────────────────┬─────────────────┐
│ Vector          │ Keyword         │ Knowledge       │
│ Embeddings      │ Indexing        │ Graph           │
│ ↓               │ ↓               │ ↓               │
│ OpenSearch      │ OpenSearch      │ Neptune         │
│ (Vector)        │ (Keyword)       │ (Graph)         │
└─────────────────┴─────────────────┴─────────────────┘
```

---

## 🔍 Troubleshooting Quick Checks

### Function Not Working?
1. Check CloudWatch logs: `/aws/lambda/[function-name]`
2. Verify DATABASE_URL environment variable
3. Check VPC security group rules
4. Validate IAM permissions

### Documents Not Processing?
1. Check source bucket: `solve-global-kr-dl-source-documents-861276078413-us-east-1`
2. Verify Textract service limits
3. Check SNS topic permissions
4. Review processing status in database

### Search Not Working?
1. Check OpenSearch collection status
2. Verify indexing Lambda functions
3. Review embedding generation logs
4. Check keyword indexing completion

---

## 📞 Emergency Contacts

### System Information
- **Documentation**: `/Users/chris/Climate_Risk_RAG_System_Documentation.md`
- **AWS Console**: https://console.aws.amazon.com/
- **Account**: 861276078413
- **Region**: us-east-1

### Key Resources
- **RDS Database**: climate_risk_rag
- **VPC**: vpc-051c21d88c7dc3819
- **Main Processing Function**: text-chunker-pipeline
- **Test Function**: solve-global-kr-pipeline-test-function
