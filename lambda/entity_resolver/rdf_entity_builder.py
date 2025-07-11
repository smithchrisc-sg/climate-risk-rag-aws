#!/usr/bin/env python3
"""
RDF Entity Builder
Creates RDF triples for resolved entities in TTL format
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from uri_minter import URIMinter

class RDFEntityBuilder:
    """Builds RDF triples for entities"""
    
    def __init__(self):
        self.uri_minter = URIMinter()
        self.prefixes = self.uri_minter.get_namespace_prefixes()
    
    def build_entity_ttl(self, resolved_entities: List[Dict[str, Any]], doc_id: str) -> str:
        """
        Build complete TTL document for resolved entities
        
        Args:
            resolved_entities: List of resolved entity dictionaries
            doc_id: Document ID for context
            
        Returns:
            Complete TTL document as string
        """
        ttl_lines = []
        
        # Add namespace prefixes
        ttl_lines.extend(self._build_prefixes())
        ttl_lines.append("")  # Empty line after prefixes
        
        # Add document context
        doc_uri = self.uri_minter.mint_document_uri(doc_id)
        ttl_lines.extend(self._build_document_context(doc_uri, doc_id))
        ttl_lines.append("")
        
        # Process each entity
        for entity in resolved_entities:
            entity_ttl = self._build_entity_triples(entity)
            if entity_ttl:
                ttl_lines.extend(entity_ttl)
                ttl_lines.append("")  # Empty line between entities
        
        # Add chunk-entity relationships
        chunk_relationships = self._build_chunk_relationships(resolved_entities, doc_id)
        if chunk_relationships:
            ttl_lines.extend(chunk_relationships)
        
        return "\n".join(ttl_lines)
    
    def _build_prefixes(self) -> List[str]:
        """Build namespace prefix declarations"""
        prefix_lines = []
        for prefix, namespace in self.prefixes.items():
            prefix_lines.append(f"@prefix {prefix}: <{namespace}> .")
        return prefix_lines
    
    def _build_document_context(self, doc_uri: str, doc_id: str) -> List[str]:
        """Build document context triples"""
        return [
            f"# Document: {doc_id}",
            f"{doc_uri} a foaf:Document ;",
            f"    dcterms:identifier \"{doc_id}\" ;",
            f"    kr:processedAt \"{datetime.utcnow().isoformat()}Z\"^^xsd:dateTime ."
        ]
    
    def _build_entity_triples(self, entity: Dict[str, Any]) -> List[str]:
        """Build RDF triples for a single entity"""
        entity_uri = entity.get('kg_uri', '')
        rdf_type = entity.get('rdf_type', '')
        properties = entity.get('properties', {})
        
        if not entity_uri or not rdf_type:
            return []
        
        lines = []
        lines.append(f"# Entity: {entity.get('canonical_name', 'Unknown')}")
        lines.append(f"{entity_uri} a {rdf_type} ;")
        
        # Add properties
        property_lines = []
        for prop_name, prop_value in properties.items():
            if prop_value is not None:
                formatted_value = self._format_property_value(prop_value)
                if formatted_value:
                    property_lines.append(f"    {prop_name} {formatted_value}")
        
        # Join properties with semicolons and commas
        if property_lines:
            # All but last property end with semicolon
            for line in property_lines[:-1]:
                lines.append(line + " ;")
            # Last property ends with period
            lines.append(property_lines[-1] + " .")
        else:
            # If no properties, close the entity declaration
            lines[-1] = lines[-1].rstrip(' ;') + " ."
        
        return lines
    
    def _format_property_value(self, value: Any) -> str:
        """Format property value for TTL serialization"""
        if value is None:
            return None
        
        if isinstance(value, bool):
            return "true" if value else "false"
        
        if isinstance(value, (int, float)):
            return str(value)
        
        if isinstance(value, str):
            # Check if it's a URI reference
            if value.startswith(('http://', 'https://', 'kr:', 'foaf:', 'schema:', 'dcterms:', 'skos:', 'qudt:', 'time:')):
                return f"<{self.uri_minter.expand_uri(value)}>" if ':' in value and not value.startswith('http') else f"<{value}>"
            else:
                # String literal - escape quotes and newlines
                escaped = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
                return f'"{escaped}"'
        
        # For other types, convert to string
        return f'"{str(value)}"'
    
    def _build_chunk_relationships(self, resolved_entities: List[Dict[str, Any]], doc_id: str) -> List[str]:
        """Build chunk-entity relationship triples"""
        lines = []
        lines.append("# Chunk-Entity Relationships")
        
        # Group entities by chunk
        chunk_entities = {}
        for entity in resolved_entities:
            chunk_id = entity.get('source_chunk')
            if chunk_id:
                if chunk_id not in chunk_entities:
                    chunk_entities[chunk_id] = []
                chunk_entities[chunk_id].append(entity)
        
        # Build relationships for each chunk
        for chunk_id, entities in chunk_entities.items():
            chunk_uri = self.uri_minter.mint_chunk_uri(doc_id, self._extract_chunk_sequence(chunk_id))
            doc_uri = self.uri_minter.mint_document_uri(doc_id)
            
            # Chunk metadata
            lines.append(f"{chunk_uri} a kr:DocumentChunk ;")
            lines.append(f"    dcterms:isPartOf {doc_uri} ;")
            lines.append(f"    dcterms:identifier \"{chunk_id}\" ;")
            
            # Entities contained in this chunk
            entity_refs = []
            for entity in entities:
                entity_uri = entity.get('kg_uri', '')
                if entity_uri:
                    entity_refs.append(f"    kr:containsEntity {entity_uri}")
            
            if entity_refs:
                # Add entity references
                for ref in entity_refs[:-1]:
                    lines.append(ref + " ;")
                lines.append(entity_refs[-1] + " .")
            else:
                lines.append("    .")
            
            lines.append("")
            
            # Reverse relationships (entity mentions chunk)
            for entity in entities:
                entity_uri = entity.get('kg_uri', '')
                if entity_uri:
                    lines.append(f"{entity_uri} kr:mentionedIn {chunk_uri} .")
        
        return lines
    
    def _extract_chunk_sequence(self, chunk_id: str) -> int:
        """Extract chunk sequence number from chunk ID"""
        try:
            # Assuming chunk_id format like "doc_id_chunk_001"
            parts = chunk_id.split('_')
            if len(parts) >= 2 and parts[-2] == 'chunk':
                return int(parts[-1])
            return 0
        except:
            return 0
    
    def build_entity_summary(self, resolved_entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build summary statistics for resolved entities"""
        if not resolved_entities:
            return {
                'total_entities': 0,
                'entity_types': {},
                'confidence_stats': {},
                'contexts': {}
            }
        
        # Count by type
        type_counts = {}
        confidence_values = []
        context_counts = {}
        
        for entity in resolved_entities:
            entity_type = entity.get('entity_type', 'UNKNOWN')
            confidence = entity.get('confidence', 0.0)
            context = entity.get('context', 'mention')
            
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
            confidence_values.append(confidence)
            context_counts[context] = context_counts.get(context, 0) + 1
        
        # Calculate confidence statistics
        if confidence_values:
            confidence_stats = {
                'min': min(confidence_values),
                'max': max(confidence_values),
                'avg': sum(confidence_values) / len(confidence_values),
                'count': len(confidence_values)
            }
        else:
            confidence_stats = {'min': 0, 'max': 0, 'avg': 0, 'count': 0}
        
        return {
            'total_entities': len(resolved_entities),
            'entity_types': type_counts,
            'confidence_stats': confidence_stats,
            'contexts': context_counts,
            'processing_timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    
    def validate_ttl(self, ttl_content: str) -> Dict[str, Any]:
        """Basic validation of TTL content"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'stats': {
                'lines': 0,
                'triples_estimated': 0,
                'prefixes': 0
            }
        }
        
        try:
            lines = ttl_content.split('\n')
            validation_result['stats']['lines'] = len(lines)
            
            prefix_count = 0
            triple_count = 0
            
            for line in lines:
                line = line.strip()
                if line.startswith('@prefix'):
                    prefix_count += 1
                elif line and not line.startswith('#') and ('.' in line or ';' in line):
                    triple_count += 1
            
            validation_result['stats']['prefixes'] = prefix_count
            validation_result['stats']['triples_estimated'] = triple_count
            
            # Basic validation checks
            if prefix_count == 0:
                validation_result['warnings'].append("No namespace prefixes found")
            
            if triple_count == 0:
                validation_result['warnings'].append("No triples found")
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
        
        return validation_result
