# Climate Risk RAG System - Project Context Summary
## Date: 2025-07-05T00:15:00Z

## 🎯 **Project Overview**

Climate Risk RAG (Retrieval-Augmented Generation) system built on AWS serverless architecture for processing and analyzing climate risk documents. The system uses a microservices approach with document processing pipeline, vector search, knowledge graph, and AI-powered query handling.

## 📁 **Project Structure**

### **Root Directory**: `/Users/chris/climate-risk-rag-aws/`

### **Key Directories**
- **`cdk/`**: AWS CDK infrastructure as code
  - `app.py`: Main CDK application
  - `stacks/`: Individual stack definitions
  - `cdk.out/`: Generated CloudFormation templates
- **`lambda/`**: Lambda function source code (17 functions)
  - `text_extractor_processor/`: Document text extraction (recently corrected)
  - `text_extractor_initiator/`: Textract job initiation
  - `text_chunker/`: Smart text chunking with structure awareness
  - `document_processor/`, `embedding_generator/`, `ner_processor/`, etc.
- **`layers/`**: Lambda layers for shared dependencies
  - `app-source/utils/`: DocumentIDManager, DatabaseManager utilities
  - `build/textextractor-layer/`: Built layer with dependencies
- **`docs/`**: Project documentation and context summaries
- **`database/`**: Database schema files
- **`backups/`**: Deployment backups and archives

## 🏗️ **Architecture Overview**

### **Data Processing Pipeline**
1. **Document Ingestion**: S3 bucket (`solve-global-kr-documents-861276078413-us-east-1`)
2. **Text Extraction**: Textract async processing with DocumentIDManager integration
3. **Text Chunking**: Smart chunking with structure awareness
4. **Embedding Generation**: Vector embeddings for semantic search
5. **NER Processing**: Named entity recognition and extraction
6. **Knowledge Graph**: Relationship mining and graph construction
7. **Vector Storage**: OpenSearch for semantic search
8. **Query Processing**: RAG-based query handling with AI responses

### **AWS Services Used**
- **Compute**: Lambda functions (Python 3.11)
- **Storage**: S3 buckets for data lake architecture
- **Database**: PostgreSQL (RDS), OpenSearch, Neptune
- **AI/ML**: Textract, Comprehend, Bedrock (Titan embeddings)
- **Messaging**: SNS/SQS for async processing
- **Networking**: VPC with isolated subnets for security

## 🔧 **Recent Major Work Completed**

### **DocumentIDManager Integration (Critical Fix)**
**Problem**: TextExtractor was using simple filename-based doc_ids instead of proper GUID-based DocumentIDManager system.

**Solution Implemented**:
- **Selective Migration**: Migrated 1,000 POC documents from SQLite to PostgreSQL
- **Corrected TextExtractor**: Integrated with DocumentIDManager properly
- **S3 Mappings**: Created lookup system for existing POC documents
- **Deployment**: Successfully deployed corrected processor

**Status**: ✅ **COMPLETE** - TextExtractor now properly integrated with DocumentIDManager

### **Key Files Modified/Created**:
- `migrate_poc_selective.py`: Selective migration utility (1,000 docs)
- `lambda/text_extractor_processor/text_extractor_processor_CORRECTED.py`: Fixed processor
- `selective_poc_s3_mappings.json`: S3 key → doc_id mappings
- Multiple test and deployment scripts

## 📊 **Current System State**

### **Document Processing Status**
- **POC Documents**: 1,000 documents migrated and integrated
- **S3 Storage**: Documents in `solve-global-kr-documents-861276078413-us-east-1`
- **Text Output**: New bucket `solve-global-kr-text-new-861276078413-us-east-1`
- **DocumentIDManager**: Fully operational with PostgreSQL backend

### **Lambda Functions Status**
- **TextExtractor Processor**: ✅ Deployed with DocumentIDManager integration
- **TextExtractor Initiator**: ✅ Active
- **Text Chunker**: ⏸️ **NEXT PRIORITY** - Needs attention after DocumentID work
- **Other Processors**: Available but may need DocumentIDManager integration

### **Database Systems**
- **PostgreSQL**: DocumentIDManager tables + TextExtractor job tracking
- **OpenSearch**: Available for vector storage
- **Neptune**: Available for knowledge graph

## 💰 **Cost Management Guidelines**

### **⚠️ CRITICAL: Expense Control**

#### **Textract Usage**
- **Current Status**: Near free tier limit
- **Cost**: ~$0.65 per page processed
- **Strategy**: Use small test documents (2-3 pages max)
- **Testing**: Reuse existing extractions when possible

#### **Comprehend Usage** (Future)
- **Cost**: Per entity/sentiment analysis call
- **Strategy**: Batch processing, limit test runs
- **Monitoring**: Track usage carefully during development

