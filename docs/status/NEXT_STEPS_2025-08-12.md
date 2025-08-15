# NEXT STEPS - August 12, 2025

## 🎯 **IMMEDIATE DEVELOPMENT PRIORITIES**

### **Phase 1: Enhanced EntityAligner Implementation**
**Target**: Upgrade EntityAligner in knowledge-graph-layer with contextual FTS-enhanced SPARQL

**Key Documents Created**:
- **`docs/knowledge-graph/ENTITIY_ALIGNMENT_APPROACH_2025-08-12.md`**: Complete design specification
- **`lambda/nlp_kg_processor/UPDATED_ARCHITECTURE_WALKTHROUGH.md`**: Efficient processing architecture
- **`docs/status/PROJECT_CONTEXT_SUMMARY_2025-08-12.md`**: Current state checkpoint
- **`docs/status/NEXT_STEPS_2025-08-12.md`**: This document

## 🔄 **DEVELOPMENT SEQUENCE**

### **Step 1: EntityAligner Enhancement Design Review**
**Objective**: Finalize technical approach before implementation

**Tasks**:
1. **Review Design Document**: `docs/knowledge-graph/ENTITIY_ALIGNMENT_APPROACH_2025-08-12.md`
2. **Validate Architecture**: Confirm nlp_kg_processor integration approach
3. **Confirm Cost Strategy**: Ensure testing approach minimizes AWS charges
4. **Approve Implementation Plan**: Get sign-off on technical approach

**Deliverable**: Approved technical specification

### **Step 2: Unit Test Framework Development**
**Objective**: Create test framework for contextual disambiguation logic

**Location**: `tests/test_contextual_entity_alignment.py`

**Test Cases**:
```python
def test_north_american_context_disambiguation():
    """Paris + Texas co-occurrence should favor Paris, Texas"""
    
def test_european_context_disambiguation():
    """European document context should favor Paris, France"""
    
def test_chunk_similarity_caching():
    """Similar chunks should reuse cached URIs"""
    
def test_entity_filtering_strategy():
    """PERSON entities should be dropped, LOCATION aligned"""
```

**Approach**: Mock Neptune responses, test scoring logic without AWS costs

**Deliverable**: Comprehensive unit test suite

### **Step 3: Enhanced EntityAligner Implementation**
**Objective**: Implement contextual FTS-enhanced SPARQL in knowledge-graph-layer

**Target File**: `layers/knowledge-graph-layer/python/utils/EntityAligner.py`

**Key Enhancements**:
1. **Context Extraction**: Document title, chunk co-occurrence analysis
2. **FTS-Enhanced Queries**: Replace fuzzy matching with contextual SPARQL
3. **Context Scoring**: Regional, co-occurrence, and semantic boosts
4. **Entity Filtering**: Drop unaligned entities, focus on meaningful alignments
5. **URI Caching**: Chunk similarity-based caching for efficiency

**Implementation Strategy**:
```python
# Enhance existing method signature
def align_entities_to_ontologies(self, entity_chunk_mappings, climate_ontology, geonames_ontology):
    # NEW: Extract document and chunk context
    document_context = self._extract_document_context(entity_chunk_mappings)
    
    # NEW: Entity frequency analysis and caching
    entity_cache = self._initialize_entity_cache()
    
    # NEW: Process entities by frequency (most common first)
    for entity_text in self._get_entities_by_frequency(entity_chunk_mappings):
        # NEW: Contextual disambiguation with caching
        alignments = self._contextual_alignment_with_cache(
            entity_text, document_context, entity_cache
        )
```

**Deliverable**: Enhanced EntityAligner with contextual capabilities

### **Step 4: Integration Testing**
**Objective**: Test enhanced EntityAligner with real Neptune data

**Approach**:
1. **Deploy Enhanced Layer**: Use standard layer build/deploy process
2. **Limited Document Testing**: 3-5 documents maximum to control costs
3. **Validation**: Compare disambiguation accuracy vs. current approach
4. **Performance Monitoring**: Query times, cache hit rates, cost impact

**Test Documents**:
- Document with "Paris" in North American context
- Document with "Paris" in European context  
- Document with multiple ambiguous locations

**Success Criteria**:
- Paris correctly disambiguated based on context
- No regression in non-location entity processing
- Performance within acceptable bounds (<2s additional per document)

**Deliverable**: Validated enhanced EntityAligner integration

### **Step 5: nlp_kg_processor Integration**
**Objective**: Integrate enhanced EntityAligner into nlp_kg_processor workflow

**Target**: `lambda/nlp_kg_processor/src/document_processor.py`

**Key Changes**:
1. **Entity Frequency Analysis**: Count and prioritize entities
2. **Efficient Processing**: Use enhanced EntityAligner with caching
3. **Entity Filtering**: Drop unaligned entities, track metrics
4. **Updated S3 Naming**: `nlp_kg_triples.ttl` for stage-specific output

