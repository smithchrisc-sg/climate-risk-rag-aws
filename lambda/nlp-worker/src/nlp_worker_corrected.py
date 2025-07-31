"""
CORRECTED NLP Worker - Entity/Keyphrase to Chunk Mapping

The original mapping logic was fundamentally flawed because it assumed:
1. Chunks were sequential segments that could be concatenated
2. Comprehend offsets were relative to concatenated chunk text

REALITY:
1. Comprehend analyzes the ORIGINAL full document text
2. Entity/keyphrase offsets are relative to the ORIGINAL document
3. Chunks may overlap, have hierarchical relationships, and are not sequential
4. We need to map original document offsets to chunks that contain that text

CORRECTED APPROACH:
1. Load the original document text that was sent to Comprehend
2. Use entity/keyphrase offsets relative to original text
3. Find chunks whose text appears at those positions in the original document
4. Handle overlapping chunks and hierarchical relationships properly
"""

import json
import boto3
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ChunkPosition:
    """Represents where a chunk's text appears in the original document"""
    chunk_id: str
    chunk_text: str
    start_offset: int
    end_offset: int
    chunk_index: int
    section_type: str
    hierarchy_level: int
    parent_chunk_id: Optional[str] = None

class CorrectedNLPWorker:
    """Corrected NLP Worker with proper entity/keyphrase to chunk mapping"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
    
    def load_original_document_text(self, doc_id: str, text_bucket: str) -> str:
        """Load the original document text that was sent to Comprehend"""
        try:
            # The text that nlp-initiator sends to Comprehend
            text_key = f"text/{doc_id}.txt"
            
            response = self.s3_client.get_object(
                Bucket=text_bucket,
                Key=text_key
            )
            
            original_text = response['Body'].read().decode('utf-8')
            logger.info(f"Loaded original document text: {len(original_text)} characters")
            return original_text
            
        except Exception as e:
            logger.error(f"Error loading original document text: {e}")
            raise
    
    def find_chunk_positions_in_original_text(self, chunks: List[Dict], original_text: str) -> List[ChunkPosition]:
        """Find where each chunk's text appears in the original document"""
        chunk_positions = []
        
        for chunk in chunks:
            chunk_text = chunk.get('text', '').strip()
            if not chunk_text:
                continue
            
            # Find all occurrences of this chunk's text in the original document
            start_pos = 0
            while True:
                pos = original_text.find(chunk_text, start_pos)
                if pos == -1:
                    break
                
                chunk_position = ChunkPosition(
                    chunk_id=chunk.get('chunk_id', ''),
                    chunk_text=chunk_text,
                    start_offset=pos,
                    end_offset=pos + len(chunk_text),
                    chunk_index=chunk.get('chunk_index', 0),
                    section_type=chunk.get('section_type', 'unknown'),
                    hierarchy_level=chunk.get('hierarchy_level', 0),
                    parent_chunk_id=chunk.get('parent_chunk_id')
                )
                
                chunk_positions.append(chunk_position)
                start_pos = pos + 1  # Look for overlapping occurrences
        
        # Sort by position in document
        chunk_positions.sort(key=lambda x: x.start_offset)
        
        logger.info(f"Found {len(chunk_positions)} chunk positions in original document")
        return chunk_positions
    
    def map_entities_to_chunks(self, entities: List[Dict], chunk_positions: List[ChunkPosition]) -> List[Dict]:
        """Map entities to chunks based on original document positions"""
        entities_by_chunk = []
        
        for entity in entities:
            entity_start = entity.get('begin_offset', 0)
            entity_end = entity.get('end_offset', 0)
            entity_text = entity.get('text', '')
            
            # Find all chunks that contain this entity
            containing_chunks = []
            for chunk_pos in chunk_positions:
                # Check if entity overlaps with this chunk
                if (entity_start < chunk_pos.end_offset and 
                    entity_end > chunk_pos.start_offset):
                    
                    # Calculate relative position within chunk
                    relative_start = max(0, entity_start - chunk_pos.start_offset)
                    relative_end = min(len(chunk_pos.chunk_text), 
                                     entity_end - chunk_pos.start_offset)
                    
                    # Verify the text matches (quality check)
                    chunk_entity_text = chunk_pos.chunk_text[relative_start:relative_end]
                    
                    containing_chunks.append({
                        'chunk_id': chunk_pos.chunk_id,
                        'chunk_index': chunk_pos.chunk_index,
                        'section_type': chunk_pos.section_type,
                        'hierarchy_level': chunk_pos.hierarchy_level,
                        'parent_chunk_id': chunk_pos.parent_chunk_id,
                        'entity_text': entity_text,
                        'entity_type': entity.get('type', ''),
                        'confidence_score': entity.get('score', 0.0),
                        'original_begin_offset': entity_start,
                        'original_end_offset': entity_end,
                        'chunk_relative_begin': relative_start,
                        'chunk_relative_end': relative_end,
                        'chunk_text_match': chunk_entity_text,
                        'text_match_quality': 1.0 if chunk_entity_text == entity_text else 0.8
                    })
            
            # Add all containing chunks (handles overlapping chunks)
            entities_by_chunk.extend(containing_chunks)
            
            if not containing_chunks:
                logger.warning(f"Entity '{entity_text}' at offset {entity_start}-{entity_end} not found in any chunk")
        
        logger.info(f"Mapped {len(entities)} entities to {len(entities_by_chunk)} chunk-entity pairs")
        return entities_by_chunk
    
    def map_keyphrases_to_chunks(self, key_phrases: List[Dict], chunk_positions: List[ChunkPosition]) -> List[Dict]:
        """Map key phrases to chunks based on original document positions"""
        phrases_by_chunk = []
        
        for phrase in key_phrases:
            phrase_start = phrase.get('begin_offset', 0)
            phrase_end = phrase.get('end_offset', 0)
            phrase_text = phrase.get('text', '')
            
            # Find all chunks that contain this phrase
            containing_chunks = []
            for chunk_pos in chunk_positions:
                # Check if phrase overlaps with this chunk
                if (phrase_start < chunk_pos.end_offset and 
                    phrase_end > chunk_pos.start_offset):
                    
                    # Calculate relative position within chunk
                    relative_start = max(0, phrase_start - chunk_pos.start_offset)
                    relative_end = min(len(chunk_pos.chunk_text), 
                                     phrase_end - chunk_pos.start_offset)
                    
                    # Verify the text matches (quality check)
                    chunk_phrase_text = chunk_pos.chunk_text[relative_start:relative_end]
                    
                    containing_chunks.append({
                        'chunk_id': chunk_pos.chunk_id,
                        'chunk_index': chunk_pos.chunk_index,
                        'section_type': chunk_pos.section_type,
                        'hierarchy_level': chunk_pos.hierarchy_level,
                        'parent_chunk_id': chunk_pos.parent_chunk_id,
                        'phrase_text': phrase_text,
                        'confidence_score': phrase.get('score', 0.0),
                        'original_begin_offset': phrase_start,
                        'original_end_offset': phrase_end,
                        'chunk_relative_begin': relative_start,
                        'chunk_relative_end': relative_end,
                        'chunk_text_match': chunk_phrase_text,
                        'text_match_quality': 1.0 if chunk_phrase_text == phrase_text else 0.8
                    })
            
            # Add all containing chunks (handles overlapping chunks)
            phrases_by_chunk.extend(containing_chunks)
            
            if not containing_chunks:
                logger.warning(f"Key phrase '{phrase_text}' at offset {phrase_start}-{phrase_end} not found in any chunk")
        
        logger.info(f"Mapped {len(key_phrases)} key phrases to {len(phrases_by_chunk)} chunk-phrase pairs")
        return phrases_by_chunk
    
    def map_results_to_chunks_corrected(self, comprehend_results: Dict[str, List], 
                                      chunks: List[Dict], doc_id: str, 
                                      text_bucket: str) -> Dict[str, List]:
        """
        CORRECTED mapping function that properly handles hierarchical chunks
        """
        if not chunks:
            logger.info("No chunks available for mapping")
            return {
                'entities_by_chunk': [],
                'key_phrases_by_chunk': []
            }
        
        try:
            # Load the original document text that Comprehend analyzed
            original_text = self.load_original_document_text(doc_id, text_bucket)
            
            # Find where each chunk appears in the original document
            chunk_positions = self.find_chunk_positions_in_original_text(chunks, original_text)
            
            if not chunk_positions:
                logger.error("Could not find any chunk positions in original document")
                return {
                    'entities_by_chunk': [],
                    'key_phrases_by_chunk': []
                }
            
            # Map entities to chunks using correct positions
            entities_by_chunk = self.map_entities_to_chunks(
                comprehend_results.get('entities', []), 
                chunk_positions
            )
            
            # Map key phrases to chunks using correct positions
            phrases_by_chunk = self.map_keyphrases_to_chunks(
                comprehend_results.get('key_phrases', []), 
                chunk_positions
            )
            
            return {
                'entities_by_chunk': entities_by_chunk,
                'key_phrases_by_chunk': phrases_by_chunk
            }
            
        except Exception as e:
            logger.error(f"Error in corrected mapping: {e}")
            raise

# Example usage and testing
def test_corrected_mapping():
    """Test the corrected mapping logic"""
    
    # Mock data for testing
    mock_entities = [
        {
            'text': 'climate change',
            'type': 'OTHER',
            'score': 0.95,
            'begin_offset': 100,
            'end_offset': 114
        }
    ]
    
    mock_chunks = [
        {
            'chunk_id': 'doc123_chunk_0001',
            'chunk_index': 0,
            'text': 'The impact of climate change on financial institutions is significant.',
            'section_type': 'paragraph',
            'hierarchy_level': 3,
            'parent_chunk_id': None
        }
    ]
    
    mock_original_text = "This document discusses various topics. The impact of climate change on financial institutions is significant. We need to address these challenges."
    
    worker = CorrectedNLPWorker()
    
    # Test chunk position finding
    chunk_positions = worker.find_chunk_positions_in_original_text(mock_chunks, mock_original_text)
    print(f"Found {len(chunk_positions)} chunk positions")
    
    # Test entity mapping
    entities_by_chunk = worker.map_entities_to_chunks(mock_entities, chunk_positions)
    print(f"Mapped entities: {json.dumps(entities_by_chunk, indent=2)}")

if __name__ == "__main__":
    test_corrected_mapping()
