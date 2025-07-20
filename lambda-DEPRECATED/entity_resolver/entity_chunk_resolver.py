#!/usr/bin/env python3
"""
Entity-Chunk Resolver
Maps NLP entities to document chunks using character offsets
"""

import json
import boto3
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class EntityChunkResolver:
    """Resolves which chunk each NLP entity belongs to using offsets"""
    
    def __init__(self, chunks_bucket: str):
        self.s3_client = boto3.client('s3')
        self.chunks_bucket = chunks_bucket
        self.chunk_cache = {}  # Cache chunks to avoid repeated S3 calls
    
    def resolve_entity_chunks(self, doc_id: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Resolve chunk associations for all entities in a document
        
        Args:
            doc_id: Document identifier
            entities: List of NLP entities with offset information
            
        Returns:
            List of entities with chunk associations
        """
        try:
            # Load chunk metadata for the document
            chunks_metadata = self._load_chunks_metadata(doc_id)
            
            if not chunks_metadata:
                logger.warning(f"No chunks metadata found for document {doc_id}")
                return []
            
            # Build chunk index for efficient lookup
            chunk_index = self._build_chunk_index(chunks_metadata)
            
            # Resolve each entity to its chunk
            resolved_entities = []
            for entity in entities:
                chunk_association = self._resolve_single_entity_chunk(entity, chunk_index)
                if chunk_association:
                    resolved_entities.append(chunk_association)
            
            logger.info(f"Resolved {len(resolved_entities)} entities to chunks for document {doc_id}")
            return resolved_entities
            
        except Exception as e:
            logger.error(f"Error resolving entity chunks for {doc_id}: {e}")
            return []
    
    def _load_chunks_metadata(self, doc_id: str) -> List[Dict[str, Any]]:
        """Load chunk metadata from S3"""
        try:
            # Check cache first
            if doc_id in self.chunk_cache:
                return self.chunk_cache[doc_id]
            
            # List all chunk files for the document
            prefix = f"chunks/{doc_id}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.chunks_bucket,
                Prefix=prefix
            )
            
            chunks_metadata = []
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    
                    # Skip non-chunk files (like summary.json)
                    if not key.endswith('_chunk_') and not key.endswith('.json'):
                        continue
                    
                    if 'summary.json' in key or 'full_text.json' in key:
                        continue
                    
                    # Load chunk data
                    try:
                        chunk_response = self.s3_client.get_object(
                            Bucket=self.chunks_bucket,
                            Key=key
                        )
                        chunk_data = json.loads(chunk_response['Body'].read().decode('utf-8'))
                        
                        # Ensure chunk has required fields
                        if self._validate_chunk_data(chunk_data):
                            chunks_metadata.append(chunk_data)
                        
                    except Exception as e:
                        logger.warning(f"Error loading chunk {key}: {e}")
                        continue
            
            # Sort chunks by index for consistent processing
            chunks_metadata.sort(key=lambda x: x.get('chunk_index', 0))
            
            # Cache the result
            self.chunk_cache[doc_id] = chunks_metadata
            
            logger.info(f"Loaded {len(chunks_metadata)} chunks for document {doc_id}")
            return chunks_metadata
            
        except Exception as e:
            logger.error(f"Error loading chunks metadata for {doc_id}: {e}")
            return []
    
    def _validate_chunk_data(self, chunk_data: Dict[str, Any]) -> bool:
        """Validate that chunk data has required fields"""
        required_fields = ['chunk_id', 'text']
        
        for field in required_fields:
            if field not in chunk_data:
                return False
        
        return True
    
    def _build_chunk_index(self, chunks_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Build chunk index with character positions for efficient lookup
        
        This reconstructs the original document structure to determine
        where each chunk starts and ends in the full text.
        """
        chunk_index = []
        current_position = 0
        
        for chunk in chunks_metadata:
            chunk_text = chunk.get('text', '')
            chunk_length = len(chunk_text)
            
            chunk_info = {
                'chunk_id': chunk.get('chunk_id'),
                'chunk_index': chunk.get('chunk_index', 0),
                'start_offset': current_position,
                'end_offset': current_position + chunk_length,
                'text_length': chunk_length,
                'text': chunk_text
            }
            
            chunk_index.append(chunk_info)
            
            # Move position forward (accounting for potential overlap or gaps)
            # For now, assume chunks are sequential without overlap
            current_position += chunk_length
        
        return chunk_index
    
    def _resolve_single_entity_chunk(self, entity: Dict[str, Any], chunk_index: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Resolve a single entity to its containing chunk
        
        Args:
            entity: NLP entity with offset information
            chunk_index: Pre-built chunk index with positions
            
        Returns:
            Entity with chunk association or None if not found
        """
        try:
            # Extract entity offset information
            entity_start = entity.get('BeginOffset', entity.get('begin_offset', entity.get('start_offset')))
            entity_end = entity.get('EndOffset', entity.get('end_offset'))
            
            if entity_start is None:
                logger.warning(f"Entity missing offset information: {entity}")
                return None
            
            # If end offset is missing, estimate it from text length
            if entity_end is None:
                entity_text = entity.get('Text', entity.get('text', ''))
                entity_end = entity_start + len(entity_text)
            
            # Find the chunk that contains this entity
            containing_chunk = self._find_containing_chunk(entity_start, entity_end, chunk_index)
            
            if containing_chunk:
                return {
                    'entity': entity,
                    'chunk_id': containing_chunk['chunk_id'],
                    'chunk_index': containing_chunk['chunk_index'],
                    'type': 'entity',
                    'entity_start_in_chunk': entity_start - containing_chunk['start_offset'],
                    'entity_end_in_chunk': entity_end - containing_chunk['start_offset']
                }
            else:
                # Try to find the closest chunk if exact match fails
                closest_chunk = self._find_closest_chunk(entity_start, chunk_index)
                if closest_chunk:
                    logger.warning(f"Entity spans chunk boundaries, assigned to closest chunk: {entity.get('Text', 'Unknown')}")
                    return {
                        'entity': entity,
                        'chunk_id': closest_chunk['chunk_id'],
                        'chunk_index': closest_chunk['chunk_index'],
                        'type': 'entity',
                        'entity_start_in_chunk': max(0, entity_start - closest_chunk['start_offset']),
                        'entity_end_in_chunk': min(closest_chunk['text_length'], entity_end - closest_chunk['start_offset']),
                        'note': 'assigned_to_closest_chunk'
                    }
                else:
                    logger.warning(f"Could not resolve chunk for entity: {entity.get('Text', 'Unknown')}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error resolving entity chunk: {e}")
            return None
    
    def _find_containing_chunk(self, entity_start: int, entity_end: int, chunk_index: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find chunk that completely contains the entity"""
        for chunk in chunk_index:
            if (chunk['start_offset'] <= entity_start and 
                entity_end <= chunk['end_offset']):
                return chunk
        return None
    
    def _find_closest_chunk(self, entity_start: int, chunk_index: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find the closest chunk if entity spans boundaries"""
        if not chunk_index:
            return None
        
        closest_chunk = None
        min_distance = float('inf')
        
        for chunk in chunk_index:
            # Calculate distance to chunk
            if entity_start < chunk['start_offset']:
                # Entity is before this chunk
                distance = chunk['start_offset'] - entity_start
            elif entity_start > chunk['end_offset']:
                # Entity is after this chunk
                distance = entity_start - chunk['end_offset']
            else:
                # Entity overlaps with this chunk
                distance = 0
            
            if distance < min_distance:
                min_distance = distance
                closest_chunk = chunk
        
        return closest_chunk
    
    def get_chunk_statistics(self, doc_id: str) -> Dict[str, Any]:
        """Get statistics about chunks for a document"""
        try:
            chunks_metadata = self._load_chunks_metadata(doc_id)
            
            if not chunks_metadata:
                return {'error': 'No chunks found'}
            
            chunk_index = self._build_chunk_index(chunks_metadata)
            
            total_length = sum(chunk['text_length'] for chunk in chunk_index)
            avg_length = total_length / len(chunk_index) if chunk_index else 0
            
            return {
                'total_chunks': len(chunk_index),
                'total_text_length': total_length,
                'average_chunk_length': avg_length,
                'min_chunk_length': min(chunk['text_length'] for chunk in chunk_index) if chunk_index else 0,
                'max_chunk_length': max(chunk['text_length'] for chunk in chunk_index) if chunk_index else 0,
                'chunk_range': {
                    'start': chunk_index[0]['start_offset'] if chunk_index else 0,
                    'end': chunk_index[-1]['end_offset'] if chunk_index else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting chunk statistics for {doc_id}: {e}")
            return {'error': str(e)}
    
    def clear_cache(self, doc_id: str = None):
        """Clear chunk cache for a specific document or all documents"""
        if doc_id:
            self.chunk_cache.pop(doc_id, None)
        else:
            self.chunk_cache.clear()
        
        logger.info(f"Cleared chunk cache for {doc_id if doc_id else 'all documents'}")
    
    def validate_entity_offsets(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate entity offset information"""
        validation_result = {
            'valid_entities': 0,
            'invalid_entities': 0,
            'missing_offsets': 0,
            'issues': []
        }
        
        for i, entity in enumerate(entities):
            entity_text = entity.get('Text', entity.get('text', ''))
            entity_start = entity.get('BeginOffset', entity.get('begin_offset', entity.get('start_offset')))
            entity_end = entity.get('EndOffset', entity.get('end_offset'))
            
            if entity_start is None:
                validation_result['missing_offsets'] += 1
                validation_result['issues'].append(f"Entity {i}: Missing start offset for '{entity_text}'")
                continue
            
            if entity_end is None:
                # This is acceptable - we can estimate from text length
                validation_result['valid_entities'] += 1
                continue
            
            # Check if offsets make sense
            if entity_end <= entity_start:
                validation_result['invalid_entities'] += 1
                validation_result['issues'].append(f"Entity {i}: Invalid offsets ({entity_start}-{entity_end}) for '{entity_text}'")
                continue
            
            # Check if text length matches offset range
            expected_length = entity_end - entity_start
            actual_length = len(entity_text)
            
            if abs(expected_length - actual_length) > 2:  # Allow small discrepancies
                validation_result['issues'].append(f"Entity {i}: Text length mismatch for '{entity_text}' (expected: {expected_length}, actual: {actual_length})")
            
            validation_result['valid_entities'] += 1
        
        return validation_result
