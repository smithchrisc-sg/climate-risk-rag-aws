"""
Revised Smart Structured Chunker
Implements intelligent chunking with minimal overlap based on document structure
Preserves semantic coherence while creating reasonably sized chunks
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    UNKNOWN = "unknown"

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
    children: List['DocumentSection'] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

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
    metadata: Dict = field(default_factory=dict)
    start_char: int = 0
    end_char: int = 0

class RevisedSmartChunker:
    """Implements structure-aware document chunking with semantic overlap"""
    
    def __init__(self, 
                 sentences_per_chunk: int = 5,     # Target sentences per chunk
                 overlap_sentences: int = 2,       # Sentence overlap between chunks
                 min_chunk_size: int = 200,        # Minimum characters per chunk
                 max_chunk_size: int = 1500,       # Maximum characters per chunk
                 respect_boundaries: bool = True,  # Respect section boundaries
                 preserve_tables: bool = True,     # Keep tables intact
                 preserve_lists: bool = True,      # Keep lists intact
                 header_context: bool = True):     # Include context with headers
        
        self.sentences_per_chunk = sentences_per_chunk
        self.overlap_sentences = overlap_sentences
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.respect_boundaries = respect_boundaries
        self.preserve_tables = preserve_tables
        self.preserve_lists = preserve_lists
        self.header_context = header_context
        
        # Patterns for identifying document structure
        self.header_patterns = [
            r'^[A-Z][A-Z\s]{5,}$',       # ALL CAPS headers
            r'^\d+\.?\s+[A-Z]',           # Numbered sections
            r'^[IVX]+\.?\s+[A-Z]',        # Roman numerals
            r'^[A-Z]\.?\s+[A-Z]',         # Letter sections
            r'^[A-Za-z\s]+:',             # Headers with colons
        ]
        
        self.list_patterns = [
            r'^\s*[-•]\s+',               # Bullet points
            r'^\s*\d+\.\s+',              # Numbered lists
            r'^\s*[a-z]\)\s+',            # Letter lists
            r'^\s*\(\d+\)\s+',            # Parenthesized numbers
        ]
        
        # Common abbreviations that shouldn't trigger sentence breaks
        self.abbreviations = [
            'Mr', 'Mrs', 'Ms', 'Dr', 'Prof', 'Sr', 'Jr', 'vs', 'etc', 'Inc', 
            'Corp', 'Ltd', 'Co', 'St', 'Ave', 'Blvd', 'Rd', 'Fig', 'Table', 
            'Ch', 'Sec', 'Vol', 'No', 'pp', 'cf', 'i.e', 'e.g', 'et al'
        ]
        
        logger.info("Initialized RevisedSmartChunker with sentences_per_chunk=%d, overlap_sentences=%d", 
                   sentences_per_chunk, overlap_sentences)
    def chunk_document(self, textract_response: Dict) -> List[StructuredChunk]:
        """Main entry point for smart structured chunking with Textract data"""
        try:
            logger.info("Starting smart structured document chunking")
            
            # Extract document structure from Textract response
            document_sections = self._extract_document_structure(textract_response)
            
            # Create structured chunks with smart overlap
            chunks = self._create_structured_chunks(document_sections)
            
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
            document_sections = self._extract_structure_from_text(text)
            
            # Create structured chunks with smart overlap
            chunks = self._create_structured_chunks(document_sections)
            
            # Post-process chunks (merge small, optimize boundaries)
            optimized_chunks = self._optimize_chunks(chunks)
            
            logger.info(f"Created {len(optimized_chunks)} smart text-only chunks")
            return optimized_chunks
            
        except Exception as e:
            logger.error(f"Smart text-only chunking failed: {e}")
            # Fallback to simple chunking
            return self._fallback_text_chunking(text)
    
    def _extract_document_structure(self, textract_response: Dict) -> List[DocumentSection]:
        """Extract hierarchical document structure from Textract blocks"""
        blocks = textract_response.get('Blocks', [])
        
        # Step 1: Group blocks by page
        pages = self._group_blocks_by_page(blocks)
        
        # Step 2: Extract raw text lines with positioning
        all_lines = []
        for page_num, page_blocks in pages.items():
            lines = self._extract_lines_with_position(page_blocks)
            for line in lines:
                line['page_number'] = page_num
            all_lines.extend(lines)
        
        # Step 3: Group lines into paragraphs and identify sections
        document_sections = self._group_lines_into_sections(all_lines)
        
        # Step 4: Build document hierarchy
        hierarchical_sections = self._build_document_hierarchy(document_sections)
        
        return hierarchical_sections
    
    def _extract_structure_from_text(self, text: str) -> List[DocumentSection]:
        """Extract document structure from plain text"""
        # Split text into lines
        lines = text.split('\n')
        
        # Process lines to identify potential sections
        sections = []
        current_section = None
        current_text = []
        current_type = SectionType.PARAGRAPH
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                # Empty line might indicate section boundary
                if current_text:
                    # Save current section
                    section_text = ' '.join(current_text)
                    sections.append(DocumentSection(
                        text=section_text,
                        section_type=current_type,
                        hierarchy_level=self._get_hierarchy_level(current_type),
                        page_number=1,  # Assume single page for plain text
                        start_char=0,
                        end_char=len(section_text)
                    ))
                    current_text = []
                continue
            
            # Check if this line is a header
            is_header = False
            for pattern in self.header_patterns:
                if re.match(pattern, line):
                    # This is likely a header
                    if current_text:
                        # Save previous section
                        section_text = ' '.join(current_text)
                        sections.append(DocumentSection(
                            text=section_text,
                            section_type=current_type,
                            hierarchy_level=self._get_hierarchy_level(current_type),
                            page_number=1,
                            start_char=0,
                            end_char=len(section_text)
                        ))
                        current_text = []
                    
                    # Create header section
                    sections.append(DocumentSection(
                        text=line,
                        section_type=SectionType.HEADER,
                        hierarchy_level=1,
                        page_number=1,
                        start_char=0,
                        end_char=len(line)
                    ))
                    is_header = True
                    break
            
            if not is_header:
                # Check if this line is a list item
                is_list = False
                for pattern in self.list_patterns:
                    if re.match(pattern, line):
                        # This is likely a list item
                        if current_text and current_type != SectionType.LIST:
                            # Save previous section if it wasn't a list
                            section_text = ' '.join(current_text)
                            sections.append(DocumentSection(
                                text=section_text,
                                section_type=current_type,
                                hierarchy_level=self._get_hierarchy_level(current_type),
                                page_number=1,
                                start_char=0,
                                end_char=len(section_text)
                            ))
                            current_text = []
                        
                        current_text.append(line)
                        current_type = SectionType.LIST
                        is_list = True
                        break
                
                if not is_list:
                    # Regular paragraph text
                    if current_type != SectionType.PARAGRAPH and current_text:
                        # Save previous non-paragraph section
                        section_text = ' '.join(current_text)
                        sections.append(DocumentSection(
                            text=section_text,
                            section_type=current_type,
                            hierarchy_level=self._get_hierarchy_level(current_type),
                            page_number=1,
                            start_char=0,
                            end_char=len(section_text)
                        ))
                        current_text = []
                        current_type = SectionType.PARAGRAPH
                    
                    current_text.append(line)
                    current_type = SectionType.PARAGRAPH
        
        # Add the last section if there's any text left
        if current_text:
            section_text = ' '.join(current_text)
            sections.append(DocumentSection(
                text=section_text,
                section_type=current_type,
                hierarchy_level=self._get_hierarchy_level(current_type),
                page_number=1,
                start_char=0,
                end_char=len(section_text)
            ))
        
        return sections
    
    def _get_hierarchy_level(self, section_type: SectionType) -> int:
        """Get hierarchy level based on section type"""
        hierarchy_map = {
            SectionType.TITLE: 0,
            SectionType.HEADER: 1,
            SectionType.SUBHEADER: 2,
            SectionType.PARAGRAPH: 3,
            SectionType.LIST: 3,
            SectionType.TABLE: 3,
            SectionType.CAPTION: 4,
            SectionType.FOOTER: 5,
            SectionType.UNKNOWN: 6
        }
        return hierarchy_map.get(section_type, 3)
    
    def _group_blocks_by_page(self, blocks: List[Dict]) -> Dict[int, List[Dict]]:
        """Group Textract blocks by page number"""
        pages = {}
        
        for block in blocks:
            if block['BlockType'] == 'PAGE':
                page_num = block.get('Page', len(pages) + 1)
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
                lines.append(line_info)
        
        # Sort lines by vertical position (top to bottom)
        lines.sort(key=lambda x: x['bounding_box'].get('Top', 0))
        
        return lines
    def _group_lines_into_sections(self, lines: List[Dict]) -> List[DocumentSection]:
        """Group lines into paragraphs and identify sections"""
        sections = []
        current_lines = []
        current_type = SectionType.PARAGRAPH
        
        for i, line in enumerate(lines):
            text = line['text'].strip()
            if not text:
                continue
            
            # Check if this is a header
            is_header = False
            for pattern in self.header_patterns:
                if re.match(pattern, text):
                    # This is likely a header
                    if current_lines:
                        # Save current section
                        section = self._create_section_from_lines(current_lines, current_type)
                        sections.append(section)
                        current_lines = []
                    
                    # Create header section
                    header_level = 1
                    if len(text) < 30:  # Short headers are likely higher level
                        header_type = SectionType.HEADER
                    else:
                        header_type = SectionType.SUBHEADER
                        header_level = 2
                    
                    sections.append(DocumentSection(
                        text=text,
                        section_type=header_type,
                        hierarchy_level=header_level,
                        page_number=line['page_number'],
                        bounding_box=line['bounding_box'],
                        confidence=line['confidence']
                    ))
                    is_header = True
                    break
            
            if is_header:
                current_type = SectionType.PARAGRAPH  # Reset for next section
                continue
            
            # Check if this is a list item
            is_list = False
            for pattern in self.list_patterns:
                if re.match(pattern, text):
                    # This is likely a list item
                    if current_lines and current_type != SectionType.LIST:
                        # Save current section if it wasn't a list
                        section = self._create_section_from_lines(current_lines, current_type)
                        sections.append(section)
                        current_lines = []
                    
                    current_lines.append(line)
                    current_type = SectionType.LIST
                    is_list = True
                    break
            
            if is_list:
                continue
            
            # Check if this is a table (heuristic: contains multiple spaces or tabs)
            if '\t' in text or '  ' in text:
                # This might be a table row
                if current_lines and current_type != SectionType.TABLE:
                    # Save current section if it wasn't a table
                    section = self._create_section_from_lines(current_lines, current_type)
                    sections.append(section)
                    current_lines = []
                
                current_lines.append(line)
                current_type = SectionType.TABLE
                continue
            
            # Regular paragraph text
            if current_type != SectionType.PARAGRAPH and current_lines:
                # Save previous non-paragraph section
                section = self._create_section_from_lines(current_lines, current_type)
                sections.append(section)
                current_lines = []
                current_type = SectionType.PARAGRAPH
            
            current_lines.append(line)
            current_type = SectionType.PARAGRAPH
        
        # Add the last section if there are any lines left
        if current_lines:
            section = self._create_section_from_lines(current_lines, current_type)
            sections.append(section)
        
        return sections
    
    def _create_section_from_lines(self, lines: List[Dict], section_type: SectionType) -> DocumentSection:
        """Create a document section from a list of lines"""
        # Combine text from all lines
        text = ' '.join(line['text'] for line in lines)
        
        # Get bounding box that encompasses all lines
        if lines:
            top = min(line['bounding_box'].get('Top', 1) for line in lines)
            left = min(line['bounding_box'].get('Left', 1) for line in lines)
            bottom = max(line['bounding_box'].get('Top', 0) + line['bounding_box'].get('Height', 0) 
                        for line in lines)
            right = max(line['bounding_box'].get('Left', 0) + line['bounding_box'].get('Width', 0) 
                       for line in lines)
            
            bounding_box = {
                'Top': top,
                'Left': left,
                'Height': bottom - top,
                'Width': right - left
            }
            
            # Average confidence
            confidence = sum(line.get('confidence', 0) for line in lines) / len(lines)
            
            # Use page number from first line
            page_number = lines[0].get('page_number', 1)
        else:
            bounding_box = {}
            confidence = 0
            page_number = 1
        
        return DocumentSection(
            text=text,
            section_type=section_type,
            hierarchy_level=self._get_hierarchy_level(section_type),
            page_number=page_number,
            bounding_box=bounding_box,
            confidence=confidence
        )
    
    def _build_document_hierarchy(self, sections: List[DocumentSection]) -> List[DocumentSection]:
        """Build document hierarchy by grouping sections under headers"""
        # This is a simplified hierarchy builder
        # In a real implementation, you would use more sophisticated logic
        # to determine parent-child relationships between sections
        
        # For now, we'll just return the flat list of sections
        # A more complex implementation would build a tree structure
        return sections
    def _create_structured_chunks(self, sections: List[DocumentSection]) -> List[StructuredChunk]:
        """Create chunks from document sections with sentence-based overlap"""
        chunks = []
        
        for section in sections:
            # Handle different section types
            if section.section_type == SectionType.TABLE and self.preserve_tables:
                # Keep tables as complete units
                chunk = self._create_table_chunk(section)
                chunks.append(chunk)
                
            elif section.section_type == SectionType.LIST and self.preserve_lists:
                # Keep lists as complete units if they're not too large
                if len(section.text) <= self.max_chunk_size:
                    chunk = self._create_list_chunk(section)
                    chunks.append(chunk)
                else:
                    # Split large lists
                    list_chunks = self._split_section_by_sentences(section)
                    chunks.extend(list_chunks)
                
            elif section.section_type in [SectionType.TITLE, SectionType.HEADER, SectionType.SUBHEADER]:
                # Headers are kept as separate chunks
                chunk = self._create_header_chunk(section)
                chunks.append(chunk)
                
            else:
                # For paragraphs and other content, split by sentences with overlap
                section_chunks = self._split_section_by_sentences(section)
                chunks.extend(section_chunks)
        
        return chunks
    
    def _split_section_by_sentences(self, section: DocumentSection) -> List[StructuredChunk]:
        """Split a section into chunks based on sentences with overlap"""
        # If section is small enough, keep it as a single chunk
        if len(section.text) <= self.max_chunk_size:
            return [self._create_basic_chunk(section)]
        
        # Split text into sentences
        sentences = self._split_into_sentences(section.text)
        
        # If very few sentences, keep as single chunk
        if len(sentences) <= self.sentences_per_chunk:
            return [self._create_basic_chunk(section)]
        
        chunks = []
        
        # Create chunks with sentence-based overlap
        for i in range(0, len(sentences), self.sentences_per_chunk - self.overlap_sentences):
            # Get sentences for this chunk
            chunk_sentences = sentences[i:i + self.sentences_per_chunk]
            
            if not chunk_sentences:
                continue
                
            # Create chunk text
            chunk_text = ' '.join(chunk_sentences)
            
            # Create chunk
            chunk = StructuredChunk(
                text=chunk_text,
                chunk_type=f"{section.section_type.value}_segment",
                hierarchy_level=section.hierarchy_level,
                page_number=section.page_number,
                section_context=f"{section.section_type.value}_content",
                word_count=len(chunk_text.split()),
                sentence_count=len(chunk_sentences),
                bounding_box=section.bounding_box,
                metadata={
                    'section_type': section.section_type.value,
                    'confidence': section.confidence,
                    'is_complete_section': False,
                    'segment_index': len(chunks),
                    'overlap_sentences': self.overlap_sentences if i > 0 else 0,
                    'smart_chunking': True
                }
            )
            
            chunks.append(chunk)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using NLTK with custom handling for edge cases"""
        # First try NLTK's sentence tokenizer
        try:
            sentences = sent_tokenize(text)
            
            # If we got only one sentence but the text is long, try regex-based approach
            if len(sentences) == 1 and len(text) > self.max_chunk_size:
                return self._split_into_sentences_regex(text)
                
            return sentences
            
        except Exception as e:
            logger.warning(f"NLTK sentence tokenization failed: {e}")
            # Fall back to regex-based approach
            return self._split_into_sentences_regex(text)
    
    def _split_into_sentences_regex(self, text: str) -> List[str]:
        """Split text into sentences using regex with handling for abbreviations"""
        # First split on obvious sentence boundaries
        potential_sentences = re.split(r'([.!?])\s+(?=[A-Z])', text)
        
        # Recombine the punctuation with the sentences
        sentences = []
        i = 0
        while i < len(potential_sentences):
            if i + 1 < len(potential_sentences) and potential_sentences[i+1] in '.!?':
                sentences.append(potential_sentences[i] + potential_sentences[i+1])
                i += 2
            else:
                sentences.append(potential_sentences[i])
                i += 1
        
        # Filter out empty sentences and handle abbreviations
        filtered_sentences = []
        current_sentence = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Check if sentence ends with an abbreviation
            ends_with_abbrev = False
            for abbr in self.abbreviations:
                if sentence.endswith(abbr) or sentence.endswith(abbr + '.'):
                    ends_with_abbrev = True
                    break
            
            if ends_with_abbrev and current_sentence:
                # This might be a false sentence break, combine with current
                current_sentence += " " + sentence
            else:
                if current_sentence:
                    filtered_sentences.append(current_sentence)
                current_sentence = sentence
        
        # Add the last sentence
        if current_sentence:
            filtered_sentences.append(current_sentence)
        
        # If we still have only one sentence and it's long, fall back to simpler splitting
        if len(filtered_sentences) == 1 and len(filtered_sentences[0]) > self.max_chunk_size:
            # Split by punctuation followed by space
            simple_sentences = re.split(r'[.!?]\s+', text)
            return [s.strip() for s in simple_sentences if s.strip()]
        
        return filtered_sentences
    
    def _create_basic_chunk(self, section: DocumentSection) -> StructuredChunk:
        """Create a basic chunk from a section"""
        return StructuredChunk(
            text=section.text,
            chunk_type=section.section_type.value,
            hierarchy_level=section.hierarchy_level,
            page_number=section.page_number,
            section_context=f"{section.section_type.value}_content",
            word_count=len(section.text.split()),
            sentence_count=len(self._split_into_sentences(section.text)),
            bounding_box=section.bounding_box,
            metadata={
                'section_type': section.section_type.value,
                'confidence': section.confidence,
                'is_complete_section': True,
                'smart_chunking': True
            }
        )
    
    def _create_header_chunk(self, section: DocumentSection) -> StructuredChunk:
        """Create a chunk for a header"""
        return StructuredChunk(
            text=section.text,
            chunk_type=f"{section.section_type.value}",
            hierarchy_level=section.hierarchy_level,
            page_number=section.page_number,
            section_context=f"{section.section_type.value}_level_{section.hierarchy_level}",
            word_count=len(section.text.split()),
            sentence_count=1,  # Headers are typically one sentence
            bounding_box=section.bounding_box,
            metadata={
                'section_type': section.section_type.value,
                'confidence': section.confidence,
                'is_header': True,
                'smart_chunking': True
            }
        )
    
    def _create_table_chunk(self, section: DocumentSection) -> StructuredChunk:
        """Create a chunk for a table"""
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
                'is_table': True,
                'smart_chunking': True
            }
        )
    
    def _create_list_chunk(self, section: DocumentSection) -> StructuredChunk:
        """Create a chunk for a list"""
        return StructuredChunk(
            text=section.text,
            chunk_type="list",
            hierarchy_level=section.hierarchy_level,
            page_number=section.page_number,
            section_context="list_items",
            word_count=len(section.text.split()),
            sentence_count=section.text.count('.') + section.text.count('!') + section.text.count('?'),
            bounding_box=section.bounding_box,
            metadata={
                'section_type': section.section_type.value,
                'confidence': section.confidence,
                'is_list': True,
                'smart_chunking': True
            }
        )
    def _create_structured_chunks(self, sections: List[DocumentSection]) -> List[StructuredChunk]:
        """Create chunks from document sections with sentence-based overlap"""
        chunks = []
        
        for section in sections:
            # Handle different section types
            if section.section_type == SectionType.TABLE and self.preserve_tables:
                # Keep tables as complete units
                chunk = self._create_table_chunk(section)
                chunks.append(chunk)
                
            elif section.section_type == SectionType.LIST and self.preserve_lists:
                # Keep lists as complete units if they're not too large
                if len(section.text) <= self.max_chunk_size:
                    chunk = self._create_list_chunk(section)
                    chunks.append(chunk)
                else:
                    # Split large lists
                    list_chunks = self._split_section_by_sentences(section)
                    chunks.extend(list_chunks)
                
            elif section.section_type in [SectionType.TITLE, SectionType.HEADER, SectionType.SUBHEADER]:
                # Headers are kept as separate chunks
                chunk = self._create_header_chunk(section)
                chunks.append(chunk)
                
            else:
                # For paragraphs and other content, split by sentences with overlap
                section_chunks = self._split_section_by_sentences(section)
                chunks.extend(section_chunks)
        
        return chunks
    
    def _split_section_by_sentences(self, section: DocumentSection) -> List[StructuredChunk]:
        """Split a section into chunks based on sentences with overlap"""
        # If section is small enough, keep it as a single chunk
        if len(section.text) <= self.max_chunk_size:
            return [self._create_basic_chunk(section)]
        
        # Split text into sentences
        sentences = self._split_into_sentences(section.text)
        
        # If very few sentences, keep as single chunk
        if len(sentences) <= self.sentences_per_chunk:
            return [self._create_basic_chunk(section)]
        
        chunks = []
        
        # Create chunks with sentence-based overlap
        for i in range(0, len(sentences), self.sentences_per_chunk - self.overlap_sentences):
            # Get sentences for this chunk
            chunk_sentences = sentences[i:i + self.sentences_per_chunk]
            
            if not chunk_sentences:
                continue
                
            # Create chunk text
            chunk_text = ' '.join(chunk_sentences)
            
            # Create chunk
            chunk = StructuredChunk(
                text=chunk_text,
                chunk_type=f"{section.section_type.value}_segment",
                hierarchy_level=section.hierarchy_level,
                page_number=section.page_number,
                section_context=f"{section.section_type.value}_content",
                word_count=len(chunk_text.split()),
                sentence_count=len(chunk_sentences),
                bounding_box=section.bounding_box,
                metadata={
                    'section_type': section.section_type.value,
                    'confidence': section.confidence,
                    'is_complete_section': False,
                    'segment_index': len(chunks),
                    'overlap_sentences': self.overlap_sentences if i > 0 else 0,
                    'smart_chunking': True
                }
            )
            
            chunks.append(chunk)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using NLTK with custom handling for edge cases"""
        # First try NLTK's sentence tokenizer
        try:
            sentences = sent_tokenize(text)
            
            # If we got only one sentence but the text is long, try regex-based approach
            if len(sentences) == 1 and len(text) > self.max_chunk_size:
                return self._split_into_sentences_regex(text)
                
            return sentences
            
        except Exception as e:
            logger.warning(f"NLTK sentence tokenization failed: {e}")
            # Fall back to regex-based approach
            return self._split_into_sentences_regex(text)
    
    def _split_into_sentences_regex(self, text: str) -> List[str]:
        """Split text into sentences using regex with handling for abbreviations"""
        # First split on obvious sentence boundaries
        potential_sentences = re.split(r'([.!?])\s+(?=[A-Z])', text)
        
        # Recombine the punctuation with the sentences
        sentences = []
        i = 0
        while i < len(potential_sentences):
            if i + 1 < len(potential_sentences) and potential_sentences[i+1] in '.!?':
                sentences.append(potential_sentences[i] + potential_sentences[i+1])
                i += 2
            else:
                sentences.append(potential_sentences[i])
                i += 1
        
        # Filter out empty sentences and handle abbreviations
        filtered_sentences = []
        current_sentence = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Check if sentence ends with an abbreviation
            ends_with_abbrev = False
            for abbr in self.abbreviations:
                if sentence.endswith(abbr) or sentence.endswith(abbr + '.'):
                    ends_with_abbrev = True
                    break
            
            if ends_with_abbrev and current_sentence:
                # This might be a false sentence break, combine with current
                current_sentence += " " + sentence
            else:
                if current_sentence:
                    filtered_sentences.append(current_sentence)
                current_sentence = sentence
        
        # Add the last sentence
        if current_sentence:
            filtered_sentences.append(current_sentence)
        
        # If we still have only one sentence and it's long, fall back to simpler splitting
        if len(filtered_sentences) == 1 and len(filtered_sentences[0]) > self.max_chunk_size:
            # Split by punctuation followed by space
            simple_sentences = re.split(r'[.!?]\s+', text)
            return [s.strip() for s in simple_sentences if s.strip()]
        
        return filtered_sentences
    
    def _create_basic_chunk(self, section: DocumentSection) -> StructuredChunk:
        """Create a basic chunk from a section"""
        return StructuredChunk(
            text=section.text,
            chunk_type=section.section_type.value,
            hierarchy_level=section.hierarchy_level,
            page_number=section.page_number,
            section_context=f"{section.section_type.value}_content",
            word_count=len(section.text.split()),
            sentence_count=len(self._split_into_sentences(section.text)),
            bounding_box=section.bounding_box,
            metadata={
                'section_type': section.section_type.value,
                'confidence': section.confidence,
                'is_complete_section': True,
                'smart_chunking': True
            }
        )
    
    def _create_header_chunk(self, section: DocumentSection) -> StructuredChunk:
        """Create a chunk for a header"""
        return StructuredChunk(
            text=section.text,
            chunk_type=f"{section.section_type.value}",
            hierarchy_level=section.hierarchy_level,
            page_number=section.page_number,
            section_context=f"{section.section_type.value}_level_{section.hierarchy_level}",
            word_count=len(section.text.split()),
            sentence_count=1,  # Headers are typically one sentence
            bounding_box=section.bounding_box,
            metadata={
                'section_type': section.section_type.value,
                'confidence': section.confidence,
                'is_header': True,
                'smart_chunking': True
            }
        )
    
    def _create_table_chunk(self, section: DocumentSection) -> StructuredChunk:
        """Create a chunk for a table"""
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
                'is_table': True,
                'smart_chunking': True
            }
        )
    
    def _create_list_chunk(self, section: DocumentSection) -> StructuredChunk:
        """Create a chunk for a list"""
        return StructuredChunk(
            text=section.text,
            chunk_type="list",
            hierarchy_level=section.hierarchy_level,
            page_number=section.page_number,
            section_context="list_items",
            word_count=len(section.text.split()),
            sentence_count=section.text.count('.') + section.text.count('!') + section.text.count('?'),
            bounding_box=section.bounding_box,
            metadata={
                'section_type': section.section_type.value,
                'confidence': section.confidence,
                'is_list': True,
                'smart_chunking': True
            }
        )
    def _optimize_chunks(self, chunks: List[StructuredChunk]) -> List[StructuredChunk]:
        """Post-process chunks to optimize size and boundaries"""
        if not chunks:
            return chunks
        
        optimized = []
        i = 0
        
        while i < len(chunks):
            chunk = chunks[i]
            
            # Check if this chunk is too small
            if len(chunk.text) < self.min_chunk_size and i + 1 < len(chunks):
                next_chunk = chunks[i + 1]
                
                # Only merge chunks from the same section type
                if (chunk.chunk_type == next_chunk.chunk_type and 
                    not chunk.chunk_type.startswith(('title', 'header', 'subheader'))):
                    
                    # Merge with next chunk
                    merged_text = chunk.text + " " + next_chunk.text
                    merged_chunk = StructuredChunk(
                        text=merged_text,
                        chunk_type=chunk.chunk_type,
                        hierarchy_level=chunk.hierarchy_level,
                        page_number=chunk.page_number,
                        section_context=chunk.section_context,
                        word_count=len(merged_text.split()),
                        sentence_count=chunk.sentence_count + next_chunk.sentence_count,
                        bounding_box=chunk.bounding_box,
                        metadata={
                            **chunk.metadata,
                            'merged': True,
                            'merged_chunks': 2
                        }
                    )
                    optimized.append(merged_chunk)
                    i += 2  # Skip next chunk
                    continue
            
            # Keep the chunk as is
            optimized.append(chunk)
            i += 1
        
        return optimized
    
    def _fallback_chunking(self, textract_response: Dict) -> List[StructuredChunk]:
        """Fallback chunking method for Textract data"""
        # Extract all text from Textract response
        text = ""
        for block in textract_response.get('Blocks', []):
            if block.get('BlockType') == 'LINE':
                text += block.get('Text', '') + " "
        
        # Use fallback text chunking
        return self._fallback_text_chunking(text)
    
    def _fallback_text_chunking(self, text: str) -> List[StructuredChunk]:
        """Simple fallback chunking for plain text"""
        # Use the approach from DocumentChunker.py
        sentences = self._split_into_sentences(text)
        chunks = []
        
        for i in range(0, len(sentences), self.sentences_per_chunk - self.overlap_sentences):
            chunk_sentences = sentences[i:i + self.sentences_per_chunk]
            if not chunk_sentences:
                continue
                
            chunk_text = ' '.join(chunk_sentences)
            
            chunk = StructuredChunk(
                text=chunk_text,
                chunk_type="fallback",
                hierarchy_level=3,
                page_number=1,
                section_context="fallback_content",
                word_count=len(chunk_text.split()),
                sentence_count=len(chunk_sentences),
                bounding_box={},
                metadata={
                    'fallback': True,
                    'chunk_index': len(chunks),
                    'overlap_sentences': self.overlap_sentences if i > 0 else 0,
                    'smart_chunking': False
                }
            )
            
            chunks.append(chunk)
        
        return chunks


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Sample text
    sample_text = """
    # Introduction
    
    This is a sample document to test the RevisedSmartChunker.
    It contains multiple paragraphs and sections to demonstrate the chunking capabilities.
    
    ## Background
    
    The smart chunker is designed to create semantically meaningful chunks from documents.
    It respects section boundaries and uses sentence-based overlap for better context.
    
    This paragraph is longer and will be split into multiple chunks with sentence overlap.
    The chunker should maintain semantic coherence while creating reasonably sized chunks.
    We want to ensure that the chunks are not too small or too large.
    The ideal chunk size is around 5 sentences, with an overlap of 1-2 sentences.
    This approach provides good context for language models while keeping chunks focused.
    
    ### Features
    
    - Respects section boundaries
    - Uses sentence-based overlap
    - Handles tables and lists appropriately
    - Optimizes chunk sizes
    - Falls back to simpler methods when needed
    
    ## Conclusion
    
    The RevisedSmartChunker provides a better approach to document chunking.
    It creates more semantically meaningful chunks that preserve document structure.
    """
    
    # Create chunker
    chunker = RevisedSmartChunker(
        sentences_per_chunk=5,
        overlap_sentences=2,
        min_chunk_size=200,
        max_chunk_size=1500
    )
    
    # Test with plain text
    chunks = chunker.chunk_text(sample_text)
    
    # Print results
    print(f"Created {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1}:")
        print(f"Type: {chunk.chunk_type}")
        print(f"Sentences: {chunk.sentence_count}")
        print(f"Words: {chunk.word_count}")
        print(f"Text: {chunk.text[:100]}...")
        print(f"Metadata: {chunk.metadata}")
