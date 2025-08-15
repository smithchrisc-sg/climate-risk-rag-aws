# Climate Risk RAG System - Project Context Summary
**Date:** August 5, 2025 15:25 UTC  
**Status:** Knowledge Graph Layer Fixed - Pipeline Operational

## Current System Status

### ✅ Recently Resolved Issues
- **Knowledge Graph Layer Import Failures**: Fixed rdflib import errors that were blocking KG processing
- **Layer Structure Problems**: Corrected AWS Lambda layer directory structure (packages now in `/python/` directory)
- **Missing Dependencies**: Added explicit isodate 0.7.2 dependency to resolve conditional dependency issues
- **Dual Layer Configuration**: Ensured KG functions have both knowledge-graph-layer and database-layer access

### 🎯 System Architecture Overview
The Climate Risk RAG system is a serverless event-driven architecture on AWS that processes climate risk documents through multiple stages:

1. **Document Ingestion**: S3 upload triggers processing pipeline
2. **Text Extraction**: AWS Textract extracts text from PDFs
3. **Text Chunking**: Smart structured chunking with sentence-based overlap
4. **Keyword Indexing**: Extracts keywords from chunks
5. **Vector Embeddings**: Creates embeddings for semantic search
6. **Knowledge Graph**: Builds RDF triples and entity relationships using Neptune

### 📁 Key Project Structure

#### `/cdk/` - Infrastructure as Code
- **Primary CDK App**: `cdk/app.py` - Main production-ready deployment
- **Layer References**: Currently using knowledge-graph-layer:30 and climate-risk-core-utilities:17
- **Infrastructure Components**: VPC, Lambda functions, S3 buckets, RDS PostgreSQL, Neptune, OpenSearch

#### `/lambda/` - Lambda Function Code
- **Knowledge Graph Functions**:
  - `document-structure-kg-processor/` - Processes document structure and generates KG triples
  - `kg-triple-loader/` - Loads TTL files into Neptune graph database
- **Pipeline Functions**: Text extraction, chunking, keyword indexing, vector embeddings
- **Shared Dependencies**: All functions use appropriate Lambda layers

