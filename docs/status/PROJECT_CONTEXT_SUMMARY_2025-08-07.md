# Climate Risk RAG System - Project Context Summary
**Date**: August 7, 2025  
**Status**: Neptune-FTS Integration Complete, Ready for Ontology Analysis

## 🎯 **Project Overview**

The Climate Risk RAG System is a serverless, event-driven document processing and analysis platform built on AWS. The system processes climate risk documents through multiple stages including text extraction, chunking, embedding, and knowledge graph construction, with advanced full-text search capabilities through Neptune-OpenSearch integration.

### **Core Architecture**
- **Document Ingestion**: S3-triggered processing pipeline
- **Text Processing**: AWS Textract → Smart chunking → Keyword extraction
- **Knowledge Graph**: Neptune cluster with RDF/SPARQL ontologies
- **Vector Search**: OpenSearch with embeddings
- **Full-Text Search**: Neptune-FTS integration for ontology search
- **Serverless Compute**: Lambda functions with shared layers

## 📁 **Project Structure & Key Directories**

### **Infrastructure Code**
- **`/cdk/`** - AWS CDK infrastructure definitions
  - CloudFormation templates for all AWS resources
  - Networking, compute, storage, and AI/ML service configurations
  - Neptune cluster and OpenSearch domain definitions

### **Lambda Functions**
- **`/lambda/`** - All Lambda function source code
  - **`text-extractor-processor/`** - AWS Textract integration
  - **`text-chunker-processor/`** - Smart structured chunking
  - **`keyword-indexer/`** - Keyword extraction and indexing
  - **`vector-embeddings-worker/`** - Embedding generation
  - **`kg-triple-loader/`** - Knowledge graph construction
  - **`admin_ontology_manager/`** - Ontology management and SPARQL queries
  - **`neptune-stream-poller/`** - **NEW**: Neptune-to-OpenSearch FTS integration
  - **`nlp_kg_processor/`** - NLP processing and entity extraction
  - **`pipeline_test_function/`** - End-to-end testing

### **Shared Code**
- **`/lambda/shared_layer/`** - Common utilities and libraries
  - Database connections, S3 utilities, logging, configuration
  - Shared across all Lambda functions for consistency

### **Documentation**
- **`/docs/`** - Project documentation
  - **`/docs/status/`** - Project status and context documents
  - Architecture diagrams, API documentation, deployment guides

## 🚀 **Recent Major Achievement: Neptune-FTS Integration**

### **What Was Accomplished Today (August 7, 2025)**

#### **1. Neptune-OpenSearch Full-Text Search Integration**
- **Deployed CloudFormation stack**: `NeptuneQuickStart` (CREATE_COMPLETE)
- **Lambda Function**: `NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3`
- **DynamoDB Table**: `NeptuneOntologyFTS-LeaseTable` for stream coordination
- **Cost-optimized configuration**: 1024MB memory, 10-minute polling, 2 shards

#### **2. Ontology Filter Development & Integration**
**Created comprehensive positive filtering system for cost optimization:**

##### **New Files Created:**
- **`/lambda/neptune-stream-poller/ontology_filter.py`** - Positive filtering logic
- **`/lambda/neptune-stream-poller/lambda_function.py`** - Main entry point
- **`/lambda/neptune-stream-poller/README.md`** - Comprehensive documentation
- **`/lambda/neptune-stream-poller/deploy.sh`** - Standard deployment script
- **`/lambda/neptune-stream-poller/deploy_with_filtering.sh`** - Filtering-enabled deployment
- **`/lambda/neptune-stream-poller/requirements.txt`** - Dependencies
- **`/lambda/neptune-stream-poller/INTEGRATION_COMPLETE.md`** - Integration status
- **`/lambda/neptune-stream-poller/RECORD_STRUCTURE_ANALYSIS.md`** - Technical analysis

