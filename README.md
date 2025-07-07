# Climate Risk RAG AWS Migration Project

**Status:** Vector Embeddings Complete - NLP Integration Next  
**Last Updated:** 2025-07-07  
**Version:** 1.1.0

## Project Overview

This project migrates a climate risk document processing system from a proof-of-concept to production AWS infrastructure. The system processes climate risk documents through a multi-stage pipeline including text extraction, chunking, vector embeddings, and NLP analysis to enable intelligent document retrieval and analysis.

## Current System Status

### ✅ Completed Components
- **Text Extraction Pipeline** - Amazon Textract integration
- **Text Chunking Pipeline** - Structured chunking with metadata  
- **Vector Embeddings Pipeline** - Amazon Bedrock Titan integration
- **Database Integration** - PostgreSQL with complete schema
- **OpenSearch Integration** - VECTORSEARCH collection operational
- **CDK Infrastructure** - Automated deployment ready

### 🔄 In Progress
- **NLP Integration** - Entity detection and key phrase extraction

### 📋 Planned
- **Search API** - Vector and hybrid search capabilities
- **Knowledge Graph** - Entity relationship mapping
- **Analytics Dashboard** - Processing metrics and insights

## Architecture

The system uses an event-driven architecture with AWS Lambda functions processing documents through multiple stages:

```
S3 Upload → Textract → Text Chunker → Vector Embeddings → OpenSearch
     ↓           ↓            ↓              ↓              ↓
  Database   Database    Database      Database      Search Index
```

## Key Technologies

- **AWS Services:** Lambda, Textract, Bedrock, OpenSearch Serverless, RDS PostgreSQL
- **Infrastructure:** AWS CDK (Python)
- **Processing:** Event-driven with SNS/SQS messaging
- **Storage:** S3 for documents and intermediate results
- **Search:** Vector embeddings with semantic search

## Performance Metrics

- **Vector Processing:** 4.6 seconds per document (19 chunks)
- **Cost per Document:** $0.002187 (vector embeddings)
- **Success Rate:** 100% in testing
- **Daily Capacity:** 1,000+ documents

## Documentation Structure

- **`docs/status/`** - Project status and progress tracking
- **`docs/architecture/`** - System architecture and design
- **`docs/integration/`** - Component integration plans
- **`docs/deployment/`** - Deployment guides and procedures
- **`docs/implementation/`** - Component implementation details

## Quick Start

### Prerequisites
- AWS CLI configured with appropriate permissions
- Python 3.11+
- AWS CDK installed
- PostgreSQL access

### Deployment
```bash
# Deploy infrastructure
cd cdk
cdk deploy vector-embeddings-pipeline --profile solve-global

# Test the pipeline
python3 test_vector_embeddings_integration.py
```

## Cost Management

The system includes comprehensive cost monitoring:
- **Textract:** ~$1.50 per 1000 pages
- **Bedrock Titan:** ~$0.002 per document
- **OpenSearch Serverless:** ~$350/month base cost
- **Total Operational:** <$500/month for 1000 docs/day

## Development Workflow

This project uses milestone-based development with Git tagging:
- `v1.0.0` - Initial migration complete
- `v1.1.0` - Vector embeddings production ready
- `v1.2.0` - NLP integration (in progress)

## Support

For questions or issues, refer to the comprehensive documentation in the `docs/` folder, particularly:
- `docs/status/PROJECT_CONTEXT_SUMMARY_*.md` for current status
- `docs/architecture/SYSTEM_ARCHITECTURE_*.md` for technical details
- `docs/deployment/COMPLETE_CDK_DEPLOYMENT_GUIDE.md` for setup

---

**Project Lead:** Climate Risk Analysis Team  
**Infrastructure:** AWS us-east-1  
**Repository:** Private (contains AWS account details)
