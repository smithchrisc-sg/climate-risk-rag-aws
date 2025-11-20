#!/usr/bin/env python3
"""
FTS SPARQL Query Builder - Builds FTS-enhanced SPARQL queries for contextual entity alignment

Specializes in geographic entity queries using geonames ontology with contextual filters.
"""

import logging
from typing import Dict, List, Any, Optional

class FTSSparqlQueryBuilder:
    """
    Builds FTS-enhanced SPARQL queries for contextual entity disambiguation
    
    Initial focus on LOCATION entities with geonames ontology
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # SPARQL prefixes for geonames
        self.geonames_prefixes = """
        PREFIX fts: <http://www.ontotext.com/owlim/fts#>
        PREFIX gn: <http://www.geonames.org/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        """
    
    def build_location_query(self, entity_text: str, document_metadata: Dict[str, Any], 
                           chunk_context: Dict[str, Any]) -> str:
        """
        Build FTS-enhanced SPARQL query for LOCATION entity disambiguation
        
        Args:
            entity_text: The location name to search for
            document_metadata: Document title, keywords for context
            chunk_context: Co-occurring entities and semantic signals
            
        Returns:
            SPARQL query string with contextual filters
        """
        
        # Base FTS query for geonames
        base_query = f"""
        {self.geonames_prefixes}
        
        SELECT ?entity ?label ?country ?admin1 ?featureClass ?lat ?lon ?population 
               ?parentCountry ?parentAdmin1Name WHERE {{
          
          # Primary FTS search
          ?entity fts:search "{entity_text}" .
          ?entity rdfs:label ?label .
          
          # Get geographic hierarchy for context matching
          ?entity gn:countryCode ?country .
          ?entity gn:parentADM1 ?admin1 .
          ?entity gn:featureClass ?featureClass .
          
          # Get parent region names for context scoring
          OPTIONAL {{ 
            ?entity gn:parentCountry ?parentCountryEntity .
            ?parentCountryEntity gn:name ?parentCountry 
          }}
          OPTIONAL {{ 
            ?admin1 gn:name ?parentAdmin1Name 
          }}
          
          # Get coordinates and population for scoring
          OPTIONAL {{ ?entity gn:lat ?lat ; gn:long ?lon }}
          OPTIONAL {{ ?entity gn:population ?population }}
          
          # Filter to populated places for location entities
          FILTER(?featureClass IN ("P.PPL", "P.PPLA", "P.PPLA2", "P.PPLC"))
        """
        
        # Add contextual filters based on document and chunk context
        contextual_filters = self._build_contextual_filters(document_metadata, chunk_context)
        
        # Complete query with filters and ordering
        complete_query = f"""
        {base_query}
        {contextual_filters}
        }}
        ORDER BY DESC(?population)
        LIMIT 10
        """
        
        self.logger.debug(f"Built FTS query for '{entity_text}' with contextual filters")
        return complete_query
    
    def _build_contextual_filters(self, document_metadata: Dict[str, Any], 
                                 chunk_context: Dict[str, Any]) -> str:
        """Build contextual SPARQL filters based on document and chunk context"""
        
        filters = []
        
        # Document-level geographic context filters
        doc_title = document_metadata.get('title', '').lower()
        
        if 'north american' in doc_title or 'usa' in doc_title or 'united states' in doc_title:
            # Boost North American locations
            filters.append('# Prefer North American locations based on document context')
            # Note: Actual boosting will be done in scoring, not filtering
        
        elif 'european' in doc_title or 'europe' in doc_title:
            # Boost European locations
            filters.append('# Prefer European locations based on document context')
        
        # Chunk-level co-occurrence filters
        entities_by_type = chunk_context.get('entities_by_type', {})
        location_entities = entities_by_type.get('LOCATION', [])
        
        if len(location_entities) > 1:
            # Multiple locations in same chunk - look for state/country patterns
            filters.append('# Multiple location entities in chunk - enhanced disambiguation needed')
        
        # Semantic signal filters
        semantic_signals = chunk_context.get('semantic_signals', [])
        if 'geographic:country_context' in semantic_signals:
            filters.append('# Country context detected in chunk')
        
        return '\n  '.join(filters) if filters else ''
    
    def build_climate_concept_query(self, entity_text: str, document_metadata: Dict[str, Any], 
                                   chunk_context: Dict[str, Any]) -> str:
        """
        Build FTS-enhanced SPARQL query for climate concept alignment
        
        Future implementation for climate risk ontology
        """
        
        # Placeholder for future climate concept queries
        climate_prefixes = """
        PREFIX fts: <http://www.ontotext.com/owlim/fts#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        """
        
        query = f"""
        {climate_prefixes}
        
        SELECT ?concept ?label ?broader ?related ?definition ?type WHERE {{
          
          # FTS search in climate risk ontology
          ?concept fts:search "{entity_text}" .
          ?concept rdfs:label ?label .
          
          # Get semantic hierarchy for context validation
          OPTIONAL {{ ?concept skos:broader ?broader }}
          OPTIONAL {{ ?concept skos:related ?related }}
          OPTIONAL {{ ?concept skos:definition ?definition }}
          OPTIONAL {{ ?concept rdf:type ?type }}
          
          # Ensure it's in climate risk ontology
          GRAPH <http://solve.global/knowledge-commons/climate-risk-ontology> {{
            ?concept rdfs:label ?label
          }}
        }}
        LIMIT 10
        """
        
        return query
    
    def build_multi_entity_cooccurrence_query(self, entities: List[str], chunk_context: Dict[str, Any]) -> str:
        """
        Build query to find relationships between co-occurring entities
        
        Future implementation for enhanced co-occurrence analysis
        """
        
        if len(entities) < 2:
            return ""
        
        # Placeholder for multi-entity relationship queries
        query = f"""
        {self.geonames_prefixes}
        
        SELECT ?entity1 ?label1 ?entity2 ?label2 ?relationship WHERE {{
          
          # Find entities that co-occur with our target entities
          ?entity1 fts:search "{entities[0]}" .
          ?entity1 rdfs:label ?label1 .
          
          # Look for related entities in the same geographic region
          ?entity1 gn:parentCountry ?country .
          ?entity2 gn:parentCountry ?country .
          ?entity2 rdfs:label ?label2 .
          
          # Filter to entities mentioned in the same chunk
          FILTER(?label2 IN ({', '.join(f'"{e}"' for e in entities[1:])}))
          
          BIND("same_country" as ?relationship)
        }}
        LIMIT 20
        """
        
        return query
