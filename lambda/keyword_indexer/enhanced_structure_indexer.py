#!/usr/bin/env python3
"""
Enhanced Structure-Aware Keyword Indexer
Leverages Textract structure analysis for intelligent boosting and field mapping
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class StructureAwareIndexer:
    """
    Enhanced indexer that uses Textract structure analysis for intelligent boosting
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
                            "filter": ["lowercase", "asciifolding", "title_synonyms"]
                        },
                        "heading_analyzer": {
                            "type": "custom", 
                            "tokenizer": "standard",
                            "filter": ["lowercase", "asciifolding", "heading_boost"]
                        },
                        "table_analyzer": {
                            "type": "custom",
                            "tokenizer": "keyword",
                            "filter": ["lowercase"]
                        }
                    },
                    "filter": {
                        "title_synonyms": {
                            "type": "synonym",
                            "synonyms": [
                                "report,document,study",
                                "climate,environmental,sustainability",
                                "risk,threat,hazard"
                            ]
                        },
                        "heading_boost": {
                            "type": "multiplexer",
                            "filters": ["lowercase", "asciifolding"]
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
                        "boost": 3.0,  # Highest boost
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
                                "analyzer": "heading_analyzer",
                                "boost": 2.5  # High boost for headings
                            },
                            "level": {"type": "integer"},
                            "page": {"type": "integer"},
                            "confidence": {"type": "float"}
                        }
                    },
                    
                    "key_value_pairs": {
                        "type": "nested",
                        "properties": {
                            "key": {
                                "type": "text",
                                "boost": 2.0  # Medium-high boost for keys
                            },
                            "value": {
                                "type": "text",
                                "boost": 1.5  # Medium boost for values
                            },
                            "confidence": {"type": "float"}
                        }
                    },
                    
                    "tables": {
                        "type": "nested",
                        "properties": {
                            "headers": {
                                "type": "text",
                                "analyzer": "table_analyzer",
                                "boost": 2.0  # Boost table headers
                            },
                            "content": {
                                "type": "text",
                                "boost": 1.2  # Slight boost for table content
                            },
                            "page": {"type": "integer"}
                        }
                    },
                    
                    "lists": {
                        "type": "nested",
                        "properties": {
                            "items": {
                                "type": "text",
                                "boost": 1.3  # Slight boost for list items
                            },
                            "type": {"type": "keyword"}  # ORDERED, UNORDERED
                        }
                    },
                    
                    # Page-level structure information
                    "page_structure": {
                        "type": "nested",
                        "properties": {
                            "page_number": {"type": "integer"},
                            "has_title": {"type": "boolean"},
                            "has_tables": {"type": "boolean"},
                            "has_figures": {"type": "boolean"},
                            "text_density": {"type": "float"},
                            "structure_confidence": {"type": "float"}
                        }
                    },
                    
                    # Enhanced metadata with structure insights
                    "structure_metadata": {
                        "properties": {
                            "document_type": {"type": "keyword"},  # report, paper, form, etc.
                            "has_toc": {"type": "boolean"},
                            "section_count": {"type": "integer"},
                            "table_count": {"type": "integer"},
                            "figure_count": {"type": "integer"},
                            "heading_hierarchy_depth": {"type": "integer"},
                            "key_sections": {
                                "type": "text",
                                "boost": 2.2  # Boost identified key sections
                            }
                        }
                    }
                }
            }
        }
        
        return mapping

    def prepare_structure_enhanced_document(self, doc_id: str, full_text: str, 
                                          textract_structure: Dict, metadata: Dict) -> Dict:
        """Prepare document with structure-enhanced fields for better boosting"""
        
        try:
            # Extract structure elements from Textract analysis
            structure_elements = self.extract_structure_elements(textract_structure)
            
            # Prepare enhanced document
            doc_data = {
                "doc_id": doc_id,
                "content": full_text,
                
                # Enhanced title extraction
                "title": self.extract_enhanced_title(structure_elements, metadata),
                
                # Structure-based fields for boosting
                "headings": structure_elements.get('headings', []),
                "key_value_pairs": structure_elements.get('key_value_pairs', []),
                "tables": structure_elements.get('tables', []),
                "lists": structure_elements.get('lists', []),
                
                # Page structure analysis
                "page_structure": structure_elements.get('page_structure', []),
                
                # Enhanced metadata with structure insights
                "structure_metadata": {
                    "document_type": self.classify_document_type(structure_elements),
                    "has_toc": structure_elements.get('has_toc', False),
                    "section_count": len(structure_elements.get('headings', [])),
                    "table_count": len(structure_elements.get('tables', [])),
                    "figure_count": structure_elements.get('figure_count', 0),
                    "heading_hierarchy_depth": self.calculate_heading_depth(structure_elements.get('headings', [])),
                    "key_sections": self.extract_key_sections(structure_elements)
                },
                
                # Standard metadata
                "author": metadata.get('author', {}).get('value'),
                "language": metadata.get('language', {}).get('value', 'en'),
                "indexed_at": datetime.utcnow().isoformat()
            }
            
            return doc_data
            
        except Exception as e:
            logger.error(f"Error preparing structure-enhanced document: {e}")
            # Fallback to basic document preparation
            return self.prepare_basic_document(doc_id, full_text, metadata)

    def extract_structure_elements(self, textract_structure: Dict) -> Dict:
        """Extract structured elements from Textract analysis"""
        
        elements = {
            'headings': [],
            'key_value_pairs': [],
            'tables': [],
            'lists': [],
            'page_structure': [],
            'has_toc': False,
            'figure_count': 0
        }
        
        if not textract_structure or 'Blocks' not in textract_structure:
            return elements
        
        blocks = textract_structure['Blocks']
        
        # Process different block types
        for block in blocks:
            block_type = block.get('BlockType')
            
            if block_type == 'LINE':
                # Detect headings based on formatting and position
                if self.is_likely_heading(block):
                    elements['headings'].append({
                        'text': block.get('Text', ''),
                        'level': self.estimate_heading_level(block),
                        'page': block.get('Page', 1),
                        'confidence': block.get('Confidence', 0.0)
                    })
            
            elif block_type == 'KEY_VALUE_SET':
                # Extract key-value pairs
                kv_pair = self.extract_key_value_pair(block, blocks)
                if kv_pair:
                    elements['key_value_pairs'].append(kv_pair)
            
            elif block_type == 'TABLE':
                # Extract table structure
                table_data = self.extract_table_data(block, blocks)
                if table_data:
                    elements['tables'].append(table_data)
            
            elif block_type == 'SELECTION_ELEMENT':
                # Could indicate forms or checklists
                pass
        
        # Analyze page-level structure
        elements['page_structure'] = self.analyze_page_structure(blocks)
        
        # Detect table of contents
        elements['has_toc'] = self.detect_table_of_contents(elements['headings'])
        
        return elements

    def is_likely_heading(self, block: Dict) -> bool:
        """Determine if a text block is likely a heading"""
        
        text = block.get('Text', '').strip()
        
        # Heuristics for heading detection
        if len(text) < 5 or len(text) > 200:
            return False
        
        # Check for heading patterns
        heading_patterns = [
            text.isupper() and len(text.split()) <= 10,  # ALL CAPS short text
            text.endswith(':') and len(text.split()) <= 8,  # Ends with colon
            any(text.startswith(prefix) for prefix in ['Chapter', 'Section', 'Part', 'Appendix']),
            text.replace('.', '').replace(' ', '').isdigit() and len(text) <= 10,  # Numbering
        ]
        
        return any(heading_patterns)

    def estimate_heading_level(self, block: Dict) -> int:
        """Estimate heading level based on formatting and content"""
        
        text = block.get('Text', '')
        
        # Simple heuristics for heading levels
        if any(text.startswith(prefix) for prefix in ['Chapter', 'Part']):
            return 1
        elif any(text.startswith(prefix) for prefix in ['Section', 'Appendix']):
            return 2
        elif text.isupper():
            return 2
        else:
            return 3

    def extract_key_value_pair(self, block: Dict, all_blocks: List[Dict]) -> Optional[Dict]:
        """Extract key-value pair from Textract blocks"""
        
        # This would need more sophisticated logic based on Textract's
        # KEY_VALUE_SET structure - simplified for example
        return {
            'key': 'extracted_key',
            'value': 'extracted_value',
            'confidence': block.get('Confidence', 0.0)
        }

    def extract_table_data(self, table_block: Dict, all_blocks: List[Dict]) -> Optional[Dict]:
        """Extract table structure and content"""
        
        # Simplified table extraction - would need full Textract table parsing
        return {
            'headers': ['Header1', 'Header2'],
            'content': 'Table content text',
            'page': table_block.get('Page', 1)
        }

    def analyze_page_structure(self, blocks: List[Dict]) -> List[Dict]:
        """Analyze structure of each page"""
        
        page_structures = []
        pages = {}
        
        # Group blocks by page
        for block in blocks:
            page_num = block.get('Page', 1)
            if page_num not in pages:
                pages[page_num] = []
            pages[page_num].append(block)
        
        # Analyze each page
        for page_num, page_blocks in pages.items():
            structure = {
                'page_number': page_num,
                'has_title': any(self.is_likely_heading(b) for b in page_blocks if b.get('BlockType') == 'LINE'),
                'has_tables': any(b.get('BlockType') == 'TABLE' for b in page_blocks),
                'has_figures': any('figure' in b.get('Text', '').lower() for b in page_blocks if b.get('BlockType') == 'LINE'),
                'text_density': len([b for b in page_blocks if b.get('BlockType') == 'LINE']) / max(len(page_blocks), 1),
                'structure_confidence': sum(b.get('Confidence', 0) for b in page_blocks) / max(len(page_blocks), 1)
            }
            page_structures.append(structure)
        
        return page_structures

    def classify_document_type(self, structure_elements: Dict) -> str:
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

    def calculate_heading_depth(self, headings: List[Dict]) -> int:
        """Calculate maximum heading hierarchy depth"""
        
        if not headings:
            return 0
        
        return max(h.get('level', 1) for h in headings)

    def extract_key_sections(self, structure_elements: Dict) -> str:
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

    def detect_table_of_contents(self, headings: List[Dict]) -> bool:
        """Detect if document has a table of contents"""
        
        for heading in headings:
            text = heading.get('text', '').lower()
            if 'table of contents' in text or 'contents' in text:
                return True
        
        return False

    def extract_enhanced_title(self, structure_elements: Dict, metadata: Dict) -> str:
        """Extract enhanced title using structure analysis"""
        
        # Try metadata first
        title = metadata.get('title', {}).get('value')
        if title and title != 'Untitled':
            return title
        
        # Look for title in headings (first high-confidence heading)
        headings = structure_elements.get('headings', [])
        if headings:
            # Sort by page and confidence
            sorted_headings = sorted(headings, key=lambda h: (h.get('page', 1), -h.get('confidence', 0)))
            if sorted_headings:
                return sorted_headings[0].get('text', 'Untitled')
        
        return 'Untitled'

    def prepare_basic_document(self, doc_id: str, full_text: str, metadata: Dict) -> Dict:
        """Fallback basic document preparation"""
        
        return {
            "doc_id": doc_id,
            "content": full_text,
            "title": metadata.get('title', {}).get('value', 'Untitled'),
            "author": metadata.get('author', {}).get('value'),
            "language": metadata.get('language', {}).get('value', 'en'),
            "indexed_at": datetime.utcnow().isoformat()
        }

    def create_structure_aware_search_query(self, query: str, boost_preferences: Dict = None) -> Dict:
        """Create search query that leverages structure-based boosting"""
        
        default_boosts = {
            'title': 3.0,
            'headings': 2.5,
            'key_sections': 2.2,
            'key_value_keys': 2.0,
            'table_headers': 2.0,
            'key_value_values': 1.5,
            'lists': 1.3,
            'table_content': 1.2,
            'content': 1.0
        }
        
        boosts = {**default_boosts, **(boost_preferences or {})}
        
        search_body = {
            "query": {
                "bool": {
                    "should": [
                        # Title (highest boost)
                        {
                            "match": {
                                "title": {
                                    "query": query,
                                    "boost": boosts['title']
                                }
                            }
                        },
                        # Headings
                        {
                            "nested": {
                                "path": "headings",
                                "query": {
                                    "match": {
                                        "headings.text": {
                                            "query": query,
                                            "boost": boosts['headings']
                                        }
                                    }
                                }
                            }
                        },
                        # Key sections
                        {
                            "match": {
                                "structure_metadata.key_sections": {
                                    "query": query,
                                    "boost": boosts['key_sections']
                                }
                            }
                        },
                        # Key-value pairs
                        {
                            "nested": {
                                "path": "key_value_pairs",
                                "query": {
                                    "bool": {
                                        "should": [
                                            {
                                                "match": {
                                                    "key_value_pairs.key": {
                                                        "query": query,
                                                        "boost": boosts['key_value_keys']
                                                    }
                                                }
                                            },
                                            {
                                                "match": {
                                                    "key_value_pairs.value": {
                                                        "query": query,
                                                        "boost": boosts['key_value_values']
                                                    }
                                                }
                                            }
                                        ]
                                    }
                                }
                            }
                        },
                        # Tables
                        {
                            "nested": {
                                "path": "tables",
                                "query": {
                                    "bool": {
                                        "should": [
                                            {
                                                "match": {
                                                    "tables.headers": {
                                                        "query": query,
                                                        "boost": boosts['table_headers']
                                                    }
                                                }
                                            },
                                            {
                                                "match": {
                                                    "tables.content": {
                                                        "query": query,
                                                        "boost": boosts['table_content']
                                                    }
                                                }
                                            }
                                        ]
                                    }
                                }
                            }
                        },
                        # Lists
                        {
                            "nested": {
                                "path": "lists",
                                "query": {
                                    "match": {
                                        "lists.items": {
                                            "query": query,
                                            "boost": boosts['lists']
                                        }
                                    }
                                }
                            }
                        },
                        # General content (base boost)
                        {
                            "match": {
                                "content": {
                                    "query": query,
                                    "boost": boosts['content']
                                }
                            }
                        }
                    ]
                }
            },
            "highlight": {
                "fields": {
                    "content": {"fragment_size": 150, "number_of_fragments": 2},
                    "title": {"fragment_size": 0, "number_of_fragments": 0},
                    "headings.text": {"fragment_size": 100, "number_of_fragments": 1},
                    "structure_metadata.key_sections": {"fragment_size": 100, "number_of_fragments": 1}
                }
            }
        }
        
        return search_body
