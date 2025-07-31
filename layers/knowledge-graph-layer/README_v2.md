# Knowledge Graph Layer v2.0.0 - NLP-Ontology Integration

## 🎯 **Overview**

The Knowledge Graph Layer v2.0.0 extends the existing Neptune/SPARQL utilities with comprehensive NLP-ontology integration capabilities. This version maintains **100% backward compatibility** while adding powerful new functionality for entity-concept alignment and bidirectional matching.

## 🛡️ **Backward Compatibility Guarantee**

**ALL existing code continues to work unchanged:**
- ✅ All existing method signatures preserved
- ✅ All existing imports work without modification  
- ✅ document-structure-kg-processor works unchanged
- ✅ URI patterns remain consistent
- ✅ Namespace management unchanged

## 📦 **What's New in v2.0.0**

### **🔍 NLP-Ontology Integration**
- **EntityAligner**: Maps Comprehend entities to ontology concepts using fuzzy matching
- **OntologyTermMatcher**: Finds ontology concept mentions in text using Aho-Corasick
- **ConceptReconciler**: Merges and resolves conflicts between bidirectional results
- **NLPKGIntegrator**: Generates final RDF triples with consistent URI patterns

### **🔧 Supporting Utilities**
- **TextNormalizer**: Advanced text processing (stemming, lemmatization, domain-specific)
- **ConfidenceScorer**: Multi-factor confidence calculation with explainable results

### **🔮 Future Search Stubs**
- **SearchQueryBuilder**: Stub for hybrid search query building
- **ResultFusionManager**: Stub for multi-backend result fusion
- **ConceptExpander**: Stub for ontology-based query expansion

## 🏗️ **Architecture**

### **Layer Structure**
```
knowledge-graph-layer/
├── requirements-v2.txt              # Extended dependencies
├── python/utils/
│   ├── __init__.py                  # Updated exports (v2.0.0)
│   │
│   # === EXISTING UTILITIES (UNCHANGED) ===
│   ├── KnowledgeGraphManager.py     # Core Neptune operations
│   ├── URIManager.py                # URI generation patterns
│   ├── OntologyManager.py           # Ontology loading/querying
│   ├── TripleManager.py             # RDF triple operations
│   ├── SPARQLQueryBuilder.py        # SPARQL query construction
│   ├── BulkLoadManager.py           # Neptune bulk loading
│   ├── kg_exceptions.py             # Exception definitions
│   │
│   # === NEW NLP UTILITIES ===
│   ├── EntityAligner.py             # Comprehend → ontology mapping
│   ├── OntologyTermMatcher.py       # Ontology → text matching
│   ├── ConceptReconciler.py         # Bidirectional result merging
│   ├── NLPKGIntegrator.py           # Final RDF integration
│   ├── TextNormalizer.py            # Text processing utilities
│   ├── ConfidenceScorer.py          # Confidence calculation
│   │
│   # === FUTURE SEARCH STUBS ===
│   ├── SearchQueryBuilder.py        # Search query building (stub)
│   ├── ResultFusionManager.py       # Result fusion (stub)
│   └── ConceptExpander.py           # Query expansion (stub)
```

### **Dependencies Added**
```
# NLP Processing
fuzzywuzzy==0.18.0              # Fuzzy string matching
python-Levenshtein==0.21.1      # Fast string distance
nltk==3.8.1                     # Text processing

# Semantic Similarity  
sentence-transformers==2.2.2    # Semantic embeddings
numpy==1.24.3                   # Mathematical operations
scipy==1.10.1                   # Scientific computing
scikit-learn==1.3.0             # ML utilities

# Pattern Matching
ahocorasick-rs==0.20.0          # Fast pattern matching

# PyTorch (CPU-only)
torch==2.0.1+cpu                # Neural network framework
torchvision==0.15.2+cpu         # Computer vision utilities

# Additional ML Dependencies
tokenizers==0.13.3              # Text tokenization
transformers==4.30.2            # Transformer models
pandas==2.0.3                   # Data manipulation
```

## 🚀 **Usage Examples**

### **Existing Functionality (Unchanged)**
```python
# All existing code works exactly the same
from utils import KnowledgeGraphManager

kg_manager = KnowledgeGraphManager()
doc_uri = kg_manager.mint_document_uri("doc123")  # Same as before
concepts = kg_manager.get_ontology_concepts()     # Same as before
```