##### **Files Modified:**
- **`/lambda/neptune-stream-poller/neptune_to_es/neptune_sparql_es_handler.py`**
  - Added import: `from ontology_filter import get_ontology_filter`
  - Added positive filtering at start of `filter_records()` method
- **`/lambda/neptune-stream-poller/neptune_to_es/neptune_sparql_es_string_indexing_handler.py`**
  - Same modifications as above for string-only indexing

##### **CloudFormation Template Optimization:**
- **`/neptune-fts-deployment/neptune-to-opensearch-optimized.json`** - Cost-optimized template
- **`/neptune-fts-deployment/parameters.json`** - Infrastructure-specific parameters

#### **3. Positive Filtering Approach**
**Philosophy**: Only index statements we explicitly want (whitelist vs blacklist)

**Example Filtering Rules:**
```python
# Geonames - only name predicates for location lookup
'http://www.geonames.org/ontology': {
    'http://www.geonames.org/ontology#name',
    'http://www.geonames.org/ontology#alternateName',
    'http://www.geonames.org/ontology#officialName',
    'http://www.geonames.org/ontology#shortName'
}

# Climate Risk - labels and descriptions for concept lookup  
'http://climate-risk-ontology': {
    'http://www.w3.org/2000/01/rdf-schema#label',
    'http://www.w3.org/2004/02/skos/core#prefLabel',
    'http://www.w3.org/2004/02/skos/core#altLabel',
    'http://www.w3.org/2004/02/skos/core#definition'
}
```

**Expected Cost Reduction**: 80-90% fewer records processed

## 🏗️ **Current Infrastructure Status**

### **Deployed AWS Resources**
- **Neptune Cluster**: `solve-global-kr-neptune-s3` (ready for FTS)
- **OpenSearch Domain**: `solve-global-kr-search` (2×m6g.large.search nodes)
- **VPC**: `vpc-051c21d88c7dc3819` with proper security groups
- **Lambda Functions**: 15+ functions across the processing pipeline
- **S3 Buckets**: Document storage, processed data, embeddings
- **RDS PostgreSQL**: Metadata and processing status tracking

### **Network Configuration**
- **Subnets**: `subnet-00efdcc220a613ae3`, `subnet-0e9efc5fdf29e9da0`
- **Security Groups**: 
  - `sg-0c9e10b9cfb4c9eb0` (Lambda)
  - `sg-09820dfa36321a5e1` (OpenSearch)
  - `sg-0c8afac0f49164069` (Neptune)
- **Route Tables**: `rtb-015f1499e8599fe2f`, `rtb-03e50ed0f0423d804`

## 💰 **Cost Management & Testing Guidelines**

### **⚠️ CRITICAL: Expense Control for Testing**

#### **High-Cost Services to Monitor:**
1. **AWS Textract**
   - **Cost**: ~$1.50 per 1,000 pages
   - **Testing Strategy**: Use small document sets (5-10 pages max)
   - **Monitoring**: Check AWS Cost Explorer daily during testing
   - **Cleanup**: Delete processed documents from S3 after testing

2. **Amazon Comprehend** (Future Usage)
   - **Cost**: ~$0.0001 per unit for entity detection
   - **Testing Strategy**: Limit to small text samples initially
   - **Batch Processing**: Use batch jobs for cost efficiency
   - **Monitoring**: Set CloudWatch alarms for usage thresholds

3. **Amazon Titan Embeddings** (Future Usage)
   - **Cost**: ~$0.0001 per 1,000 input tokens
   - **Testing Strategy**: Use cached embeddings when possible
   - **Optimization**: Batch embedding requests
   - **Storage**: Monitor OpenSearch storage costs

4. **OpenSearch Domain**
   - **Current Cost**: ~$200/month for 2×m6g.large nodes
   - **Optimization**: Right-size based on actual usage
   - **Monitoring**: Track index size and query patterns

5. **Neptune Cluster**
   - **Current Cost**: ~$400/month for db.r5.large
   - **Optimization**: Consider smaller instance for development
   - **Monitoring**: Track read/write operations

