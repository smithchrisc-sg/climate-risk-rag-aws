# CODEBASE REFERENCE - Climate Risk RAG
**Purpose**: Quick reference for development workflows, deployment, and common patterns  
**Last Updated**: 2025-11-20  
**Last Runtime Upgrade**: 2025-11-20 (All functions → Python 3.11, layers → latest versions)

---

## 🐍 PYTHON ENVIRONMENT

### Python Version
- **Lambda Runtime**: Python 3.11 (all functions standardized as of 2025-11-20)
- **Local Development**: Python 3.12
- **Target Runtime**: Python 3.11

### Lambda Layer Versions (Current)
- **database-core-layer**: v18 (all functions)
- **knowledge-graph-layer**: v63 (includes bulk loading bug fix)
- **opensearch-dependencies**: v4
- **database-dependencies**: v2

### All Functions on Python 3.11
- gaip-search-lambda
- text-extractor-initiator
- text-extractor-processor
- nlp-initiator
- nlp-worker
- nlp-worker-keyphrase
- nlp-worker-entity
- nlp_kg_processor
- kg-integration-worker
- kg-triple-loader
- document-structure-kg-processor
- gaip-jwt-authorizer
- vector-embeddings-initiator
- vector-embeddings-worker
- keyword-indexer

### Key Dependencies
- **boto3**: AWS SDK (Lambda runtime provides this)
- **opensearchpy**: OpenSearch client
- **requests-aws4auth**: AWS SigV4 authentication
- **psycopg2-binary**: PostgreSQL database client
- **rdflib**: RDF/Turtle parsing for knowledge graph

---

## 📁 DIRECTORY STRUCTURE

### `/lambda/` - Lambda Functions
```
lambda/
├── search/                    # Main search API (gaip-search-lambda)
│   ├── handler.py            # Entry point
│   ├── src/search/           # Search services
│   │   ├── coordinator.py           # Main orchestration
│   │   ├── bm25_search_service.py   # Keyword search
│   │   ├── vector_search_service.py # Semantic search
│   │   ├── ranking_engine.py        # RRF fusion
│   │   ├── solution_searcher.py     # Neptune KG queries
│   │   ├── related_documents_service.py # TSD retrieval
│   │   ├── session_manager.py       # S3 session caching
│   │   └── postgres.py              # Database utilities
│   └── deployment.zip        # Created during deployment
│
├── keyword-indexer/          # OpenSearch BM25 indexing
│   ├── handler.py
│   └── src/keyword_indexer.py
│
├── vector-embeddings-worker/ # Bedrock Titan embeddings
│   ├── handler.py
│   └── src/vector_embeddings_worker.py
│
├── text-extractor-initiator/ # Textract job initiation
├── text-extractor-processor/ # Textract result processing
├── nlp-offset-mapper/        # NLP processing
└── kg-triple-loader/         # Neptune bulk loading
```

### `/layers/` - Lambda Layers
```
layers/
├── database-core-layer/      # PostgreSQL utilities
│   └── python/utils/DatabaseManager.py
│
└── knowledge-graph-layer/    # Neptune and SPARQL
    └── python/knowledge_graph/
        ├── KnowledgeGraphManager.py
        └── BulkLoadManager.py
```

### `/solution_ingestion/` - Document Processing
```
solution_ingestion/
├── process_manifest_pipeline.py  # Batch document processing
├── generators/                    # Embedding and processing utilities
└── TODO_DATA_FIXES.md            # Data quality issues tracker
```

### `/trusted_source_document_selection/` - TSD Management
```
trusted_source_document_selection/
├── wb_natcat_tsd_manifest_lexical.jsonl  # 477 World Bank TSDs
├── estimate_page_counts.py               # Cost estimation
├── process_manifest_pipeline.py          # Batch processing
└── test_tsd_opensearch.sh               # Searchability testing
```

### `/test-v2-webapp/` - Test webapp using the API
```
test-v2-webapp/
├── app.js                          # webapp javascript
├── index.html                      # single page test application
└── assets                          # icons, etc.
```
---

## 🚀 LAMBDA DEPLOYMENT

