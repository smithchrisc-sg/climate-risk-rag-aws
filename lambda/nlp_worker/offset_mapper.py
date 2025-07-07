"""
Offset Mapper - Maps NLP results from full document to specific chunks
Critical for Knowledge Graph construction and chunk-level analysis
"""
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class OffsetMapper:
    """Maps NLP results from full document to specific chunks using text offsets"""
    
    def __init__(self, full_text: str, chunks: List[Dict[str, Any]]):
        """
        Initialize offset mapper
        
        Args:
            full_text: Complete document text
            chunks: List of chunk dictionaries with text and metadata
        """
        self.full_text = full_text
        self.chunks = chunks
        self.chunk_offsets = self._calculate_chunk_offsets()
        
        logger.info(f"Initialized offset mapper for {len(chunks)} chunks, {len(full_text)} characters")
    
    def _calculate_chunk_offsets(self) -> List[Dict[str, Any]]:
        """Calculate the text offsets for each chunk in the full document"""
        chunk_offsets = []
        current_search_start = 0
        
        for i, chunk in enumerate(self.chunks):
            chunk_text = chunk.get('text', '').strip()
            chunk_id = chunk.get('chunk_id', f'chunk_{i}')
            chunk_index = chunk.get('chunk_index', i)
            
            if not chunk_text:
                logger.warning(f"Empty chunk text for chunk {chunk_id}")
                chunk_offsets.append({
                    'chunk_id': chunk_id,
                    'chunk_index': chunk_index,
                    'start_offset': -1,
                    'end_offset': -1,
                    'text': chunk_text,
                    'mapping_status': 'empty_text'
                })
                continue
            
            # Find the chunk text in the full document
            start_offset = self.full_text.find(chunk_text, current_search_start)
            
            if start_offset != -1:
                end_offset = start_offset + len(chunk_text)
                chunk_offsets.append({
                    'chunk_id': chunk_id,
                    'chunk_index': chunk_index,
                    'start_offset': start_offset,
                    'end_offset': end_offset,
                    'text': chunk_text,
                    'mapping_status': 'mapped'
                })
                current_search_start = end_offset
                logger.debug(f"Mapped chunk {chunk_id} to offsets {start_offset}-{end_offset}")
            else:
                # Try fuzzy matching for chunks that might have slight differences
                fuzzy_match = self._find_fuzzy_match(chunk_text, current_search_start)
                
                if fuzzy_match:
                    chunk_offsets.append({
                        'chunk_id': chunk_id,
                        'chunk_index': chunk_index,
                        'start_offset': fuzzy_match['start'],
                        'end_offset': fuzzy_match['end'],
                        'text': chunk_text,
                        'mapping_status': 'fuzzy_mapped',
                        'similarity_score': fuzzy_match['similarity']
                    })
                    current_search_start = fuzzy_match['end']
                    logger.debug(f"Fuzzy mapped chunk {chunk_id} to offsets {fuzzy_match['start']}-{fuzzy_match['end']}")
                else:
                    # Handle case where exact text match fails
                    logger.warning(f"Could not map chunk {chunk_id} to document offsets")
                    chunk_offsets.append({
                        'chunk_id': chunk_id,
                        'chunk_index': chunk_index,
                        'start_offset': -1,
                        'end_offset': -1,
                        'text': chunk_text,
                        'mapping_status': 'unmapped'
                    })
        
        # Log mapping statistics
        mapped_count = sum(1 for co in chunk_offsets if co['mapping_status'] in ['mapped', 'fuzzy_mapped'])
        logger.info(f"Chunk mapping complete: {mapped_count}/{len(chunk_offsets)} chunks mapped")
        
        return chunk_offsets
    
    def _find_fuzzy_match(self, chunk_text: str, start_pos: int, similarity_threshold: float = 0.8) -> Optional[Dict[str, Any]]:
        """
        Find fuzzy match for chunk text that might have slight differences
        Uses sliding window approach with similarity scoring
        """
        chunk_len = len(chunk_text)
        search_window = min(chunk_len * 2, 2000)  # Reasonable search window
        
        best_match = None
        best_similarity = 0.0
        
        # Search in a window around the expected position
        search_end = min(start_pos + search_window, len(self.full_text))
        
        for pos in range(start_pos, search_end - chunk_len + 1):
            candidate = self.full_text[pos:pos + chunk_len]
            similarity = self._calculate_similarity(chunk_text, candidate)
            
            if similarity > best_similarity and similarity >= similarity_threshold:
                best_similarity = similarity
                best_match = {
                    'start': pos,
                    'end': pos + chunk_len,
                    'similarity': similarity
                }
        
        return best_match
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple character-based similarity between two texts"""
        if not text1 or not text2:
            return 0.0
        
        # Simple character overlap similarity
        set1 = set(text1.lower())
        set2 = set(text2.lower())
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def map_to_chunks(self, nlp_results: Dict[str, Any]) -> Dict[str, Any]:
        """Map entities and phrases to their containing chunks"""
        
        mapped_results = {
            'doc_id': nlp_results['doc_id'],
            'provider': nlp_results['provider'],
            'processed_at': nlp_results['processed_at'],
            'processing_cost': nlp_results['processing_cost'],
            'processing_duration': nlp_results.get('processing_duration', 0.0),
            'chunk_mappings': [],
            'mapping_statistics': {
                'total_entities': len(nlp_results.get('entities', [])),
                'total_key_phrases': len(nlp_results.get('key_phrases', [])),
                'mapped_entities': 0,
                'mapped_key_phrases': 0,
                'unmapped_entities': 0,
                'unmapped_key_phrases': 0
            }
        }
        
        # Map entities to chunks
        for entity in nlp_results.get('entities', []):
            chunk_mapping = self._find_containing_chunk(
                entity['begin_offset'], 
                entity['end_offset']
            )
            
            if chunk_mapping:
                mapped_results['chunk_mappings'].append({
                    'type': 'entity',
                    'chunk_id': chunk_mapping['chunk_id'],
                    'chunk_index': chunk_mapping['chunk_index'],
                    'text': entity['text'],
                    'entity_type': entity['type'],
                    'confidence': entity['confidence'],
                    'document_begin_offset': entity['begin_offset'],
                    'document_end_offset': entity['end_offset'],
                    'chunk_begin_offset': entity['begin_offset'] - chunk_mapping['start_offset'],
                    'chunk_end_offset': entity['end_offset'] - chunk_mapping['start_offset'],
                    'mapping_quality': chunk_mapping['mapping_status']
                })
                mapped_results['mapping_statistics']['mapped_entities'] += 1
            else:
                logger.warning(f"Could not map entity '{entity['text']}' at offsets {entity['begin_offset']}-{entity['end_offset']}")
                mapped_results['mapping_statistics']['unmapped_entities'] += 1
        
        # Map key phrases to chunks
        for phrase in nlp_results.get('key_phrases', []):
            chunk_mapping = self._find_containing_chunk(
                phrase['begin_offset'], 
                phrase['end_offset']
            )
            
            if chunk_mapping:
                mapped_results['chunk_mappings'].append({
                    'type': 'key_phrase',
                    'chunk_id': chunk_mapping['chunk_id'],
                    'chunk_index': chunk_mapping['chunk_index'],
                    'text': phrase['text'],
                    'confidence': phrase['confidence'],
                    'document_begin_offset': phrase['begin_offset'],
                    'document_end_offset': phrase['end_offset'],
                    'chunk_begin_offset': phrase['begin_offset'] - chunk_mapping['start_offset'],
                    'chunk_end_offset': phrase['end_offset'] - chunk_mapping['start_offset'],
                    'mapping_quality': chunk_mapping['mapping_status']
                })
                mapped_results['mapping_statistics']['mapped_key_phrases'] += 1
            else:
                logger.warning(f"Could not map key phrase '{phrase['text']}' at offsets {phrase['begin_offset']}-{phrase['end_offset']}")
                mapped_results['mapping_statistics']['unmapped_key_phrases'] += 1
        
        # Log mapping results
        stats = mapped_results['mapping_statistics']
        logger.info(f"Mapping complete: {stats['mapped_entities']}/{stats['total_entities']} entities, "
                   f"{stats['mapped_key_phrases']}/{stats['total_key_phrases']} key phrases mapped")
        
        return mapped_results
    
    def _find_containing_chunk(self, begin_offset: int, end_offset: int) -> Optional[Dict[str, Any]]:
        """Find which chunk contains the given text offsets"""
        
        for chunk_info in self.chunk_offsets:
            # Skip unmapped chunks
            if chunk_info['mapping_status'] == 'unmapped' or chunk_info['start_offset'] == -1:
                continue
            
            # Check if the entity/phrase is contained within this chunk
            if (chunk_info['start_offset'] <= begin_offset < chunk_info['end_offset'] and
                chunk_info['start_offset'] < end_offset <= chunk_info['end_offset']):
                return chunk_info
        
        # If no exact match, try to find the closest chunk
        return self._find_closest_chunk(begin_offset, end_offset)
    
    def _find_closest_chunk(self, begin_offset: int, end_offset: int) -> Optional[Dict[str, Any]]:
        """Find the closest chunk when no exact match is found"""
        
        best_chunk = None
        min_distance = float('inf')
        
        for chunk_info in self.chunk_offsets:
            if chunk_info['mapping_status'] == 'unmapped' or chunk_info['start_offset'] == -1:
                continue
            
            # Calculate distance from entity to chunk
            if end_offset <= chunk_info['start_offset']:
                # Entity is before chunk
                distance = chunk_info['start_offset'] - end_offset
            elif begin_offset >= chunk_info['end_offset']:
                # Entity is after chunk
                distance = begin_offset - chunk_info['end_offset']
            else:
                # Entity overlaps with chunk
                distance = 0
            
            if distance < min_distance:
                min_distance = distance
                best_chunk = chunk_info
        
        if best_chunk and min_distance < 100:  # Only return if reasonably close
            logger.debug(f"Found closest chunk {best_chunk['chunk_id']} at distance {min_distance}")
            return best_chunk
        
        return None
    
    def get_mapping_quality_report(self) -> Dict[str, Any]:
        """Generate a report on mapping quality"""
        
        total_chunks = len(self.chunk_offsets)
        mapped_chunks = sum(1 for co in self.chunk_offsets if co['mapping_status'] in ['mapped', 'fuzzy_mapped'])
        fuzzy_mapped = sum(1 for co in self.chunk_offsets if co['mapping_status'] == 'fuzzy_mapped')
        unmapped_chunks = sum(1 for co in self.chunk_offsets if co['mapping_status'] == 'unmapped')
        
        return {
            'total_chunks': total_chunks,
            'mapped_chunks': mapped_chunks,
            'fuzzy_mapped_chunks': fuzzy_mapped,
            'unmapped_chunks': unmapped_chunks,
            'mapping_success_rate': mapped_chunks / total_chunks if total_chunks > 0 else 0.0,
            'document_length': len(self.full_text),
            'chunk_coverage': {
                chunk['chunk_id']: chunk['mapping_status'] 
                for chunk in self.chunk_offsets
            }
        }