#### **Bedrock/Titan Embeddings** (Future)
- **Cost**: Per token processed for embeddings
- **Strategy**: Efficient chunking, avoid redundant processing
- **Testing**: Use small document subsets

#### **General Cost Controls**
- **Lambda**: Monitor execution time and memory usage
- **S3**: Lifecycle policies for temporary data
- **RDS**: Right-size instances, monitor connections
- **Data Transfer**: Minimize cross-region transfers

### **Testing Best Practices**
1. **Start Small**: Use 1-2 page documents for initial tests
2. **Reuse Data**: Leverage existing processed documents
3. **Monitor Costs**: Check AWS billing regularly
4. **Batch Operations**: Group similar operations together
5. **Clean Up**: Remove test data after validation

## 📚 **Key Reference Documents**

### **Recent Work Summaries**
- `NEXT_STEPS_2025-07-04T20-07-00Z.md`: Original directory structure planning
- `NEXT_STEPS_2025-07-04T21-00-00Z.md`: DocumentIDManager integration strategy
- `SELECTIVE_MIGRATION_COMPLETE_2025-07-04T21-20-00Z.md`: Migration implementation
- `CORRECTED_TEXTEXTRACTOR_COMPLETE_2025-07-04T23-25-00Z.md`: Processor correction
- `DEPLOYMENT_COMPLETE_2025-07-05T00-05-00Z.md`: Deployment summary

### **Technical Documentation**
- `layers/DEPLOYMENT_GUIDE.md`: Layer management and deployment
- `database/textextractor_schema.sql`: TextExtractor database schema
- `layers/app-source/utils/schema/postgresql_schema.sql`: DocumentIDManager schema

### **Configuration Files**
- `cdk/stacks/textextractor_lambda_stack_complete.py`: Complete Lambda stack
- `selective_poc_s3_mappings.json`: POC document mappings (1,000 entries)

## 🔄 **Current Integration Status**

### **Working Systems**
- ✅ **Document Upload**: S3 triggers working
- ✅ **Text Extraction**: Textract integration with DocumentIDManager
- ✅ **Database**: PostgreSQL with DocumentIDManager operational
- ✅ **Messaging**: SNS/SQS async processing

### **Next Priority Systems**
- 🔄 **Text Chunking**: Smart chunker needs testing with new doc_id format
- ⏳ **Embedding Generation**: Awaiting chunking completion
- ⏳ **NER Processing**: Awaiting text processing pipeline
- ⏳ **Knowledge Graph**: Awaiting entity extraction

## 🧪 **Testing Infrastructure**

### **Available Test Scripts**
- `test_corrected_textextractor.py`: Processor validation
- `test_deployed_textextractor.py`: Deployment verification
- `test_migration_utility.py`: Migration validation
- `migrate_poc_selective.py`: Data migration utility

### **Test Data**
- **POC Documents**: 1,000 World Bank climate documents
- **S3 Bucket**: Documents ready for processing
- **Sample Documents**: Small files for cost-effective testing

## 🔐 **Security & Access**

### **AWS Configuration**
- **Profile**: `solve-global` (configured)
- **Region**: `us-east-1` (primary)
- **Account**: `861276078413`

### **Database Access**
- **PostgreSQL**: RDS instance with proper credentials
- **Connection**: Via VPC isolated subnets
- **Security**: Lambda functions have required IAM roles

## 🎯 **Success Metrics**

### **Completed Milestones**
- ✅ DocumentIDManager integration working
- ✅ 1,000 POC documents migrated successfully
- ✅ TextExtractor using proper GUID-based doc_ids
- ✅ S3 directory structure consistent
- ✅ Database systems integrated

### **Current Capabilities**
- Process documents with proper doc_id management
- Maintain data consistency across systems
- Support both POC and new documents
- Cost-effective testing with existing data

## 🚀 **Immediate Next Steps**

1. **Text Chunker Integration**: Test with new doc_id message format
2. **End-to-End Validation**: Complete document → chunks → embeddings flow
3. **Cost Monitoring**: Implement usage tracking for expensive services
4. **Pipeline Optimization**: Improve processing efficiency

## 📞 **Key Contacts & Resources**

### **Development Environment**
- **Local Path**: `/Users/chris/climate-risk-rag-aws/`
- **AWS Profile**: `solve-global`
- **Primary Region**: `us-east-1`

### **Critical Dependencies**
- **DocumentIDManager**: Core system for document identification
- **PostgreSQL**: Primary database for metadata and job tracking
- **S3 Buckets**: Data lake storage for all processing stages
- **Lambda Layers**: Shared utilities and dependencies

---

**Status**: 🎯 **DOCUMENTID INTEGRATION COMPLETE - READY FOR TEXT CHUNKING**  
**Next Priority**: Text chunker integration and testing  
**Cost Status**: Monitoring required for Textract and future AI services  
**Architecture**: Solid foundation with proper document ID management
