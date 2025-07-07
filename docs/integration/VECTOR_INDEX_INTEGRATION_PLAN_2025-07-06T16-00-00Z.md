# Vector Index Porting and Integration Plan
**Generated:** 2025-07-06T16:00:00Z  
**Phase:** Vector Index Implementation (Phase 2A)  
**Status:** Ready for Implementation

## 🎯 **Executive Summary**

This plan ports the POC's Qdrant-based vector indexing system to AWS using OpenSearch Serverless with Amazon Titan embeddings, integrating seamlessly with the existing async keyword indexing architecture while maintaining cost efficiency and leveraging existing abstractions.

## 📊 **POC Analysis - What We're Porting**

### **Existing POC Components**
1. **QdrantIndexer.py**: Vector storage and similarity search with metadata filtering
2. **EmbeddingsManager.py**: Sentence-transformers embeddings with batch processing
3. **OpenSearchIndexer.py**: Hybrid search capabilities (partial implementation)

### **Key POC Features to Preserve**
- **Batch Processing**: Efficient embedding generation in configurable batches
- **Metadata Integration**: Rich document metadata for enhanced search
- **Error Handling**: Comprehensive retry logic and provenance tracking
- **Composite Scoring**: Similarity + metadata confidence + structural quality
- **Structured Storage**: Document-organized embedding storage

### **POC Code Analysis Summary**
```python
# From QdrantIndexer.py - Key patterns to preserve:
- UUID-based chunk identification
- Enhanced payload schema with metadata
- Composite scoring algorithm
- Batch processing with retry logic
- Structural quality assessment

# From EmbeddingsManager.py - Key patterns to preserve:
- Batch embedding creation (configurable batch_size)
- S3-based embedding storage with directory structure
- DocumentIDManager integration
- ProvenanceTracker integration
- Comprehensive error handling
```

## 🏗️ **AWS Integration Architecture**

### **Target Architecture**
```
Text Chunker → SNS (chunks-ready) → Vector Embeddings Processor
                                           ↓
                                    Amazon Titan Embeddings
                                           ↓
                                    OpenSearch Vector Index
                                           ↓
                                    Enhanced Hybrid Search
```

### **Lambda Function Structure**
```
lambda/
├── vector_embeddings_processor/     # NEW - Initiator (async pattern)
│   ├── vector_embeddings_processor.py
│   └── requirements.txt
├── vector_embeddings_worker/        # NEW - Background worker
│   ├── vector_embeddings_worker.py
│   ├── titan_embeddings_manager.py  # Ported from EmbeddingsManager
│   ├── opensearch_vector_indexer.py # Ported from OpenSearchIndexer
│   └── requirements.txt
└── vector_searcher/                 # ENHANCED - Existing stub
    ├── hybrid_search_engine.py      # NEW - Combines keyword + vector
    └── vector_searcher.py           # ENHANCED
```

## 🔄 **Messaging Integration**

### **SNS/SQS Flow**
```yaml
Text Chunker:
  publishes_to: text-chunking-complete
  message_format:
    doc_id: "0032f6cb_f0caef34"
    stage: "chunks_ready"
    chunks_location:
      bucket: "solve-global-kr-chunks-861276078413-us-east-1"
      prefix: "0032f6cb_f0caef34/"
      pattern: "0032f6cb_f0caef34_chunk_NNNN.json"

Vector Embeddings Processor:
  subscribes_to: text-chunking-complete
  publishes_to: vector-embeddings-complete
  message_format:
    doc_id: "0032f6cb_f0caef34"
    stage: "embeddings_ready"
    embeddings_count: 18
    opensearch_indexed: true
    titan_cost_actual: 0.0234
```

### **Async Processing Pattern** (Following Keyword Indexer Model)
1. **Initiator Function**: Quick delegation (~200ms execution)
2. **Worker Function**: Background processing with Titan API calls
3. **SNS Callbacks**: Success/failure notifications
4. **Database Tracking**: Status updates throughout process

## 🧩 **Code Reuse and Abstraction Strategy**