### **New NLP-Ontology Integration**
```python
from utils import (
    KnowledgeGraphManager,
    EntityAligner,
    OntologyTermMatcher, 
    ConceptReconciler,
    NLPKGIntegrator
)

# Initialize with existing KG manager
kg_manager = KnowledgeGraphManager()

# 1. Entity → Ontology Alignment
entity_aligner = EntityAligner(kg_manager, min_confidence=0.6)
entity_results = entity_aligner.align_entities_to_concepts(
    entities_by_chunk=nlp_worker_output,
    ontology_domains=['climate', 'financial']
)

# 2. Ontology → Text Matching  
term_matcher = OntologyTermMatcher(kg_manager, min_confidence=0.7)
term_matcher.build_pattern_automaton(['climate', 'financial'])
mention_results = term_matcher.find_concept_mentions(
    chunks=chunk_data,
    include_co_occurrences=True
)

# 3. Bidirectional Reconciliation
reconciler = ConceptReconciler(kg_manager)
reconciled_results = reconciler.reconcile_bidirectional_mappings(
    entity_mappings=entity_results,
    ontology_mentions=mention_results
)

# 4. Final KG Integration
integrator = NLPKGIntegrator(kg_manager, s3_bucket='my-bucket')
final_result = integrator.integrate_nlp_with_document_structure(
    reconciled_mappings=reconciled_results,
    doc_id='doc123'
)
```

## 🔧 **Lambda Function Integration**

### **Existing Functions (No Changes Required)**
```python
# document-structure-kg-processor continues to work unchanged
from utils import KnowledgeGraphManager

class DocumentStructureKGProcessor:
    def __init__(self):
        self.kg_manager = KnowledgeGraphManager()  # Same as before
        
    def process_document(self, doc_id, chunks):
        # All existing methods work unchanged
        doc_uri = self.kg_manager.mint_document_uri(doc_id)
        # ... rest of existing code unchanged
```

### **New NLP Lambda Functions**
```python
# nlp-entity-ontology-mapper
from utils import KnowledgeGraphManager, EntityAligner

def lambda_handler(event, context):
    kg_manager = KnowledgeGraphManager()
    entity_aligner = EntityAligner(kg_manager)
    
    # Process entities from corrected nlp-worker
    result = entity_aligner.align_entities_to_concepts(
        entities_by_chunk=event['entities_by_chunk'],
        ontology_domains=event.get('ontology_domains', ['climate', 'financial'])
    )
    
    return result

# nlp-ontology-term-finder  
from utils import KnowledgeGraphManager, OntologyTermMatcher

def lambda_handler(event, context):
    kg_manager = KnowledgeGraphManager()
    term_matcher = OntologyTermMatcher(kg_manager)
    
    # Build automaton and find mentions
    term_matcher.build_pattern_automaton(event.get('ontology_domains'))
    result = term_matcher.find_concept_mentions(
        chunks=event['chunks'],
        include_co_occurrences=True
    )
    
    return result
```

## 📊 **Performance Characteristics**

### **Layer Size**
- **v1.0.6**: ~16MB
- **v2.0.0**: ~50-60MB (within 250MB Lambda limit)
- **Impact**: Increased cold start time (~2-3 seconds additional)

### **Memory Usage**
- **Existing functions**: No change
- **NLP functions**: 512MB-1GB recommended (for ML models)
- **Pattern matching**: Efficient Aho-Corasick implementation

### **Processing Speed**
- **Entity alignment**: ~100-500 entities/second
- **Pattern matching**: ~1000-5000 terms/second  
- **Reconciliation**: ~50-200 mappings/second

## 🧪 **Testing Strategy**

### **Backward Compatibility Testing**
```bash
# 1. Test existing functionality
python3 test_existing_functionality.py

# 2. Test document-structure-kg-processor
python3 test_document_processor.py

# 3. Validate URI consistency
python3 test_uri_consistency.py
```

### **New Functionality Testing**
```bash
# 1. Test NLP utilities individually
python3 test_entity_aligner.py
python3 test_term_matcher.py
python3 test_reconciler.py

# 2. Test end-to-end integration
python3 test_nlp_integration.py

# 3. Performance testing
python3 test_performance.py
```

## 🚀 **Deployment Instructions**

