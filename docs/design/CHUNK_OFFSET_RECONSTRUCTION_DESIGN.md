# Chunk Offset Reconstruction Design Document

## Problem Statement

### Core Issue
The NLP pipeline successfully extracts entities and key phrases from documents using AWS Comprehend, but fails to map these entities back to document chunks due to coordinate system misalignment.

### Technical Details
- **Comprehend entities**: Have offsets from raw extracted text (225K characters)
- **Smart chunked data**: Uses Textract's layout analysis, losing original document offsets
- **Result**: 0% entity-to-chunk mapping success rate despite 3,691 entities and 8,996 key phrases extracted

### Impact
- Entity mapping metrics show 91%+ chunk success but 0% entity/key phrase mapping
- Empty `*_by_chunk.json` files in S3
- Search quality impact remains 0.0 (no entity-enhanced search)

## Root Cause Analysis

### Smart Chunking Process
The sophisticated chunking process uses Textract's structured layout analysis:

1. **Text Extraction**: Raw text extracted (225K characters)
2. **Structure Analysis**: Textract provides hierarchical layout blocks
3. **Smart Chunking**: Creates chunks based on document structure (paragraphs, sections)
4. **Offset Loss**: Original document character positions are lost during structural processing

### Example Data Structures

**Chunk Structure (Missing Offsets):**
```json
{
  "chunk_id": "064762102bead7b04a39_chunk_0226",
  "doc_id": "064762102bead7b04a39",
  "chunk_index": 226,
  "text": "31.\nMonetary policy has continued to be expansionary...",
  "page_numbers": [17],
  "character_count": 769,
  "section_type": "paragraph",
  "hierarchy_level": 2
  // MISSING: document_start_offset, document_end_offset
}
```

**Textract Structure (Available):**
```json
{
  "BlockType": "LINE",
  "Text": "Monetary policy has continued to be expansionary to support economic",
  "Geometry": { "BoundingBox": {...} },
  "Page": 17
}
```

## Solution Design

### Approach: Post-Processing Offset Reconstruction

Add document offset reconstruction as a post-processing step after chunk creation, using first/last word matching with comprehensive validation.

### Algorithm Overview

1. **Normalize Text**: Standardize whitespace in both full document and chunk text
2. **Extract Keywords**: Use first N and last M words from each chunk
3. **Find Positions**: Locate keyword positions in full document text
4. **Validate Matches**: Apply sanity checks for distance, order, and similarity
5. **Convert Coordinates**: Map normalized positions back to raw text offsets

### Implementation Details

#### Core Method Structure
```python
def add_document_offsets(self, chunks: List[Dict], raw_text: str, textract_blocks: List[Dict]) -> List[Dict]:
    """Add document offsets with comprehensive validation"""
    
    # Pre-normalize the full text once
    normalized_full_text = self._normalize_whitespace(raw_text)
    
    for chunk in chunks:
        chunk_text = chunk['text']
        normalized_chunk = self._normalize_whitespace(chunk_text)
        
        # Try multiple word combinations for robustness
        offset_result = self._find_chunk_offsets_with_validation(
            chunk_text, normalized_chunk, normalized_full_text, raw_text
        )
        
        if offset_result:
            chunk['document_start_offset'] = offset_result['start']
            chunk['document_end_offset'] = offset_result['end']
            chunk['offset_confidence'] = offset_result['confidence']
        else:
            chunk['document_start_offset'] = -1
            chunk['document_end_offset'] = -1
            chunk['offset_confidence'] = 0.0
            logger.warning(f"Failed to find offsets for chunk {chunk['chunk_id']}")
    
    return chunks
```

#### Multi-Strategy Word Matching
```python
def _find_chunk_offsets_with_validation(self, original_chunk: str, normalized_chunk: str, 
                                       normalized_full: str, raw_full: str) -> Optional[Dict]:
    """Find offsets with multiple strategies and validation"""
    
    words = normalized_chunk.split()
    if len(words) < 4:
        return None
    
    # Strategy 1: Different word counts for start/end
    strategies = [
        {'start_words': 4, 'end_words': 3},  # More words at start (sentences often start uniquely)
        {'start_words': 3, 'end_words': 4},  # More words at end
        {'start_words': 5, 'end_words': 2},  # Many start, few end
        {'start_words': 2, 'end_words': 5},  # Few start, many end
        {'start_words': 3, 'end_words': 3},  # Equal (fallback)
    ]
    
    for strategy in strategies:
        result = self._try_word_strategy(
            words, strategy, normalized_full, raw_full, normalized_chunk
        )
        if result:
            return result
    
    return None
```

