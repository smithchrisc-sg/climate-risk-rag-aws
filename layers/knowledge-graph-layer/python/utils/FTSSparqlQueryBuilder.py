#!/usr/bin/env python3
"""
FTS SPARQL Query Builder - Builds Neptune FTS-enhanced SPARQL queries for contextual entity alignment

Specializes in geographic entity queries using geonames ontology with proper Neptune FTS SERVICE syntax.
"""

import os
import logging
from typing import Dict, List, Any, Optional

# Import constants from OntologyManager
from .OntologyManager import (
    GEONAMES_ONTOLOGY_DATA_GRAPH_IRI,
    GEONAMES_ONTOLOGY_GRAPH_IRI,
    GEONAMES_NAMESPACE_IRI,
    CLIMATE_RISK_NAMESPACE_IRI
)

class FTSSparqlQueryBuilder:
    """
    Builds Neptune FTS-enhanced SPARQL queries for contextual entity disambiguation
    
    Uses proper Neptune FTS SERVICE syntax with OpenSearch integration
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Get OpenSearch endpoint from environment
        self.opensearch_endpoint = os.getenv('OPENSEARCH_ENDPOINT', '')
        if not self.opensearch_endpoint:
            self.logger.warning("OPENSEARCH_ENDPOINT not configured - FTS queries may fail")
        
        # SPARQL prefixes for Neptune FTS queries
        ## NOTE: the gn prefix is not what we expect - it's the geonames ontology data graph iri.  This is what the OpenSearch amazon_neptune index is using. 
        self.fts_prefixes = f"""
        PREFIX gn: <{GEONAMES_ONTOLOGY_GRAPH_IRI}#>
        PREFIX kr: <{CLIMATE_RISK_NAMESPACE_IRI}>
        PREFIX neptune-fts: <http://aws.amazon.com/neptune/vocab/v01/services/fts#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        """
    
    def _should_skip_entity(self, entity_text: str) -> bool:
        """Determine if entity should be skipped due to likely poor match quality"""
        
        # Skip entities with 2+ words (more aggressive filtering)
        word_count = len(entity_text.split())
        if word_count >= 2:
            self.logger.info(f"FTSSparqlQueryBuilder: Skipping multi-word entity '{entity_text}' ({word_count} words)")
            return True
        
        # Skip entities with problematic terms that cause timeouts
        problematic_terms = {
            'region', 'area', 'zone', 'district', 'territory', 
            'sector', 'division', 'department', 'office', 'center',
            'administration', 'administrative', 'municipality', 'province',
            'asia', 'africa', 'europe', 'america'  # Geographic regions that are too broad
        }
        
        entity_lower = entity_text.lower()
        for term in problematic_terms:
            if term in entity_lower:
                self.logger.info(f"FTSSparqlQueryBuilder: Skipping entity '{entity_text}' containing problematic term '{term}'")
                return True
        
        return False
    
    def build_location_query(self, entity_text: str, document_metadata: Dict[str, Any], 
                           chunk_context: Dict[str, Any]) -> Optional[str]:
        """
        Build Neptune FTS-enhanced SPARQL query for LOCATION entity disambiguation
        
        Args:
            entity_text: The location name to search for
            document_metadata: Document title, keywords for context
            chunk_context: Co-occurring entities and semantic signals
            
        Returns:
            Neptune FTS SPARQL query string with proper SERVICE syntax, or None if entity should be skipped
        """
        
        self.logger.info(f"FTSSparqlQueryBuilder: Building location query for entity '{entity_text}'")
        
        # Pre-filter problematic entities
        if self._should_skip_entity(entity_text):
            return None  # Signal to skip this entity
        
        self.logger.info(f"FTSSparqlQueryBuilder: OpenSearch endpoint: {self.opensearch_endpoint}")
        
        # Use phrase matching for entities with whitespace
        has_whitespace = ' ' in entity_text.strip()
        if has_whitespace:
            # Use phrase query syntax for exact matching
            escaped_entity = self._escape_sparql_string(entity_text)
            search_query = f'"{escaped_entity}"'  # Double quotes for phrase matching
            fts_limit = 20  # Stricter limit for phrase queries
            self.logger.info(f"FTSSparqlQueryBuilder: Using phrase matching for entity with whitespace '{entity_text}'")
        else:
            # Single word can use regular matching
            escaped_entity = self._escape_sparql_string(entity_text)
            search_query = f'"{escaped_entity}"'  # Still use double quotes for consistency
            fts_limit = 50
            self.logger.info(f"FTSSparqlQueryBuilder: Using regular matching for single-word entity '{entity_text}'")
        
        self.logger.info(f"FTSSparqlQueryBuilder: Final search query: {search_query}")
        
        # Build Neptune FTS query with proper SERVICE syntax
        query = f"""
        {self.fts_prefixes}
        
        SELECT ?entity ?label ?country ?admin1 ?featureClass ?featureCode ?lat ?lon ?population ?parentCountry ?parentAdmin1Name
        WHERE {{
            SERVICE neptune-fts:search {{
                neptune-fts:config neptune-fts:endpoint '{self.opensearch_endpoint}' .
                neptune-fts:config neptune-fts:queryType 'match' .
                neptune-fts:config neptune-fts:field gn:name .
                neptune-fts:config neptune-fts:query '{search_query}' .
                neptune-fts:config neptune-fts:return ?entity .
            }}

            GRAPH <{GEONAMES_ONTOLOGY_DATA_GRAPH_IRI}> {{
                ?entity gn:name ?label .
                OPTIONAL {{ ?entity gn:parentADM1 ?admin1 }}
                OPTIONAL {{ ?entity gn:featureClass ?featureClass }}
                OPTIONAL {{ ?entity gn:featureCode ?featureCode }}
                OPTIONAL {{ ?entity gn:lat ?lat ; gn:long ?lon }}
                OPTIONAL {{ ?entity gn:population ?population }}
                OPTIONAL {{ 
                    ?entity gn:parentCountry ?parentCountryEntity .
                    ?parentCountryEntity gn:name ?parentCountry 
                }}  
                OPTIONAL {{ ?admin1 gn:name ?parentAdmin1Name }}
            }}

            FILTER( !BOUND(?featureClass) || STRAFTER(STR(?featureClass), "#") IN ("P","A") )
        }}
        ORDER BY DESC(?population)
        LIMIT {fts_limit}
        """
        
        self.logger.info(f"FTSSparqlQueryBuilder: Built Neptune FTS query for '{entity_text}' targeting geonames data graph")
        self.logger.debug(f"FTSSparqlQueryBuilder: Complete query for '{entity_text}':\n{query}")
        return query
    
    def build_location_query_with_alternates(self, entity_text: str, document_metadata: Dict[str, Any], 
                                           chunk_context: Dict[str, Any]) -> str:
        """
        Build Neptune FTS query that searches multiple geonames fields (name, alternateName, asciiname)
        
        Args:
            entity_text: The location name to search for
            document_metadata: Document title, keywords for context
            chunk_context: Co-occurring entities and semantic signals
            
        Returns:
            Neptune FTS SPARQL query string searching multiple fields
        """
        
        # Escape entity text for SPARQL
        escaped_entity_text = self._escape_sparql_string(entity_text)
        
        # Build query that searches multiple fields with UNION
        query = f"""
        {self.fts_prefixes}
        
        SELECT ?entity ?label ?country ?admin1 ?featureClass ?lat ?lon ?population 
               ?parentCountry ?parentAdmin1Name WHERE {{
          
          {{
            # Search primary name field
            SERVICE neptune-fts:search {{
              neptune-fts:config neptune-fts:endpoint '{self.opensearch_endpoint}' .
              neptune-fts:config neptune-fts:queryType 'match' .
              neptune-fts:config neptune-fts:field gn:name .
              neptune-fts:config neptune-fts:query '{escaped_entity_text}' .
              neptune-fts:config neptune-fts:return ?entity .
            }}
          }} UNION {{
            # Search alternate names
            SERVICE neptune-fts:search {{
              neptune-fts:config neptune-fts:endpoint '{self.opensearch_endpoint}' .
              neptune-fts:config neptune-fts:queryType 'match' .
              neptune-fts:config neptune-fts:field gn:alternateName .
              neptune-fts:config neptune-fts:query '{escaped_entity_text}' .
              neptune-fts:config neptune-fts:return ?entity .
            }}
          }} UNION {{
            # Search ASCII names
            SERVICE neptune-fts:search {{
              neptune-fts:config neptune-fts:endpoint '{self.opensearch_endpoint}' .
              neptune-fts:config neptune-fts:queryType 'match' .
              neptune-fts:config neptune-fts:field gn:asciiname .
              neptune-fts:config neptune-fts:query '{escaped_entity_text}' .
              neptune-fts:config neptune-fts:return ?entity .
            }}
          }}
          
          # Query geonames data within the proper named graph
          GRAPH <{GEONAMES_ONTOLOGY_DATA_GRAPH_IRI}> {{
            ?entity gn:name ?label .
            
            # Get geographic hierarchy for context matching
            OPTIONAL {{ ?entity gn:countryCode ?country }}
            OPTIONAL {{ ?entity gn:parentADM1 ?admin1 }}
            OPTIONAL {{ ?entity gn:featureClass ?featureClass }}
            
            # Get coordinates and population for scoring
            OPTIONAL {{ ?entity gn:lat ?lat ; gn:long ?lon }}
            OPTIONAL {{ ?entity gn:population ?population }}
            
            # Get parent region names for context scoring
            OPTIONAL {{ 
              ?entity gn:parentCountry ?parentCountryEntity .
              ?parentCountryEntity gn:name ?parentCountry 
            }}
            OPTIONAL {{ 
              ?admin1 gn:name ?parentAdmin1Name 
            }}
          }}
          
          # Filter to populated places and administrative divisions
          FILTER(!BOUND(?featureClass) || STRAFTER(STR(?featureClass), "#") IN ("P","A"))
        }}
        ORDER BY DESC(?population)
        LIMIT 10
        """
        
        self.logger.debug(f"Built Neptune FTS multi-field query for '{entity_text}' targeting geonames data graph")
        return query
    
    def build_climate_concept_query(self, entity_text: str, document_metadata: Dict[str, Any], 
                                  chunk_context: Dict[str, Any]) -> str:
        """
        Build Neptune FTS query for climate risk concept alignment (future enhancement)
        
        Args:
            entity_text: The concept text to search for
            document_metadata: Document title, keywords for context
            chunk_context: Co-occurring entities and semantic signals
            
        Returns:
            Neptune FTS SPARQL query string for climate concepts
        """
        
        # Placeholder for future climate risk ontology FTS queries
        # This would target CLIMATE_RISK_ONTOLOGY_GRAPH_IRI when implemented
        
        self.logger.info(f"Climate concept FTS queries not yet implemented for '{entity_text}'")
        return ""
    
    def _escape_sparql_string(self, text: str) -> str:
        """
        Escape special characters in SPARQL string literals
        
        Args:
            text: Raw text to escape
            
        Returns:
            SPARQL-safe escaped string
        """
        if not text:
            return ""
        
        # Escape common SPARQL special characters
        escaped = text.replace('\\', '\\\\')  # Escape backslashes first
        escaped = escaped.replace('"', '\\"')  # Escape quotes
        escaped = escaped.replace("'", "\\'")  # Escape single quotes
        escaped = escaped.replace('\n', '\\n')  # Escape newlines
        escaped = escaped.replace('\r', '\\r')  # Escape carriage returns
        escaped = escaped.replace('\t', '\\t')  # Escape tabs
        
        return escaped
    
    def get_opensearch_endpoint(self) -> str:
        """
        Get the configured OpenSearch endpoint
        
        Returns:
            OpenSearch endpoint URL or empty string if not configured
        """
        return self.opensearch_endpoint
    
    def is_fts_enabled(self) -> bool:
        """
        Check if FTS is properly configured
        
        Returns:
            True if OpenSearch endpoint is configured, False otherwise
        """
        return bool(self.opensearch_endpoint)