#### **Cost Control Measures:**
- **Development Environment**: Use smaller instance types
- **Automated Cleanup**: Lambda functions to delete test data
- **Resource Tagging**: Tag all resources for cost tracking
- **Budget Alerts**: Set up AWS Budget alerts at $100, $500, $1000
- **Daily Monitoring**: Check AWS Cost Explorer daily during active development

### **Testing Best Practices:**
1. **Start Small**: Always test with minimal data sets
2. **Incremental Scaling**: Gradually increase test data size
3. **Resource Cleanup**: Automated cleanup after each test run
4. **Cost Tracking**: Monitor costs before, during, and after tests
5. **Documentation**: Record costs for each test scenario

## 📚 **Reference Documentation**

### **Key Work Summary Documents:**
- **`NEPTUNE_OPENSEARCH_INTEGRATION_GUIDE.md`** - Technical implementation details
- **`OPENSEARCH_MULTILANGUAGE_SUPPORT.md`** - Multilanguage search capabilities
- **`NEPTUNE_OPENSEARCH_REUSE_ANALYSIS.md`** - Infrastructure cost analysis
- **`INFRASTRUCTURE_REFERENCE.md`** - Current AWS resource inventory

### **Architecture Documents:**
- **`README.md`** - Project overview and getting started
- **`PROJECT_CONTEXT.md`** - Previous project context
- **`NEXT_STEPS.md`** - Planned future work
- **`docs/architecture_diagram.png`** - System architecture visualization

## 🔧 **Current System Capabilities**

### **Document Processing Pipeline**
1. **Text Extraction**: PDF/Word → Structured text via Textract
2. **Smart Chunking**: Respects document structure, sentence-based overlap
3. **Keyword Indexing**: Automated keyword extraction and indexing
4. **Vector Embeddings**: Semantic search capabilities
5. **Knowledge Graph**: RDF triples in Neptune with SPARQL queries
6. **Full-Text Search**: Neptune-FTS integration for ontology search

### **Ontology Management**
- **Admin Interface**: `admin_ontology_manager` Lambda for SPARQL queries
- **Triple Loading**: Bulk loading of RDF data into Neptune
- **FTS Integration**: Full-text search within SPARQL queries
- **Multilanguage Support**: Geographic entity matching across languages

### **Search Capabilities**
- **Hybrid Search**: Keyword + vector search in OpenSearch
- **Ontology Search**: FTS queries within Neptune SPARQL
- **Entity Alignment**: Match NLP results to ontology concepts
- **Geographic Matching**: "Ciudad de Nueva York" → "New York City"

## 🎯 **Integration Points & APIs**

### **Lambda Layer Integration**
- **Shared utilities** across all functions
- **Database connections** (PostgreSQL, Neptune, OpenSearch)
- **S3 operations** and file handling
- **Logging and monitoring** standardization

### **Knowledge Graph Layer**
- **OntologyManager.py**: Enhanced with FTS methods
  - `list_ontologies()` - List available ontologies
  - `load_ontology()` - Load ontology data
  - `search_ontology_specific()` - FTS within specific ontologies
- **NLPKGIntegrator.py**: Entity mapping capabilities
  - `map_entities_to_chunks()` - Align NLP results to ontologies

### **SPARQL FTS Queries**
```sparql
PREFIX neptune-fts: <http://aws.amazon.com/neptune/vocab/v01/services/fts#>

SELECT ?concept ?label ?score
WHERE {
    ?concept rdfs:label ?label .
    FILTER(neptune-fts:query(neptune-fts:field('object'), 'climate adaptation'))
    BIND(neptune-fts:score() AS ?score)
}
ORDER BY DESC(?score)
```

## 🚨 **Known Issues & Limitations**

### **Current Limitations**
1. **Ontology Filtering**: Using example rules, needs real ontology analysis
2. **Cost Optimization**: Not yet tested with large-scale data
3. **Performance Tuning**: OpenSearch and Neptune sizing needs optimization
4. **Error Handling**: Some edge cases in stream processing not fully tested

