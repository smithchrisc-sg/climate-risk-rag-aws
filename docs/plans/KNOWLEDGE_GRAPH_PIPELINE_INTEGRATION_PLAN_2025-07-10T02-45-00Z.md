# Knowledge Graph Pipeline Integration Plan
## Date: 2025-07-10T02:45:00Z
## Status: Ready for Implementation

## EXECUTIVE SUMMARY

This document outlines the integration plan for connecting our working Neptune SPARQL loader to the overall document processing pipeline. The knowledge graph Lambda will be triggered from NLP completion to create comprehensive document structure and semantic triples in Neptune.

**Current Status**: Neptune SPARQL loader is fully operational and successfully loading document structure data. Ready for pipeline integration.

---

## INTEGRATION ARCHITECTURE

### **Trigger Strategy: NLP Complete** ⭐ **RECOMMENDED**

**Why NLP Complete vs Chunking Complete**:
- ✅ **All data available**: Document structure, entities, events, relationships
- ✅ **Complete knowledge graph**: Single operation creates full semantic representation
- ✅ **Future-proof**: Ready for entity/event processing without re-architecture
- ✅ **Simpler orchestration**: Single trigger point vs multiple stages

### **Message Flow Integration**
```
Document Processing → Chunking → NLP Processing → Knowledge Graph Loading
                                      ↓
                              SNS: nlp_complete
                                      ↓
                          neptune-kg-orchestrator
                                      ↓
                    [Document Structure] → [Entities] → [Events] → [Relationships]
                                      ↓
                              Neptune Knowledge Graph
```

---

## IMPLEMENTATION PHASES

### **Phase 1: Basic Integration** (1-2 days)
**Goal**: Connect existing SPARQL loader to NLP completion pipeline

#### **Tasks**:
1. **Update NLP Completion Handler**
   - Add knowledge graph trigger to existing NLP completion Lambda
   - Include document metadata in SNS message payload
   - Pass S3 locations for chunks and NLP results

2. **Modify SPARQL Loader**
   - Accept SNS trigger messages (currently accepts direct invocation)
   - Parse document metadata from message payload
   - Maintain existing document structure loading capability

3. **Test Integration**
   - Verify trigger from NLP completion works
   - Confirm document structure loading via pipeline
   - Validate Neptune data matches direct invocation results

#### **Success Criteria**:
- ✅ NLP completion triggers knowledge graph loading
- ✅ Document structure loaded successfully via pipeline
- ✅ No regression in existing functionality

### **Phase 2: Entity Integration** (3-5 days)
**Goal**: Add entity processing from NLP results

#### **Tasks**:
1. **Create Entity TTL Generation**
   - Read NER results from S3 (entities bucket)
   - Generate entity triples with systematic URIs
   - Link entities to document chunks where they appear
   - Create entity type hierarchies

2. **Extend SPARQL Loader**
   - Add entity loading capability to existing loader
   - Handle entity-chunk relationships
   - Support entity type classifications

3. **Entity Validation**
   - Add SPARQL queries to validate entity loading
   - Count entities by type and document
   - Verify entity-chunk relationships

#### **Success Criteria**:
- ✅ Entities extracted from NLP results
- ✅ Entity triples loaded into Neptune
- ✅ Entity-document relationships established
- ✅ Validation queries confirm data integrity

### **Phase 3: Event Integration** (3-5 days)
**Goal**: Add event processing and relationships

#### **Tasks**:
1. **Create Event TTL Generation**
   - Read event extraction results from S3
   - Generate event triples with temporal information
   - Link events to entities and documents
   - Create event type classifications

2. **Relationship Processing**
   - Process entity-entity relationships
   - Create entity-event relationships
   - Handle temporal relationships

3. **Complete Knowledge Graph**
   - Full semantic representation of documents
   - Multi-layered relationships (document, entity, event)
   - Temporal and semantic connections