### **Lambda Layer Dependencies**
```yaml
vector_embeddings_processor:
  layers:
    - app-source-layer          # DocumentIDManager, DatabaseManager
    - aws-core-layer           # boto3, basic AWS utilities
    
vector_embeddings_worker:
  layers:
    - app-source-layer          # DocumentIDManager, DatabaseManager  
    - opensearch-layer         # OpenSearch client
    - aws-core-layer           # boto3, Titan Bedrock client
    - data-processing-layer    # numpy for vector operations (if needed)
```

### **Shared Utilities (Already in app-source layer)**
- **DocumentIDManager**: GUID-based document tracking ✅
- **DatabaseManager**: PostgreSQL connection management ✅
- **Status tracking patterns**: Consistent with existing processors ✅

### **New Shared Components** (Add to app-source layer)
```python
# layers/app-source/utils/TitanEmbeddingsManager.py
class TitanEmbeddingsManager:
    """AWS Titan embeddings with batch processing and caching"""
    
# layers/app-source/utils/VectorIndexManager.py  
class VectorIndexManager:
    """OpenSearch vector operations abstraction"""
```

## 📝 **Detailed Implementation Plan**

### **Phase 1: Core Vector Processing (Week 1)**

#### **1.1 TitanEmbeddingsManager** (Port from EmbeddingsManager.py)
```python
# lambda/vector_embeddings_worker/titan_embeddings_manager.py
class TitanEmbeddingsManager:
    def __init__(self, bedrock_client, model_id="amazon.titan-embed-text-v1"):
        self.bedrock_client = bedrock_client
        self.model_id = model_id
        self.batch_size = 25  # Titan API limit
        self.cache_bucket = "solve-global-kr-embeddings-cache-861276078413-us-east-1"
        
    def create_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Batch process with Titan API - cost optimized"""
        
    def cache_embeddings_s3(self, doc_id: str, embeddings: List[Dict]):
        """Cache results to avoid reprocessing"""
        
    def load_cached_embeddings(self, doc_id: str) -> Optional[List[Dict]]:
        """Load cached embeddings if available"""
```

**Key Changes from POC**:
- Replace sentence-transformers with Titan Bedrock API
- Add S3 caching for cost optimization
- Maintain batch processing pattern from POC
- Preserve error handling and provenance tracking
- Follow DocumentIDManager integration pattern

#### **1.2 OpenSearch Vector Indexer** (Port from OpenSearchIndexer.py)
```python
# lambda/vector_embeddings_worker/opensearch_vector_indexer.py
class OpenSearchVectorIndexer:
    def __init__(self, opensearch_client, index_name="climate-risk-vector-index"):
        self.client = opensearch_client
        self.index_name = index_name
        
    def create_vector_index_mapping(self):
        """Enhanced mapping with vector fields"""
        mapping = {
            "mappings": {
                "properties": {
                    # Existing keyword fields from current index
                    "doc_id": {"type": "keyword"},
                    "content": {"type": "text"},
                    "title": {"type": "text"},
                    
                    # New vector fields
                    "content_vector": {
                        "type": "knn_vector",
                        "dimension": 1536,  # Titan embedding dimension
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib"
                        }
                    },
                    "chunk_vectors": {
                        "type": "nested",
                        "properties": {
                            "chunk_id": {"type": "keyword"},
                            "vector": {
                                "type": "knn_vector",
                                "dimension": 1536
                            },
                            "metadata_confidence": {"type": "float"},
                            "structural_quality": {"type": "float"}
                        }
                    }
                }
            }
        }
        
    def index_document_vectors(self, doc_id: str, chunk_embeddings: List[Dict]):
        """Index vectors with metadata - following existing pattern"""
        
    def _calculate_composite_score(self, similarity_score: float, 
                                 metadata_confidence: float,
                                 structural_quality: float) -> float:
        """Port composite scoring from POC QdrantIndexer"""
```

**Key Changes from POC**:
- Use OpenSearch Serverless instead of local OpenSearch
- Integrate with existing DocumentIDManager
- Follow async processing pattern
- Maintain composite scoring approach from POC
- Preserve metadata-rich indexing

