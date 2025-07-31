#!/usr/bin/env python3
"""
Admin Ontology Manager Lambda - Administrative utility for ontology management operations
Provides API endpoints for loading, validating, and managing ontology data in S3
"""

import json
import logging
import os
import time
import traceback
from typing import Dict, Any, Optional, List

# Import from knowledge graph layer
from utils.OntologyManager import OntologyManager
from utils.KnowledgeGraphManager import KnowledgeGraphManager
from utils.kg_exceptions import KGValidationError, KGDataFormatError
from rdflib import URIRef
from utils.kg_exceptions import KGQueryError, KGValidationError, KGDataFormatError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Admin Lambda handler for ontology management operations
    
    Supported operations:
    - load_ontology_from_s3: Load ontology from S3 key
    - load_ontology_from_content: Load ontology from provided content
    - persist_ontology_to_neptune: Persist loaded ontology to Neptune
    - get_concepts: Retrieve ontology concepts
    - get_concept_details: Get detailed concept information
    - find_concepts_by_label: Search concepts by label
    - validate_concept: Validate concept existence
    - get_concept_relationships: Get concept relationships
    - get_ontology_stats: Get ontology statistics
    - clear_cache: Clear ontology cache
    """
    
    try:
        # Parse the event
        operation = event.get('operation')
        parameters = event.get('parameters', {})
        
        logger.info(f"Admin ontology operation requested: {operation}")
        logger.debug(f"Parameters: {parameters}")
        
        if not operation:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameter: operation',
                    'supported_operations': [
                        'load_ontology_from_s3',
                        'load_ontology_from_content',
                        'persist_ontology_to_neptune',
                        'load_and_persist_ontology',
                        'execute_sparql_query',
                        'get_concepts',
                        'get_concept_details',
                        'find_concepts_by_label',
                        'validate_concept',
                        'get_concept_relationships',
                        'get_ontology_stats',
                        'clear_cache'
                    ]
                })
            }
        
        # Initialize ontology manager with required namespaces
        from rdflib import Namespace
        
        kr_ns = Namespace("https://solve.global/kr/")
        dcterms_ns = Namespace("http://purl.org/dc/terms/")
        foaf_ns = Namespace("http://xmlns.com/foaf/0.1/")
        skos_ns = Namespace("http://www.w3.org/2004/02/skos/core#")
        
        ontology_manager = OntologyManager(kr_ns, dcterms_ns, foaf_ns, skos_ns)
        
        # Route to appropriate operation
        if operation == 'load_ontology_from_s3':
            result = handle_load_ontology_from_s3(ontology_manager, parameters)
            
        elif operation == 'load_ontology_from_content':
            result = handle_load_ontology_from_content(ontology_manager, parameters)
            
        elif operation == 'persist_ontology_to_neptune':
            # Initialize KG manager for Neptune operations
            kg_manager = KnowledgeGraphManager()
            result = handle_persist_ontology_to_neptune(ontology_manager, kg_manager, parameters)
            
        elif operation == 'load_and_persist_ontology':
            # Initialize KG manager for Neptune operations
            kg_manager = KnowledgeGraphManager()
            result = handle_load_and_persist_ontology(ontology_manager, kg_manager, parameters)
            
        elif operation == 'execute_sparql_query':
            # Initialize KG manager for Neptune operations
            kg_manager = KnowledgeGraphManager()
            result = handle_execute_sparql_query(kg_manager, parameters)
            
        elif operation == 'get_concepts':
            result = handle_get_concepts(ontology_manager, parameters)
            
        elif operation == 'get_concept_details':
            result = handle_get_concept_details(ontology_manager, parameters)
            
        elif operation == 'find_concepts_by_label':
            result = handle_find_concepts_by_label(ontology_manager, parameters)
            
        elif operation == 'validate_concept':
            result = handle_validate_concept(ontology_manager, parameters)
            
        elif operation == 'get_concept_relationships':
            result = handle_get_concept_relationships(ontology_manager, parameters)
            
        elif operation == 'get_ontology_stats':
            result = handle_get_ontology_stats(ontology_manager, parameters)
            
        elif operation == 'clear_cache':
            result = handle_clear_cache(ontology_manager, parameters)
            
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Unsupported operation: {operation}',
                    'supported_operations': [
                        'load_ontology_from_s3',
                        'load_ontology_from_content',
                        'persist_ontology_to_neptune',
                        'load_and_persist_ontology',
                        'execute_sparql_query',
                        'get_concepts', 
                        'get_concept_details',
                        'find_concepts_by_label',
                        'validate_concept',
                        'get_concept_relationships',
                        'get_ontology_stats',
                        'clear_cache'
                    ]
                })
            }
        
        logger.info(f"Operation {operation} completed successfully")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'operation': operation,
                'success': True,
                'result': result
            })
        }
        
    except (KGQueryError, KGValidationError, KGDataFormatError) as e:
        logger.error(f"Knowledge graph error in operation {operation}: {e}")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'operation': operation,
                'success': False,
                'error': str(e),
                'error_type': 'KnowledgeGraphError'
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in operation {operation}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'operation': operation,
                'success': False,
                'error': str(e),
                'error_type': 'InternalError'
            })
        }

def handle_load_ontology_from_s3(ontology_manager, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Handle loading ontology from S3"""
    s3_key = parameters.get('s3_key')
    format_type = parameters.get('format', 'turtle')
    force_reload = parameters.get('force_reload', False)
    named_graph = parameters.get('named_graph')
    
    if not s3_key:
        raise KGValidationError("Missing required parameter: s3_key")
    
    logger.info(f"Loading ontology from S3: {s3_key} (format: {format_type}, named_graph: {named_graph})")
    
    success = ontology_manager.load_ontology_from_s3(s3_key, format_type, force_reload, named_graph)
    
    return {
        'loaded': success,
        's3_key': s3_key,
        'format': format_type,
        'force_reload': force_reload,
        'named_graph': named_graph,
        'ontology_stats': ontology_manager.get_stats()
    }

