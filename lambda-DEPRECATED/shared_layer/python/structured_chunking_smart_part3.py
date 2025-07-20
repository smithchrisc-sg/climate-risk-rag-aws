"""
Smart Structured Chunking Module - Part 3 (Final)
Smart paragraph splitting and optimization methods
"""

    def _split_paragraph_with_smart_overlap(self, section: DocumentSection, all_sections: List[DocumentSection], index: int) -> List[StructuredChunk]:
        """Split paragraphs with smart overlap strategy"""
        text = section.text
        
        if len(text) <= self.max_chunk_size:
            # Small paragraph, keep as single chunk
            return [self._create_paragraph_chunk(section, 0)]
        
        # Split into sentences
        sentences = self._split_into_sentences(text)
        
        if len(sentences) <= 3:
            # Very few sentences, keep together
            return [self._create_paragraph_chunk(section, 0)]
        
        chunks = []
        current_chunk_sentences = []
        current_length = 0
        
        for sentence_idx, sentence in enumerate(sentences):
            sentence_length = len(sentence)
            
            # Check if adding this sentence would exceed max size
            if (current_length + sentence_length > self.max_chunk_size and 
                current_chunk_sentences):
                
                # Create chunk from current sentences
                chunk_text = ' '.join(current_chunk_sentences)
                chunk = self._create_paragraph_segment_chunk(
                    chunk_text, section, len(chunks), 
                    len(current_chunk_sentences), sentence_idx
                )
                chunks.append(chunk)
                
                # Smart overlap strategy - only minimal overlap when splitting within logical units
                if self.semantic_overlap and len(chunks) > 0:
                    # Only 1 sentence overlap for continuity within the same paragraph
                    overlap_sentences = current_chunk_sentences[-1:]
                    current_chunk_sentences = overlap_sentences + [sentence]
                    current_length = sum(len(s) for s in current_chunk_sentences)
                    
                    # Mark overlap in metadata
                    chunk.metadata['has_overlap'] = True
                    chunk.metadata['overlap_sentences'] = 1
                else:
                    # No overlap - clean boundary
                    current_chunk_sentences = [sentence]
                    current_length = sentence_length
            else:
                current_chunk_sentences.append(sentence)
                current_length += sentence_length
        
        # Add final chunk
        if current_chunk_sentences:
            chunk_text = ' '.join(current_chunk_sentences)
            chunk = self._create_paragraph_segment_chunk(
                chunk_text, section, len(chunks), 
                len(current_chunk_sentences), len(sentences)
            )
            chunks.append(chunk)
        
        return chunks
    
    def _create_paragraph_chunk(self, section: DocumentSection, segment_index: int) -> StructuredChunk:
        """Create a complete paragraph chunk"""
        return StructuredChunk(
            text=section.text,
            chunk_type="paragraph",
            hierarchy_level=section.hierarchy_level,
            page_number=section.page_number,
            section_context="paragraph_content",
            word_count=len(section.text.split()),
            sentence_count=self._count_sentences(section.text),
            bounding_box=section.bounding_box,
            metadata={
                'section_type': section.section_type.value,
                'confidence': section.confidence,
                'is_complete_paragraph': True,
                'segment_index': segment_index,
                'overlap_strategy': 'none',
                'smart_chunking': True
            }
        )
    
    def _create_paragraph_segment_chunk(self, chunk_text: str, section: DocumentSection, 
                                        segment_index: int, sentence_count: int, 
                                        end_sentence_idx: int) -> StructuredChunk:
        """Create a paragraph segment chunk with smart metadata"""
        return StructuredChunk(
            text=chunk_text,
            chunk_type="paragraph_segment",
            hierarchy_level=section.hierarchy_level,
            page_number=section.page_number,
            section_context="paragraph_content",
            word_count=len(chunk_text.split()),
            sentence_count=sentence_count,
            bounding_box=section.bounding_box,
            metadata={
                'section_type': section.section_type.value,
                'confidence': section.confidence,
                'is_segment': True,
                'segment_index': segment_index,
                'end_sentence_index': end_sentence_idx,
                'parent_section_length': len(section.text),
                'overlap_strategy': 'minimal_semantic' if self.semantic_overlap else 'none',
                'smart_chunking': True,
                'has_overlap': False  # Will be updated if overlap is added
            }
        )
    
    def _create_default_chunk(self, section: DocumentSection) -> StructuredChunk:
        """Create a default chunk for any section"""
        return StructuredChunk(
            text=section.text,
            chunk_type="default",
            hierarchy_level=section.hierarchy_level,
            page_number=section.page_number,
            section_context=section.section_type.value,
            word_count=len(section.text.split()),
            sentence_count=self._count_sentences(section.text),
            bounding_box=section.bounding_box,
            metadata={
                'section_type': section.section_type.value,
                'confidence': section.confidence,
                'overlap_strategy': 'none',
                'smart_chunking': True
            }
        )
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Enhanced sentence splitting"""
        import re
        
        # Enhanced sentence splitting with better handling of abbreviations
        # Common abbreviations that shouldn't trigger sentence breaks
        abbreviations = r'(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|Inc|Corp|Ltd|Co|St|Ave|Blvd|Rd|Fig|Table|Ch|Sec|Vol|No|pp|cf|i\.e|e\.g|et al)'
        
        # Split on sentence endings, but not after abbreviations
        sentences = re.split(r'(?<!' + abbreviations + r')\s*[.!?]+\s+(?=[A-Z])', text)
        
        # Clean up sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Handle edge cases where splitting failed
        if len(sentences) == 1 and len(text) > self.max_chunk_size:
            # Fallback to simpler splitting
            sentences = re.split(r'[.!?]+\s+', text)
            sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _count_sentences(self, text: str) -> int:
        """Count sentences in text"""
        return len(self._split_into_sentences(text))
    
    def _optimize_chunks(self, chunks: List[StructuredChunk]) -> List[StructuredChunk]:
        """Smart post-processing to optimize chunk boundaries and sizes"""
        if not chunks:
            return chunks
        
        optimized = []
        i = 0
        
        while i < len(chunks):
            chunk = chunks[i]
            
            # Smart merging logic for small chunks
            if (len(chunk.text) < self.min_chunk_size and 
                i + 1 < len(chunks)):
                
                next_chunk = chunks[i + 1]
                
                # Only merge compatible chunks
                if self._can_merge_chunks(chunk, next_chunk):
                    merged_chunk = self._merge_chunks(chunk, next_chunk)
                    optimized.append(merged_chunk)
                    i += 2  # Skip next chunk as it's been merged
                else:
                    optimized.append(chunk)
                    i += 1
            else:
                optimized.append(chunk)
                i += 1
        
        return optimized
    
    def _can_merge_chunks(self, chunk1: StructuredChunk, chunk2: StructuredChunk) -> bool:
        """Determine if two chunks can be safely merged"""
        
        # Don't merge different chunk types
        if chunk1.chunk_type != chunk2.chunk_type:
            return False
        
        # Don't merge if combined size would be too large
        combined_length = len(chunk1.text) + len(chunk2.text)
        if combined_length > self.max_chunk_size:
            return False
        
        # Don't merge across page boundaries
        if chunk1.page_number != chunk2.page_number:
            return False
        
        # Don't merge different hierarchy levels
        if chunk1.hierarchy_level != chunk2.hierarchy_level:
            return False
        
        # Don't merge tables or lists (they should remain intact)
        if chunk1.chunk_type in ['table', 'list']:
            return False
        
        return True
    
    def _merge_chunks(self, chunk1: StructuredChunk, chunk2: StructuredChunk) -> StructuredChunk:
        """Merge two compatible chunks"""
        
        # Determine appropriate separator
        separator = self._get_merge_separator(chunk1, chunk2)
        
        merged_text = chunk1.text + separator + chunk2.text
        
        return StructuredChunk(
            text=merged_text,
            chunk_type=chunk1.chunk_type,
            hierarchy_level=chunk1.hierarchy_level,
            page_number=chunk1.page_number,
            section_context=chunk1.section_context,
            word_count=chunk1.word_count + chunk2.word_count,
            sentence_count=chunk1.sentence_count + chunk2.sentence_count,
            bounding_box=self._merge_bounding_boxes(chunk1.bounding_box, chunk2.bounding_box),
            metadata={
                **chunk1.metadata,
                'merged': True,
                'merged_from': [chunk1.metadata.get('segment_index', 0), 
                               chunk2.metadata.get('segment_index', 1)],
                'optimization': 'merged_small_chunks'
            }
        )
    
    def _get_merge_separator(self, chunk1: StructuredChunk, chunk2: StructuredChunk) -> str:
        """Get appropriate separator for merging chunks"""
        
        if chunk1.chunk_type == 'list':
            return '\n'
        elif chunk1.chunk_type in ['header', 'title']:
            return ' '
        else:
            return ' '  # Default space separator
    
    def _fallback_chunking(self, textract_response: Dict) -> List[StructuredChunk]:
        """Fallback to simple chunking if smart structured chunking fails"""
        logger.warning("Falling back to simple chunking")
        
        # Extract all text from Textract response
        text = ""
        for block in textract_response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                text += block.get('Text', '') + '\n'
        
        # Simple sentence-based chunking with no overlap (consistent with smart strategy)
        sentences = self._split_into_sentences(text)
        chunks = []
        
        chunk_size = 8  # sentences per chunk (larger than original for better coherence)
        overlap = 0     # no overlap for consistency
        
        for i in range(0, len(sentences), chunk_size):
            chunk_sentences = sentences[i:i + chunk_size]
            if chunk_sentences:
                chunk_text = ' '.join(chunk_sentences)
                chunk = StructuredChunk(
                    text=chunk_text,
                    chunk_type="fallback",
                    hierarchy_level=1,
                    page_number=1,
                    section_context="fallback_chunk",
                    word_count=len(chunk_text.split()),
                    sentence_count=len(chunk_sentences),
                    bounding_box={},
                    metadata={
                        'fallback': True, 
                        'chunk_index': len(chunks),
                        'overlap_strategy': 'none',
                        'smart_chunking': False
                    }
                )
                chunks.append(chunk)
        
        return chunks


# Combine all parts into the complete module
def combine_smart_chunking_parts():
    """Combine all parts of the smart chunking module"""
    
    # Read all parts
    with open('/Users/chris/climate-risk-rag-aws/lambda/shared_layer/python/structured_chunking_smart.py', 'r') as f:
        part1 = f.read()
    
    with open('/Users/chris/climate-risk-rag-aws/lambda/shared_layer/python/structured_chunking_smart_part2.py', 'r') as f:
        part2 = f.read()
    
    with open('/Users/chris/climate-risk-rag-aws/lambda/shared_layer/python/structured_chunking_smart_part3.py', 'r') as f:
        part3 = f.read()
    
    # Combine into complete module
    complete_module = part1 + '\n' + part2 + '\n' + part3
    
    # Write complete module
    with open('/Users/chris/climate-risk-rag-aws/lambda/shared_layer/python/structured_chunking_smart_complete.py', 'w') as f:
        f.write(complete_module)
    
    print("✅ Smart structured chunking module combined successfully")

if __name__ == "__main__":
    combine_smart_chunking_parts()