### Standard Deployment Pattern
```bash
# Navigate to Lambda directory
cd /Users/chris/climate-risk-rag-aws/lambda/search

# Create deployment package
zip -q -r deployment.zip handler.py src/

# Deploy to AWS
aws lambda update-function-code \
  --function-name gaip-search-lambda \
  --zip-file fileb://deployment.zip \
  --region us-east-1

# Verify deployment
aws lambda get-function \
  --function-name gaip-search-lambda \
  --region us-east-1 \
  --query 'Configuration.LastModified'
```

### Lambda Functions and Names
| Directory | Function Name | Purpose |
|-----------|--------------|---------|
| `lambda/search/` | `gaip-search-lambda` | Main search API |
| `lambda/keyword-indexer/` | `keyword-indexer` | OpenSearch BM25 indexing |
| `lambda/vector-embeddings-worker/` | `vector-embeddings-worker` | Bedrock embeddings |
| `lambda/text-extractor-initiator/` | `text-extractor-initiator` | Textract initiation |
| `lambda/text-extractor-processor/` | `text-extractor-processor` | Textract processing |
| `lambda/nlp-offset-mapper/` | `nlp-offset-mapper` | NLP processing |
| `lambda/kg-triple-loader/` | `kg-triple-loader` | Neptune loading |

### Lambda Layer Deployment
```bash
# Navigate to layer directory
cd /Users/chris/climate-risk-rag-aws/layers/knowledge-graph-layer

# Create layer package
zip -q -r layer.zip python/

# Publish new layer version
aws lambda publish-layer-version \
  --layer-name knowledge-graph-layer \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.12 \
  --region us-east-1

# Update Lambda to use new layer version
aws lambda update-function-configuration \
  --function-name kg-triple-loader \
  --layers arn:aws:lambda:us-east-1:861276078413:layer:knowledge-graph-layer:63 \
  --region us-east-1
```

---

## 🔐 AWS SERVICES & CONFIGURATION

### Region
- **Primary Region**: `us-east-1`

### OpenSearch
- **Endpoint**: `vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com`
- **Access**: VPC-only (requires EC2 bastion or Lambda in VPC)
- **Authentication**: Basic auth with username/password
- **Credentials**: `admin:veqpat-kegba2-zapbyZ`
- **Indices**:
  - `documents_keyword` - BM25 search with content_type field
  - `chunks_vector` - Semantic search with 1536-dim Titan embeddings

### Neptune
- **Endpoint**: Retrieved from environment variable `NEPTUNE_ENDPOINT`
- **Current Instance**: `db.r5.2xlarge` (temporary for bulk loading)
- **Normal Instance**: `db.r5.large`
- **Access**: VPC-only
- **Authentication**: IAM SigV4

### PostgreSQL Database
- **Host**: Environment variable `DB_HOST`
- **Database**: Environment variable `DB_NAME`
- **User**: Environment variable `DB_USER`
- **Password**: Environment variable `DB_PASSWORD`
- **Key Tables**:
  - `documents` - Document metadata (doc_id, title, source_url, file_hash)
  - `document_processing_status` - Pipeline stage tracking
  - `document_processing_audit` - Audit trail

### S3 Buckets
- **Processing Bucket**: `gaip-document-processing-bucket-*`
- **Session Cache**: `gaip-search-sessions-*`
- **Webapp**: `gaip-api-v2-webapp-1758042975`

### Bedrock
- **Model**: `amazon.titan-embed-text-v1`
- **Region**: `us-east-1`
- **Cost**: $0.0001 per 1K tokens

### Textract
- **Cost**: $0.065 per page
- **Usage**: Document text extraction

### CloudFront
- **Distribution ID**: `E1X7VBE3EV1C5K`
- **Purpose**: Webapp CDN

### Secrets Manager
- **Database Credentials**: Retrieved via environment variables in Lambda
- **OpenSearch Credentials**: Hardcoded in Lambda code (basic auth)

---

## 🔧 COMMON ENVIRONMENT VARIABLES

### Search Lambda
```bash
DB_HOST=<rds-endpoint>
DB_NAME=gaip_knowledge_repository
DB_USER=<username>
DB_PASSWORD=<password>
NEPTUNE_ENDPOINT=<neptune-endpoint>
```

### Text Extractor Initiator
```bash
TEXT_EXTRACTION_COMPLETE_TOPIC_ARN=arn:aws:sns:us-east-1:861276078413:text-extraction-complete
```

