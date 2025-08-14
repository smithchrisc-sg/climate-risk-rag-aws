"""
Simplified Component Manager

Manages minimal components needed for LOCATION entity alignment using FTS SPARQL.
No complex ontology loading - just KG manager for SPARQL queries and URI manager for chunk URIs.
"""

import logging
from typing import Dict, Any

# Layer imports - minimal set needed
from utils.KnowledgeGraphManager import KnowledgeGraphManager
from utils.URIManager import URIManager

logger = logging.getLogger(__name__)


class ComponentManager:
    """
    Simplified component manager for LOCATION entity alignment.
    """
    
    def initialize_components(self) -> Dict[str, Any]:
        """
        Initialize minimal components needed for FTS SPARQL alignment.
        
        Returns:
            Dictionary of initialized components
        """
        try:
            logger.info("Initializing simplified components for LOCATION entity alignment")
            
            # Initialize knowledge graph manager (for FTS SPARQL queries)
            kg_manager = KnowledgeGraphManager()
            logger.info("KnowledgeGraphManager initialized")
            
            # Initialize URI manager (for chunk URI generation)
            uri_manager = URIManager()
            logger.info("URIManager initialized")
            
            components = {
                'kg_manager': kg_manager,
                'uri_manager': uri_manager
            }
            
            logger.info("Simplified components initialized successfully")
            return components
            
        except Exception as e:
            logger.error(f"Component initialization failed: {str(e)}")
            raise
