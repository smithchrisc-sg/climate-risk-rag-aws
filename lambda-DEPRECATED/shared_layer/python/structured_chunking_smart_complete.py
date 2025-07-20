"""
Smart Structured Chunking Module
Implements intelligent chunking with minimal overlap based on document structure
Eliminates unnecessary redundancy while preserving semantic coherence
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
    page_number: int = 1
    bounding_box: Dict = None
    confidence: float = 1.0
    start_char: int = 0
    end_char: int = 0
    children: List['DocumentSection'] = None
    metadata: Dict = None

@dataclass
class StructuredChunk:
    """Represents a structured chunk with context"""
    text: str
    chunk_type: str
    hierarchy_level: int
    page_number: int = 1
    section_context: str = ""
    word_count: int = 0
    sentence_count: int = 0
    bounding_box: Dict = None
    metadata: Dict = None
    start_char: int = 0
    end_char: int = 0

class SmartStructuredChunker:
    """Implements structure-aware document chunking with smart overlap strategy"""
    
    def __init__(self, 
                 min_chunk_size: int = 150,         # Larger for complete thoughts
                 max_chunk_size: int = 1200,        # Allow larger chunks for sections
                 overlap_sentences: int = 0,        # No fixed overlap
                 semantic_overlap: bool = True,     # Smart overlap when needed
                 respect_boundaries: bool = True,   # Respect section boundaries
                 preserve_tables: bool = True,      # Keep tables intact
                 preserve_lists: bool = True,       # Keep lists intact
                 header_context: bool = True):      # Include context with headers
        
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_sentences = overlap_sentences
        self.semantic_overlap = semantic_overlap
        self.respect_boundaries = respect_boundaries
        self.preserve_tables = preserve_tables
        self.preserve_lists = preserve_lists
        self.header_context = header_context
        
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
        """Main entry point for smart structured chunking"""
        try:
            logger.info("Starting smart structured document chunking")
            
            # Extract document structure from Textract response
            document_structure = self._extract_document_structure(textract_response)
            
            # Create structured chunks with smart overlap
            chunks = self._create_smart_structured_chunks(document_structure)
            
            # Post-process chunks (merge small, optimize boundaries)
            optimized_chunks = self._optimize_chunks(chunks)
            
            logger.info(f"Created {len(optimized_chunks)} smart structured chunks")
            return optimized_chunks
            
        except Exception as e:
            logger.error(f"Error in smart structured chunking: {str(e)}")
            # Fallback to simple chunking
            return self._fallback_chunking(textract_response)
    
    def chunk_text(self, text: str) -> List[StructuredChunk]:
        """Chunk plain text without Textract structure data"""
        try:
            logger.info("Starting smart text-only chunking")
            
            # Create a simple document structure from plain text
            lines = text.split('\n')
            sections = []
            
            current_section = None
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Simple heuristics for text-only chunking
                if len(line) < 100 and (line.isupper() or line.endswith(':')):
                    # Likely a header
                    if current_section:
                        sections.append(current_section)
                    current_section = DocumentSection(
                        text=line,
                        section_type=SectionType.HEADER,
                        hierarchy_level=1,
                        start_char=0,
                        end_char=len(line),
                        bounding_box={},
                        metadata={'text_only': True}
                    )
                else:
                    # Regular paragraph text
                    if current_section and current_section.section_type == SectionType.PARAGRAPH:
                        # Continue current paragraph
                        current_section.text += ' ' + line
                    else:
                        # Start new paragraph
                        if current_section:
                            sections.append(current_section)
                        current_section = DocumentSection(
                            text=line,
                            section_type=SectionType.PARAGRAPH,
                            hierarchy_level=3,
                            start_char=0,
                            end_char=len(line),
                            bounding_box={},
                            metadata={'text_only': True}
                        )
            
            # Add the last section
            if current_section:
                sections.append(current_section)
            
            # Create smart structured chunks
            chunks = self._create_smart_structured_chunks(sections)
            
            logger.info(f"Smart text-only chunking created {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Smart text-only chunking failed: {e}")
            # Fallback to simple chunking
            return self._fallback_text_chunking(text)
    
    def _fallback_text_chunking(self, text: str) -> List[StructuredChunk]:
        """Simple fallback chunking for plain text"""
        chunks = []
        chunk_size = self.max_chunk_size
        overlap = 100
        
        for i in range(0, len(text), chunk_size - overlap):
            chunk_text = text[i:i + chunk_size]
            if chunk_text.strip():
                chunks.append(StructuredChunk(
                    text=chunk_text.strip(),
                    chunk_type="text",
                    hierarchy_level=3,
                    start_char=i,
                    end_char=min(i + chunk_size, len(text)),
                    bounding_box={},
                    metadata={
                        'chunking_method': 'fallback_text',
                        'chunk_size': len(chunk_text),
                        'overlap_used': overlap if i > 0 else 0
                    }
                ))
        
        return chunks
    
    def _extract_document_structure(self, textract_response: Dict) -> List[DocumentSection]:
        """Extract hierarchical document structure from Textract blocks"""
        blocks = textract_response.get('Blocks', [])
        
        # Group blocks by page
        pages = self._group_blocks_by_page(blocks)
        
        document_sections = []
        
        for page_num, page_blocks in pages.items():
            # Extract text lines with positioning
            lines = self._extract_lines_with_position(page_blocks)
            
            # Identify document sections with enhanced structure detection
            page_sections = self._identify_smart_sections(lines, page_num)
            
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
    
    def _identify_smart_sections(self, lines: List[Dict], page_num: int) -> List[DocumentSection]:
        """Identify logical sections with enhanced structure awareness"""
        sections = []
        current_section = None
        
        for i, line in enumerate(lines):
            text = line['text'].strip()
            if not text:
                continue
            
            # Determine section type and hierarchy with smart detection
            section_type, hierarchy_level = self._classify_line_smart(text, line, lines, i)
            
            # Smart section boundary detection
            should_start_new_section = self._should_start_new_section(
                current_section, section_type, hierarchy_level, text, line, lines, i
            )
            
            if should_start_new_section:
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
                    metadata={'line_count': 1, 'smart_detection': True}
                )
            else:
                # Add to current section with smart concatenation
                if current_section:
                    current_section.text += self._get_section_separator(current_section, text)
                    current_section.metadata['line_count'] += 1
                    
                    # Update bounding box to encompass all lines
                    current_section.bounding_box = self._merge_bounding_boxes(
                        current_section.bounding_box, line['bounding_box']
                    )
        
        # Add final section
        if current_section:
            sections.append(current_section)
        
        return sections
    
    def _should_start_new_section(self, current_section, section_type, hierarchy_level, 
                                  text, line, all_lines, index):
        """Smart decision on whether to start a new section"""
        
        if current_section is None:
            return True
        
        # Always start new section for different types
        if section_type != current_section.section_type:
            return True
        
        # For headers, start new section if hierarchy level changes
        if section_type in [SectionType.HEADER, SectionType.SUBHEADER, SectionType.TITLE]:
            if hierarchy_level <= current_section.hierarchy_level:
                return True
        
        # For tables and lists, each is typically a separate section
        if section_type in [SectionType.TABLE, SectionType.LIST]:
            return True
        
        # For paragraphs, use smart continuation logic
        if section_type == SectionType.PARAGRAPH:
            return self._should_start_new_paragraph_section(
                current_section, text, line, all_lines, index
            )
        
        return False
    
    def _should_start_new_paragraph_section(self, current_section, text, line, all_lines, index):
        """Determine if paragraph should start new section based on context"""
        
        # Check for significant spacing (paragraph break)
        if index > 0:
            prev_line = all_lines[index - 1]
            vertical_gap = line['top'] - (prev_line['top'] + prev_line['height'])
            
            # Significant vertical gap suggests new paragraph
            if vertical_gap > prev_line['height'] * 1.5:
                return True
        
        # Check for indentation changes
        current_indent = line['left']
        if hasattr(current_section, 'typical_indent'):
            indent_diff = abs(current_indent - current_section.typical_indent)
            if indent_diff > 0.05:  # Significant indentation change
                return True
        else:
            current_section.typical_indent = current_indent
        
        # Check current section length
        if len(current_section.text) > self.max_chunk_size * 0.8:
            return True
        
        return False
    
    def _get_section_separator(self, current_section, new_text):
        """Get appropriate separator between section parts"""
        
        if current_section.section_type == SectionType.LIST:
            return '\n'  # Lists need line breaks
        elif current_section.section_type in [SectionType.HEADER, SectionType.TITLE]:
            return ' '   # Headers typically single line
        else:
            return ' '   # Default space separator
    
    def _classify_line_smart(self, text: str, line: Dict, all_lines: List[Dict], index: int) -> Tuple[SectionType, int]:
        """Enhanced line classification with smart detection"""
        
        # Check for headers using multiple signals
        if self._is_header_smart(text, line, all_lines, index):
            hierarchy_level = self._determine_header_level_smart(text, line, all_lines, index)
            if hierarchy_level == 1:
                return SectionType.TITLE, 1
            elif hierarchy_level == 2:
                return SectionType.HEADER, 2
            else:
                return SectionType.SUBHEADER, hierarchy_level
        
        # Check for lists with enhanced detection
        if self._is_list_item_smart(text, line, all_lines, index):
            return SectionType.LIST, 4
        
        # Check for table content with Textract table analysis
        if self._is_table_content_smart(text, line, all_lines, index):
            return SectionType.TABLE, 5
        
        # Check for captions
        if self._is_caption_smart(text, line):
            return SectionType.CAPTION, 6
        
        # Default to paragraph with smart context
        return SectionType.PARAGRAPH, 3

    def _is_header_smart(self, text: str, line: Dict, all_lines: List[Dict], index: int) -> bool:
        """Enhanced header detection using multiple signals"""
        
        # Pattern matching
        import re
        for pattern in self.header_patterns:
            if re.match(pattern, text):
                return True
        
        # Font size analysis (enhanced with context)
        bbox = line['bounding_box']
        line_height = bbox.get('Height', 0)
        
        # Compare with surrounding lines (more context)
        surrounding_heights = []
        for i in range(max(0, index-2), min(len(all_lines), index+3)):
            if i != index:
                surrounding_heights.append(all_lines[i]['bounding_box'].get('Height', 0))
        
        if surrounding_heights:
            avg_height = sum(surrounding_heights) / len(surrounding_heights)
            # Significantly larger text is likely a header
            if line_height > avg_height * 1.3:
                return True
        
        # Positioning analysis (enhanced)
        left_margin = bbox.get('Left', 0)
        
        # Very left-aligned and short text might be header
        if left_margin < 0.1 and len(text) < 100 and len(text.split()) <= 10:
            return True
        
        # All caps and reasonable length might be header
        if text.isupper() and 3 <= len(text.split()) <= 12:
            return True
        
        # Check for common header words
        header_indicators = ['chapter', 'section', 'introduction', 'conclusion', 'summary', 'overview']
        if any(indicator in text.lower() for indicator in header_indicators):
            if len(text.split()) <= 8:
                return True
        
        return False
    
    def _determine_header_level_smart(self, text: str, line: Dict, all_lines: List[Dict], index: int) -> int:
        """Enhanced header hierarchy level determination"""
        import re
        
        # Check for numbered sections with more patterns
        if re.match(r'^\d+\.?\s+', text):
            return 2
        elif re.match(r'^\d+\.\d+\.?\s+', text):
            return 3
        elif re.match(r'^\d+\.\d+\.\d+\.?\s+', text):
            return 4
        
        # Check for Roman numerals
        if re.match(r'^[IVX]+\.?\s+', text):
            return 2
        
        # Check for letter sections
        if re.match(r'^[A-Z]\.?\s+', text):
            return 3
        
        # Font size-based with enhanced logic
        line_height = line['bounding_box'].get('Height', 0)
        
        # Calculate relative size compared to document average
        all_heights = [l['bounding_box'].get('Height', 0) for l in all_lines]
        avg_height = sum(all_heights) / len(all_heights) if all_heights else 0.02
        
        relative_size = line_height / avg_height if avg_height > 0 else 1
        
        if relative_size > 1.8:  # Very large text
            return 1
        elif relative_size > 1.4:  # Large text
            return 2
        elif relative_size > 1.1:  # Slightly larger text
            return 3
        else:
            return 4
    
    def _is_list_item_smart(self, text: str, line: Dict, all_lines: List[Dict], index: int) -> bool:
        """Enhanced list item detection"""
        import re
        
        # Standard list patterns
        for pattern in self.list_patterns:
            if re.match(pattern, text):
                return True
        
        # Check for indented text that might be list items
        left_margin = line['bounding_box'].get('Left', 0)
        
        # Compare with surrounding lines to detect indentation
        if index > 0:
            prev_margin = all_lines[index - 1]['bounding_box'].get('Left', 0)
            if left_margin > prev_margin + 0.02:  # Indented
                # Check if it starts with common list indicators
                if re.match(r'^\s*[•▪▫◦‣⁃]\s+', text) or re.match(r'^\s*[→➤➢]\s+', text):
                    return True
        
        return False
    
    def _is_table_content_smart(self, text: str, line: Dict, all_lines: List[Dict], index: int) -> bool:
        """Enhanced table content detection"""
        
        # Multiple tab-separated values
        if '\t' in text and len(text.split('\t')) > 2:
            return True
        
        # Multiple spaces suggesting columns (enhanced)
        import re
        if re.search(r'\s{3,}', text) and len(text.split()) > 3:
            # Check if surrounding lines also look like table content
            table_like_count = 0
            for i in range(max(0, index-1), min(len(all_lines), index+2)):
                if i != index:
                    other_text = all_lines[i]['text']
                    if re.search(r'\s{3,}', other_text) and len(other_text.split()) > 2:
                        table_like_count += 1
            
            if table_like_count >= 1:  # At least one surrounding line looks table-like
                return True
        
        # Check for common table patterns
        table_patterns = [
            r'^\s*\|\s*.*\s*\|\s*$',  # Pipe-separated
            r'.*\s+\d+\s+\d+.*',      # Numbers in columns
            r'.*\s+\$\d+.*',          # Currency values
        ]
        
        for pattern in table_patterns:
            if re.match(pattern, text):
                return True
        
        return False
    
    def _is_caption_smart(self, text: str, line: Dict) -> bool:
        """Enhanced caption detection"""
        import re
        caption_patterns = [
            r'^Figure\s+\d+',
            r'^Table\s+\d+',
            r'^Chart\s+\d+',
            r'^Graph\s+\d+',
            r'^Image\s+\d+',
            r'^Exhibit\s+\d+',
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
    
    def _create_smart_structured_chunks(self, sections: List[DocumentSection]) -> List[StructuredChunk]:
        """Create chunks with smart overlap strategy"""
        chunks = []
        
        for i, section in enumerate(sections):
            # Handle different section types with smart strategies
            if section.section_type == SectionType.TABLE and self.preserve_tables:
                # Tables as complete units - no overlap
                chunk = self._create_table_chunk(section)
                chunks.append(chunk)
                
            elif section.section_type == SectionType.LIST and self.preserve_lists:
                # Lists as complete units - no overlap
                chunk = self._create_list_chunk(section)
                chunks.append(chunk)
                
            elif section.section_type in [SectionType.TITLE, SectionType.HEADER, SectionType.SUBHEADER]:
                # Headers with natural context - no artificial overlap
                if self.header_context:
                    chunk = self._create_header_with_context(section, sections, i)
                else:
                    chunk = self._create_header_chunk(section)
                chunks.append(chunk)
                
            elif section.section_type == SectionType.PARAGRAPH:
                # Paragraphs with smart overlap only when splitting
                para_chunks = self._split_paragraph_with_smart_overlap(section, sections, i)
                chunks.extend(para_chunks)
                
            else:
                # Default chunk creation
                chunk = self._create_default_chunk(section)
                chunks.append(chunk)
        
        return chunks
    
    def _create_table_chunk(self, section: DocumentSection) -> StructuredChunk:
        """Create a chunk for table content - complete unit, no overlap"""
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
                'preserve_structure': True,
                'overlap_strategy': 'none',
                'smart_chunking': True
            }
        )
    
    def _create_list_chunk(self, section: DocumentSection) -> StructuredChunk:
        """Create a chunk for list content - complete unit, no overlap"""
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
                'is_list': True,
                'overlap_strategy': 'none',
                'smart_chunking': True
            }
        )
    
    def _create_header_with_context(self, section: DocumentSection, all_sections: List[DocumentSection], index: int) -> StructuredChunk:
        """Create header chunk with natural context - no artificial overlap"""
        
        # Include header and naturally following content
        context_text = section.text
        included_sections = [section.section_type.value]
        
        # Add following content if it's a paragraph and reasonably sized
        if index + 1 < len(all_sections):
            next_section = all_sections[index + 1]
            if (next_section.section_type == SectionType.PARAGRAPH and 
                len(next_section.text) < self.max_chunk_size // 2):
                context_text += '\n\n' + next_section.text
                included_sections.append('following_paragraph')
        
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
                'is_header': True,
                'includes_context': True,
                'included_sections': included_sections,
                'overlap_strategy': 'natural_context',
                'smart_chunking': True
            }
        )
    
    def _create_header_chunk(self, section: DocumentSection) -> StructuredChunk:
        """Create simple header chunk without context"""
        return StructuredChunk(
            text=section.text,
            chunk_type="header",
            hierarchy_level=section.hierarchy_level,
            page_number=section.page_number,
            section_context=f"header_level_{section.hierarchy_level}",
            word_count=len(section.text.split()),
            sentence_count=self._count_sentences(section.text),
            bounding_box=section.bounding_box,
            metadata={
                'section_type': section.section_type.value,
                'confidence': section.confidence,
                'is_header': True,
                'overlap_strategy': 'none',
                'smart_chunking': True
            }
        )

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
        abbreviations = ['Mr', 'Mrs', 'Ms', 'Dr', 'Prof', 'Sr', 'Jr', 'vs', 'etc', 'Inc', 'Corp', 'Ltd', 'Co', 'St', 'Ave', 'Blvd', 'Rd', 'Fig', 'Table', 'Ch', 'Sec', 'Vol', 'No', 'pp', 'cf', 'i.e', 'e.g', 'et al']
        
        # Split on sentence endings with look-ahead for capital letters
        sentences = re.split(r'\s*[.!?]+\s+(?=[A-Z])', text)
        
        # Filter out sentences that end with common abbreviations
        filtered_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Check if sentence ends with an abbreviation
            ends_with_abbrev = False
            for abbrev in abbreviations:
                if sentence.endswith(abbrev) or sentence.endswith(abbrev + '.'):
                    ends_with_abbrev = True
                    break
            
            # If it ends with abbreviation, try to merge with next sentence
            if ends_with_abbrev and filtered_sentences:
                # This might be a false sentence break, but we'll keep it for now
                # More sophisticated logic could merge sentences here
                pass
                
            filtered_sentences.append(sentence)
        
        sentences = filtered_sentences
        
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