### **Phase 2: Lambda Functions (Week 1-2)**

#### **2.1 Vector Embeddings Processor** (Initiator - New)
```python
# lambda/vector_embeddings_processor/vector_embeddings_processor.py
import json
import boto3
from utils.DatabaseManager import DatabaseManager
from utils.DocumentIDManager import DocumentIDManager

def lambda_handler(event, context):
    """
    Async initiator following keyword indexer pattern:
    1. Parse chunks-ready message
    2. Validate document exists
    3. Delegate to worker via SNS
    4. Return quickly (~200ms)
    """
    try:
        # Parse SNS message
        message = json.loads(event['Records'][0]['Sns']['Message'])
        doc_id = message['doc_id']
        
        # Quick validation
        db_manager = DatabaseManager()
        if not db_manager.document_exists(doc_id):
            raise ValueError(f"Document {doc_id} not found")
            
        # Update status to PROCESSING
        db_manager.update_vector_embeddings_status(
            doc_id, 'PROCESSING', 'Vector embeddings initiated'
        )
        
        # Delegate to worker
        sns_client = boto3.client('sns')
        worker_message = {
            'doc_id': doc_id,
            'chunks_location': message['chunks_location'],
            'processing_type': 'vector_embeddings'
        }
        
        sns_client.publish(
            TopicArn=os.environ['VECTOR_WORKER_TOPIC_ARN'],
            Message=json.dumps(worker_message)
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'doc_id': doc_id,
                'status': 'delegated_to_worker',
                'processing_time_ms': context.get_remaining_time_in_millis()
            })
        }
        
    except Exception as e:
        # Error handling following existing pattern
        logger.error(f"Vector embeddings processor error: {str(e)}")
        if 'doc_id' in locals():
            db_manager.update_vector_embeddings_status(
                doc_id, 'FAILED', str(e)
            )
        raise
```

**Integration Points**:
- Subscribe to `text-chunking-complete` SNS topic
- Use existing DocumentIDManager for validation
- Follow async delegation pattern (75% cost savings proven)
- Database status tracking following established patterns

#### **2.2 Vector Embeddings Worker** (Background - New)
```python
# lambda/vector_embeddings_worker/vector_embeddings_worker.py
import json
import boto3
from titan_embeddings_manager import TitanEmbeddingsManager
from opensearch_vector_indexer import OpenSearchVectorIndexer
from utils.DatabaseManager import DatabaseManager
from utils.DocumentIDManager import DocumentIDManager

def lambda_handler(event, context):
    """
    Background processing:
    1. Load chunks from S3
    2. Generate Titan embeddings (batched)
    3. Index in OpenSearch with metadata
    4. Update database status
    5. Publish completion message
    """
    try:
        # Parse worker message
        message = json.loads(event['Records'][0]['Sns']['Message'])
        doc_id = message['doc_id']
        chunks_location = message['chunks_location']
        
        # Initialize managers
        db_manager = DatabaseManager()
        bedrock_client = boto3.client('bedrock-runtime')
        embeddings_manager = TitanEmbeddingsManager(bedrock_client)
        
        # Load chunks from S3
        chunks = load_chunks_from_s3(chunks_location)
        
        # Check for cached embeddings
        cached_embeddings = embeddings_manager.load_cached_embeddings(doc_id)
        if cached_embeddings:
            logger.info(f"Using cached embeddings for {doc_id}")
            embeddings = cached_embeddings
        else:
            # Generate embeddings with Titan
            embeddings = embeddings_manager.create_embeddings_batch(chunks)
            # Cache for future use
            embeddings_manager.cache_embeddings_s3(doc_id, embeddings)
        
        # Index in OpenSearch
        opensearch_client = get_opensearch_client()
        vector_indexer = OpenSearchVectorIndexer(opensearch_client)
        vector_indexer.index_document_vectors(doc_id, embeddings)
        
        # Update database status
        db_manager.update_vector_embeddings_status(
            doc_id, 'COMPLETED', 
            f'Successfully processed {len(embeddings)} embeddings'
        )
        
        # Publish completion message
        publish_completion_message(doc_id, len(embeddings))
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'doc_id': doc_id,
                'embeddings_count': len(embeddings),
                'status': 'completed'
            })
        }
        
    except Exception as e:
        # Comprehensive error handling
        logger.error(f"Vector embeddings worker error: {str(e)}")
        if 'doc_id' in locals():
            db_manager.update_vector_embeddings_status(
                doc_id, 'FAILED', str(e)
            )
        raise
```

