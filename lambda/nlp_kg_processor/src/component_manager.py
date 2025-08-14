"""
Component Manager

Manages initialization and lifecycle of knowledge graph layer components.
"""

import logging
from typing import Dict, Any

# Layer imports - using the correct import pattern
from utils.EntityAlignmentManager import EntityAlignmentManager  # NEW: Contextual alignment manager
from utils.KnowledgeGraphManager import KnowledgeGraphManager
from utils.OntologyManager import OntologyManager
from utils.NLPKGIntegrator import NLPKGIntegrator
from utils.TripleManager import TripleManager
from utils.URIManager import URIManager

logger = logging.getLogger(__name__)


class ComponentManager:
    """
    Manages initialization and configuration of layer components.
    """
    
    def initialize_components(self) -> Dict[str, Any]:
        """
        Initialize all layer components needed for processing.
        
        Returns:
            Dictionary of initialized components for reuse across documents
        """
        try:
            # Initialize knowledge graph manager first (needed by other components)
            kg_manager = KnowledgeGraphManager()
            
            # Initialize ontology manager
            ontology_manager = OntologyManager()
            
            # Load ontologies from Neptune (for backward compatibility)
            # FIXME ontology manager doesn't have a load_xxx method
            try:
                climate_ontology = ontology_manager.load_climate_risk_ontology()
            except Exception as e:
                logger.warning(f"Could not load climate ontology: {e}")
                climate_ontology = None
                
            try:
                geonames_ontology = ontology_manager.load_geonames_ontology()
            except Exception as e:
                logger.warning(f"Could not load geonames ontology: {e}")
                geonames_ontology = None
            
            # CHANGE: Use EntityAlignmentManager instead of EntityAligner
            # This provides both basic and contextual alignment based on environment variables
            entity_aligner = EntityAlignmentManager(kg_manager)
            
            # Initialize other components (unchanged)
            nlp_kg_integrator = NLPKGIntegrator(kg_manager)
            triple_manager = TripleManager(kg_manager)
            uri_manager = URIManager()
            
            components = {
                'kg_manager': kg_manager,
                'ontology_manager': ontology_manager,
                'entity_aligner': entity_aligner,  # Same interface, enhanced implementation
                'nlp_kg_integrator': nlp_kg_integrator,
                'triple_manager': triple_manager,
                'uri_manager': uri_manager,
                'climate_ontology': climate_ontology,    # Maintained for backward compatibility
                'geonames_ontology': geonames_ontology   # Maintained for backward compatibility
            }
            
            # Log alignment configuration
            alignment_stats = entity_aligner.get_alignment_statistics()
            logger.info(f"Components initialized successfully. Contextual alignment: {alignment_stats.get('contextual_enabled', False)}")
            
            return components
            
        except Exception as e:
            logger.error(f"Component initialization failed: {str(e)}")
            raise
