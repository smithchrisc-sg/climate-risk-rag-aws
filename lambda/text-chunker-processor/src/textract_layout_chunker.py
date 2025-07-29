"""
Textract Layout-Based Hierarchical Chunker
Creates document tree structure from Textract LAYOUT analysis
Maintains parent-child relationships and respects document hierarchy
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re

logger = logging.getLogger(__name__)

class LayoutType(Enum):
    """Textract LAYOUT block types"""
    TITLE = "LAYOUT_TITLE"
    SECTION_HEADER = "LAYOUT_SECTION_HEADER"
    TEXT = "LAYOUT_TEXT"
    LIST = "LAYOUT_LIST"
    TABLE = "LAYOUT_TABLE"
    FIGURE = "LAYOUT_FIGURE"
    HEADER = "LAYOUT_HEADER"
    FOOTER = "LAYOUT_FOOTER"
    PAGE_NUMBER = "LAYOUT_PAGE_NUMBER"

@dataclass
class DocumentNode:
    """Represents a node in the document tree"""
    id: str
    block_type: str
    text: str
    page_number: int
    confidence: float
    geometry: Dict
    reading_order: int
    parent_id: Optional[str] = None
    children_ids: List[str] = None
    hierarchy_level: int = 0
    
    def __post_init__(self):
        if self.children_ids is None:
            self.children_ids = []

@dataclass
class ChunkMetadata:
    """Metadata for a chunk"""
    chunk_id: str
    doc_id: str
    chunk_index: int
    text: str
    page_numbers: List[int]
    character_count: int
    section_type: str
    hierarchy_level: int
    parent_chunk_id: Optional[str]
    child_chunk_ids: List[str]
    sibling_chunk_ids: List[str]
    table_count: int = 0
    list_count: int = 0
    figure_count: int = 0
    is_split_paragraph: bool = False
    split_part: int = 0
    total_splits: int = 1

class TextractLayoutChunker:
    """
    Hierarchical document chunker based on Textract LAYOUT analysis
    Creates tree structure respecting document hierarchy
    """
    
    def __init__(self,
                 max_paragraph_size: int = 1500,
                 sentence_overlap: int = 2,
                 min_chunk_size: int = 50):
        """
        Initialize the layout-based chunker
        
        Args:
            max_paragraph_size: Maximum size for a single paragraph chunk
            sentence_overlap: Number of sentences to overlap when splitting paragraphs
            min_chunk_size: Minimum chunk size (for very short content)
        """
        self.max_paragraph_size = max_paragraph_size
        self.sentence_overlap = sentence_overlap
        self.min_chunk_size = min_chunk_size
        
        logger.info("Initialized TextractLayoutChunker")
        logger.info(f"  Max paragraph size: {max_paragraph_size}")
        logger.info(f"  Sentence overlap: {sentence_overlap}")
        logger.info(f"  Min chunk size: {min_chunk_size}")
    
    def chunk_document(self, doc_id: str, textract_response: Dict, text_analysis: Dict) -> List[Dict]:
        """
        Main chunking method - creates hierarchical chunks from Textract LAYOUT
        
        Args:
            doc_id: Document identifier
            textract_response: Raw Textract response with LAYOUT blocks
            text_analysis: Processed text analysis data
            
        Returns:
            List of chunk dictionaries with hierarchical relationships
        """
        logger.info(f"Starting hierarchical chunking for document {doc_id}")
        
        try:
            # Step 1: Build document tree from LAYOUT blocks
            document_tree = self._build_document_tree(textract_response)
            logger.info(f"Built document tree with {len(document_tree)} nodes")
            
            # Step 2: Determine hierarchy levels
            self._assign_hierarchy_levels(document_tree)
            
            # Step 3: Create chunks from tree structure
            chunks = self._create_chunks_from_tree(doc_id, document_tree)
            logger.info(f"Created {len(chunks)} hierarchical chunks")
            
            # Step 4: Establish parent-child relationships
            self._establish_relationships(chunks)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error in hierarchical chunking: {str(e)}")
            # Fallback to basic chunking if layout parsing fails
            return self._fallback_chunking(doc_id, textract_response)
    
    def _build_document_tree(self, textract_response: Dict) -> Dict[str, DocumentNode]:
        """Build tree structure from Textract LAYOUT blocks"""
        
        blocks = textract_response.get('blocks', [])
        document_tree = {}
        layout_blocks = []
        
        # Extract LAYOUT blocks and create nodes
        for block in blocks:
            block_type = block.get('BlockType', '')
            
            if block_type.startswith('LAYOUT_'):
                # Get text content from child LINE blocks
                text_content = self._extract_layout_text(block, blocks)
                
                # Get reading order (use geometry if not available)
                reading_order = block.get('ReadingOrder', 0)
                if reading_order == 0:
                    reading_order = self._calculate_reading_order(block.get('Geometry', {}))
                
                node = DocumentNode(
                    id=block['Id'],
                    block_type=block_type,
                    text=text_content,
                    page_number=block.get('Page', 1),
                    confidence=block.get('Confidence', 0.0),
                    geometry=block.get('Geometry', {}),
                    reading_order=reading_order
                )
                
                document_tree[node.id] = node
                layout_blocks.append(node)
        
        # Sort by reading order for proper document flow
        layout_blocks.sort(key=lambda x: (x.page_number, x.reading_order))
        
        logger.info(f"Extracted {len(layout_blocks)} LAYOUT blocks")
        return document_tree
    
    def _extract_layout_text(self, layout_block: Dict, all_blocks: List[Dict]) -> str:
        """Extract text content from LAYOUT block's child LINE blocks"""
        
        relationships = layout_block.get('Relationships', [])
        child_ids = []
        
        for rel in relationships:
            if rel.get('Type') == 'CHILD':
                child_ids.extend(rel.get('Ids', []))
        
        # Find child LINE blocks and extract text
        text_parts = []
        for block in all_blocks:
            if block['Id'] in child_ids and block.get('BlockType') == 'LINE':
                text_parts.append(block.get('Text', ''))
        
        return '\n'.join(text_parts).strip()
    
    def _calculate_reading_order(self, geometry: Dict) -> float:
        """Calculate reading order from geometry (top-to-bottom, left-to-right)"""
        bbox = geometry.get('BoundingBox', {})
        top = bbox.get('Top', 0)
        left = bbox.get('Left', 0)
        
        # Primary sort by top position, secondary by left position
        return top * 1000 + left
    
    def _assign_hierarchy_levels(self, document_tree: Dict[str, DocumentNode]):
        """Assign hierarchy levels based on layout types and document structure"""
        
        # Define hierarchy mapping
        hierarchy_map = {
            LayoutType.TITLE.value: 1,
            LayoutType.SECTION_HEADER.value: 2,
            LayoutType.TEXT.value: 3,
            LayoutType.LIST.value: 3,
            LayoutType.TABLE.value: 3,
            LayoutType.FIGURE.value: 3,
            LayoutType.HEADER.value: 0,  # Page headers
            LayoutType.FOOTER.value: 0,  # Page footers
            LayoutType.PAGE_NUMBER.value: 0  # Page numbers
        }
        
        # Assign base hierarchy levels
        for node in document_tree.values():
            base_level = hierarchy_map.get(node.block_type, 3)
            node.hierarchy_level = base_level
        
        # Refine hierarchy based on document structure
        self._refine_hierarchy_levels(document_tree)
    
    def _refine_hierarchy_levels(self, document_tree: Dict[str, DocumentNode]):
        """Refine hierarchy levels based on document flow and content analysis"""
        
        nodes_by_page = {}
        for node in document_tree.values():
            page = node.page_number
            if page not in nodes_by_page:
                nodes_by_page[page] = []
            nodes_by_page[page].append(node)
        
        # Process each page
        for page_nodes in nodes_by_page.values():
            # Sort by reading order
            page_nodes.sort(key=lambda x: x.reading_order)
            
            # Analyze section headers for sub-levels
            current_section_level = 1
            
            for node in page_nodes:
                if node.block_type == LayoutType.SECTION_HEADER.value:
                    # Analyze header text for numbering patterns
                    header_level = self._analyze_header_level(node.text)
                    if header_level > 0:
                        node.hierarchy_level = header_level
                        current_section_level = header_level
                    else:
                        # Increment from previous section
                        current_section_level += 1
                        node.hierarchy_level = min(current_section_level, 5)
                
                elif node.block_type in [LayoutType.TEXT.value, LayoutType.LIST.value]:
                    # Content follows current section level
                    node.hierarchy_level = current_section_level + 1
    
    def _analyze_header_level(self, header_text: str) -> int:
        """Analyze header text to determine hierarchy level from numbering"""
        
        # Pattern for numbered headers (1., 1.1., 1.1.1., etc.)
        number_pattern = r'^(\d+(?:\.\d+)*)\.'
        match = re.match(number_pattern, header_text.strip())
        
        if match:
            number_parts = match.group(1).split('.')
            return len(number_parts) + 1  # +1 because titles are level 1
        
        # Pattern for Roman numerals
        roman_pattern = r'^[IVX]+\.'
        if re.match(roman_pattern, header_text.strip()):
            return 2
        
        # Pattern for letters
        letter_pattern = r'^[A-Z]\.'
        if re.match(letter_pattern, header_text.strip()):
            return 3
        
        return 0  # No clear numbering pattern
    
    def _create_chunks_from_tree(self, doc_id: str, document_tree: Dict[str, DocumentNode]) -> List[ChunkMetadata]:
        """Create chunks from document tree, respecting hierarchy"""
        
        chunks = []
        chunk_index = 0
        
        # Sort nodes by page and reading order
        sorted_nodes = sorted(document_tree.values(), 
                            key=lambda x: (x.page_number, x.reading_order))
        
        for node in sorted_nodes:
            # Skip page headers, footers, and page numbers for main content
            if node.hierarchy_level == 0:
                continue
            
            # Determine section type
            section_type = self._get_section_type(node.block_type)
            
            # Check if paragraph needs splitting
            if (node.block_type == LayoutType.TEXT.value and 
                len(node.text) > self.max_paragraph_size):
                
                # Split long paragraph
                paragraph_chunks = self._split_paragraph(
                    doc_id, node, chunk_index, section_type
                )
                chunks.extend(paragraph_chunks)
                chunk_index += len(paragraph_chunks)
                
            else:
                # Create single chunk
                chunk = ChunkMetadata(
                    chunk_id=f"{doc_id}_chunk_{chunk_index:04d}",
                    doc_id=doc_id,
                    chunk_index=chunk_index,
                    text=node.text,
                    page_numbers=[node.page_number],
                    character_count=len(node.text),
                    section_type=section_type,
                    hierarchy_level=node.hierarchy_level,
                    parent_chunk_id=None,  # Will be set in relationship phase
                    child_chunk_ids=[],
                    sibling_chunk_ids=[],
                    table_count=1 if node.block_type == LayoutType.TABLE.value else 0,
                    list_count=1 if node.block_type == LayoutType.LIST.value else 0,
                    figure_count=1 if node.block_type == LayoutType.FIGURE.value else 0
                )
                
                chunks.append(chunk)
                chunk_index += 1
        
        return chunks
    
    def _get_section_type(self, block_type: str) -> str:
        """Map LAYOUT block type to section type"""
        
        type_mapping = {
            LayoutType.TITLE.value: "title",
            LayoutType.SECTION_HEADER.value: "header",
            LayoutType.TEXT.value: "paragraph",
            LayoutType.LIST.value: "list",
            LayoutType.TABLE.value: "table",
            LayoutType.FIGURE.value: "figure"
        }
        
        return type_mapping.get(block_type, "paragraph")
    
    def _split_paragraph(self, doc_id: str, node: DocumentNode, 
                        start_index: int, section_type: str) -> List[ChunkMetadata]:
        """Split long paragraph into multiple chunks with sentence overlap"""
        
        text = node.text
        sentences = self._split_into_sentences(text)
        
        if len(sentences) <= 1:
            # Can't split meaningfully, return as single chunk
            return [ChunkMetadata(
                chunk_id=f"{doc_id}_chunk_{start_index:04d}",
                doc_id=doc_id,
                chunk_index=start_index,
                text=text,
                page_numbers=[node.page_number],
                character_count=len(text),
                section_type=section_type,
                hierarchy_level=node.hierarchy_level,
                parent_chunk_id=None,
                child_chunk_ids=[],
                sibling_chunk_ids=[]
            )]
        
        chunks = []
        current_chunk_sentences = []
        current_size = 0
        chunk_part = 1
        
        for i, sentence in enumerate(sentences):
            sentence_size = len(sentence)
            
            # Check if adding this sentence would exceed limit
            if (current_size + sentence_size > self.max_paragraph_size and 
                current_chunk_sentences):
                
                # Create chunk from current sentences
                chunk_text = ' '.join(current_chunk_sentences)
                chunk = ChunkMetadata(
                    chunk_id=f"{doc_id}_chunk_{start_index + len(chunks):04d}",
                    doc_id=doc_id,
                    chunk_index=start_index + len(chunks),
                    text=chunk_text,
                    page_numbers=[node.page_number],
                    character_count=len(chunk_text),
                    section_type=section_type,
                    hierarchy_level=node.hierarchy_level,
                    parent_chunk_id=None,
                    child_chunk_ids=[],
                    sibling_chunk_ids=[],
                    is_split_paragraph=True,
                    split_part=chunk_part,
                    total_splits=0  # Will be updated after all chunks created
                )
                chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_start = max(0, len(current_chunk_sentences) - self.sentence_overlap)
                current_chunk_sentences = current_chunk_sentences[overlap_start:]
                current_size = sum(len(s) for s in current_chunk_sentences)
                chunk_part += 1
            
            current_chunk_sentences.append(sentence)
            current_size += sentence_size
        
        # Add final chunk if there are remaining sentences
        if current_chunk_sentences:
            chunk_text = ' '.join(current_chunk_sentences)
            chunk = ChunkMetadata(
                chunk_id=f"{doc_id}_chunk_{start_index + len(chunks):04d}",
                doc_id=doc_id,
                chunk_index=start_index + len(chunks),
                text=chunk_text,
                page_numbers=[node.page_number],
                character_count=len(chunk_text),
                section_type=section_type,
                hierarchy_level=node.hierarchy_level,
                parent_chunk_id=None,
                child_chunk_ids=[],
                sibling_chunk_ids=[],
                is_split_paragraph=True,
                split_part=chunk_part,
                total_splits=chunk_part
            )
            chunks.append(chunk)
        
        # Update total_splits for all chunks
        total_splits = len(chunks)
        for chunk in chunks:
            chunk.total_splits = total_splits
        
        logger.info(f"Split paragraph into {len(chunks)} chunks with {self.sentence_overlap} sentence overlap")
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using simple heuristics"""
        
        # Simple sentence splitting - can be enhanced with more sophisticated NLP
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Clean up sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:  # Filter very short fragments
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences
    
    def _establish_relationships(self, chunks: List[ChunkMetadata]):
        """Establish parent-child and sibling relationships between chunks"""
        
        # Group chunks by hierarchy level
        levels = {}
        for chunk in chunks:
            level = chunk.hierarchy_level
            if level not in levels:
                levels[level] = []
            levels[level].append(chunk)
        
        # Sort levels
        sorted_levels = sorted(levels.keys())
        
        # Establish parent-child relationships
        for i, level in enumerate(sorted_levels[:-1]):  # Skip last level (no children)
            parent_level = level
            child_level = sorted_levels[i + 1]
            
            parent_chunks = levels[parent_level]
            child_chunks = levels[child_level]
            
            # Assign children to parents based on document order
            current_parent_idx = 0
            
            for child in child_chunks:
                # Find appropriate parent (last parent before this child)
                while (current_parent_idx < len(parent_chunks) - 1 and
                       parent_chunks[current_parent_idx + 1].chunk_index < child.chunk_index):
                    current_parent_idx += 1
                
                if current_parent_idx < len(parent_chunks):
                    parent = parent_chunks[current_parent_idx]
                    child.parent_chunk_id = parent.chunk_id
                    parent.child_chunk_ids.append(child.chunk_id)
        
        # Establish sibling relationships
        for level_chunks in levels.values():
            for i, chunk in enumerate(level_chunks):
                siblings = []
                if i > 0:
                    siblings.append(level_chunks[i-1].chunk_id)
                if i < len(level_chunks) - 1:
                    siblings.append(level_chunks[i+1].chunk_id)
                chunk.sibling_chunk_ids = siblings
        
        logger.info("Established hierarchical relationships between chunks")
    
    def _fallback_chunking(self, doc_id: str, textract_response: Dict) -> List[Dict]:
        """Fallback to basic chunking if LAYOUT parsing fails"""
        
        logger.warning("Falling back to basic chunking due to LAYOUT parsing error")
        
        # Extract all LINE blocks as fallback
        blocks = textract_response.get('blocks', [])
        text_lines = []
        
        for block in blocks:
            if block.get('BlockType') == 'LINE':
                text_lines.append(block.get('Text', ''))
        
        full_text = '\n'.join(text_lines)
        
        # Create single chunk as fallback
        chunk = {
            'chunk_id': f"{doc_id}_chunk_0000",
            'doc_id': doc_id,
            'chunk_index': 0,
            'text': full_text,
            'page_numbers': [1],
            'character_count': len(full_text),
            'section_type': 'paragraph',
            'hierarchy_level': 3,
            'parent_chunk_id': None,
            'child_chunk_ids': [],
            'sibling_chunk_ids': [],
            'table_count': 0,
            'list_count': 0,
            'figure_count': 0,
            'is_split_paragraph': False,
            'split_part': 1,
            'total_splits': 1
        }
        
        return [chunk]
    
    def chunks_to_dict(self, chunks: List[ChunkMetadata]) -> List[Dict]:
        """Convert ChunkMetadata objects to dictionaries for JSON serialization"""
        
        result = []
        for chunk in chunks:
            chunk_dict = {
                'chunk_id': chunk.chunk_id,
                'doc_id': chunk.doc_id,
                'chunk_index': chunk.chunk_index,
                'text': chunk.text,
                'page_numbers': chunk.page_numbers,
                'character_count': chunk.character_count,
                'section_type': chunk.section_type,
                'hierarchy_level': chunk.hierarchy_level,
                'parent_chunk_id': chunk.parent_chunk_id,
                'child_chunk_ids': chunk.child_chunk_ids,
                'sibling_chunk_ids': chunk.sibling_chunk_ids,
                'table_count': chunk.table_count,
                'list_count': chunk.list_count,
                'figure_count': chunk.figure_count,
                'is_split_paragraph': chunk.is_split_paragraph,
                'split_part': chunk.split_part,
                'total_splits': chunk.total_splits
            }
            result.append(chunk_dict)
        
        return result