**Cost Optimization Features**:
- Embedding caching in S3 (avoid reprocessing)
- Batch processing (25 texts per Titan API call)
- Error handling with graceful degradation
- Comprehensive status tracking

### **Phase 3: Enhanced Search (Week 2)**

#### **3.1 Hybrid Search Engine** (New)
```python
# lambda/vector_searcher/hybrid_search_engine.py
class HybridSearchEngine:
    def __init__(self, opensearch_client):
        self.client = opensearch_client
        self.keyword_index = "climate-risk-keyword-index"
        self.vector_index = "climate-risk-vector-index"
        
    def search(self, query: str, search_type="hybrid", limit=10):
        """
        Hybrid search combining keyword and vector results
        """
        if search_type == "keyword":
            return self.keyword_search(query, limit)
        elif search_type == "vector":
            return self.vector_search(query, limit)
        else:  # hybrid
            return self.hybrid_search(query, limit)
    
    def hybrid_search(self, query: str, limit: int):
        """
        Intelligent fusion of keyword and vector search results
        """
        # Keyword search (existing)
        keyword_results = self.keyword_search(query, limit * 2)
        
        # Vector search (new)
        query_embedding = self.generate_query_embedding(query)
        vector_results = self.vector_search_by_vector(query_embedding, limit * 2)
        
        # Intelligent fusion (ported from POC)
        return self.fuse_results(keyword_results, vector_results, limit)
    
    def fuse_results(self, keyword_results, vector_results, limit):
        """
        Port composite scoring algorithm from POC QdrantIndexer
        """
        # Combine and rank results using composite scoring
        # Weight: 70% similarity, 20% metadata confidence, 10% structural quality
        pass
        
    def generate_query_embedding(self, query: str):
        """Generate embedding for search query using Titan"""
        bedrock_client = boto3.client('bedrock-runtime')
        # Use same Titan model as indexing
        pass
```

**Key Features**:
- Preserve POC's composite scoring algorithm
- Integrate with existing keyword search
- Configurable search weights
- Fallback to keyword-only if vector fails

## 💰 **Cost Management Strategy**

### **Development Phase Budget**
```yaml
Titan Embeddings:
  cost_per_1k_tokens: $0.0004
  development_corpus: ~500 chunks (existing POC docs)
  estimated_tokens: ~125k tokens
  development_cost: ~$50

OpenSearch Serverless:
  monthly_cost: ~$108 (already deployed)
  additional_cost: $0 (shared with keyword index)

Lambda Processing:
  vector_processor: ~$5-10 for development
  total_development: ~$65-70
```

### **Production Cost Estimates**
```yaml
1K Documents Processing:
  chunks_estimate: ~18k chunks
  tokens_estimate: ~4.5M tokens  
  titan_cost: ~$1,800
  lambda_cost: ~$50
  total_initial: ~$1,850

Ongoing Monthly:
  new_documents: ~100/month
  monthly_cost: ~$185
  search_operations: minimal (OpenSearch queries)
```

### **Cost Optimization Measures**
1. **Embedding Caching**: Store Titan results in S3 to avoid reprocessing
2. **Batch Processing**: 25 texts per API call (maximize efficiency)
3. **Async Architecture**: 75% cost reduction vs synchronous (proven)
4. **Selective Processing**: Only process new/changed chunks
5. **Development Strategy**: Use existing POC documents to minimize new Textract costs

## 🔧 **CDK Infrastructure Updates**