#### `/layers/` - Lambda Layer Definitions
- **knowledge-graph-layer/**: Contains rdflib, isodate, and KG processing utilities
  - **CRITICAL**: Use only `build_layer.sh` script for building
  - **Current Version**: v30 with corrected structure and dependencies
  - **Key Packages**: rdflib 7.1.4, isodate 0.7.2, requests-aws4auth, boto3
- **climate-risk-core-utilities/**: DatabaseManager and core utilities (v17)

#### `/docs/` - Documentation and Status
- **Status Directory**: Contains timestamped project context and work summaries
- **Architecture Documentation**: System design and component interactions
- **Work Summaries**: Historical context of major changes and fixes

### 🔧 Current Layer Configuration

#### Knowledge Graph Layer v30 (CORRECTED)
- **Structure**: Proper `/python/` directory for AWS Lambda compatibility
- **Dependencies**: 
  - rdflib 7.1.4 (upgraded from 7.0.0)
  - isodate 0.7.2 (explicitly added to resolve conditional dependency)
  - requests-aws4auth 1.2.3
  - boto3, botocore, urllib3, certifi, charset-normalizer
- **Size**: 16.5MB (32 packages, eliminated duplicate certifi)
- **Build Process**: Use ONLY `layers/knowledge-graph-layer/build_layer.sh`

#### Database Layer v17 (STABLE)
- **Contains**: DatabaseManager, PostgreSQL utilities, core database functions
- **Size**: 17.3MB
- **Status**: Working correctly, no changes needed

### 🚨 Critical Operational Notes

#### Cost Management - ALWAYS BE FRUGAL
- **Test Runs**: Use `--num-documents 1 --max-size-mb 4` for pipeline tests
- **AWS Textract**: Charges per page processed (~$0.0015/page)
- **Amazon Comprehend**: Will charge per entity extraction request when implemented
- **Titan Embeddings**: Will charge per embedding generation when implemented
- **Pipeline Test Duration**: ~5-6 minutes per single document test
- **Cost Estimation**: Single 20-page document test ≈ $0.03-0.05

#### Development Standards
- **Python Version**: ALWAYS use `python3` command, never `python`
- **Layer Building**: Use ONLY the correct build script (`build_layer.sh`)
- **Layer Validation**: Always verify `/python/` directory structure before deployment
- **Dual Layer Requirements**: KG functions need BOTH knowledge-graph-layer AND database-layer
- **Testing Protocol**: Single document tests before any multi-document processing

### 📊 Recent Work Summary References

#### Layer Fix Implementation (August 5, 2025)
- **Problem**: rdflib import failures due to incorrect layer structure and missing isodate dependency
- **Root Cause**: Packages at root level instead of `/python/` directory, conditional dependency exclusion
- **Solution**: Rebuilt layer with corrected structure, explicit isodate dependency
- **Validation**: End-to-end pipeline test confirmed successful triple loading to Neptune

#### Build Process Standardization
- **Cleanup**: Removed problematic `build_layer_v2*.sh` scripts with hardcoded dependencies
- **Standardization**: Retained only working `build_layer.sh` and corrected `requirements.txt`
- **Version Control**: Updated CDK references to match deployed layer versions

### 🔍 Key Lambda Functions Status

#### document-structure-kg-processor
- **Status**: Active and operational
- **Layers**: knowledge-graph-layer:30 + climate-risk-core-utilities:17
- **Function**: Processes document structure, extracts entities, generates RDF triples
- **Output**: TTL files stored in S3, triggers kg-triple-loader

#### kg-triple-loader  
- **Status**: Active and operational
- **Layers**: knowledge-graph-layer:30 + climate-risk-core-utilities:17
- **Function**: Loads TTL files into Neptune graph database
- **Validation**: Successfully loaded triples in recent test

### 🗃️ Database and Storage

#### PostgreSQL (RDS)
- **Host**: solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com
- **Database**: climate_risk_rag
- **Secret**: rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863

#### Neptune Graph Database
- **Endpoint**: solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182
- **Status**: Operational, successfully receiving and storing RDF triples
- **Verification**: Jupyter notebook access for SPARQL queries and triple validation

#### S3 Buckets
- **Source**: solve-global-kr-dl-source-861276078413-us-east-1
- **Text**: solve-global-kr-dl-text-861276078413-us-east-1  
- **Chunks**: solve-global-kr-dl-chunks-861276078413-us-east-1
- **TTL**: solve-global-kr-dl-neptune-ttl-861276078413-us-east-1

### 🧪 Testing and Validation

#### Pipeline Testing
- **Command**: `python3 invoke_pipeline_test.py --num-documents 1 --max-size-mb 4`
- **Duration**: ~5-6 minutes for complete processing
- **Validation Points**: 
  - Text extraction completion
  - Chunking and keyword indexing
  - Vector embedding generation
  - Knowledge graph triple creation
  - Neptune triple loading
  - Database record updates

#### Recent Test Results (August 5, 2025)
- **Document**: 064762102bead7b04a39.pdf (1.5MB, ~20 pages)
- **Status**: ✅ Complete success through all pipeline stages
- **Triples**: Successfully loaded into Neptune with correct count
- **Layers**: Both KG and database layers functioning correctly

### 🔗 Integration Points

#### SNS Topics
- **kg-triples-ready**: arn:aws:sns:us-east-1:861276078413:kg-triples-ready
- **Function**: Triggers triple loading after KG processing completion

#### VPC Configuration
- **VPC ID**: vpc-051c21d88c7dc3819
- **Subnets**: subnet-03d8bd6cf3491f38c, subnet-0c0be1dd59f70f70e
- **Security Group**: sg-0c9e10b9cfb4c9eb0

### 📚 Reference Documentation
- **Architecture Guide**: docs/architecture_diagram.png
- **Processing Flow**: PROCESSING_FLOW.pdf
- **API Documentation**: docs/API.md
- **Migration Plans**: MULTI_ONTOLOGY_MIGRATION_PLAN.md

### ⚠️ Known Considerations
- **Layer Size Limits**: Combined layers approach AWS Lambda 250MB limit
- **VPC Cold Starts**: Functions in VPC may have longer cold start times
- **Cost Monitoring**: Track usage of pay-per-use services (Textract, Comprehend, Titan)
- **Neptune Capacity**: Monitor graph database storage and query performance
- **Build Consistency**: Always use standardized build processes to prevent regressions

This system is now operational with corrected knowledge graph processing capabilities and proper dual-layer configuration for all KG-related Lambda functions.