### Keyword Indexer
```bash
# OpenSearch endpoint hardcoded in code
# Database credentials same as search lambda
```

---

## 📝 GIT WORKFLOW & IDIOSYNCRASIES

### ⚠️ CRITICAL: Never `git add .` at Top Level
**Problem**: Repository has large files and many untracked files that cause timeouts

**Solution**: Always add specific directories
```bash
# ✅ CORRECT - Specific directories
git add lambda/search lambda/keyword-indexer test-v2-webapp

# ✅ CORRECT - Specific files
git add docs/status/PROJECT_CONTEXT_SUMMARY_2025-11-20.md

# ❌ WRONG - Will timeout
git add .
```

### Current Branch
- **Branch**: `feature/climate-risk-ontology-filtering`
- **Ahead of origin**: Multiple commits (push periodically)

### Commit Message Format
```bash
# Good commit message format
git commit -m "Brief summary of change

- Bullet point detail 1
- Bullet point detail 2
- Impact or reason for change"
```

### Common Git Commands
```bash
# Check status (safe)
git status

# Add specific directories
git add lambda/search test-v2-webapp

# Commit with message
git commit -m "Description of changes"

# Push to remote
git push origin feature/climate-risk-ontology-filtering

# View recent commits
git log --oneline -10
```

---

## 🧪 TESTING & VALIDATION

### Test Document Processing
```bash
cd /Users/chris/climate-risk-rag-aws/trusted_source_document_selection

# Dry run (no actual processing)
python3 process_manifest_pipeline.py \
  --manifest wb_natcat_tsd_manifest_lexical.jsonl \
  --limit 1 \
  --dry-run

# Process 1 document
python3 process_manifest_pipeline.py \
  --manifest wb_natcat_tsd_manifest_lexical.jsonl \
  --limit 1

# Process batch (5 docs at a time, 3 min delay)
python3 process_manifest_pipeline.py \
  --manifest wb_natcat_tsd_manifest_lexical.jsonl \
  --limit 25 \
  --batch-size 5 \
  --delay 180
```

### Test OpenSearch from VPC
```bash
# SSH to EC2 bastion
ssh ec2-user@ec2-dev

# Run test script
cd climate-risk-rag-aws
./test_tsd_opensearch.sh
```

### Database Queries
```sql
-- Check processing status
SELECT stage, status, COUNT(*) 
FROM document_processing_status 
WHERE timestamp >= CURRENT_DATE 
GROUP BY stage, status;

-- Check recent completions
SELECT doc_id, timestamp 
FROM document_processing_status 
WHERE stage = 'textract_complete' 
AND status = 'completed'
AND timestamp >= CURRENT_DATE
ORDER BY timestamp DESC;
```

### CloudWatch Logs
```bash
# Tail search lambda logs
aws logs tail /aws/lambda/gaip-search-lambda --follow --region us-east-1

# Tail keyword indexer logs
aws logs tail /aws/lambda/keyword-indexer --follow --region us-east-1
```

---

## 💰 COST MANAGEMENT

### Expensive Services - Use Carefully
1. **Textract**: $0.065/page (~$2,470 for 477 TSDs with 38K pages)
2. **Bedrock Titan**: $0.0001/1K tokens (adds up with large queries)
3. **Neptune**: $1.40/hour for db.r5.2xlarge
4. **OpenSearch**: Instance hours and storage

### Testing Best Practices
- **Limit test batches**: Use `--limit 1` for single document tests
- **Dry run first**: Use `--dry-run` flag before batch processing
- **Check deduplication**: Verify documents aren't already processed
- **Monitor costs**: Check AWS Cost Explorer regularly
- **Use page count estimator**: Run `estimate_page_counts.py` before bulk processing

---

## 🔍 COMMON DEBUGGING PATTERNS

### Lambda Not Working After Deployment
1. Check CloudWatch logs for errors
2. Verify layer versions are correct
3. Check environment variables are set
4. Verify IAM permissions for VPC/services

### OpenSearch Queries Timing Out
1. Check if Neptune is under heavy load (bulk loading)
2. Verify VPC connectivity from Lambda
3. Check OpenSearch cluster health
4. Review query complexity and size