### **New CDK Stack** (Following existing patterns)
```python
# cdk/app_vector_embeddings_pipeline.py
class VectorEmbeddingsPipelineStack(Stack):
    def __init__(self, scope, construct_id, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        # Import existing resources
        existing_vpc = ec2.Vpc.from_lookup(self, "ExistingVPC", vpc_name="solve-global-kr-rag-vpc")
        
        # Vector Embeddings Processor Lambda (Initiator)
        vector_processor = aws_lambda.Function(
            self, "VectorEmbeddingsProcessor",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            handler="vector_embeddings_processor.lambda_handler",
            code=aws_lambda.Code.from_asset("../lambda/vector_embeddings_processor"),
            layers=[app_source_layer, aws_core_layer],
            timeout=Duration.minutes(1),
            memory_size=256
        )
        
        # Vector Embeddings Worker Lambda (Background)
        vector_worker = aws_lambda.Function(
            self, "VectorEmbeddingsWorker", 
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            handler="vector_embeddings_worker.lambda_handler",
            code=aws_lambda.Code.from_asset("../lambda/vector_embeddings_worker"),
            layers=[app_source_layer, opensearch_layer, aws_core_layer],
            timeout=Duration.minutes(15),
            memory_size=1024,
            vpc=existing_vpc
        )
        
        # SNS Topics and SQS Queues
        vector_worker_topic = sns.Topic(self, "VectorWorkerTopic")
        vector_completion_topic = sns.Topic(self, "VectorCompletionTopic")
        
        # IAM Roles for Bedrock access
        vector_worker.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"]
            )
        )
```

### **Required Permissions**
```yaml
Bedrock:
  - bedrock:InvokeModel (Titan embeddings)
  
OpenSearch:
  - aoss:APIAccessAll (vector indexing)
  
S3:
  - s3:GetObject (read chunks)
  - s3:PutObject (cache embeddings)
  
SNS/SQS:
  - sns:Publish (coordination messages)
  - sqs:ReceiveMessage, sqs:DeleteMessage
```

## 📊 **Database Schema Extensions**

### **New Status Tracking Table**
```sql
CREATE TABLE vector_embeddings_status (
    doc_id VARCHAR(255) PRIMARY KEY,
    status VARCHAR(50) NOT NULL,
    embeddings_count INTEGER,
    titan_cost_estimate DECIMAL(10,6),
    titan_cost_actual DECIMAL(10,6),
    opensearch_indexed BOOLEAN DEFAULT FALSE,
    cache_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    processing_duration_seconds INTEGER,
    
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
);

-- Index for efficient querying
CREATE INDEX idx_vector_embeddings_status ON vector_embeddings_status(status);
CREATE INDEX idx_vector_embeddings_created_at ON vector_embeddings_status(created_at);
```

### **Integration with Existing Tables**
```sql
-- Add vector processing status to document_processing_status
ALTER TABLE document_processing_status 
ADD COLUMN vector_embeddings_status VARCHAR(50) DEFAULT 'PENDING',
ADD COLUMN vector_embeddings_completed_at TIMESTAMP;
```

## 🧪 **Testing Strategy**

### **Phase 1: Component Testing**
1. **Titan Integration**: Test embedding generation with small text samples
   - Validate API integration and response format
   - Test batch processing with different sizes
   - Verify cost calculations and caching

2. **OpenSearch Vector**: Test vector indexing and similarity search
   - Create test index with vector mapping
   - Index sample embeddings
   - Perform similarity searches

3. **Cost Validation**: Monitor actual vs estimated costs
   - Track Titan API costs per batch
   - Validate caching effectiveness
   - Monitor Lambda execution costs

### **Phase 2: Integration Testing**
1. **End-to-End Pipeline**: Text chunker → Vector processor → Search
   - Use existing POC documents for testing
   - Validate message flow through SNS/SQS
   - Test error handling and recovery

2. **Hybrid Search**: Validate keyword + vector result fusion
   - Compare search results quality
   - Test different query types
   - Validate composite scoring