#### **Success Criteria**:
- ✅ Events extracted and loaded as triples
- ✅ Entity-event relationships established
- ✅ Complete knowledge graph for documents
- ✅ Ready for dual traversal queries

---

## TECHNICAL IMPLEMENTATION DETAILS

### **SNS Message Format Enhancement**
```json
{
  "doc_id": "0032f6cb_f0caef34",
  "processing_stage": "nlp_complete",
  "knowledge_graph_trigger": true,
  "timestamp": "2025-07-10T02:45:00Z",
  "s3_locations": {
    "chunks": "s3://solve-global-kr-chunks-861276078413-us-east-1/0032f6cb_f0caef34/",
    "entities": "s3://solve-global-kr-entities-861276078413-us-east-1/0032f6cb_f0caef34/",
    "events": "s3://solve-global-kr-events-861276078413-us-east-1/0032f6cb_f0caef34/",
    "text": "s3://solve-global-kr-text-new-861276078413-us-east-1/extracted_text/0032f6cb_f0caef34.txt"
  },
  "processing_metadata": {
    "word_count": 2501,
    "sentence_count": 135,
    "page_count": 6,
    "chunk_count": 19,
    "entity_count": 45,
    "event_count": 12
  }
}
```

### **Lambda Function Architecture**

#### **Option A: Extend Existing SPARQL Loader** ⭐ **RECOMMENDED**
- Modify `neptune-sparql-loader` to handle different data types
- Add entity and event processing capabilities
- Maintain single function for simplicity

#### **Option B: Create Orchestrator + Specialized Loaders**
- `neptune-kg-orchestrator`: Coordinates multi-stage loading
- `neptune-entity-loader`: Specialized entity processing
- `neptune-event-loader`: Specialized event processing

**Recommendation**: Start with Option A for simplicity, refactor to Option B if complexity grows.

### **S3 TTL Structure Updates**
```
s3://solve-global-kr-neptune-ttl-861276078413-us-east-1/
├── documents/{doc_id}/
│   ├── document.ttl       # ✅ Document structure (working)
│   ├── chunks.ttl         # ✅ Chunk metadata (working)
│   ├── entities.ttl       # 🆕 NLP entities as triples
│   ├── events.ttl         # 🆕 NLP events as triples
│   ├── relationships.ttl  # 🆕 Entity-entity relationships
│   └── metadata.json      # ✅ Processing metadata (working)
├── ontology/
│   ├── document_structure_schema.ttl  # ✅ Working
│   ├── entity_schema.ttl              # 🆕 Entity type definitions
│   └── event_schema.ttl               # 🆕 Event type definitions
```

### **Environment Configuration**
```bash
# Add to existing Lambda environment variables
ENABLE_KNOWLEDGE_GRAPH=true
KG_PROCESSING_STAGE=nlp_complete
ENTITY_PROCESSING_ENABLED=true
EVENT_PROCESSING_ENABLED=true
NEPTUNE_TTL_BUCKET=solve-global-kr-neptune-ttl-861276078413-us-east-1
```

---

## INTEGRATION POINTS

### **1. NLP Completion Handler Updates**
**Location**: `src/lambda/nlp_completion_handler.py` (or equivalent)

**Changes Needed**:
```python
def handle_nlp_completion(event, context):
    # Existing NLP completion logic
    process_nlp_results(doc_id, nlp_results)
    
    # NEW: Trigger knowledge graph loading
    if should_trigger_knowledge_graph(doc_id):
        trigger_knowledge_graph_loading(doc_id, nlp_results)
    
    return success_response
```

### **2. SPARQL Loader Enhancements**
**Location**: `src/knowledge_graph/neptune_simple_sparql_loader.py`