### Documents Not Appearing in Search
1. Check `content_type` field is set correctly
2. Verify document in both keyword and vector indices
3. Check database processing status
4. Review CloudWatch logs for indexing errors

### Related Documents Not Showing
1. Verify query is stored in session (check logs)
2. Check solution has complete facets (title, summary, risk_types, countries, solution_types)
3. Verify TSDs have `content_type='trusted_source_document'`
4. Check database has title and source_url for TSDs

---

## 📚 KEY REFERENCE DOCUMENTS

### Project Documentation
- `/docs/status/PROJECT_CONTEXT_SUMMARY_2025-11-19.md` - Latest project state
- `/docs/status/NEXT_STEPS_2025-11-19.md` - Planned work
- `/docs/status/PRODUCTION_READINESS_IMPROVEMENTS_2025-09-24.md` - Production checklist
- `/solution_ingestion/TODO_DATA_FIXES.md` - Data quality issues

### Architecture & API
- `/docs/infrastructure/INFRASTRUCTURE_STACKS_GUIDE.md` - CDK stacks
- `/docs/api/solve-global-gaip-kr-api-DRAFT-v1.yaml` - API specification
- `/docs/RELATED_DOCUMENTS_IMPLEMENTATION_PLAN_2025-11-15.md` - Related docs design

### Database & Queries
- `/docs/DATABASE_QUERIES_REFERENCE.md` - Common SQL queries
- `/docs/status/SPARQL_QUERIES_REFERENCE_2025-09-15.md` - Neptune queries

---

## 🛠️ WEBAPP DEPLOYMENT

### Deploy to S3 and Invalidate CloudFront
```bash
cd /Users/chris/climate-risk-rag-aws/test-v2-webapp

# Sync to S3
aws s3 sync . s3://gaip-api-v2-webapp-1758042975 \
  --exclude ".git/*" \
  --exclude "*.md"

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id E1X7VBE3EV1C5K \
  --paths "/*"
```

### Webapp Files
- `index.html` - HTML structure
- `app.js` - Main application logic
- `styles.css` - Styling

---

## 🔄 COMMON WORKFLOWS

### Deploy Lambda Function
```bash
cd lambda/<function-name>
zip -q -r deployment.zip handler.py src/
aws lambda update-function-code \
  --function-name <function-name> \
  --zip-file fileb://deployment.zip \
  --region us-east-1
```

### Process Documents
```bash
cd trusted_source_document_selection
python3 process_manifest_pipeline.py \
  --manifest wb_natcat_tsd_manifest_lexical.jsonl \
  --limit <count> \
  --batch-size 5 \
  --delay 180
```

### Check Processing Status
```sql
SELECT COUNT(*) FROM document_processing_status 
WHERE stage = 'textract_complete' 
AND status = 'completed'
AND timestamp >= CURRENT_DATE;
```

### Test Search API
```bash
# From local machine (requires VPN or bastion)
curl -X POST https://<api-gateway-url>/search \
  -H "Content-Type: application/json" \
  -d '{"query":"climate risk","filters":{"solution_category":["natural-catastrophe"]}}'
```

---

## 📞 QUICK REFERENCE

### AWS Account ID
`861276078413`

### Key ARNs
- Text Extraction Topic: `arn:aws:sns:us-east-1:861276078413:text-extraction-complete`
- Knowledge Graph Layer: `arn:aws:lambda:us-east-1:861276078413:layer:knowledge-graph-layer:63`

### Python Import Patterns
```python
# Lambda layers
from utils.DatabaseManager import DatabaseManager
from knowledge_graph.KnowledgeGraphManager import KnowledgeGraphManager

# Local modules
from search.coordinator import SearchCoordinator
from search.related_documents_service import RelatedDocumentsService
```

### Common File Paths
- Manifest: `/Users/chris/climate-risk-rag-aws/trusted_source_document_selection/wb_natcat_tsd_manifest_lexical.jsonl`
- Lambda: `/Users/chris/climate-risk-rag-aws/lambda/<function-name>/`
- Webapp: `/Users/chris/climate-risk-rag-aws/test-v2-webapp/`
- Docs: `/Users/chris/climate-risk-rag-aws/docs/`

---

**Last Updated**: 2025-11-20  
**Maintained By**: Development Team  
**Purpose**: Quick reference to avoid common pitfalls and speed up development
