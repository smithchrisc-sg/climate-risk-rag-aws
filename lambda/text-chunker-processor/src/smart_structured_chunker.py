"""
Smart Structured Chunking Module
Implements intelligent chunking with minimal overlap based on document structure
Eliminates unnecessary redundancy while preserving semantic coherence
PRESERVED FROM DEPRECATED VERSION - NO FUNCTIONALITY CHANGES
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

    def __post_init__(self):
        if self.children is None:
            self.children = []

@dataclass
class ChunkMetadata:
    """Metadata for a text chunk"""
    chunk_id: str
    doc_id: str
    chunk_index: int
    start_char: int
    end_char: int
    page_numbers: List[int]
    section_types: List[str]
    hierarchy_levels: List[int]
    overlap_with_previous: bool = False
    overlap_with_next: bool = False
    semantic_context: str = ""
    table_count: int = 0
    list_count: int = 0

class SmartStructuredChunker:
    """
    Advanced chunker that uses document structure for intelligent segmentation
    PRESERVED FUNCTIONALITY - NO CHANGES TO CHUNKING LOGIC
    """
    
    def __init__(self, 
                 min_chunk_size: int = 150,
                 max_chunk_size: int = 1200,
                 overlap_sentences: int = 0,
                 semantic_overlap: bool = True,
                 respect_boundaries: bool = True,
                 preserve_tables: bool = True,
                 preserve_lists: bool = True,
                 header_context: bool = True):
        
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_sentences = overlap_sentences
        self.semantic_overlap = semantic_overlap
        self.respect_boundaries = respect_boundaries
        self.preserve_tables = preserve_tables
        self.preserve_lists = preserve_lists
        self.header_context = header_context
        
        logger.info(f"SmartStructuredChunker initialized with settings:")
        logger.info(f"  Min chunk size: {min_chunk_size}")
        logger.info(f"  Max chunk size: {max_chunk_size}")
        logger.info(f"  Semantic overlap: {semantic_overlap}")
        logger.info(f"  Respect boundaries: {respect_boundaries}")
        logger.info(f"  Preserve tables: {preserve_tables}")
        logger.info(f"  Header context: {header_context}")

    def analyze_document_structure(self, textract_response: Dict) -> List[DocumentSection]:
        """
        Analyze Textract response to identify document structure
        Enhanced to use LAYOUT blocks when available
        """
        try:
            blocks = textract_response.get('blocks', [])
            sections = []
            
            # Check if we have layout information
            layout_blocks = [b for b in blocks if b.get('BlockType') == 'LAYOUT']
            has_layout = len(layout_blocks) > 0
            
            if has_layout:
                logger.info(f"Using LAYOUT analysis: {len(layout_blocks)} layout blocks found")
                sections = self._analyze_structure_with_layout(blocks)
            else:
                logger.info("Using fallback LINE-based analysis")
                sections = self._analyze_structure_fallback(blocks)
            
            logger.info(f"Analyzed document structure: {len(sections)} sections identified")
            return sections
            
        except Exception as e:
            logger.error(f"Error analyzing document structure: {e}")
            return []

    def _analyze_structure_with_layout(self, blocks: List[Dict]) -> List[DocumentSection]:
        """
        Analyze document structure using LAYOUT blocks
        """
        sections = []
        layout_blocks = [b for b in blocks if b.get('BlockType') == 'LAYOUT']
        
        # Sort layout blocks by reading order and page
        layout_blocks.sort(key=lambda x: (
            x.get('Page', 1),
            x.get('ReadingOrder', 999)
        ))
        
        for layout_block in layout_blocks:
            layout_type = layout_block.get('LayoutType', '').upper()
            text = layout_block.get('Text', '').strip()
            
            if not text:
                continue
            
            # Map Textract layout types to our section types
            section_type = self._map_layout_type_to_section_type(layout_type)
            hierarchy_level = self._determine_hierarchy_from_layout(layout_type, text)
            
            section = DocumentSection(
                text=text,
                section_type=section_type,
                hierarchy_level=hierarchy_level,
                page_number=layout_block.get('Page', 1),
                bounding_box=layout_block.get('Geometry', {}).get('BoundingBox', {}),
                confidence=layout_block.get('Confidence', 1.0),
                start_char=0  # Will be set when processing chunks
            )
            
            sections.append(section)
        
        return sections

    def _analyze_structure_fallback(self, blocks: List[Dict]) -> List[DocumentSection]:
        """
        Fallback analysis using LINE blocks (original method)
        """
        sections = []
        
        # Group blocks by page
        pages = {}
        for block in blocks:
            if block.get('BlockType') == 'PAGE':
                page_num = block.get('Page', 1)
                pages[page_num] = {'lines': [], 'tables': [], 'forms': []}
        
        # Organize content by page
        for block in blocks:
            page_num = block.get('Page', 1)
            block_type = block.get('BlockType')
            
            if block_type == 'LINE':
                if page_num in pages:
                    pages[page_num]['lines'].append(block)
            elif block_type == 'TABLE':
                if page_num in pages:
                    pages[page_num]['tables'].append(block)
            elif block_type in ['KEY_VALUE_SET']:
                if page_num in pages:
                    pages[page_num]['forms'].append(block)
        
        # Process each page
        for page_num, page_content in pages.items():
            page_sections = self._analyze_page_structure(page_content, page_num)
            sections.extend(page_sections)
        
        return sections

    def _map_layout_type_to_section_type(self, layout_type: str) -> SectionType:
        """
        Map Textract layout types to our section types
        """
        layout_mapping = {
            'TITLE': SectionType.TITLE,
            'SECTION_HEADER': SectionType.HEADER,
            'HEADER': SectionType.HEADER,
            'FOOTER': SectionType.FOOTER,
            'PAGE_HEADER': SectionType.HEADER,
            'PAGE_FOOTER': SectionType.FOOTER,
            'LIST': SectionType.LIST,
            'TABLE': SectionType.TABLE,
            'FIGURE': SectionType.CAPTION,
            'TEXT': SectionType.PARAGRAPH
        }
        
        return layout_mapping.get(layout_type, SectionType.PARAGRAPH)

    def _determine_hierarchy_from_layout(self, layout_type: str, text: str) -> int:
        """
        Determine hierarchy level from layout type and text
        """
        if layout_type == 'TITLE':
            return 1
        elif layout_type in ['SECTION_HEADER', 'HEADER']:
            # Check for numbered headers for sub-levels
            if any(char.isdigit() for char in text[:10]):
                return 2
            return 3
        elif layout_type == 'PAGE_HEADER':
            return 2
        elif layout_type in ['LIST', 'TABLE']:
            return 4
        else:
            return 5

    def _analyze_page_structure(self, page_content: Dict, page_num: int) -> List[DocumentSection]:
        """
        Analyze structure of a single page
        PRESERVED FUNCTIONALITY - NO CHANGES
        """
        sections = []
        lines = page_content.get('lines', [])
        
        # Sort lines by vertical position
        lines.sort(key=lambda x: x.get('Geometry', {}).get('BoundingBox', {}).get('Top', 0))
        
        current_section = None
        current_text = []
        
        for line in lines:
            text = line.get('Text', '').strip()
            if not text:
                continue
            
            # Determine section type based on text characteristics
            section_type = self._classify_line_type(text, line)
            hierarchy_level = self._determine_hierarchy_level(text, section_type)
            
            # Check if we need to start a new section
            if (current_section is None or 
                section_type != current_section.section_type or
                (section_type in [SectionType.TITLE, SectionType.HEADER, SectionType.SUBHEADER] and current_text)):
                
                # Save previous section
                if current_section and current_text:
                    current_section.text = '\n'.join(current_text)
                    current_section.end_char = current_section.start_char + len(current_section.text)
                    sections.append(current_section)
                
                # Start new section
                bbox = line.get('Geometry', {}).get('BoundingBox', {})
                current_section = DocumentSection(
                    text="",
                    section_type=section_type,
                    hierarchy_level=hierarchy_level,
                    page_number=page_num,
                    bounding_box=bbox,
                    confidence=line.get('Confidence', 1.0),
                    start_char=0  # Will be set when processing chunks
                )
                current_text = []
            
            current_text.append(text)
        
        # Add final section
        if current_section and current_text:
            current_section.text = '\n'.join(current_text)
            current_section.end_char = current_section.start_char + len(current_section.text)
            sections.append(current_section)
        
        return sections

    def _classify_line_type(self, text: str, line_block: Dict) -> SectionType:
        """
        Classify line type based on text characteristics
        PRESERVED FUNCTIONALITY - NO CHANGES
        """
        # Title indicators
        if (len(text) < 100 and 
            (text.isupper() or 
             any(word in text.lower() for word in ['report', 'analysis', 'study', 'assessment']) or
             not text.endswith('.'))):
            return SectionType.TITLE
        
        # Header indicators
        if (text.endswith(':') or 
            any(char.isdigit() for char in text[:10]) or
            len(text.split()) < 10):
            return SectionType.HEADER
        
        # List indicators
        if (text.startswith(('•', '-', '*', '◦')) or
            text.lstrip().startswith(tuple('123456789')) or
            text.lstrip().startswith(('a)', 'b)', 'c)', 'i)', 'ii)', 'iii)'))):
            return SectionType.LIST
        
        # Default to paragraph
        return SectionType.PARAGRAPH

    def _determine_hierarchy_level(self, text: str, section_type: SectionType) -> int:
        """
        Determine hierarchy level of section
        PRESERVED FUNCTIONALITY - NO CHANGES
        """
        if section_type == SectionType.TITLE:
            return 1
        elif section_type == SectionType.HEADER:
            # Check for numbered headers
            if any(char.isdigit() for char in text[:5]):
                return 2
            return 3
        elif section_type == SectionType.SUBHEADER:
            return 4
        else:
            return 5

    def create_smart_chunks(self, raw_text: str, textract_response: Dict, doc_id: str) -> List[Dict]:
        """
        Create intelligent chunks using document structure
        PRESERVED FUNCTIONALITY - NO CHANGES TO CHUNKING LOGIC
        """
        try:
            # Analyze document structure
            sections = self.analyze_document_structure(textract_response)
            
            if not sections:
                logger.warning("No document structure found, falling back to basic chunking")
                return self._create_basic_chunks(raw_text, doc_id)
            
            # Create chunks from sections
            chunks = []
            current_chunk_text = ""
            current_chunk_metadata = {
                'page_numbers': set(),
                'section_types': set(),
                'hierarchy_levels': set(),
                'table_count': 0,
                'list_count': 0
            }
            
            section_context = ""  # For header context
            
            for i, section in enumerate(sections):
                section_text = section.text
                
                # Add header context if enabled
                if (self.header_context and 
                    section.section_type in [SectionType.TITLE, SectionType.HEADER] and
                    section.hierarchy_level <= 3):
                    section_context = section_text
                
                # Check if adding this section would exceed max chunk size
                potential_text = current_chunk_text
                if potential_text and section_context and section.section_type == SectionType.PARAGRAPH:
                    potential_text += f"\n\n[Context: {section_context}]\n{section_text}"
                else:
                    potential_text += f"\n\n{section_text}" if potential_text else section_text
                
                # Decide whether to start new chunk
                if (len(potential_text) > self.max_chunk_size and 
                    len(current_chunk_text) >= self.min_chunk_size):
                    
                    # Save current chunk
                    if current_chunk_text:
                        chunk = self._create_chunk_from_text(
                            current_chunk_text, 
                            doc_id, 
                            len(chunks), 
                            current_chunk_metadata
                        )
                        chunks.append(chunk)
                    
                    # Start new chunk
                    current_chunk_text = section_text
                    current_chunk_metadata = {
                        'page_numbers': {section.page_number},
                        'section_types': {section.section_type.value},
                        'hierarchy_levels': {section.hierarchy_level},
                        'table_count': 1 if section.section_type == SectionType.TABLE else 0,
                        'list_count': 1 if section.section_type == SectionType.LIST else 0
                    }
                else:
                    # Add to current chunk
                    if current_chunk_text:
                        if section_context and section.section_type == SectionType.PARAGRAPH:
                            current_chunk_text += f"\n\n[Context: {section_context}]\n{section_text}"
                        else:
                            current_chunk_text += f"\n\n{section_text}"
                    else:
                        current_chunk_text = section_text
                    
                    # Update metadata
                    current_chunk_metadata['page_numbers'].add(section.page_number)
                    current_chunk_metadata['section_types'].add(section.section_type.value)
                    current_chunk_metadata['hierarchy_levels'].add(section.hierarchy_level)
                    
                    if section.section_type == SectionType.TABLE:
                        current_chunk_metadata['table_count'] += 1
                    elif section.section_type == SectionType.LIST:
                        current_chunk_metadata['list_count'] += 1
            
            # Add final chunk
            if current_chunk_text:
                chunk = self._create_chunk_from_text(
                    current_chunk_text, 
                    doc_id, 
                    len(chunks), 
                    current_chunk_metadata
                )
                chunks.append(chunk)
            
            # Add semantic overlap if enabled
            if self.semantic_overlap:
                chunks = self._add_semantic_overlap(chunks)
            
            logger.info(f"Created {len(chunks)} smart structured chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error creating smart chunks: {e}")
            return self._create_basic_chunks(raw_text, doc_id)

    def _create_chunk_from_text(self, text: str, doc_id: str, chunk_index: int, metadata: Dict) -> Dict:
        """
        Create chunk dictionary from text and metadata
        PRESERVED FUNCTIONALITY - NO CHANGES
        """
        chunk_id = f"{doc_id}_chunk_{chunk_index:04d}"
        
        return {
            'chunk_id': chunk_id,
            'doc_id': doc_id,
            'chunk_index': chunk_index,
            'text': text.strip(),
            'character_count': len(text.strip()),
            'page_numbers': sorted(list(metadata['page_numbers'])),
            'section_types': sorted(list(metadata['section_types'])),
            'hierarchy_levels': sorted(list(metadata['hierarchy_levels'])),
            'table_count': metadata['table_count'],
            'list_count': metadata['list_count'],
            'semantic_context': metadata.get('semantic_context', ''),
            'overlap_with_previous': False,
            'overlap_with_next': False
        }

    def _add_semantic_overlap(self, chunks: List[Dict]) -> List[Dict]:
        """
        Add intelligent semantic overlap between chunks
        PRESERVED FUNCTIONALITY - NO CHANGES
        """
        if len(chunks) <= 1:
            return chunks
        
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]
            
            # Check if semantic overlap is beneficial
            current_text = current_chunk['text']
            next_text = next_chunk['text']
            
            # Look for sentence boundaries for clean overlap
            current_sentences = current_text.split('. ')
            next_sentences = next_text.split('. ')
            
            if len(current_sentences) > 1 and len(next_sentences) > 1:
                # Add last sentence of current chunk to next chunk
                overlap_text = current_sentences[-1]
                if len(overlap_text) > 20:  # Only meaningful overlaps
                    next_chunk['text'] = f"[Previous context: {overlap_text}] {next_text}"
                    next_chunk['overlap_with_previous'] = True
                    current_chunk['overlap_with_next'] = True
        
        return chunks

    def _create_basic_chunks(self, text: str, doc_id: str) -> List[Dict]:
        """
        Fallback basic chunking when structure analysis fails
        PRESERVED FUNCTIONALITY - NO CHANGES
        """
        chunks = []
        words = text.split()
        
        chunk_size = self.max_chunk_size // 5  # Rough word estimate
        
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunk_text = ' '.join(chunk_words)
            
            chunk_id = f"{doc_id}_chunk_{len(chunks):04d}"
            
            chunk = {
                'chunk_id': chunk_id,
                'doc_id': doc_id,
                'chunk_index': len(chunks),
                'text': chunk_text,
                'character_count': len(chunk_text),
                'page_numbers': [1],
                'section_types': ['paragraph'],
                'hierarchy_levels': [5],
                'table_count': 0,
                'list_count': 0,
                'semantic_context': '',
                'overlap_with_previous': False,
                'overlap_with_next': False
            }
            
            chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} basic chunks as fallback")
        return chunks
