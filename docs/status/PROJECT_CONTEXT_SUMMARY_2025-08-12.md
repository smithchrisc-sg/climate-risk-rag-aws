# PROJECT CONTEXT SUMMARY - August 12, 2025

## 🎯 **CURRENT PROJECT STATE**

### **System Overview**
The Climate Risk RAG system is a serverless event-driven architecture on AWS that processes climate risk documents through multiple stages: text extraction, chunking, NLP processing, knowledge graph construction, and vector embeddings. The system uses a data lake structure in S3 with Lambda functions connected via SNS messaging.

### **Recent Major Achievement**
Successfully deployed **Neptune Stream Poller with enhanced multi-ontology filtering** for both geonames and climate risk ontologies. The system now has:
- Layer version 8 with contextual filtering capabilities
- Feature flags: `ENABLE_GEONAMES_FILTERING=true`, `ENABLE_CLIMATE_RISK_FILTERING=true`
- Enhanced filtering functionality confirmed working with climate risk concepts properly indexed

## 🏗️ **CURRENT ARCHITECTURE STATUS**

### **Working Components**
- **Text Extraction Pipeline**: Textract-based document processing
- **Text Chunking**: Smart structured chunking with sentence-based overlap
- **NLP Processing**: Amazon Comprehend entity extraction with chunk alignment
- **Knowledge Graph**: Neptune with geonames and climate risk ontologies loaded
- **Vector Embeddings**: OpenSearch integration for semantic search
- **Neptune Stream Poller**: Enhanced with multi-ontology filtering (v8)

### **Key Infrastructure**
- **CDK Deployment**: `cdk/app_production_ready_fixed.py`
- **Lambda Functions**: 20+ functions in `lambda/` directory
- **Lambda Layers**: `layers/` with database-layer, knowledge-graph-layer, etc.
- **Neptune Cluster**: With FTS enabled, geonames and climate risk ontologies loaded
- **OpenSearch**: Vector embeddings and full-text search capabilities

## 🎯 **CURRENT FOCUS: ENHANCED ENTITY ALIGNMENT**

### **Problem Statement**
Current EntityAligner uses basic fuzzy matching, leading to poor disambiguation of ambiguous entities like "Paris" (could be Paris, France or Paris, Texas depending on context).

### **Solution Design**
Comprehensive **Contextual Entity Alignment** approach documented in:
`/Users/chris/climate-risk-rag-aws/docs/knowledge-graph/ENTITIY_ALIGNMENT_APPROACH_2025-08-12.md`

**Key Features**:
- **Multi-Level Context**: Document title, chunk co-occurrence, semantic signals
- **FTS-Enhanced SPARQL**: Contextual queries against Neptune ontologies
- **Extensible Ontology Framework**: Easy addition of new ontologies
- **Context Scoring**: Regional, co-occurrence, and semantic context weighting

### **Implementation Target**
**nlp_kg_processor Lambda** (`lambda/nlp_kg_processor/`) - processes NLP results and creates knowledge graph triples using enhanced EntityAligner from knowledge-graph-layer.

**Updated Architecture**: 
`/Users/chris/climate-risk-rag-aws/lambda/nlp_kg_processor/UPDATED_ARCHITECTURE_WALKTHROUGH.md`

**Key Architectural Decisions**:
- Single document processing (not batches)
- Pre-aligned entities from nlp-worker (no re-alignment needed)
- Efficient URI caching with chunk similarity
- Entity filtering strategy (drop unaligned entities)
- Future organizational ontology for ORG entities

## 📁 **KEY WORKING DIRECTORIES**

### **Infrastructure & Deployment**
- **`cdk/`**: AWS CDK infrastructure code
  - `app_production_ready_fixed.py`: Main CDK application
  - Complete infrastructure definitions for all services

### **Lambda Functions**
- **`lambda/nlp_kg_processor/`**: Target for entity alignment enhancement
- **`lambda/neptune-stream-poller/`**: Recently enhanced with multi-ontology filtering
- **`lambda/nlp-worker/`**: Provides pre-aligned entities to nlp_kg_processor
- **`lambda/text-chunker-processor/`**: Smart structured chunking
- **`lambda/vector-embeddings-worker/`**: OpenSearch integration
- **20+ other Lambda functions**: Complete processing pipeline

### **Lambda Layers**
- **`layers/knowledge-graph-layer/`**: Contains EntityAligner and KG utilities
  - `python/utils/EntityAligner.py`: Current fuzzy matching implementation
  - Target for contextual enhancement implementation
- **`layers/database-layer/`**: Database utilities and managers
- **Other layers**: Shared utilities across Lambda functions

### **Documentation**
- **`docs/knowledge-graph/`**: Entity alignment design documents
- **`docs/infrastructure/`**: Infrastructure reference guides
- **`docs/status/`**: Project context and progress summaries
- **`docs/testing/`**: Testing strategies and guidelines

