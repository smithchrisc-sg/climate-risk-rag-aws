# Climate Risk RAG System - Complete Documentation
**Last Updated**: July 12, 2025  
**System Status**: ✅ FULLY OPERATIONAL  
**Version**: Production Ready

---

## Table of Contents
1. [System Overview](#system-overview)
2. [AWS Infrastructure](#aws-infrastructure)
3. [Lambda Functions Inventory](#lambda-functions-inventory)
4. [Database Configuration](#database-configuration)
5. [Storage Components](#storage-components)
6. [Processing Pipeline Flow](#processing-pipeline-flow)
7. [Cost Analysis](#cost-analysis)
8. [Security Configuration](#security-configuration)
9. [Monitoring & Logging](#monitoring--logging)
10. [Troubleshooting Guide](#troubleshooting-guide)

---

## System Overview

### Architecture
The Climate Risk RAG (Retrieval-Augmented Generation) system is a serverless document processing pipeline built on AWS that:
- Extracts text from PDF documents using AWS Textract
- Processes text through NLP pipelines for entity recognition
- Generates vector embeddings for semantic search
- Creates keyword indexes for traditional search
- Builds knowledge graphs for relationship mapping
- Stores processed data in multiple formats for RAG applications

### Key Capabilities
- **Document Processing**: 1000+ documents/day capacity
- **Multi-Modal Search**: Vector similarity + keyword search + knowledge graph
- **Cost Efficient**: ~$0.039 per document processing cost
- **Scalable**: Serverless architecture with auto-scaling
- **Secure**: VPC-isolated with encrypted data storage

---

## AWS Infrastructure

### Account Information
- **AWS Account ID**: 861276078413
- **Primary Region**: us-east-1
- **Environment**: Production

### Core Services Used
- **AWS Lambda**: 16 processing functions
- **Amazon RDS**: PostgreSQL database cluster
- **Amazon S3**: 6 data lake buckets
- **AWS Textract**: Document text extraction
- **Amazon OpenSearch Serverless**: 2 search collections
- **Amazon Neptune**: Knowledge graph database
- **Amazon SNS**: Inter-service messaging
- **Amazon SQS**: Queue management with DLQ
- **AWS IAM**: Role-based access control

---

## Lambda Functions Inventory

### 1. Document Ingestion & Text Extraction
| Function Name | Runtime | Memory | Timeout | Handler | Description |
|---------------|---------|--------|---------|---------|-------------|
| `solve-global-kr-textextractor-initiator` | python3.11 | 1024MB | 300s | `text_extractor_initiator.lambda_handler` | Initiates async Textract jobs |
| `solve-global-kr-textextractor-processor` | python3.11 | 1024MB | 900s | `text_extractor_processor_simplified.lambda_handler` | Processes completed Textract jobs |
| `solve-global-kr-textextractor-trigger` | python3.11 | 1024MB | 60s | `index.lambda_handler` | Manual trigger for testing |

**Key Environment Variables:**
```bash
DATABASE_URL=postgresql://postgres:c0xfd_t#PBUqV(pLM-9IqM59G:>c@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require
TEXTRACT_SNS_TOPIC_ARN=arn:aws:sns:us-east-1:861276078413:solve-global-kr-textract-completion
TEXTRACT_SERVICE_ROLE_ARN=arn:aws:iam::861276078413:role/solve-global-kr-textract-service-role
OUTPUT_BUCKET=solve-global-kr-chunks-861276078413-us-east-1
```

### 2. Text Chunking & Processing
| Function Name | Runtime | Memory | Timeout | Handler | Description |
|---------------|---------|--------|---------|---------|-------------|
| `text-chunker-pipeline` | python3.11 | 1024MB | 900s | `text_chunker_processor_updated.lambda_handler` | Main text chunking with pipeline integration |
| `solve-global-kr-text-chunker-db` | python3.11 | 1024MB | 600s | `text_chunker_processor.lambda_handler` | Text chunker with database integration |
| `solve-global-kr-text-chunker-phase1` | python3.11 | 512MB | 300s | `text_chunker_processor.lambda_handler` | Phase 1 testing version |

**Key Environment Variables:**
```bash
TEXT_BUCKET=solve-global-kr-text-new-861276078413-us-east-1
CHUNKS_BUCKET=solve-global-kr-chunks-861276078413-us-east-1
CHUNKS_READY_TOPIC_ARN=arn:aws:sns:us-east-1:861276078413:chunks-ready
PHASE=PRODUCTION_PIPELINE
STANDARDIZED_MESSAGING_ENABLED=true
```

### 3. NLP Processing
| Function Name | Runtime | Memory | Timeout | Handler | Description |
|---------------|---------|--------|---------|---------|-------------|
| `nlp-processor` | python3.11 | 256MB | 60s | `nlp_processor_simplified.lambda_handler` | NLP Processing Initiator |
| `nlp-worker` | python3.11 | 1024MB | 600s | `nlp_worker_updated.lambda_handler` | NLP Background Worker |

### 4. Vector Embeddings
| Function Name | Runtime | Memory | Timeout | Handler | Description |
|---------------|---------|--------|---------|---------|-------------|
| `vector-embeddings-pipelin-VectorEmbeddingsProcesso-YU1t1iUbDEkA` | python3.11 | 256MB | 60s | `vector_embeddings_processor.lambda_handler` | Vector embeddings processor |
| `vector-embeddings-pipelin-VectorEmbeddingsWorker5F-nCQL6EhDMuyi` | python3.11 | 2048MB | 900s | `vector_embeddings_worker.lambda_handler` | Vector embeddings worker |

**Key Environment Variables:**
```bash
OPENSEARCH_ENDPOINT=https://rui72a7agqnqo77vk34b.us-east-1.aoss.amazonaws.com
EMBEDDINGS_MODEL_TYPE=titan
COST_THRESHOLD_PER_DOC=0.50
VECTOR_COMPLETION_TOPIC_ARN=arn:aws:sns:us-east-1:861276078413:vector-completion
VECTOR_WORKER_TOPIC_ARN=arn:aws:sns:us-east-1:861276078413:vector-embeddings-worker
```

### 5. Keyword Indexing
| Function Name | Runtime | Memory | Timeout | Handler | Description |
|---------------|---------|--------|---------|---------|-------------|
| `keyword-indexer` | python3.11 | 1024MB | 900s | `keyword_indexer_processor.lambda_handler` | Synchronous keyword indexer |
| `async-keyword-indexer-initiator` | python3.11 | 512MB | 120s | `simple_async_processor.lambda_handler` | Async keyword indexer initiator |
| `async-keyword-indexer-worker` | python3.11 | 1024MB | 600s | `worker_processor.lambda_handler` | Async keyword indexer worker |

**Key Environment Variables:**
```bash
OPENSEARCH_ENDPOINT=https://i7dzyfap1fe42z9delui.us-east-1.aoss.amazonaws.com
INDEX_NAME=climate-risk-keyword-index
PHASE=PRODUCTION_KEYWORD_INDEXING
COMPLETION_TOPIC_ARN=arn:aws:sns:us-east-1:861276078413:keyword-indexing-complete
WORKER_FUNCTION_NAME=async-keyword-indexer-worker
```

### 6. Knowledge Graph Processing
| Function Name | Runtime | Memory | Timeout | Handler | Description |
|---------------|---------|--------|---------|---------|-------------|
| `document-structure-kg-processor` | python3.11 | 512MB | 300s | `document_structure_kg_processor.lambda_handler` | Document structure KG processor |
| `entity-resolution-service` | python3.11 | 1024MB | 600s | `entity_resolver.lambda_handler` | Entity resolution service |
| `kg-integration-worker` | python3.11 | 1024MB | 600s | `kg_integration_worker.lambda_handler` | KG integration worker |

**Key Environment Variables:**
```bash
NEPTUNE_ENDPOINT=solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com
TTL_BUCKET=solve-global-kr-dl-neptune-ttl-861276078413-us-east-1
ENTITY_BASE_URI=http://solve.global/knowledge-commons/schema#
ENTITY_NAMESPACE=kr:
KG_INTEGRATION_TOPIC_ARN=arn:aws:sns:us-east-1:861276078413:kg-integration-processing
```

### 7. Pipeline Testing & Coordination
| Function Name | Runtime | Memory | Timeout | Handler | Description |
|---------------|---------|--------|---------|---------|-------------|
| `solve-global-kr-pipeline-test-function` | python3.11 | 1024MB | 900s | `pipeline_test_handler.lambda_handler` | Pipeline test function |

---

## Database Configuration

### PostgreSQL Database
- **Endpoint**: `solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com`
- **Port**: 5432
- **Database Name**: `climate_risk_rag`
- **SSL Mode**: Required

### Standard Database URL (Used by All Functions)
```
postgresql://postgres:c0xfd_t#PBUqV(pLM-9IqM59G:>c@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require
```

### Database Schema
The database contains tables for:
- Document metadata and processing status
- Text chunks and their relationships
- Entity extraction results
- Processing job tracking
- Vector embedding metadata

---

## Storage Components

### S3 Buckets

#### Data Lake Buckets
| Bucket Name | Purpose | Content Type |
|-------------|---------|--------------|
| `solve-global-kr-dl-source-documents-861276078413-us-east-1` | Source documents | PDF files |
| `solve-global-kr-dl-text-861276078413-us-east-1` | Extracted text | JSON/TXT files |
| `solve-global-kr-dl-chunks-861276078413-us-east-1` | Text chunks | JSON files |
| `solve-global-kr-dl-ner-results-861276078413-us-east-1` | NER results | JSON files |
| `solve-global-kr-dl-neptune-ttl-861276078413-us-east-1` | Neptune TTL files | TTL/RDF files |

#### Processing Buckets
| Bucket Name | Purpose | Content Type |
|-------------|---------|--------------|
| `solve-global-kr-text-new-861276078413-us-east-1` | Text processing | JSON files |
| `solve-global-kr-chunks-861276078413-us-east-1` | Chunk processing | JSON files |
| `solve-global-kr-cache-861276078413-us-east-1` | Processing cache | Various |

### OpenSearch Collections

#### Vector Search Collection
- **Endpoint**: `https://rui72a7agqnqo77vk34b.us-east-1.aoss.amazonaws.com`
- **Purpose**: Vector similarity search
- **Index**: Document embeddings using AWS Titan

#### Keyword Search Collection  
- **Endpoint**: `https://i7dzyfap1fe42z9delui.us-east-1.aoss.amazonaws.com`
- **Purpose**: Traditional keyword search
- **Index Name**: `climate-risk-keyword-index`

### Neptune Knowledge Graph
- **Cluster Endpoint**: `solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com`
- **Purpose**: Entity relationships and knowledge graph
- **Query Language**: SPARQL/Gremlin

---

## Processing Pipeline Flow

### 1. Document Ingestion
```
Source Documents (S3) → Textract Initiator → AWS Textract → Textract Processor → Text Storage (S3)
```

### 2. Text Processing
```
Text Storage → Text Chunker → Chunks Storage → NLP Processor → NLP Worker
```

### 3. Parallel Processing Streams

#### Vector Embeddings Stream
```
Chunks → Vector Processor → Vector Worker → OpenSearch (Vector Collection)
```

#### Keyword Indexing Stream
```
Text → Keyword Indexer → OpenSearch (Keyword Collection)
```

#### Knowledge Graph Stream
```
Text → Document Structure KG → Entity Resolution → KG Integration → Neptune
```

### 4. Coordination & Messaging
- **SNS Topics**: Inter-service communication
- **SQS Queues**: Async processing with DLQ
- **Database**: State tracking and coordination

---

## Cost Analysis

### Current Processing Costs (Validated July 2025)
- **Textract**: $42.25 for batch processing
- **OpenSearch**: $62.20 operational costs
- **Lambda**: Minimal (serverless pricing)
- **Storage**: ~$10-20/month for current data volume

### Projected Costs (1000 documents/day)
- **Per Document**: ~$0.039
- **Monthly Total**: <$500
- **Annual Projection**: <$6,000

### Cost Optimization Features
- Serverless architecture (pay-per-use)
- Efficient text chunking to minimize processing
- Batch processing for Textract
- OpenSearch Serverless (auto-scaling)

---

## Security Configuration

### VPC Configuration
- **VPC ID**: `vpc-051c21d88c7dc3819`
- **Subnets**: 
  - `subnet-03d8bd6cf3491f38c`
  - `subnet-0c0be1dd59f70f70e`
  - `subnet-0e9efc5fdf29e9da0`
  - `subnet-00efdcc220a613ae3`

### Security Groups (Function-Specific)
- Text Extractor: `sg-08518057bfb59e735`
- Text Chunker: `sg-099296a5c809e8d9d`
- Vector Processing: `sg-075e1c169015c3e52`
- Keyword Indexing: `sg-0c9e10b9cfb4c9eb0`
- Knowledge Graph: `sg-0c043bcb40f656321`

### IAM Roles
- **Textract Service Role**: `arn:aws:iam::861276078413:role/solve-global-kr-textract-service-role`
- **Lambda Execution Roles**: Function-specific roles with least privilege
- **Cross-Service Access**: SNS, SQS, S3, RDS, OpenSearch, Neptune

### Encryption
- **Database**: SSL/TLS required
- **S3**: Server-side encryption enabled
- **OpenSearch**: Encryption at rest and in transit
- **Neptune**: Encryption enabled

---

## Monitoring & Logging

### CloudWatch Logs
Each Lambda function has dedicated log groups:
```
/aws/lambda/[function-name]
```

### Key Metrics to Monitor
- **Lambda Invocations**: Success/failure rates
- **Textract Jobs**: Processing time and costs
- **Database Connections**: Connection pool usage
- **OpenSearch**: Query performance and indexing rates
- **Neptune**: Query response times

### Alerting Recommendations
- Lambda error rates > 5%
- Database connection failures
- Textract job failures
- OpenSearch indexing delays
- Cost thresholds exceeded

---

## Troubleshooting Guide

### Common Issues & Solutions

#### 1. Database Connection Failures
**Symptoms**: Lambda timeouts, connection errors
**Solution**: 
- Verify DATABASE_URL environment variable
- Check VPC security group rules
- Validate RDS instance status

#### 2. Textract Processing Delays
**Symptoms**: Documents stuck in processing
**Solution**:
- Check Textract service limits
- Verify SNS topic permissions
- Review Textract job status in console

#### 3. OpenSearch Indexing Issues
**Symptoms**: Search results missing recent documents
**Solution**:
- Check OpenSearch collection status
- Verify IAM permissions for indexing
- Review Lambda function logs for errors

#### 4. Memory/Timeout Issues
**Symptoms**: Lambda function timeouts
**Solution**:
- Increase memory allocation (affects CPU)
- Extend timeout settings
- Optimize code for large documents

### Diagnostic Commands

#### Check Function Configuration
```bash
aws lambda get-function-configuration --function-name [FUNCTION_NAME] --region us-east-1
```

#### Verify Database Connectivity
```bash
aws lambda get-function-configuration --function-name [FUNCTION_NAME] --region us-east-1 --query 'Environment.Variables.DATABASE_URL'
```

#### List S3 Bucket Contents
```bash
aws s3 ls s3://[BUCKET_NAME]/ --recursive
```

#### Check Textract Job Status
```bash
aws textract get-document-analysis --job-id [JOB_ID] --region us-east-1
```

---

## Maintenance & Updates

### Regular Maintenance Tasks
1. **Weekly**: Review CloudWatch logs for errors
2. **Monthly**: Analyze cost reports and optimize
3. **Quarterly**: Update Lambda runtimes and dependencies
4. **Annually**: Review and update security configurations

### Update Procedures
1. **Lambda Functions**: Use blue/green deployments
2. **Database Schema**: Plan migrations carefully
3. **Infrastructure**: Use CDK/CloudFormation for consistency
4. **Dependencies**: Update Lambda layers regularly

### Backup Strategy
- **Database**: Automated RDS backups enabled
- **S3 Data**: Versioning and cross-region replication
- **Configuration**: Infrastructure as Code (CDK)
- **Code**: Git repository with tagged releases

---

## Contact & Support

### System Administrators
- **Primary**: Climate Risk RAG Team
- **AWS Account**: 861276078413
- **Region**: us-east-1

### Documentation Updates
This document should be updated whenever:
- New Lambda functions are added
- Configuration changes are made
- Infrastructure components are modified
- Performance optimizations are implemented

**Last Validation**: July 12, 2025  
**Next Review**: August 12, 2025  
**Document Version**: 1.0