#### Comprehensive Validation
```python
def _try_word_strategy(self, words: List[str], strategy: Dict, normalized_full: str, 
                      raw_full: str, normalized_chunk: str) -> Optional[Dict]:
    """Try a specific word count strategy"""
    
    start_words = ' '.join(words[:strategy['start_words']])
    end_words = ' '.join(words[-strategy['end_words']:])
    
    # Find start position
    start_candidates = self._find_all_positions(start_words, normalized_full)
    
    for start_pos in start_candidates:
        # Find end position (must be after start)
        end_search_start = start_pos + len(start_words)
        end_candidates = self._find_all_positions(end_words, normalized_full, end_search_start)
        
        for end_pos in end_candidates:
            # Sanity check 1: Reasonable distance
            distance = end_pos - start_pos
            if distance < 50 or distance > 2000:  # Chunk should be 50-2000 chars
                continue
            
            # Sanity check 2: Order check
            if end_pos <= start_pos + len(start_words):
                continue
            
            # Sanity check 3: Extract candidate text and compare
            candidate_start = start_pos
            candidate_end = end_pos + len(end_words)
            candidate_text = normalized_full[candidate_start:candidate_end]
            
            # Calculate similarity
            similarity = self._calculate_text_similarity(normalized_chunk, candidate_text)
            
            if similarity > 0.85:  # 85% similarity threshold
                # Convert normalized positions back to raw text positions
                raw_start = self._convert_to_raw_position(candidate_start, raw_full)
                raw_end = self._convert_to_raw_position(candidate_end, raw_full)
                
                return {
                    'start': raw_start,
                    'end': raw_end,
                    'confidence': similarity,
                    'strategy': f"{strategy['start_words']}-{strategy['end_words']}"
                }
    
    return None
```

#### Text Similarity and Normalization
```python
def _calculate_text_similarity(self, text1: str, text2: str) -> float:
    """Calculate similarity between two normalized texts"""
    # Simple word-based similarity
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0

def _normalize_whitespace(self, text: str) -> str:
    """Normalize whitespace consistently"""
    import re
    # Replace multiple whitespace with single space
    normalized = re.sub(r'\s+', ' ', text.strip())
    # Remove common OCR artifacts
    normalized = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)]', ' ', normalized)
    return normalized
```

## Implementation Plan

### Files to Modify

#### Primary Implementation
- **File**: `/lambda/text-chunker-processor/src/smart_structured_chunker.py`
- **Method**: Add `add_document_offsets()` method to `SmartStructuredChunker` class
- **Integration**: Call from `create_smart_chunks()` after chunk creation

#### Alternative Implementation
- **File**: `/lambda/text-chunker-processor/src/textract_layout_chunker.py`
- **Method**: Add similar offset reconstruction to layout chunker
- **Integration**: Call from `chunk_document()` method

### Processing Stages

1. **Text Extraction**: Raw text and Textract structure downloaded
2. **Smart Chunking**: Chunks created using document structure
3. **Offset Reconstruction**: NEW - Add document offsets to chunks
4. **S3 Upload**: Enhanced chunks with offsets uploaded
5. **NLP Processing**: Entity mapping now works with proper coordinates

### Integration Points

#### In `create_smart_chunks()` method:
```python
# After chunks are created
chunks = self._create_chunks_from_sections(sections, doc_id)

# NEW: Add document offsets
chunks = self.add_document_offsets(chunks, raw_text, textract_response['blocks'])

# Continue with existing logic
if self.semantic_overlap:
    chunks = self._add_semantic_overlap(chunks)
```

## Validation Strategy

### Testing Approach
1. **Current Document**: Test with `064762102bead7b04a39` (known entity data)
2. **Offset Accuracy**: Verify reconstructed offsets align with original text
3. **Entity Mapping**: Confirm entities map to correct chunks
4. **Performance**: Measure processing time impact

### Success Metrics
- **Offset Reconstruction Rate**: >90% of chunks get valid offsets
- **Entity Mapping Success**: >50% of entities map to chunks (vs current 0%)
- **Search Quality Impact**: >0.0 (vs current 0.0)
- **Processing Time**: <30 seconds additional processing

### Fallback Strategy
If offset reconstruction fails for some chunks:
- Mark with `offset_confidence: 0.0`
- Log failures for analysis
- Continue processing (partial success better than total failure)

## Risk Assessment

### Technical Risks
- **Performance Impact**: O(n*m) text searching for 604 chunks
- **Memory Usage**: Full text normalization and multiple candidate searches
- **Edge Cases**: Cross-page chunks, special characters, OCR artifacts

### Mitigation Strategies
- **Early Termination**: Stop searching after first high-confidence match
- **Caching**: Reuse normalized full text across chunks
- **Graceful Degradation**: Continue processing even if some chunks fail

## Expected Outcomes

### Immediate Benefits
- **Entity Mapping**: 3,691 entities and 8,996 key phrases can map to chunks
- **Search Enhancement**: Entity-enhanced search becomes functional
- **Pipeline Completion**: Full NLP processing pipeline works end-to-end

### Long-term Impact
- **Search Quality**: Improved search relevance through entity context
- **Knowledge Graph**: Entities can be properly linked to document sections
- **Analytics**: Document-level entity analysis becomes possible

## Alternative Approaches Considered

### Option 1: Run Comprehend on Individual Chunks
- **Pros**: Perfect coordinate alignment
- **Cons**: Context loss, higher cost (604 API calls), slower processing
- **Decision**: Rejected due to context loss impact on entity quality

### Option 2: Modify Chunking to Preserve Offsets
- **Pros**: Clean solution, no post-processing needed
- **Cons**: Major architectural change, risk to existing functionality
- **Decision**: Deferred - post-processing approach is safer

### Option 3: Fuzzy Full-Text Matching
- **Pros**: Simple implementation
- **Cons**: Performance issues, accuracy concerns with OCR text
- **Decision**: Enhanced with word-based approach for better accuracy
