# NLP-KG PROCESSOR - UPDATED EFFICIENT ARCHITECTURE

## 🏗️ **REVISED ARCHITECTURE OVERVIEW**

The `nlp_kg_processor` processes **single documents** (not batches) with pre-aligned entities from `nlp-worker`, implementing efficient URI caching and contextual disambiguation.

## 🔄 **UPDATED PROCESS FLOW**

### **📨 EVENT RECEPTION** 
**Entry Point**: `handler.py` → `NLPKGProcessor.process()`

**Input**: SNS message from `nlp-worker` Lambda containing **single document**:
```json
{
  "processing_requests": [
    {
      "document_id": "doc123",
      "s3_bucket": "bucket-name", 
      "nlp_results_key": "nlp-results/doc123/comprehend_results.json",
      "chunks_key": "chunks/doc123/chunks.json"
    }
  ]
}
```

**Note**: Loop structure remains for message compatibility, but will always contain exactly one document.

### **🔍 PHASE 1: MESSAGE PARSING & VALIDATION**
**Component**: `MessageParser`
- Extract single document request
- Validate required fields
- **Simplified**: No multi-document handling needed

### **⚙️ PHASE 2: COMPONENT INITIALIZATION**
**Component**: `ComponentManager`
- Initialize knowledge-graph-layer utilities
- Load ontologies from Neptune
- **Same as before**: Reusable components

### **📥 PHASE 3: DATA RETRIEVAL**
**Component**: `DataRetriever`

**Enhanced Data Structure**: Entities come **pre-aligned** to chunks from nlp-worker:
```json
{
  "entities_by_chunk": [
    {
      "chunk_id": "doc123_chunk_0001",
      "chunk_index": 0,
      "section_type": "paragraph", 
      "hierarchy_level": 2,
      "parent_chunk_id": "doc123_chunk_0000",
      "entity": "Paris",
      "type": "LOCATION",
      "score": 0.95,
      "original_begin_offset": 1245,
      "original_end_offset": 1250,
      "chunk_relative_begin": 45,
      "chunk_relative_end": 50
    }
  ]
}
```

**Output**: 
- `nlp_results`: Pre-aligned entities by chunk
- `chunks_data`: Document chunk information

### **📊 PHASE 4: ENTITY FREQUENCY ANALYSIS** ⭐ **NEW**
**Component**: `EntityFrequencyAnalyzer`

**Process**:
1. **Entity Counting**: Count occurrences of each raw entity across all chunks
   ```python
   entity_counts = {
     'Paris': 45,      # appears in 45 chunks
     'London': 22,     # appears in 22 chunks  
     'Brisbane': 9     # appears in 9 chunks
   }
   ```

2. **Processing Order**: Sort entities by frequency (descending) for efficient caching
3. **Cache Initialization**: Initialize per-document URI cache

**Output**: Prioritized entity processing order + empty cache

### **🎯 PHASE 5: DOCUMENT CONTEXT EXTRACTION** ⭐ **PLACEHOLDER**
**Component**: `DocumentContextAnalyzer`

**Process**: **TBD** - Extract document-level signals for disambiguation
- Document title analysis
- Domain classification  
- Regional context detection

**Output**: `document_context` - signals for entity disambiguation

### **🔗 PHASE 6: FOCUSED ENTITY ALIGNMENT & FILTERING** ⭐ **MAJOR ENHANCEMENT**
**Component**: `FocusedEntityAligner`

