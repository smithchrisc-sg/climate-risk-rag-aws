#!/usr/bin/env python3
"""
Structure-Aware Keyword Indexer
Leverages Textract structure analysis for enhanced search boosting with fallback
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class StructureAwareProcessor:
    """
    Enhanced processor that uses Textract structure analysis for intelligent boosting
    """
    
    def __init__(self, opensearch_client, index_name: str):
        self.client = opensearch_client
        self.index_name = index_name

    def create_enhanced_index_mapping(self):
        """Create enhanced index mapping that leverages Textract structure"""
        
        mapping = {
            "settings": {
                "analysis": {
                    "analyzer": {
                        "title_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "asciifolding"]
                        },
                        "heading_analyzer": {
                            "type": "custom", 
                            "tokenizer": "standard",
                            "filter": ["lowercase", "asciifolding"]
                        },
                        "table_analyzer": {
                            "type": "custom",
                            "tokenizer": "keyword",
                            "filter": ["lowercase"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    # Core document fields
                    "doc_id": {"type": "keyword"},
                    "content": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    
                    # Structure-based fields with different boost levels
                    "title": {
                        "type": "text",
                        "analyzer": "title_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "suggest": {"type": "completion"}
                        }
                    },
                    
                    # Textract structure-derived fields
                    "headings": {
                        "type": "nested",
                        "properties": {
                            "text": {
                                "type": "text",
                                "analyzer": "heading_analyzer"
                            },
                            "level": {"type": "integer"},
                            "page": {"type": "integer"},
                            "confidence": {"type": "float"}
                        }
                    },
                    
                    "key_value_pairs": {
                        "type": "nested",
                        "properties": {
                            "key": {"type": "text"},
                            "value": {"type": "text"},
                            "confidence": {"type": "float"}
                        }
                    },
                    
                    "tables": {
                        "type": "nested",
                        "properties": {
                            "headers": {
                                "type": "text",
                                "analyzer": "table_analyzer"
                            },
                            "content": {"type": "text"},
                            "page": {"type": "integer"}
                        }
                    },
                    
                    "lists": {
                        "type": "nested",
                        "properties": {
                            "items": {"type": "text"},
                            "type": {"type": "keyword"}  # ORDERED, UNORDERED
                        }
                    },
                    
                    # Enhanced metadata with structure insights
                    "structure_metadata": {
                        "properties": {
                            "document_type": {"type": "keyword"},
                            "has_toc": {"type": "boolean"},
                            "section_count": {"type": "integer"},
                            "table_count": {"type": "integer"},
                            "figure_count": {"type": "integer"},
                            "heading_hierarchy_depth": {"type": "integer"},
                            "key_sections": {"type": "text"},
                            "structure_available": {"type": "boolean"}
                        }
                    },
                    
                    # Standard metadata
                    "author": {"type": "text"},
                    "language": {"type": "keyword"},
                    "processing": {
                        "properties": {
                            "overall_confidence": {"type": "float"},
                            "status": {"type": "keyword"},
                            "word_count": {"type": "integer"}
                        }
                    },
                    "indexed_at": {"type": "date"}
                }
            }
        }
        
        return mapping

    def prepare_structure_enhanced_document(self, doc_id: str, full_text: str, 
                                          textract_structure: Optional[Dict], 
                                          metadata: Dict, filename: str) -> Dict:
        """Prepare document with structure-enhanced fields or fallback to standard"""
        
        try:
            # Check if we have Textract structure data
            if textract_structure and self._has_valid_structure(textract_structure):
                logger.info(f"Using Textract structure analysis for {doc_id}")
                return self._prepare_with_structure(doc_id, full_text, textract_structure, metadata, filename)
            else:
                logger.info(f"Falling back to standard processing for {doc_id}")
                return self._prepare_standard_document(doc_id, full_text, metadata, filename)
                
        except Exception as e:
            logger.error(f"Error in structure processing for {doc_id}: {e}")
            logger.info(f"Falling back to standard processing for {doc_id}")
            return self._prepare_standard_document(doc_id, full_text, metadata, filename)

    def _has_valid_structure(self, textract_structure: Dict) -> bool:
        """Check if Textract structure data is valid and useful"""
        
        if not textract_structure or 'Blocks' not in textract_structure:
            return False
        
        blocks = textract_structure['Blocks']
        if not blocks or len(blocks) < 5:  # Too few blocks to be useful
            return False
        
        # Check for meaningful structure elements
        block_types = set(block.get('BlockType') for block in blocks)
        useful_types = {'LINE', 'WORD', 'KEY_VALUE_SET', 'TABLE', 'CELL'}
        
        return len(block_types.intersection(useful_types)) >= 2

    def _prepare_with_structure(self, doc_id: str, full_text: str, 
                               textract_structure: Dict, metadata: Dict, filename: str) -> Dict:
        """Prepare document with full Textract structure analysis"""
        
        # Extract structure elements
        structure_elements = self._extract_structure_elements(textract_structure)
        
        # Prepare enhanced document
        doc_data = {
            "doc_id": doc_id,
            "content": full_text,
            
            # Enhanced title extraction
            "title": self._extract_enhanced_title(structure_elements, metadata, filename),
            
            # Structure-based fields for boosting
            "headings": structure_elements.get('headings', []),
            "key_value_pairs": structure_elements.get('key_value_pairs', []),
            "tables": structure_elements.get('tables', []),
            "lists": structure_elements.get('lists', []),
            
            # Enhanced metadata with structure insights
            "structure_metadata": {
                "document_type": self._classify_document_type(structure_elements),
                "has_toc": structure_elements.get('has_toc', False),
                "section_count": len(structure_elements.get('headings', [])),
                "table_count": len(structure_elements.get('tables', [])),
                "figure_count": structure_elements.get('figure_count', 0),
                "heading_hierarchy_depth": self._calculate_heading_depth(structure_elements.get('headings', [])),
                "key_sections": self._extract_key_sections(structure_elements),
                "structure_available": True
            },
            
            # Standard metadata
            "author": self._extract_metadata_value(metadata, 'author'),
            "language": self._extract_metadata_value(metadata, 'language', 'en'),
            "processing": {
                "overall_confidence": metadata.get('processing', {}).get('overall_confidence', 0.8),
                "status": "indexed",
                "word_count": len(full_text.split()) if full_text else 0
            },
            "indexed_at": datetime.utcnow().isoformat()
        }
        
        return doc_data

    def _prepare_standard_document(self, doc_id: str, full_text: str, 
                                  metadata: Dict, filename: str) -> Dict:
        """Fallback to standard document preparation without structure"""
        
        doc_data = {
            "doc_id": doc_id,
            "content": full_text,
            "title": self._extract_metadata_value(metadata, 'title', filename or 'Untitled'),
            
            # Empty structure fields for consistency
            "headings": [],
            "key_value_pairs": [],
            "tables": [],
            "lists": [],
            
            # Basic structure metadata
            "structure_metadata": {
                "document_type": "general_document",
                "has_toc": False,
                "section_count": 0,
                "table_count": 0,
                "figure_count": 0,
                "heading_hierarchy_depth": 0,
                "key_sections": "",
                "structure_available": False
            },
            
            # Standard metadata
            "author": self._extract_metadata_value(metadata, 'author'),
            "language": self._extract_metadata_value(metadata, 'language', 'en'),
            "processing": {
                "overall_confidence": metadata.get('processing', {}).get('overall_confidence', 0.8),
                "status": "indexed",
                "word_count": len(full_text.split()) if full_text else 0
            },
            "indexed_at": datetime.utcnow().isoformat()
        }
        
        return doc_data

    def _extract_structure_elements(self, textract_structure: Dict) -> Dict:
        """Extract structured elements from Textract analysis"""
        
        elements = {
            'headings': [],
            'key_value_pairs': [],
            'tables': [],
            'lists': [],
            'has_toc': False,
            'figure_count': 0
        }
        
        blocks = textract_structure.get('Blocks', [])
        
        # Process different block types
        for block in blocks:
            block_type = block.get('BlockType')
            
            if block_type == 'LINE':
                # Detect headings based on formatting and position
                if self._is_likely_heading(block):
                    elements['headings'].append({
                        'text': block.get('Text', ''),
                        'level': self._estimate_heading_level(block),
                        'page': block.get('Page', 1),
                        'confidence': block.get('Confidence', 0.0)
                    })
            
            elif block_type == 'KEY_VALUE_SET':
                # Extract key-value pairs
                kv_pair = self._extract_key_value_pair(block, blocks)
                if kv_pair:
                    elements['key_value_pairs'].append(kv_pair)
            
            elif block_type == 'TABLE':
                # Extract table structure
                table_data = self._extract_table_data(block, blocks)
                if table_data:
                    elements['tables'].append(table_data)
        
        # Detect table of contents
        elements['has_toc'] = self._detect_table_of_contents(elements['headings'])
        
        return elements

    def _is_likely_heading(self, block: Dict) -> bool:
        """Determine if a text block is likely a heading"""
        
        text = block.get('Text', '').strip()
        
        # Basic heuristics for heading detection
        if len(text) < 3 or len(text) > 200:
            return False
        
        # Check for heading patterns
        heading_indicators = [
            text.isupper() and len(text.split()) <= 10,  # ALL CAPS short text
            text.endswith(':') and len(text.split()) <= 8,  # Ends with colon
            any(text.lower().startswith(prefix) for prefix in ['chapter', 'section', 'part', 'appendix']),
            # Simple numbering patterns
            len(text.split()) <= 3 and any(char.isdigit() for char in text[:5])
        ]
        
        return any(heading_indicators)

    def _estimate_heading_level(self, block: Dict) -> int:
        """Estimate heading level based on content"""
        
        text = block.get('Text', '').lower()
        
        # Simple heuristics for heading levels
        if any(text.startswith(prefix) for prefix in ['chapter', 'part']):
            return 1
        elif any(text.startswith(prefix) for prefix in ['section', 'appendix']):
            return 2
        elif text.isupper():
            return 2
        else:
            return 3

    def _extract_key_value_pair(self, block: Dict, all_blocks: List[Dict]) -> Optional[Dict]:
        """Extract key-value pair from Textract blocks"""
        
        # Simplified extraction - in practice would need full Textract parsing
        entity_types = block.get('EntityTypes', [])
        
        if 'KEY' in entity_types:
            return {
                'key': block.get('Text', ''),
                'value': '',  # Would need to find associated VALUE block
                'confidence': block.get('Confidence', 0.0)
            }
        
        return None

    def _extract_table_data(self, table_block: Dict, all_blocks: List[Dict]) -> Optional[Dict]:
        """Extract table structure and content"""
        
        # Simplified table extraction
        return {
            'headers': ['Column 1', 'Column 2'],  # Would extract actual headers
            'content': 'Table content would be extracted here',
            'page': table_block.get('Page', 1)
        }

    def _classify_document_type(self, structure_elements: Dict) -> str:
        """Classify document type based on structure"""
        
        headings = structure_elements.get('headings', [])
        tables = structure_elements.get('tables', [])
        kv_pairs = structure_elements.get('key_value_pairs', [])
        
        # Simple classification logic
        if len(kv_pairs) > 10:
            return 'form'
        elif len(tables) > 5:
            return 'data_report'
        elif len(headings) > 10:
            return 'structured_report'
        elif structure_elements.get('has_toc'):
            return 'formal_document'
        else:
            return 'general_document'

    def _calculate_heading_depth(self, headings: List[Dict]) -> int:
        """Calculate maximum heading hierarchy depth"""
        
        if not headings:
            return 0
        
        return max(h.get('level', 1) for h in headings)

    def _extract_key_sections(self, structure_elements: Dict) -> str:
        """Extract key section names for boosting"""
        
        headings = structure_elements.get('headings', [])
        
        # Focus on likely important sections
        key_section_keywords = [
            'executive summary', 'conclusion', 'recommendations', 'findings',
            'methodology', 'results', 'discussion', 'introduction', 'abstract'
        ]
        
        key_sections = []
        for heading in headings:
            text = heading.get('text', '').lower()
            if any(keyword in text for keyword in key_section_keywords):
                key_sections.append(heading.get('text', ''))
        
        return ' '.join(key_sections)

    def _detect_table_of_contents(self, headings: List[Dict]) -> bool:
        """Detect if document has a table of contents"""
        
        for heading in headings:
            text = heading.get('text', '').lower()
            if 'table of contents' in text or 'contents' in text:
                return True
        
        return False

    def _extract_enhanced_title(self, structure_elements: Dict, metadata: Dict, filename: str) -> str:
        """Extract enhanced title using structure analysis"""
        
        # Try metadata first
        title = self._extract_metadata_value(metadata, 'title')
        if title and title != 'Untitled':
            return title
        
        # Look for title in headings (first high-confidence heading)
        headings = structure_elements.get('headings', [])
        if headings:
            # Sort by page and confidence
            sorted_headings = sorted(headings, key=lambda h: (h.get('page', 1), -h.get('confidence', 0)))
            if sorted_headings:
                return sorted_headings[0].get('text', filename or 'Untitled')
        
        return filename or 'Untitled'

    def _extract_metadata_value(self, metadata: Dict, key: str, default: str = None) -> str:
        """Extract metadata value with nested dictionary handling"""
        
        value = metadata.get(key, {})
        if isinstance(value, dict) and 'value' in value:
            extracted = value['value']
            if isinstance(extracted, dict) and 'value' in extracted:
                return extracted['value']
            return extracted
        elif isinstance(value, str):
            return value
        
        return default