## 🧪 **TESTING STRATEGY & COST MANAGEMENT**

### **🚨 CRITICAL: Cost Control Measures**

**High-Cost Services to Monitor**:
- **Textract**: ~$1.50/1000 pages - Use existing processed documents when possible
- **Comprehend**: ~$0.019/document - Limit test document sets to 5-10 documents max
- **Bedrock/Titan**: ~$0.002/document for embeddings - Monitor usage carefully
- **Neptune**: Query costs can accumulate with FTS searches

**Cost Control Strategies**:
1. **Use Existing Data**: Test with already-processed documents in S3 data lake
2. **Limited Test Sets**: Maximum 5-10 documents for validation
3. **Mock Testing First**: Unit tests with mock data before real service integration
4. **Pipeline Testing**: Use `invoke_pipeline_test.py --num-documents 3 --force`
5. **Monitor AWS Costs**: Check billing dashboard regularly during development

### **Testing Approach**
- **Unit Testing**: Mock data for logic validation (no AWS costs)
- **Integration Testing**: Limited real data sets (controlled costs)
- **End-to-End Testing**: `invoke_pipeline_test.py` with minimal document count
- **Performance Testing**: Monitor query times and resource usage

## 📚 **REFERENCE DOCUMENTS**

### **Architecture & Design**
- **`CURRENT_STATE_ARCHITECTURE_2025-08-11.md`**: Complete system architecture
- **`docs/infrastructure/INFRASTRUCTURE_REFERENCE.md`**: Infrastructure mappings
- **`docs/infrastructure/MESSAGING_ALIGNMENT_SUMMARY.md`**: SNS topic patterns

### **Recent Work Summaries**
- **Neptune Stream Poller Enhancement**: Multi-ontology filtering deployment
- **Entity Alignment Design**: Contextual FTS-enhanced SPARQL approach
- **nlp_kg_processor Architecture**: Updated efficient processing flow

### **Testing & Development**
- **`docs/testing/LOCATION_ENTITY_ALIGNMENT_TEST_PLAN.md`**: Focused testing strategy
- **Architectural Discipline Checklist**: Development guidelines and risk mitigation

## 🔧 **DEVELOPMENT ENVIRONMENT**

### **Requirements**
- **Python 3.11+**: Required for Lambda functions
- **AWS CLI**: Configured with appropriate permissions
- **CDK**: For infrastructure deployment
- **Git**: Version control with clean commit history

### **Key Environment Variables**
- **Neptune Endpoint**: For knowledge graph queries
- **OpenSearch Endpoint**: For vector similarity and FTS
- **S3 Buckets**: Data lake structure for document processing
- **SNS Topics**: Pipeline messaging between Lambda functions

## 🎯 **IMMEDIATE PRIORITIES**

### **1. Location Entity Disambiguation**
Focus on LOCATION/GPE entities using geonames ontology with contextual FTS-enhanced SPARQL queries.

### **2. Enhanced EntityAligner Implementation**
Upgrade existing EntityAligner in knowledge-graph-layer with:
- Document context extraction
- Chunk co-occurrence analysis
- FTS-enhanced SPARQL queries
- Context-based confidence scoring

### **3. Efficient Processing Architecture**
Implement URI caching with chunk similarity to avoid redundant disambiguation of same entities across similar chunks.

## 🚨 **CRITICAL SUCCESS FACTORS**

### **Architectural Discipline**
- **Conservative Approach**: One change at a time, thorough testing
- **Layer Management**: Use standard build/deploy processes
- **Cost Control**: Monitor AWS service usage carefully
- **Version Control**: Clean git commits for rollback capability

### **Quality Assurance**
- **Disambiguation Accuracy**: >90% correct for ambiguous location names
- **Performance**: <2s additional processing time per document
- **No Regression**: Existing functionality must continue working
- **Cost Efficiency**: Minimal increase in processing costs

## 📋 **KNOWN ISSUES & CONSIDERATIONS**

### **Entity Types Strategy**
- **LOCATION/GPE**: Target for contextual disambiguation (geonames)
- **ORG**: Future organizational ontology needed
- **OTHER**: Climate risk concepts (existing ontology)
- **PERSON**: Drop (too complex to disambiguate meaningfully)

### **Future Ontology Development**
Organizational ontology needed for:
- Government agencies (health departments, environmental agencies)
- Climate finance organizations (World Bank, development funds)
- Insurance/risk organizations (SEADRIF, GAIP)
- International organizations (UN agencies, IPCC)

### **Performance Considerations**
- Chunk similarity calculations using OpenSearch KNN
- FTS query performance in Neptune
- Cache management for large documents
- Memory usage optimization

This context summary provides complete information for resuming development work on the enhanced entity alignment system while maintaining cost control and architectural discipline.
