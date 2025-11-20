#!/usr/bin/env python3
"""
Integration Proposal - How to integrate contextual alignment into existing pipeline

Shows minimal changes needed to nlp_kg_processor to use the new EntityAlignmentManager
"""

# In nlp_kg_processor/src/component_manager.py
# MINIMAL CHANGE - just replace EntityAligner with EntityAlignmentManager

def initialize_components(self) -> Dict[str, Any]:
    """Initialize all required components for NLP-KG processing."""
    
    try:
        # Existing components (unchanged)
        database_manager = DatabaseManager()
        kg_manager = KnowledgeGraphManager()
        
        # CHANGE: Replace EntityAligner with EntityAlignmentManager
        # OLD: entity_aligner = EntityAligner(kg_manager)
        entity_aligner = EntityAlignmentManager(kg_manager)  # NEW
        
        # Existing components (unchanged)
        uri_manager = URIManager()
        triple_manager = TripleManager()
        nlp_kg_integrator = NLPKGIntegrator()
        
        return {
            'database_manager': database_manager,
            'kg_manager': kg_manager,
            'entity_aligner': entity_aligner,  # Same interface, enhanced implementation
            'uri_manager': uri_manager,
            'triple_manager': triple_manager,
            'nlp_kg_integrator': nlp_kg_integrator,
            'climate_ontology': None,  # Maintained for backward compatibility
            'geonames_ontology': None  # Maintained for backward compatibility
        }
    
    except Exception as e:
        self.logger.error(f"Failed to initialize components: {e}")
        raise


# In nlp_kg_processor/src/document_processor.py
# NO CHANGES NEEDED - existing interface maintained

def process_document_request(self, request: Dict[str, Any], components: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single document request through the full NLP-KG pipeline."""
    
    # ... existing code unchanged ...
    
    # Phase 5: Ontology Alignment (SAME INTERFACE, ENHANCED IMPLEMENTATION)
    logger.info(f"Phase 5: Aligning entities with ontologies for {document_id}")
    aligned_entities = components['entity_aligner'].align_entities_to_ontologies(
        entity_chunk_mappings,
        components['climate_ontology'],    # Maintained for compatibility
        components['geonames_ontology']    # Maintained for compatibility
    )
    
    # ... rest of existing code unchanged ...


# Environment Variables for Lambda Function
# Add these to the Lambda function's environment variables:

LAMBDA_ENVIRONMENT_VARIABLES = {
    # Existing variables (unchanged)
    "DATABASE_URL": "postgresql://...",
    "NEPTUNE_ENDPOINT": "solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com",
    
    # NEW: Contextual alignment feature flags
    "ENABLE_CONTEXTUAL_ALIGNMENT": "true",
    "CONTEXTUAL_ALIGNMENT_ENTITY_TYPES": "LOCATION",
    "CONTEXTUAL_ALIGNMENT_ONTOLOGIES": "geonames",
    
    # NEW: FTS query configuration
    "FTS_QUERY_TIMEOUT_MS": "2000",
    "FTS_MAX_RESULTS_PER_ONTOLOGY": "10",
    "CONTEXTUAL_CONFIDENCE_THRESHOLD": "0.3",
    
    # NEW: Context scoring weights
    "CONTEXT_WEIGHT_DOCUMENT_TITLE": "0.3",
    "CONTEXT_WEIGHT_CHUNK_COOCCURRENCE": "0.4",
    "CONTEXT_WEIGHT_SEMANTIC_SIGNALS": "0.2",
    "CONTEXT_WEIGHT_ENTITY_TYPE_MATCH": "0.1"
}


# Testing Configuration Examples

# Test 1: Enable contextual alignment for LOCATION entities only
TEST_CONFIG_LOCATION_ONLY = {
    "ENABLE_CONTEXTUAL_ALIGNMENT": "true",
    "CONTEXTUAL_ALIGNMENT_ENTITY_TYPES": "LOCATION",
    "CONTEXTUAL_ALIGNMENT_ONTOLOGIES": "geonames"
}

# Test 2: Disable contextual alignment (fallback to basic)
TEST_CONFIG_BASIC_ONLY = {
    "ENABLE_CONTEXTUAL_ALIGNMENT": "false"
}

# Test 3: Future expansion to multiple entity types
TEST_CONFIG_MULTI_ENTITY = {
    "ENABLE_CONTEXTUAL_ALIGNMENT": "true",
    "CONTEXTUAL_ALIGNMENT_ENTITY_TYPES": "LOCATION,ORG",
    "CONTEXTUAL_ALIGNMENT_ONTOLOGIES": "geonames,climate_risk"
}


# Deployment Strategy

DEPLOYMENT_PHASES = {
    "Phase 1": {
        "description": "Implement and test LOCATION + geonames only",
        "config": TEST_CONFIG_LOCATION_ONLY,
        "test_documents": ["064762102bead7b04a39"],  # Nepal document
        "success_criteria": "Improved disambiguation of location entities"
    },
    
    "Phase 2": {
        "description": "Validate backward compatibility",
        "config": TEST_CONFIG_BASIC_ONLY,
        "test_documents": ["064762102bead7b04a39"],
        "success_criteria": "No regression in basic alignment functionality"
    },
    
    "Phase 3": {
        "description": "Performance and cost validation",
        "config": TEST_CONFIG_LOCATION_ONLY,
        "test_documents": ["multiple documents"],
        "success_criteria": "Acceptable query performance and AWS costs"
    }
}


# Monitoring and Observability

MONITORING_METRICS = {
    "alignment_method_used": "contextual vs basic",
    "entities_processed_contextual": "count of entities using contextual alignment",
    "entities_processed_basic": "count of entities using basic alignment",
    "fts_query_latency": "average FTS-SPARQL query time",
    "alignment_confidence_scores": "distribution of confidence scores",
    "context_signals_detected": "types and frequency of context signals"
}


# Error Handling and Fallback

ERROR_HANDLING_STRATEGY = {
    "fts_query_timeout": "Fall back to basic alignment",
    "neptune_connection_error": "Fall back to basic alignment",
    "contextual_aligner_initialization_error": "Disable contextual alignment, use basic only",
    "scoring_engine_error": "Use base FTS scores without contextual boosting"
}