**Integration Points**:
- Phase 4: Entity frequency analysis (new)
- Phase 5: Document context extraction (placeholder)
- Phase 6: Enhanced entity alignment with filtering
- Phase 9: Updated TTL file naming

**Deliverable**: Fully integrated efficient entity processing pipeline

### **Step 6: End-to-End Validation**
**Objective**: Validate complete pipeline with enhanced entity alignment

**Test Method**: 
```bash
cd /Users/chris/climate-risk-rag-aws
python3 invoke_pipeline_test.py --num-documents 3 --force
```

**Validation Points**:
1. **Entity Extraction**: nlp-worker provides pre-aligned entities
2. **Contextual Alignment**: Enhanced EntityAligner disambiguates correctly
3. **Knowledge Graph**: Correct URIs and relationships in Neptune
4. **Performance**: No significant latency increase
5. **Cost Impact**: Minimal increase in processing costs

**Success Metrics**:
- >90% disambiguation accuracy for ambiguous locations
- <2s additional processing time per document
- No regression in existing functionality
- Controlled cost increase (<10% of current processing cost)

**Deliverable**: Production-ready enhanced entity alignment system

## 🔧 **IMPLEMENTATION CONSIDERATIONS**

### **Cost Control Strategy**
**Testing Phases**:
1. **Unit Tests**: Mock data (no AWS costs)
2. **Integration Tests**: 3-5 documents max (controlled costs)
3. **Performance Tests**: Monitor Neptune query costs
4. **Production Validation**: Gradual rollout

**Cost Monitoring**:
- Track Neptune FTS query costs vs. fuzzy matching
- Monitor Comprehend usage during testing
- Use existing processed documents when possible
- Set AWS billing alerts for development account

### **Risk Mitigation**
**Technical Risks**:
- **Layer Modification**: Use standard build/deploy processes
- **Performance Impact**: Monitor query times and resource usage
- **Accuracy Regression**: Comprehensive testing before deployment

**Rollback Strategy**:
- **Git Version Control**: Clean commits for easy rollback
- **Layer Versioning**: Keep previous layer version available
- **Gradual Deployment**: Test with subset before full rollout

### **Quality Assurance**
**Testing Strategy**:
- **Unit Tests**: Logic validation with mock data
- **Integration Tests**: Real Neptune data with limited scope
- **Performance Tests**: Query time and resource monitoring
- **Accuracy Tests**: Ground truth validation for disambiguation

**Success Validation**:
- Disambiguation accuracy metrics
- Performance benchmarking
- Cost impact analysis
- Regression testing for existing functionality

## 📋 **DELIVERABLES CHECKLIST**

### **Documentation**
- ✅ **Entity Alignment Design**: `ENTITIY_ALIGNMENT_APPROACH_2025-08-12.md`
- ✅ **Architecture Walkthrough**: `UPDATED_ARCHITECTURE_WALKTHROUGH.md`
- ✅ **Project Context**: `PROJECT_CONTEXT_SUMMARY_2025-08-12.md`
- ✅ **Next Steps**: `NEXT_STEPS_2025-08-12.md`

### **Implementation** (Pending)
- ⏳ **Unit Test Framework**: Contextual disambiguation tests
- ⏳ **Enhanced EntityAligner**: FTS-enhanced SPARQL implementation
- ⏳ **Integration Testing**: Real Neptune data validation
- ⏳ **nlp_kg_processor Updates**: Efficient processing integration
- ⏳ **End-to-End Validation**: Complete pipeline testing

### **Validation** (Pending)
- ⏳ **Disambiguation Accuracy**: >90% for ambiguous locations
- ⏳ **Performance Metrics**: <2s additional processing time
- ⏳ **Cost Analysis**: Controlled increase in processing costs
- ⏳ **Regression Testing**: No impact on existing functionality

## 🎯 **SUCCESS CRITERIA**

### **Technical Success**
- **Contextual Disambiguation**: Paris correctly identified as Texas vs. France based on context
- **Efficient Processing**: URI caching reduces redundant disambiguation
- **Entity Filtering**: Meaningful entities kept, unaligned entities dropped
- **Performance**: Acceptable latency and cost impact

### **Architectural Success**
- **Clean Integration**: Enhanced EntityAligner works within existing architecture
- **Extensible Design**: Easy addition of future ontologies (organizations)
- **Maintainable Code**: Clear separation of concerns, comprehensive testing
- **Cost Efficiency**: Minimal impact on processing costs

### **Operational Success**
- **Reliable Processing**: Consistent results across document types
- **Monitoring**: Comprehensive metrics for alignment accuracy and performance
- **Rollback Capability**: Safe deployment with rollback options
- **Documentation**: Complete documentation for future development

## 🚀 **READY TO PROCEED**

The foundation is in place with comprehensive design documents and architectural planning. The next step is to begin implementation with the unit test framework, followed by the enhanced EntityAligner development.

**Immediate Action**: Review and approve the technical approach outlined in the design documents, then proceed with Step 1 (Design Review) and Step 2 (Unit Test Framework Development).
