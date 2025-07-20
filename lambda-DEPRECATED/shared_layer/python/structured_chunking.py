"""
Structured Chunking Module
Implements AutoChunker-inspired chunking using Amazon Textract's document structure detection
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class BlockType(Enum):
    """Textract block types"""
    PAGE = "PAGE"
    LINE = "LINE"
    WORD = "WORD"
    SELECTION_ELEMENT = "SELECTION_ELEMENT"
    TABLE = "TABLE"
    CELL = "CELL"
    MERGED_CELL = "MERGED_CELL"
    TITLE = "TITLE"
    QUERY = "QUERY"
    QUERY_RESULT = "QUERY_RESULT"

class SectionType(Enum):
    """Document section types"""
    TITLE = "title"
    HEADER = "header"
    SUBHEADER = "subheader"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    FOOTER = "footer"
    CAPTION = "caption"

@dataclass
class DocumentSection:
    """Represents a logical section of a document"""
    text: str
    section_type: SectionType
    hierarchy_level: int
    page_number: int
    bounding_box: Dict
    confidence: float
    children: List['DocumentSection'] = None
    metadata: Dict = None

@dataclass
class StructuredChunk:
    """Represents a structured chunk with context"""
    text: str
    chunk_type: str
    hierarchy_level: int
    page_number: int
    section_context: str
    word_count: int
    sentence_count: int
    bounding_box: Dict
    metadata: Dict

class StructuredChunker:
    """Implements structure-aware document chunking using Textract output"""
    
    def __init__(self, 
                 min_chunk_size: int = 100,
                 max_chunk_size: int = 1000,
                 overlap_sentences: int = 2,
                 preserve_tables: bool = True):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_sentences = overlap_sentences
        self.preserve_tables = preserve_tables
        
        # Patterns for identifying document structure
        self.header_patterns = [
            r'^[A-Z][A-Z\s]{10,}$',  # ALL CAPS headers
            r'^\d+\.?\s+[A-Z]',       # Numbered sections
            r'^[IVX]+\.?\s+[A-Z]',    # Roman numerals
            r'^[A-Z]\.\s+[A-Z]',      # Letter sections
        ]
        
        self.list_patterns = [
            r'^\s*[-•]\s+',           # Bullet points
            r'^\s*\d+\.\s+',          # Numbered lists
            r'^\s*[a-z]\)\s+',        # Letter lists
        ]
    
    def chunk_document(self, textract_response: Dict) -> List[StructuredChunk]:
        """Main entry point for structured chunking"""
        try:
            logger.info("Starting structured document chunking")
            
            # Extract document structure from Textract response
            document_structure = self._extract_document_structure(textract_response)
            
            # Create structured chunks
            chunks = self._create_structured_chunks(document_structure)
            
            # Post-process chunks (merge small, split large)
            optimized_chunks = self._optimize_chunks(chunks)
            
            logger.info(f"Created {len(optimized_chunks)} structured chunks")
            return optimized_chunks
            
        except Exception as e:
            logger.error(f"Error in structured chunking: {str(e)}")
            # Fallback to simple chunking
            return self._fallback_chunking(textract_response)
    
    def _extract_document_structure(self, textract_response: Dict) -> List[DocumentSection]:
        """Extract hierarchical document structure from Textract blocks"""
        blocks = textract_response.get('Blocks', [])
        
        # Group blocks by page
        pages = self._group_blocks_by_page(blocks)
        
        document_sections = []
        
        for page_num, page_blocks in pages.items():
            # Extract text lines with positioning
            lines = self._extract_lines_with_position(page_blocks)
            
            # Identify document sections
            page_sections = self._identify_sections(lines, page_num)
            
            document_sections.extend(page_sections)
        
        return document_sections
    
    def _group_blocks_by_page(self, blocks: List[Dict]) -> Dict[int, List[Dict]]:
        """Group Textract blocks by page number"""
        pages = {}
        
        for block in blocks:
            if block['BlockType'] == 'PAGE':
                page_num = len(pages) + 1
                pages[page_num] = []
            elif 'Page' in block:
                page_num = block['Page']
                if page_num not in pages:
                    pages[page_num] = []
                pages[page_num].append(block)
        
        return pages
    
    def _extract_lines_with_position(self, page_blocks: List[Dict]) -> List[Dict]:
        """Extract text lines with positional information"""
        lines = []
        
        for block in page_blocks:
            if block['BlockType'] == 'LINE':
                line_info = {
                    'text': block.get('Text', ''),
                    'confidence': block.get('Confidence', 0),
                    'bounding_box': block.get('Geometry', {}).get('BoundingBox', {}),
                    'block_id': block.get('Id', ''),
                    'relationships': block.get('Relationships', [])
                }
                
                # Calculate position metrics for structure detection
                bbox = line_info['bounding_box']
                line_info['top'] = bbox.get('Top', 0)
                line_info['left'] = bbox.get('Left', 0)
                line_info['width'] = bbox.get('Width', 0)
                line_info['height'] = bbox.get('Height', 0)
                
                lines.append(line_info)
        
        # Sort lines by vertical position (top to bottom)
        lines.sort(key=lambda x: (x['top'], x['left']))
        
        return lines
    
    def _identify_sections(self, lines: List[Dict], page_num: int) -> List[DocumentSection]:
        """Identify logical sections from text lines"""
        sections = []
        current_section = None
        
        for i, line in enumerate(lines):
            text = line['text'].strip()
            if not text:
                continue
            
            # Determine section type and hierarchy
            section_type, hierarchy_level = self._classify_line(text, line, lines, i)
            
            # Start new section if type changes or hierarchy indicates new section
            if (current_section is None or 
                section_type != current_section.section_type or
                (section_type == SectionType.HEADER and hierarchy_level <= current_section.hierarchy_level)):
                
                # Save previous section
                if current_section:
                    sections.append(current_section)
                
                # Start new section
                current_section = DocumentSection(
                    text=text,
                    section_type=section_type,
                    hierarchy_level=hierarchy_level,
                    page_number=page_num,
                    bounding_box=line['bounding_box'],
                    confidence=line['confidence'],
                    metadata={'line_count': 1}
                )
            else:
                # Add to current section
                current_section.text += '\n' + text
                current_section.metadata['line_count'] += 1
                
                # Update bounding box to encompass all lines
                current_section.bounding_box = self._merge_bounding_boxes(
                    current_section.bounding_box, line['bounding_box']
                )
        
        # Add final section
        if current_section:
            sections.append(current_section)
        
        return sections
    
    def _classify_line(self, text: str, line: Dict, all_lines: List[Dict], index: int) -> Tuple[SectionType, int]:
        """Classify a text line into section type and hierarchy level"""
        
        # Check for headers using multiple signals
        if self._is_header(text, line, all_lines, index):
            hierarchy_level = self._determine_header_level(text, line)
            if hierarchy_level == 1:
                return SectionType.TITLE, 1
            elif hierarchy_level == 2:
                return SectionType.HEADER, 2
            else:
                return SectionType.SUBHEADER, hierarchy_level
        
        # Check for lists
        if self._is_list_item(text):
            return SectionType.LIST, 4
        
        # Check for table content (would need additional Textract table analysis)
        if self._is_table_content(text, line):
            return SectionType.TABLE, 5
        
        # Check for captions
        if self._is_caption(text):
            return SectionType.CAPTION, 6
        
        # Default to paragraph
        return SectionType.PARAGRAPH, 3
    
    def _is_header(self, text: str, line: Dict, all_lines: List[Dict], index: int) -> bool:
        """Determine if a line is a header using multiple signals"""
        
        # Pattern matching
        import re
        for pattern in self.header_patterns:
            if re.match(pattern, text):
                return True
        
        # Font size analysis (if available in Textract geometry)
        bbox = line['bounding_box']
        line_height = bbox.get('Height', 0)
        
        # Compare with surrounding lines
        if index > 0 and index < len(all_lines) - 1:
            prev_height = all_lines[index - 1]['bounding_box'].get('Height', 0)
            next_height = all_lines[index + 1]['bounding_box'].get('Height', 0)
            
            # Significantly larger text might be a header
            if line_height > prev_height * 1.2 and line_height > next_height * 1.2:
                return True
        
        # Positioning analysis
        left_margin = bbox.get('Left', 0)
        
        # Very left-aligned text might be a header
        if left_margin < 0.1 and len(text) < 100:
            return True
        
        # All caps and short might be header
        if text.isupper() and len(text.split()) <= 8:
            return True
        
        return False
    
    def _determine_header_level(self, text: str, line: Dict) -> int:
        """Determine header hierarchy level"""
        import re
        
        # Check for numbered sections
        if re.match(r'^\d+\.?\s+', text):
            return 2
        elif re.match(r'^\d+\.\d+\.?\s+', text):
            return 3
        elif re.match(r'^\d+\.\d+\.\d+\.?\s+', text):
            return 4
        
        # Check for Roman numerals
        if re.match(r'^[IVX]+\.?\s+', text):
            return 2
        
        # Font size-based (approximate)
        line_height = line['bounding_box'].get('Height', 0)
        if line_height > 0.03:  # Large text
            return 1
        elif line_height > 0.02:  # Medium text
            return 2
        else:
            return 3
    
    def _is_list_item(self, text: str) -> bool:
        """Check if text is a list item"""
        import re
        for pattern in self.list_patterns:
            if re.match(pattern, text):
                return True
        return False
    
    def _is_table_content(self, text: str, line: Dict) -> bool:
        """Check if text is part of a table"""
        # This would be enhanced with Textract's table detection
        # For now, use simple heuristics
        
        # Multiple tab-separated values
        if '\t' in text and len(text.split('\t')) > 2:
            return True
        
        # Multiple spaces suggesting columns
        import re
        if re.search(r'\s{3,}', text) and len(text.split()) > 3:
            return True
        
        return False
    
    def _is_caption(self, text: str) -> bool:
        """Check if text is a caption"""
        import re
        caption_patterns = [
            r'^Figure\s+\d+',
            r'^Table\s+\d+',
            r'^Chart\s+\d+',
            r'^Graph\s+\d+',
        ]
        
        for pattern in caption_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _merge_bounding_boxes(self, bbox1: Dict, bbox2: Dict) -> Dict:
        """Merge two bounding boxes to encompass both"""
        if not bbox1:
            return bbox2
        if not bbox2:
            return bbox1
        
        # Calculate merged bounding box
        left = min(bbox1.get('Left', 0), bbox2.get('Left', 0))
        top = min(bbox1.get('Top', 0), bbox2.get('Top', 0))
        
        right1 = bbox1.get('Left', 0) + bbox1.get('Width', 0)
        right2 = bbox2.get('Left', 0) + bbox2.get('Width', 0)
        right = max(right1, right2)
        
        bottom1 = bbox1.get('Top', 0) + bbox1.get('Height', 0)
        bottom2 = bbox2.get('Top', 0) + bbox2.get('Height', 0)
        bottom = max(bottom1, bottom2)
        
        return {
            'Left': left,
            'Top': top,
            'Width': right - left,
            'Height': bottom - top
        }
    
    def _create_structured_chunks(self, sections: List[DocumentSection]) -> List[StructuredChunk]:
        """Create chunks from document sections"""
        chunks = []
        
        for i, section in enumerate(sections):
            # Handle different section types
            if section.section_type == SectionType.TABLE and self.preserve_tables:
                # Tables as single chunks
                chunk = self._create_table_chunk(section)
                chunks.append(chunk)
                
            elif section.section_type in [SectionType.TITLE, SectionType.HEADER, SectionType.SUBHEADER]:
                # Headers with following content
                chunk = self._create_header_chunk(section, sections, i)
                chunks.append(chunk)
                
            elif section.section_type == SectionType.PARAGRAPH:
                # Split long paragraphs intelligently
                para_chunks = self._split_paragraph_intelligently(section)
                chunks.extend(para_chunks)
                
            elif section.section_type == SectionType.LIST:
                # Lists as coherent chunks
                chunk = self._create_list_chunk(section)
                chunks.append(chunk)
                
            else:
                # Default chunk creation
                chunk = self._create_default_chunk(section)
                chunks.append(chunk)
        
        return chunks
    
    def _create_table_chunk(self, section: DocumentSection) -> StructuredChunk:
        """Create a chunk for table content"""
        return StructuredChunk(
            text=section.text,
            chunk_type="table",
            hierarchy_level=section.hierarchy_level,
            page_number=section.page_number,
            section_context="table_data",
            word_count=len(section.text.split()),
            sentence_count=section.text.count('.') + section.text.count('!') + section.text.count('?'),
            bounding_box=section.bounding_box,
            metadata={
                'section_type': section.section_type.value,
                'confidence': section.confidence,
                'preserve_structure': True
            }
        )
    
    def _create_header_chunk(self, section: DocumentSection, all_sections: List[DocumentSection], index: int) -> StructuredChunk:
        """Create a chunk for header with context"""
        
        # Include header and some following content for context
        context_text = section.text
        
        # Add following paragraph if it exists and is short
        if index + 1 < len(all_sections):
            next_section = all_sections[index + 1]
            if (next_section.section_type == SectionType.PARAGRAPH and 
                len(next_section.text) < self.max_chunk_size // 2):
                context_text += '\n\n' + next_section.text
        
        return StructuredChunk(
            text=context_text,
            chunk_type="header_with_context",
            hierarchy_level=section.hierarchy_level,
            page_number=section.page_number,
            section_context=f"header_level_{section.hierarchy_level}",
            word_count=len(context_text.split()),
            sentence_count=self._count_sentences(context_text),
            bounding_box=section.bounding_box,
            metadata={
                'section_type': section.section_type.value,
                'confidence': section.confidence,
                'is_header': True
            }
        )
    
    def _split_paragraph_intelligently(self, section: DocumentSection) -> List[StructuredChunk]:
        """Split long paragraphs while preserving coherence"""
        text = section.text
        
        if len(text) <= self.max_chunk_size:
            # Small paragraph, keep as single chunk
            return [self._create_default_chunk(section)]
        
        # Split into sentences
        sentences = self._split_into_sentences(text)
        
        chunks = []
        current_chunk_sentences = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # Check if adding this sentence would exceed max size
            if (current_length + sentence_length > self.max_chunk_size and 
                current_chunk_sentences):
                
                # Create chunk from current sentences
                chunk_text = ' '.join(current_chunk_sentences)
                chunk = StructuredChunk(
                    text=chunk_text,
                    chunk_type="paragraph_segment",
                    hierarchy_level=section.hierarchy_level,
                    page_number=section.page_number,
                    section_context="paragraph_content",
                    word_count=len(chunk_text.split()),
                    sentence_count=len(current_chunk_sentences),
                    bounding_box=section.bounding_box,
                    metadata={
                        'section_type': section.section_type.value,
                        'confidence': section.confidence,
                        'is_segment': True,
                        'segment_index': len(chunks)
                    }
                )
                chunks.append(chunk)
                
                # Start new chunk with overlap
                if len(current_chunk_sentences) > self.overlap_sentences:
                    overlap_sentences = current_chunk_sentences[-self.overlap_sentences:]
                    current_chunk_sentences = overlap_sentences + [sentence]
                    current_length = sum(len(s) for s in current_chunk_sentences)
                else:
                    current_chunk_sentences = [sentence]
                    current_length = sentence_length
            else:
                current_chunk_sentences.append(sentence)
                current_length += sentence_length
        
        # Add final chunk
        if current_chunk_sentences:
            chunk_text = ' '.join(current_chunk_sentences)
            chunk = StructuredChunk(
                text=chunk_text,
                chunk_type="paragraph_segment",
                hierarchy_level=section.hierarchy_level,
                page_number=section.page_number,
                section_context="paragraph_content",
                word_count=len(chunk_text.split()),
                sentence_count=len(current_chunk_sentences),
                bounding_box=section.bounding_box,
                metadata={
                    'section_type': section.section_type.value,
                    'confidence': section.confidence,
                    'is_segment': True,
                    'segment_index': len(chunks)
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _create_list_chunk(self, section: DocumentSection) -> StructuredChunk:
        """Create a chunk for list content"""
        return StructuredChunk(
            text=section.text,
            chunk_type="list",
            hierarchy_level=section.hierarchy_level,
            page_number=section.page_number,
            section_context="list_content",
            word_count=len(section.text.split()),
            sentence_count=section.text.count('\n') + 1,  # List items
            bounding_box=section.bounding_box,
            metadata={
                'section_type': section.section_type.value,
                'confidence': section.confidence,
                'is_list': True
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
                'confidence': section.confidence
            }
        )
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using simple heuristics"""
        import re
        
        # Simple sentence splitting (could be enhanced with NLTK or spaCy)
        sentences = re.split(r'[.!?]+\s+', text)
        
        # Clean up sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _count_sentences(self, text: str) -> int:
        """Count sentences in text"""
        return len(self._split_into_sentences(text))
    
    def _optimize_chunks(self, chunks: List[StructuredChunk]) -> List[StructuredChunk]:
        """Post-process chunks to optimize size and coherence"""
        optimized = []
        
        i = 0
        while i < len(chunks):
            chunk = chunks[i]
            
            # Merge very small chunks with next chunk if appropriate
            if (len(chunk.text) < self.min_chunk_size and 
                i + 1 < len(chunks) and
                chunks[i + 1].chunk_type == chunk.chunk_type):
                
                next_chunk = chunks[i + 1]
                merged_chunk = StructuredChunk(
                    text=chunk.text + '\n\n' + next_chunk.text,
                    chunk_type=chunk.chunk_type,
                    hierarchy_level=min(chunk.hierarchy_level, next_chunk.hierarchy_level),
                    page_number=chunk.page_number,
                    section_context=chunk.section_context,
                    word_count=chunk.word_count + next_chunk.word_count,
                    sentence_count=chunk.sentence_count + next_chunk.sentence_count,
                    bounding_box=self._merge_bounding_boxes(chunk.bounding_box, next_chunk.bounding_box),
                    metadata={**chunk.metadata, 'merged': True}
                )
                optimized.append(merged_chunk)
                i += 2  # Skip next chunk as it's been merged
            else:
                optimized.append(chunk)
                i += 1
        
        return optimized
    
    def _fallback_chunking(self, textract_response: Dict) -> List[StructuredChunk]:
        """Fallback to simple chunking if structured chunking fails"""
        logger.warning("Falling back to simple chunking")
        
        # Extract all text from Textract response
        text = ""
        for block in textract_response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                text += block.get('Text', '') + '\n'
        
        # Simple sentence-based chunking
        sentences = self._split_into_sentences(text)
        chunks = []
        
        chunk_size = 5  # sentences per chunk
        overlap = 2     # sentence overlap
        
        for i in range(0, len(sentences), chunk_size - overlap):
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
                    metadata={'fallback': True, 'chunk_index': len(chunks)}
                )
                chunks.append(chunk)
        
        return chunks
