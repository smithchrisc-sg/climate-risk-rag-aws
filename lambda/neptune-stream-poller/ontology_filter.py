#!/usr/bin/env python3
"""
Ontology Filter for Neptune Stream Processing - Positive Filtering Approach
Filters Neptune Stream records using a whitelist approach: only index statements we explicitly care about.

This approach is more efficient and precise than exclusion-based filtering.
For each ontology, we define exactly which predicates we want to index for FTS.
"""

import logging
import os
from typing import Dict, List, Any, Optional, Set, Tuple

logger = logging.getLogger(__name__)

class OntologyFilter:
    """
    Positive filtering for Neptune Stream records - only index statements we explicitly want
    """
    
    def __init__(self):
        """Initialize the ontology filter with positive filtering rules"""
        
        # Load filtering rules
        self.filtering_rules = self._load_filtering_rules()
        
        # Configuration flags
        self.filtering_enabled = os.getenv('ONTOLOGY_FILTERING_ENABLED', 'false').lower() == 'true'
        self.log_filtered_records = os.getenv('LOG_FILTERED_RECORDS', 'false').lower() == 'true'
        
        logger.info(f"OntologyFilter initialized - Enabled: {self.filtering_enabled}")
        if self.filtering_enabled:
            logger.info(f"Filtering rules loaded for {len(self.filtering_rules)} ontologies")
            for ontology, rules in self.filtering_rules.items():
                logger.info(f"  {ontology}: {len(rules)} predicates")
    
    def _load_filtering_rules(self) -> Dict[str, Set[str]]:
        """
        Load positive filtering rules: ontology -> set of predicates to index
        
        Returns:
            Dict mapping ontology graph URIs to sets of predicates to index
        """
        
        # Default rules - only index these specific predicates for FTS
        default_rules = {
            # Geonames ontology schema - vocabulary definitions and labels
            'http://www.geonames.org/ontology': {
                'http://www.w3.org/2000/01/rdf-schema#label',
                'http://www.w3.org/2000/01/rdf-schema#comment',
                'http://www.w3.org/2004/02/skos/core#prefLabel',
                'http://www.w3.org/2004/02/skos/core#altLabel',
                'http://www.w3.org/2004/02/skos/core#definition'
            },
            
            # Geonames data - actual place names for location lookup
            'http://www.geonames.org/ontology/data': {
                'http://www.geonames.org/ontology#name',
                'http://www.geonames.org/ontology#alternateName',
                'http://www.geonames.org/ontology#officialName',
                'http://www.geonames.org/ontology#shortName'
            },
            
            # Climate risk ontology - labels and descriptions for concept lookup
            'http://climate-risk-ontology': {
                'http://www.w3.org/2000/01/rdf-schema#label',
                'http://www.w3.org/2000/01/rdf-schema#comment',
                'http://www.w3.org/2004/02/skos/core#prefLabel',
                'http://www.w3.org/2004/02/skos/core#altLabel',
                'http://www.w3.org/2004/02/skos/core#definition',
                'http://www.w3.org/2004/02/skos/core#note',
                'http://climate-risk-ontology#description'
            },
            
            # RDFS/SKOS core - standard semantic web predicates
            'http://www.w3.org/2000/01/rdf-schema': {
                'http://www.w3.org/2000/01/rdf-schema#label',
                'http://www.w3.org/2000/01/rdf-schema#comment'
            },
            
            'http://www.w3.org/2004/02/skos/core': {
                'http://www.w3.org/2004/02/skos/core#prefLabel',
                'http://www.w3.org/2004/02/skos/core#altLabel',
                'http://www.w3.org/2004/02/skos/core#definition',
                'http://www.w3.org/2004/02/skos/core#note'
            }
        }
        
        # Allow environment variable override
        env_rules = os.getenv('ONTOLOGY_FILTERING_RULES', '')
        if env_rules:
            try:
                import json
                custom_rules = json.loads(env_rules)
                logger.info("Using custom filtering rules from environment")
                return {k: set(v) for k, v in custom_rules.items()}
            except Exception as e:
                logger.warning(f"Failed to parse custom filtering rules: {e}, using defaults")
        
        return {k: set(v) for k, v in default_rules.items()}
    
    def should_index_record(self, record: Dict[str, Any]) -> bool:
        """
        Determine if a stream record should be indexed using positive filtering
        
        Args:
            record: Neptune stream record
            
        Returns:
            bool: True if record matches a statement we explicitly want to index
        """
        
        # If filtering is disabled, index everything
        if not self.filtering_enabled:
            return True
        
        try:
            # Handle Neptune stream record format
            record_data = record.get('data', record)  # DATA_STR constant = 'data'
            
            # Extract statement from Neptune stream format
            if 'eventData' in record_data:
                stmt = record_data['eventData']['stmt']
            elif 'stmt' in record_data:
                stmt = record_data['stmt']
            else:
                # Unknown format, log and exclude
                if self.log_filtered_records:
                    logger.warning(f"Unknown record format: {list(record_data.keys())}")
                return False
            
            # Get statement components
            graph_uri = stmt.get('graph', '')
            predicate_uri = stmt.get('predicate', '')
            obj_data = stmt.get('object', {})
            
            # Must be a literal for FTS indexing
            if obj_data.get('type') != 'literal':
                if self.log_filtered_records:
                    logger.debug(f"Skipping non-literal: {predicate_uri}")
                return False
            
            # Check if this statement matches our positive filtering rules
            should_index = self._matches_filtering_rules(graph_uri, predicate_uri)
            
            # Log decision if enabled
            if self.log_filtered_records:
                if should_index:
                    obj_value = obj_data.get('value', '')[:50]
                    logger.debug(f"✅ Including: {self._shorten_uri(graph_uri)} | {self._shorten_uri(predicate_uri)} | {obj_value}...")
                else:
                    logger.debug(f"❌ Excluding: {self._shorten_uri(graph_uri)} | {self._shorten_uri(predicate_uri)}")
            
            return should_index
            
        except Exception as e:
            logger.error(f"Error filtering record: {e}")
            if self.log_filtered_records:
                logger.error(f"Record structure: {record}")
            # Default to exclude on error to be safe
            return False
    
    def _matches_filtering_rules(self, graph_uri: str, predicate_uri: str) -> bool:
        """
        Check if a graph/predicate combination matches our positive filtering rules
        
        Args:
            graph_uri: Graph URI from the statement
            predicate_uri: Predicate URI from the statement
            
        Returns:
            bool: True if this statement should be indexed
        """
        
        # Check exact graph matches first
        if graph_uri in self.filtering_rules:
            return predicate_uri in self.filtering_rules[graph_uri]
        
        # Check partial graph matches (for flexibility)
        for rule_graph, predicates in self.filtering_rules.items():
            if rule_graph in graph_uri or graph_uri in rule_graph:
                if predicate_uri in predicates:
                    return True
        
        # No match found
        return False
    
    def _shorten_uri(self, uri: str) -> str:
        """Shorten URI for logging readability"""
        if not uri:
            return uri
        
        # Common prefixes for readability
        prefixes = {
            'http://www.geonames.org/ontology#': 'gn:',
            'http://www.w3.org/2000/01/rdf-schema#': 'rdfs:',
            'http://www.w3.org/2004/02/skos/core#': 'skos:',
            'http://climate-risk-ontology#': 'cro:',
            'http://www.geonames.org/ontology': 'gn-ont',
            'http://climate-risk-ontology': 'cro-ont'
        }
        
        for full, short in prefixes.items():
            if uri.startswith(full):
                return uri.replace(full, short)
        
        # Return last part of URI if no prefix match
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        
        return uri
    
    def filter_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter a batch of stream records using positive filtering
        
        Args:
            records: List of Neptune stream records
            
        Returns:
            List of records that match our positive filtering rules
        """
        
        if not self.filtering_enabled:
            logger.debug(f"Filtering disabled - processing all {len(records)} records")
            return records
        
        filtered_records = []
        stats = {'total': len(records), 'by_ontology': {}, 'by_predicate': {}}
        
        for record in records:
            if self.should_index_record(record):
                filtered_records.append(record)
                
                # Collect stats if logging enabled
                if self.log_filtered_records:
                    try:
                        record_data = record.get('data', record)
                        if 'eventData' in record_data:
                            stmt = record_data['eventData']['stmt']
                        elif 'stmt' in record_data:
                            stmt = record_data['stmt']
                        else:
                            continue
                        
                        graph = self._shorten_uri(stmt.get('graph', ''))
                        predicate = self._shorten_uri(stmt.get('predicate', ''))
                        
                        stats['by_ontology'][graph] = stats['by_ontology'].get(graph, 0) + 1
                        stats['by_predicate'][predicate] = stats['by_predicate'].get(predicate, 0) + 1
                        
                    except Exception:
                        pass  # Don't fail filtering due to stats collection
        
        # Log filtering results
        original_count = len(records)
        filtered_count = len(filtered_records)
        filtered_out = original_count - filtered_count
        
        if original_count > 0:
            filter_percentage = (filtered_out / original_count) * 100
            logger.info(f"Positive filtering: {original_count} → {filtered_count} records ({filter_percentage:.1f}% filtered out)")
            
            # Log detailed stats if enabled
            if self.log_filtered_records and filtered_count > 0:
                logger.info(f"Indexed by ontology: {dict(stats['by_ontology'])}")
                logger.info(f"Indexed by predicate: {dict(stats['by_predicate'])}")
        
        return filtered_records
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """Get current filter configuration and stats"""
        
        return {
            'filtering_enabled': self.filtering_enabled,
            'filtering_approach': 'positive_whitelist',
            'ontologies_count': len(self.filtering_rules),
            'total_predicates': sum(len(predicates) for predicates in self.filtering_rules.values()),
            'filtering_rules': {
                ontology: list(predicates) for ontology, predicates in self.filtering_rules.items()
            },
            'log_filtered_records': self.log_filtered_records
        }
    
    def add_filtering_rule(self, ontology_graph: str, predicates: List[str]):
        """
        Add a new filtering rule at runtime
        
        Args:
            ontology_graph: Graph URI to filter for
            predicates: List of predicate URIs to index for this graph
        """
        
        if ontology_graph not in self.filtering_rules:
            self.filtering_rules[ontology_graph] = set()
        
        self.filtering_rules[ontology_graph].update(predicates)
        logger.info(f"Added filtering rule: {ontology_graph} -> {len(predicates)} predicates")

# Global filter instance (singleton pattern)
_ontology_filter = None

def get_ontology_filter() -> OntologyFilter:
    """Get the global ontology filter instance"""
    global _ontology_filter
    if _ontology_filter is None:
        _ontology_filter = OntologyFilter()
    return _ontology_filter

# For testing and configuration
if __name__ == "__main__":
    # Test the positive filtering approach
    filter_instance = OntologyFilter()
    
    # Sample test records
    test_records = [
        {
            'data': {
                'eventData': {
                    'stmt': {
                        'graph': 'http://www.geonames.org/ontology',
                        'subject': 'https://sws.geonames.org/1642911/',
                        'predicate': 'http://www.geonames.org/ontology#name',
                        'object': {'type': 'literal', 'value': 'Jakarta'}
                    }
                }
            }
        },
        {
            'data': {
                'eventData': {
                    'stmt': {
                        'graph': 'http://www.geonames.org/ontology',
                        'subject': 'https://sws.geonames.org/1642911/',
                        'predicate': 'http://www.geonames.org/ontology#alternateName',
                        'object': {'type': 'literal', 'value': 'Djakarta', 'language': 'af'}
                    }
                }
            }
        },
        {
            'data': {
                'eventData': {
                    'stmt': {
                        'graph': 'http://www.geonames.org/ontology',
                        'subject': 'https://sws.geonames.org/1642911/',
                        'predicate': 'http://www.w3.org/2000/01/rdf-schema#isDefinedBy',
                        'object': {'type': 'uri', 'value': 'https://sws.geonames.org/1642911/about.rdf'}
                    }
                }
            }
        },
        {
            'data': {
                'eventData': {
                    'stmt': {
                        'graph': 'http://document-data',
                        'predicate': 'http://example.org/document#content',
                        'object': {'type': 'literal', 'value': 'Document content...'}
                    }
                }
            }
        }
    ]
    
    # Test positive filtering
    filter_instance.filtering_enabled = True
    filter_instance.log_filtered_records = True
    
    filtered = filter_instance.filter_records(test_records)
    print(f"\nPositive filtering results:")
    print(f"Original: {len(test_records)}, Filtered: {len(filtered)}")
    print(f"Filter stats: {filter_instance.get_filter_stats()}")
    
    # Should only include gn:name and gn:alternateName literals
    # Should exclude rdfs:isDefinedBy (not a literal) and document content (wrong graph)