3. **Performance Testing**: Response times and accuracy metrics
   - Measure search response times
   - Test with varying document corpus sizes
   - Validate memory and CPU usage

### **Phase 3: Production Validation**
1. **POC Document Testing**: Use existing 1K document corpus
   - Process subset of documents initially
   - Gradually scale to full corpus
   - Monitor costs and performance

2. **Search Quality**: Compare hybrid vs keyword-only results
   - A/B test search relevance
   - Measure user satisfaction metrics
   - Fine-tune scoring weights

3. **Cost Analysis**: Validate budget projections
   - Track actual vs projected costs
   - Optimize batch sizes and caching
   - Adjust processing strategies

## 🎯 **Success Criteria**

### **Functional Requirements**
- **Vector Generation**: Successfully process chunks into Titan embeddings
- **Hybrid Search**: Combine keyword and vector search effectively  
- **Cost Efficiency**: Stay within $200 development budget
- **Performance**: Sub-second search response times
- **Integration**: Seamless integration with existing pipeline

### **Technical Requirements**
- **Reliability**: 99%+ uptime with proper error handling
- **Scalability**: Handle 1K+ documents efficiently
- **Maintainability**: Follow established patterns and abstractions
- **Monitoring**: Comprehensive logging and status tracking

### **Quality Metrics**
- **Search Relevance**: 20-30% improvement over keyword-only
- **Response Time**: <500ms for typical queries
- **Cost per Search**: <$0.001 per query
- **Processing Speed**: <30 seconds per document for embeddings

## 🚀 **Implementation Timeline** (REVISED)

### **Day 1: Complete Implementation**
- [ ] Create pluggable embeddings architecture (Titan + SentenceTransformers)
- [ ] Port and implement Vector Embeddings Processor + Worker
- [ ] Set up SNS/SQS integration following existing patterns
- [ ] Create OpenSearch vector indexing
- [ ] Deploy and test with small document set
- [ ] Cost analysis and model comparison
- [ ] Production deployment if costs are acceptable

### **Cost Threshold Decision Point**
- **If Titan costs > $0.50/document**: Switch to SentenceTransformers in Lambda
- **If Titan costs acceptable**: Continue with Titan
- **Architecture supports both**: Easy model swapping

## 🔍 **Risk Mitigation**

### **Technical Risks**
1. **Titan API Limits**: Implement proper rate limiting and retry logic
2. **OpenSearch Performance**: Monitor and optimize vector search performance
3. **Cost Overruns**: Strict budget monitoring and automated alerts
4. **Integration Complexity**: Incremental testing and validation

### **Mitigation Strategies**
- **Incremental Development**: Build and test components separately
- **Cost Monitoring**: Daily budget tracking with automated alerts
- **Performance Testing**: Regular benchmarking throughout development
- **Rollback Plans**: Maintain ability to revert to keyword-only search

## 📚 **Documentation Requirements**

### **During Implementation**
- [ ] Vector processing architecture documentation
- [ ] Titan integration guide and best practices
- [ ] OpenSearch vector configuration guide
- [ ] Hybrid search algorithm documentation
- [ ] Cost optimization strategies and results

### **Post-Implementation**
- [ ] Complete system architecture documentation
- [ ] Deployment and operations guide
- [ ] Performance tuning guide
- [ ] Troubleshooting and maintenance procedures
- [ ] Search API documentation

## 🔗 **Integration with Future Phases**

### **Phase 3: Knowledge Graph Integration**
- Vector embeddings will enhance entity relationship discovery
- Hybrid search will incorporate graph-based results
- Composite scoring will include graph connectivity metrics

### **Phase 4: Complete RAG System**
- Vector search will provide context for LLM responses
- Hybrid search will optimize context selection
- Cost-optimized architecture will support production RAG queries

---

**This comprehensive plan provides a clear roadmap from the current enhanced keyword indexing system to a complete hybrid search solution with vector capabilities, maintaining cost efficiency and production reliability while leveraging proven POC algorithms and existing AWS infrastructure.**