**Entity Processing Strategy**:
```python
# Process entities in frequency order (most common first)
for entity_text in sorted_entities:
    chunks_with_entity = get_chunks_containing_entity(entity_text)
    
    for chunk_id in chunks_with_entity:
        # Determine target ontologies based on entity type
        target_ontologies = select_ontologies_for_entity(entity_type)
        
        # Check cache first
        cached_uri = check_cache_with_similarity(entity_text, chunk_id, target_ontologies)
        
        if cached_uri:
            # Use cached URI if chunk is similar to previous
            assign_cached_uri(entity_text, chunk_id, cached_uri)
        else:
            # Try alignment with target ontologies
            alignment_result = contextual_disambiguation(
                entity_text, chunk_id, document_context, target_ontologies
            )
            
            if alignment_result.aligned:
                # Successfully aligned - keep entity
                assign_uri(entity_text, chunk_id, alignment_result.uri)
                update_cache(entity_text, chunk_id, alignment_result.uri)
            else:
                # No alignment found - drop entity
                drop_entity(entity_text, chunk_id, reason="no_ontology_alignment")
```

**Ontology Selection Strategy**:
```python
def select_ontologies_for_entity(entity_type):
    ontology_map = {
        'LOCATION': ['geonames'],
        'GPE': ['geonames'],  # Geopolitical entities
        'ORG': ['organizations'],  # Future organizational ontology
        'OTHER': ['climate_risk'],  # Climate concepts, treaties, etc.
        'PERSON': []  # Drop - too hard to disambiguate meaningfully
    }
    return ontology_map.get(entity_type, [])
```

**Entity Filtering Results**:
- ✅ **LOCATION/GPE**: Align with geonames ontology
- ✅ **ORG**: Align with organizations ontology (future)
- ✅ **OTHER**: Align with climate risk ontology  
- ❌ **PERSON**: Drop (disambiguation too complex for current scope)
- ❌ **Unaligned entities**: Drop (no relevant ontology match)

**Cache Strategy**: Same similarity-based caching, but per ontology type

**Output**: 
- `aligned_entities`: Only entities successfully aligned to target ontologies
- `dropped_entities`: Tracking data for entities filtered out

## 🏢 **FUTURE: ORGANIZATIONAL ONTOLOGY DESIGN**

### **Scope & Domain Coverage**
**Government Organizations**:
- Health departments (Singapore Dept of Health, Health Canada)
- Environmental agencies (EPA, Environment Canada)
- Regulatory bodies, ministries, departments

**Climate Finance & Development**:
- Development banks (World Bank, ADB, AfDB)
- Climate funds (Green Climate Fund, Adaptation Fund)
- Bilateral development agencies (USAID, DFID, GIZ)

**Insurance & Risk Management**:
- Protection gap initiatives (SEADRIF, GAIP, CCRIF)
- Insurance companies, reinsurers
- Risk modeling organizations

**International Organizations**:
- UN agencies (UNEP, UNDP, WMO)
- Intergovernmental organizations (IPCC, OECD)
- Regional bodies (ASEAN, EU, AU)

**Research & Think Tanks**:
- Climate research institutions
- Policy think tanks
- Academic institutions

### **Ontological Structure**
```turtle
# Organizational taxonomy with types and relationships
:SingaporeDeptHealth rdf:type :GovernmentHealthDirectorate ;
    rdfs:label "Singapore Department of Health" ;
    :hasJurisdiction :Singapore ;
    :organizationType :GovernmentAgency ;
    :sector :Health ;
    :hasAcronym "MOH" .

:HealthCanada rdf:type :GovernmentHealthDirectorate ;
    rdfs:label "Health Canada" ;
    :hasJurisdiction :Canada ;
    :organizationType :GovernmentMinistry ;
    :sector :Health .

:WorldBank rdf:type :MultilateralDevelopmentBank ;
    rdfs:label "World Bank" ;
    :hasAcronym "WB" ;
    :organizationType :InternationalFinancialInstitution ;
    :sector :Development ;
    :hasSubsidiary :WorldBankGroup .

:SEADRIF rdf:type :RegionalRiskPool ;
    rdfs:label "Southeast Asia Disaster Risk Insurance Facility" ;
    :hasAcronym "SEADRIF" ;
    :organizationType :RiskFinancingMechanism ;
    :sector :DisasterRisk ;
    :hasJurisdiction :SoutheastAsia .

# Enables queries like "find all government health directorates"
# or "compare organizations of type :MultilateralDevelopmentBank"
```

