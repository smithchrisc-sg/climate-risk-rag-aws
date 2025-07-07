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