**Changes Needed**:
```python
def lambda_handler(event, context):
    # Handle both direct invocation and SNS triggers
    if 'Records' in event:
        # SNS trigger from pipeline
        doc_id, processing_data = parse_sns_message(event)
    else:
        # Direct invocation (existing)
        doc_id = event.get('doc_id')
    
    # Load based on available data
    load_document_structure(doc_id)
    
    if processing_data.get('entities_available'):
        load_entities(doc_id, processing_data)
    
    if processing_data.get('events_available'):
        load_events(doc_id, processing_data)
```

### **3. Async Architecture Integration**
**Location**: `src/knowledge_graph/deploy_async_bulk_loading.sh`

**Updates Needed**:
- Add SNS subscription for NLP completion topic
- Update Lambda permissions for cross-service access
- Configure environment variables for pipeline integration

---

## TESTING STRATEGY

### **Integration Testing Scenarios**
1. **Document Structure Only** (Phase 1)
   - Trigger from NLP completion
   - Verify document/section/chunk loading
   - Validate Neptune data integrity

2. **Document + Entities** (Phase 2)
   - Include entity processing
   - Test entity-chunk relationships
   - Verify entity type classifications

3. **Complete Knowledge Graph** (Phase 3)
   - Full semantic processing
   - Entity-event relationships
   - Temporal connections

### **Performance Testing**
- Single document processing time
- Multiple document batch processing
- Neptune query performance with loaded data
- Memory usage during large document processing

### **Error Handling Testing**
- Malformed NLP results
- Missing S3 data
- Neptune connection failures
- Partial loading scenarios

---

## MONITORING & OBSERVABILITY

### **CloudWatch Metrics**
```python
# Custom metrics to track
- knowledge_graph_loading_success_rate
- processing_time_by_stage (structure, entities, events)
- triple_count_growth_over_time
- error_rate_by_processing_type
- documents_processed_per_hour
```

### **SNS Notifications**
- Knowledge graph processing started
- Each stage completion (structure, entities, events)
- Processing errors and failures
- Validation results and data quality metrics

### **CloudWatch Dashboards**
- Knowledge graph processing pipeline health
- Neptune data growth and query performance
- Error rates and processing bottlenecks
- Cost tracking for Neptune and Lambda usage

---

## COST CONSIDERATIONS

### **Neptune Costs**
- **Instance costs**: db.t3.medium (~$50/month)
- **Storage costs**: Minimal for our data volumes
- **Query costs**: Pay per query execution

### **Lambda Costs**
- **Execution time**: SPARQL loader runs ~30 seconds
- **Memory usage**: 512MB sufficient for current volumes
- **Invocation frequency**: Per document processed

### **S3 Costs**
- **TTL storage**: Minimal (KB per document)
- **Transfer costs**: Intra-region transfers free

**Estimated Monthly Cost**: $60-80 for moderate usage (100 documents/month)

---

## ROLLBACK STRATEGY

### **Phase Rollback**
- Each phase can be disabled via environment variables
- Existing document structure loading continues working
- No impact on upstream NLP processing

### **Data Rollback**
- Neptune supports SPARQL DELETE operations
- Can remove specific document data if needed
- S3 TTL files provide backup/recovery capability

---

## SUCCESS METRICS

### **Technical Metrics**
- ✅ 100% success rate for document structure loading
- ✅ <60 seconds processing time per document
- ✅ Zero data loss during pipeline integration
- ✅ All validation queries pass

### **Business Metrics**
- ✅ Complete knowledge graph for processed documents
- ✅ Ready for dual traversal query implementation
- ✅ Scalable to 1000+ documents
- ✅ Foundation for advanced semantic search

---

## NEXT STEPS

1. **Immediate** (Today): Create project context and next steps documents
2. **Phase 1** (Tomorrow): Begin NLP completion handler integration
3. **Phase 2** (Next week): Implement entity processing
4. **Phase 3** (Following week): Complete event and relationship processing

This plan provides a clear roadmap for integrating our working Neptune SPARQL loader into the complete document processing pipeline, enabling comprehensive knowledge graph construction for the GAIP dual traversal strategy.