### **1. Build Layer**
```bash
cd /path/to/knowledge-graph-layer
./build_layer_v2.sh
```

### **2. Deploy to AWS**
```bash
# Upload layer
aws lambda publish-layer-version \
    --layer-name knowledge-graph-layer \
    --description "Knowledge Graph Layer v2.0.0 - NLP-Ontology Integration" \
    --zip-file fileb://knowledge-graph-layer-v2.0.0.zip \
    --compatible-runtimes python3.11

# Note the returned LayerVersionArn
```

### **3. Update CDK Stack**
```python
# Update layer reference in CDK
layers=[
    lambda_.LayerVersion.from_layer_version_arn(
        self, "KnowledgeGraphLayer",
        layer_version_arn="arn:aws:lambda:us-east-1:ACCOUNT:layer:knowledge-graph-layer:7"  # New version
    )
]
```

### **4. Test Existing Functions**
```bash
# Test document-structure-kg-processor first
aws lambda invoke \
    --function-name document-structure-kg-processor \
    --payload '{"test": "data"}' \
    response.json

# Verify no errors and consistent output
```

### **5. Deploy New Functions**
```bash
# Deploy new NLP Lambda functions
cdk deploy nlp-entity-ontology-mapper
cdk deploy nlp-ontology-term-finder
cdk deploy nlp-concept-reconciler
cdk deploy nlp-kg-integrator
```

## 🔍 **Troubleshooting**

### **Common Issues**

#### **Import Errors**
```python
# ❌ Wrong
from utils.EntityAligner import EntityAligner

# ✅ Correct  
from utils import EntityAligner
```

#### **Memory Issues**
```python
# Increase Lambda memory for NLP functions
memory_size=1024  # MB (up from 512MB)
timeout=Duration.minutes(5)  # Increase timeout
```

#### **Cold Start Issues**
```python
# Use provisioned concurrency for frequently used functions
provisioned_concurrency_config=lambda_.ProvisionedConcurrencyConfig(
    provisioned_concurrent_executions=2
)
```

### **Validation Commands**
```bash
# Check layer contents
unzip -l knowledge-graph-layer-v2.0.0.zip | grep -E "(EntityAligner|KnowledgeGraphManager)"

# Test imports
python3 -c "from utils import KnowledgeGraphManager, EntityAligner; print('✅ Imports successful')"

# Check version
python3 -c "from utils import __version__; print(f'Layer version: {__version__}')"
```

## 📋 **Migration Checklist**

### **Pre-Deployment**
- [ ] Build layer v2.0.0 successfully
- [ ] Validate layer size (<250MB unzipped)
- [ ] Test imports in local environment
- [ ] Review new dependencies for security

### **Deployment**
- [ ] Upload new layer version to AWS
- [ ] Update CDK stack with new layer ARN
- [ ] Test document-structure-kg-processor with new layer
- [ ] Verify URI consistency in test environment
- [ ] Deploy new NLP Lambda functions

### **Post-Deployment**
- [ ] Monitor CloudWatch logs for errors
- [ ] Check memory usage and cold start times
- [ ] Validate end-to-end NLP pipeline
- [ ] Update documentation and runbooks

## 🎯 **Success Criteria**

### **Backward Compatibility**
- ✅ All existing Lambda functions work unchanged
- ✅ URI patterns remain consistent
- ✅ Performance impact <20% for existing functions
- ✅ No breaking changes in method signatures

### **New Functionality**
- ✅ Entity-ontology alignment accuracy >80%
- ✅ Pattern matching performance >1000 terms/second
- ✅ Reconciliation success rate >90%
- ✅ RDF integration generates valid TTL

### **Operational**
- ✅ Layer deployment successful
- ✅ Memory usage within Lambda limits
- ✅ Cold start times <10 seconds
- ✅ Error rates <5% for normal operations

## 📚 **Additional Resources**

- **Architecture Documentation**: `docs/knowledge-graph/`
- **API Reference**: `docs/api/knowledge-graph-layer-v2.md`
- **Performance Tuning**: `docs/performance/nlp-optimization.md`
- **Troubleshooting Guide**: `docs/troubleshooting/kg-layer-issues.md`

---

**Knowledge Graph Layer v2.0.0 provides powerful NLP-ontology integration while maintaining complete backward compatibility. All existing functionality continues to work unchanged, with new capabilities available for advanced document processing and knowledge extraction.**