### **Data Sources & Curation**
**Manual Curation** (Preferred):
- Focused, high-quality data for climate/risk domain
- Controlled vocabulary and consistent structure
- Domain expertise in organizational relationships

**External Sources** (Supplementary):
- Wikidata/DBpedia for basic organizational data
- Official organizational registries
- Sector-specific databases (insurance, development finance)

**Hybrid Approach**:
- Core climate/risk organizations: Manual curation
- Extended coverage: Semi-automated from external sources
- Continuous refinement based on document processing

### **Implementation Timeline**
1. **Phase 1**: Location disambiguation (geonames) - Current focus
2. **Phase 2**: Climate concepts (existing climate risk ontology)
3. **Phase 3**: Organizational ontology development & integration
4. **Phase 4**: Advanced contextual disambiguation across all ontologies

## 📊 **ENTITY PROCESSING METRICS & MONITORING**

### **Alignment Success Tracking**
```python
processing_metrics = {
    'entities_by_type': {
        'LOCATION': {'total': 245, 'aligned': 198, 'dropped': 47},
        'ORG': {'total': 156, 'aligned': 89, 'dropped': 67},  # Future: higher alignment rate
        'OTHER': {'total': 334, 'aligned': 201, 'dropped': 133},
        'PERSON': {'total': 89, 'aligned': 0, 'dropped': 89}  # All dropped by design
    },
    'alignment_by_ontology': {
        'geonames': {'queries': 245, 'successful': 198, 'success_rate': 0.81},
        'climate_risk': {'queries': 334, 'successful': 201, 'success_rate': 0.60},
        'organizations': {'queries': 0, 'successful': 0, 'success_rate': 0.0}  # Future
    },
    'cache_performance': {
        'cache_hits': 156,
        'cache_misses': 243,
        'cache_hit_rate': 0.39,
        'similarity_checks': 89
    },
    'document_coverage': {
        'total_entities_extracted': 824,
        'entities_kept': 488,
        'entities_dropped': 336,
        'coverage_rate': 0.59
    }
}
```

### **Quality Assurance**
- **Dropped Entity Analysis**: Review dropped entities to identify ontology gaps
- **Alignment Accuracy**: Sample validation of aligned entities
- **Cache Effectiveness**: Monitor cache hit rates and similarity thresholds
- **Coverage Trends**: Track coverage rates across document types

### **🏷️ PHASE 7: DETERMINISTIC URI GENERATION**
**Component**: `URIManager`

**Clarified Responsibilities**:
```python
class URIManager:
    def generate_document_uri(self, document_id):
        """Deterministic: doc:{document_id}"""
        return f"doc:{document_id}"
    
    def generate_chunk_uri(self, document_id, chunk_id):
        """Deterministic: doc:{document_id}/chunk:{chunk_id}"""
        return f"doc:{document_id}/chunk:{chunk_id}"
    
    def generate_entity_instance_uri(self, document_id, chunk_id, entity_text, ontology_uri):
        """Deterministic: Links entity instance to ontology concept"""
        return f"doc:{document_id}/chunk:{chunk_id}/entity:{hash(entity_text)}"
```

**Not Used For**:
- ❌ Entity alignment URIs (come from ontologies)
- ❌ Caching (algorithmic generation only)
- ❌ Disambiguation (handled by EntityAligner)

**Used For**:
- ✅ Document structure URIs
- ✅ Chunk URIs  
- ✅ Entity instance URIs (linking instances to ontology concepts)

### **🕸️ PHASE 8: KNOWLEDGE GRAPH CONSTRUCTION**
**Component**: `TripleManager`
- Create RDF triples from aligned entities
- Model entity-document, entity-chunk relationships
- **Same as before**: Triple generation logic

### **💾 PHASE 9: DATA PERSISTENCE**
**Component**: `PipelineIntegrator`