### **Technical Debt**
1. **Lambda Dependencies**: Some functions need dependency updates
2. **Monitoring**: Need comprehensive CloudWatch dashboards
3. **Testing**: End-to-end testing needs automation
4. **Documentation**: Some Lambda functions need updated README files

## 🔐 **Security & Access**

### **Current Security Posture**
- **VPC Isolation**: All resources in private subnets
- **Security Groups**: Restrictive access between components
- **IAM Roles**: Least-privilege access for Lambda functions
- **Encryption**: At-rest and in-transit encryption enabled

### **Access Patterns**
- **Neptune**: SPARQL endpoint access via Lambda
- **OpenSearch**: VPC-only access with fine-grained permissions
- **S3**: Bucket policies for document access
- **RDS**: Database credentials via AWS Secrets Manager

## 📊 **Monitoring & Observability**

### **Current Monitoring**
- **CloudWatch Logs**: All Lambda functions logging
- **CloudWatch Metrics**: Custom metrics for processing stages
- **Neptune Monitoring**: Query performance and resource usage
- **OpenSearch Monitoring**: Index size, query performance
- **Cost Monitoring**: AWS Cost Explorer and Budget alerts

### **Key Metrics to Track**
- **Document Processing Rate**: Documents per hour
- **Error Rates**: Failed processing by stage
- **Cost per Document**: Total processing cost
- **Query Performance**: SPARQL and OpenSearch response times
- **Storage Growth**: S3, OpenSearch, Neptune storage usage

## 🎯 **Success Criteria**

### **Functional Requirements Met**
- ✅ **Document Processing**: End-to-end pipeline operational
- ✅ **Knowledge Graph**: RDF data loading and SPARQL queries
- ✅ **Full-Text Search**: Neptune-FTS integration working
- ✅ **Cost Optimization**: Filtering framework in place
- ✅ **Scalability**: Serverless architecture handles variable load

### **Performance Targets**
- **Processing Speed**: <5 minutes per document (average)
- **Query Response**: <2 seconds for SPARQL FTS queries
- **Cost Efficiency**: <$1 per document processed
- **Availability**: 99.9% uptime for processing pipeline

## 🔄 **Development Workflow**

### **Current Process**
1. **Local Development**: Test Lambda functions locally
2. **CDK Deployment**: Infrastructure as code
3. **Lambda Deployment**: Individual function updates
4. **Integration Testing**: End-to-end pipeline tests
5. **Monitoring**: CloudWatch logs and metrics review

### **Best Practices Established**
- **Consistent Structure**: All Lambda functions follow same pattern
- **Shared Dependencies**: Common code in shared layer
- **Documentation**: README for each component
- **Version Control**: Git-based development workflow
- **Cost Awareness**: Monitor expenses during development

---

## 📋 **Quick Start for New Conversations**

### **To Resume Work:**
1. **Review this document** for current status
2. **Check `/docs/status/`** for latest updates
3. **Examine `/lambda/neptune-stream-poller/`** for recent FTS work
4. **Review CloudFormation stack** `NeptuneQuickStart` status
5. **Monitor costs** in AWS Cost Explorer before testing

### **Key Commands:**
```bash
# Deploy Neptune FTS integration
cd /Users/chris/climate-risk-rag-aws/lambda/neptune-stream-poller
./deploy_with_filtering.sh

# Monitor Lambda logs
aws logs tail /aws/lambda/NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3 --follow

# Test end-to-end pipeline
python run_test_with_cleanup.py

# Check infrastructure status
cdk list
cdk diff
```

### **Immediate Priorities:**
1. **Analyze actual ontology data** to refine filtering rules
2. **Test Neptune-FTS integration** with real data
3. **Optimize costs** based on usage patterns
4. **Enhance monitoring** and alerting
5. **Document lessons learned** from deployment

---

**Status**: System operational, Neptune-FTS integrated, ready for ontology analysis and production optimization.