def handle_load_ontology_from_content(ontology_manager, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Handle loading ontology from provided content"""
    ttl_content = parameters.get('ttl_content')
    force_reload = parameters.get('force_reload', False)
    named_graph = parameters.get('named_graph')
    
    if not ttl_content:
        raise KGValidationError("Missing required parameter: ttl_content")
    
    logger.info(f"Loading ontology from provided TTL content (named_graph: {named_graph})")
    
    success = ontology_manager.load_ontology_from_ttl(ttl_content, force_reload, named_graph)
    
    return {
        'loaded': success,
        'content_length': len(ttl_content),
        'force_reload': force_reload,
        'named_graph': named_graph,
        'ontology_stats': ontology_manager.get_stats()
    }

def handle_get_concepts(ontology_manager, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Handle getting ontology concepts"""
    concept_type = parameters.get('concept_type')
    
    logger.info(f"Getting concepts (type filter: {concept_type})")
    
    concepts = ontology_manager.get_concepts(concept_type)
    
    return {
        'concepts': concepts,
        'concept_count': len(concepts),
        'concept_type_filter': concept_type
    }

def handle_get_concept_details(ontology_manager, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Handle getting concept details"""
    concept_uri = parameters.get('concept_uri')
    
    if not concept_uri:
        raise KGValidationError("Missing required parameter: concept_uri")
    
    logger.info(f"Getting concept details for: {concept_uri}")
    
    details = ontology_manager.get_concept_details(concept_uri)
    
    return {
        'concept_uri': concept_uri,
        'details': details
    }

def handle_find_concepts_by_label(ontology_manager, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Handle finding concepts by label"""
    label = parameters.get('label')
    fuzzy = parameters.get('fuzzy', True)
    
    if not label:
        raise KGValidationError("Missing required parameter: label")
    
    logger.info(f"Finding concepts by label: {label} (fuzzy: {fuzzy})")
    
    concepts = ontology_manager.find_concepts_by_label(label, fuzzy)
    
    return {
        'search_label': label,
        'fuzzy_search': fuzzy,
        'concepts': concepts,
        'concept_count': len(concepts)
    }

def handle_validate_concept(ontology_manager, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Handle concept validation"""
    concept_uri = parameters.get('concept_uri')
    ontology_concept = parameters.get('ontology_concept', '')
    
    if not concept_uri:
        raise KGValidationError("Missing required parameter: concept_uri")
    
    logger.info(f"Validating concept: {concept_uri} (expected type: {ontology_concept})")
    
    is_valid = ontology_manager.validate_concept(concept_uri, ontology_concept)
    
    return {
        'concept_uri': concept_uri,
        'expected_type': ontology_concept,
        'is_valid': is_valid
    }

def handle_get_concept_relationships(ontology_manager, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Handle getting concept relationships"""
    concept_uri = parameters.get('concept_uri')
    
    if not concept_uri:
        raise KGValidationError("Missing required parameter: concept_uri")
    
    logger.info(f"Getting relationships for concept: {concept_uri}")
    
    relationships = ontology_manager.get_concept_relationships(concept_uri)
    
    return {
        'concept_uri': concept_uri,
        'relationships': relationships,
        'relationship_count': len(relationships)
    }

def handle_execute_sparql_query(kg_manager, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Handle executing SPARQL queries against Neptune"""
    query = parameters.get('query')
    
    if not query:
        raise KGValidationError("Missing required parameter: query")
    
    logger.info(f"Executing SPARQL query: {query[:100]}...")
    
    results = kg_manager.execute_sparql_query(query)
    
    return {
        'query': query,
        'results': results,
        'result_count': len(results)
    }


def handle_load_and_persist_ontology(ontology_manager, kg_manager, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Handle loading ontology from S3 and persisting to Neptune in one operation"""
    # First load the ontology
    load_result = handle_load_ontology_from_s3(ontology_manager, parameters)
    
    if not load_result.get('loaded'):
        return {
            'loaded': False,
            'persisted': False,
            'error': 'Failed to load ontology',
            'load_result': load_result
        }
    
    # Then persist to Neptune
    persist_params = {
        'named_graph': parameters.get('named_graph'),
        'method': parameters.get('persist_method', 'sparql')
    }
    persist_result = handle_persist_ontology_to_neptune(ontology_manager, kg_manager, persist_params)
    
    return {
        'loaded': True,
        'persisted': persist_result.get('persisted', False),
        'load_result': load_result,
        'persist_result': persist_result
    }


def handle_persist_ontology_to_neptune(ontology_manager, kg_manager, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Handle persisting loaded ontology to Neptune"""
    named_graph = parameters.get('named_graph')
    method = parameters.get('method', 'sparql')  # 'sparql' or 'bulk_load'
    
    if not ontology_manager._ontology_loaded:
        raise KGValidationError("No ontology loaded. Load an ontology first.")
    
    logger.info(f"Persisting ontology to Neptune using {method} method (named_graph: {named_graph})")
    
    # Serialize the ontology to TTL
    if named_graph:
        # Get the specific named graph
        from rdflib import URIRef
        named_graph_uri = URIRef(named_graph)
        named_graph_obj = ontology_manager.ontology_graph.get_context(named_graph_uri)
        ttl_content = named_graph_obj.serialize(format='turtle')
    else:
        ttl_content = ontology_manager.ontology_graph.serialize(format='turtle')
    
    if method == 'bulk_load':
        # Upload to S3 and use Neptune bulk load
        s3_key = f"ontology/neptune-load-{named_graph.replace('/', '-').replace(':', '-')}-{int(time.time())}.ttl" if named_graph else f"ontology/neptune-load-default-{int(time.time())}.ttl"
        s3_uri = kg_manager.upload_ttl_to_s3(ttl_content, s3_key)
        
        load_result = kg_manager.bulk_load_from_s3(
            s3_uri=s3_uri,
            format='turtle',
            graph_uri=named_graph
        )
        
        return {
            'persisted': True,
            'method': 'bulk_load',
            'named_graph': named_graph,
            's3_uri': s3_uri,
            'load_id': load_result.get('loadId'),
            'ttl_size': len(ttl_content),
            'triple_count': len(ontology_manager.ontology_graph)
        }
    else:
        # Use SPARQL INSERT with individual triples
        if named_graph:
            # Parse the TTL content and insert triples individually
            from rdflib import Graph as RDFGraph
            temp_graph = RDFGraph()
            temp_graph.parse(data=ttl_content, format='turtle')
            
            # Build SPARQL INSERT query with individual triples
            triples_sparql = []
            for s, p, o in temp_graph:
                # Handle subject (URI or BNode)
                if isinstance(s, URIRef):
                    subj_str = f"<{s}>"
                else:  # BNode
                    subj_str = f"_:{s}"
                
                # Handle predicate (always URI)
                pred_str = f"<{p}>"
                
                # Handle object (URI, BNode, or Literal)
                if isinstance(o, URIRef):
                    obj_str = f"<{o}>"
                elif hasattr(o, 'datatype') and hasattr(o, 'language'):  # Literal
                    literal_value = str(o).replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
                    if o.datatype:
                        obj_str = f'"{literal_value}"^^<{o.datatype}>'
                    elif o.language:
                        obj_str = f'"{literal_value}"@{o.language}'
                    else:
                        obj_str = f'"{literal_value}"'
                else:  # BNode
                    obj_str = f"_:{o}"
                
                triples_sparql.append(f"{subj_str} {pred_str} {obj_str} .")
            
            # Create SPARQL INSERT query
            sparql_insert = f"""
            INSERT DATA {{
                GRAPH <{named_graph}> {{
                    {' '.join(triples_sparql)}
                }}
            }}
            """
            success = kg_manager.execute_sparql_update(sparql_insert)
        else:
            # Use the existing bulk_insert_ttl for default graph
            success = kg_manager.bulk_insert_ttl(ttl_content, named_graph)
        
        return {
            'persisted': success,
            'method': 'sparql_insert_parsed',
            'named_graph': named_graph,
            'ttl_size': len(ttl_content),
            'triple_count': len(ontology_manager.ontology_graph)
        }
    """Handle getting ontology statistics"""
    logger.info("Getting ontology statistics")
    
    stats = ontology_manager.get_stats()
    cache_stats = ontology_manager.get_cache_stats()
    
    return {
        'ontology_stats': stats,
        'cache_stats': cache_stats
    }

def handle_clear_cache(ontology_manager, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Handle clearing ontology cache"""
    logger.info("Clearing ontology cache")
    
    ontology_manager.clear_cache()
    
    return {
        'cache_cleared': True,
        'message': 'Ontology cache has been cleared'
    }