**Updated S3 Naming**:
- **Path**: `knowledge-graph/{document_id}/nlp_kg_triples.ttl`
- **Rationale**: Multiple stages produce triples in same folder
- **Other stages**: `document_structure_kg_triples.ttl`, etc.

**Process**:
1. Convert triples to TTL format
2. Store with stage-specific naming
3. Trigger `kg-triple-loader` via SNS

## 🚀 **EFFICIENCY OPTIMIZATIONS**

### **📈 URI Caching Benefits**
- **Avoid Redundant Disambiguation**: "Paris" in 45 chunks → disambiguate once, cache 44 times
- **Chunk Similarity**: Similar chunks likely have same entity meaning
- **Frequency-First Processing**: Build cache with most common entities first

### **⚡ OpenSearch Integration**
- **Existing Embeddings**: Reuse chunk embeddings from earlier pipeline stage
- **KNN Similarity**: Efficient chunk comparison using existing index
- **Configurable Threshold**: Tune similarity sensitivity via environment

### **🎯 Smart Cache Management**
```python
# Example cache evolution
# Initial: Paris in chunk_0001 → geonames:4717560 (Paris, Texas)
# Later: Paris in chunk_0234 → check similarity to chunk_0001
# If similar (>0.80): use geonames:4717560
# If different: full disambiguation → maybe geonames:2988507 (Paris, France)
# Cache now has both mappings for future chunks
```

### **📊 Processing Limits**
- **Cache Size Limits**: Prevent runaway memory usage
- **Similarity Check Limits**: Max comparisons per entity
- **Timeout Handling**: Fallback to full disambiguation if cache checks timeout

## 🔧 **CONFIGURATION PARAMETERS**

### **Environment Variables**
```bash
CHUNK_SIMILARITY_THRESHOLD=0.80          # Similarity threshold for URI caching
MAX_CACHE_ENTRIES_PER_ENTITY=10          # Prevent runaway cache growth
MAX_SIMILARITY_CHECKS_PER_ENTITY=5       # Limit cache comparison overhead
OPENSEARCH_ENDPOINT=https://...          # For chunk similarity queries
KG_LOADER_SNS_TOPIC_ARN=arn:aws:sns:... # Downstream pipeline trigger
```

## 📋 **UPDATED COMPONENT RESPONSIBILITIES**

### **New Components**
- **EntityFrequencyAnalyzer**: Count and prioritize entities
- **DocumentContextAnalyzer**: Extract document-level signals (TBD)
- **EfficientEntityAligner**: Caching + contextual disambiguation
- **ChunkSimilarityChecker**: OpenSearch KNN integration

### **Modified Components**
- **MessageParser**: Simplified for single document
- **DataRetriever**: Handle pre-aligned entity structure
- **PipelineIntegrator**: Updated S3 naming convention

### **Unchanged Components**
- **ComponentManager**: Same initialization logic
- **TripleManager**: Same triple generation
- **URIManager**: Same URI generation (but less usage)
- **ResponseBuilder**: Same response format

## 🎯 **TESTING IMPLICATIONS**

### **Cache Testing**
- Test similarity threshold sensitivity
- Validate cache hit/miss ratios
- Test cache growth limits

### **Performance Testing**
- Measure disambiguation time savings
- OpenSearch query performance
- Memory usage with large documents

### **Accuracy Testing**
- Validate cached URIs are correct
- Test edge cases where similarity fails
- Compare accuracy vs. full disambiguation

## 🚨 **RISK MITIGATION**

### **Cache Consistency**
- Validate cached URIs haven't changed
- Fallback to full disambiguation on cache errors
- Monitor cache hit rates

### **Performance Safeguards**
- Timeout on similarity checks
- Limit cache size growth
- Graceful degradation if OpenSearch unavailable

### **Accuracy Safeguards**
- Configurable similarity thresholds
- Manual override for critical entities
- Audit logging for cache decisions

This architecture provides significant efficiency gains while maintaining disambiguation accuracy through intelligent caching and contextual analysis.
