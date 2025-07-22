#!/usr/bin/env python3
"""
Structure-Aware Keyword Indexer
Leverages Textract structure analysis for enhanced search boosting with fallback
PRESERVED FROM DEPRECATED VERSION - NO FUNCTIONALITY CHANGES
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class StructureAwareProcessor:
    """
    Enhanced processor that uses Textract structure analysis for intelligent boosting
    PRESERVED FUNCTIONALITY - NO CHANGES TO OPENSEARCH LOGIC
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
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "timestamp": {"type": "date"},
                    
                    # Structure-enhanced fields with boosting
                    "title_content": {
                        "type": "text",
                        "analyzer": "title_analyzer",
                        "boost": 3.0
                    },
                    "heading_content": {
                        "type": "text", 
                        "analyzer": "heading_analyzer",
                        "boost": 2.0
                    },
                    "table_content": {
                        "type": "text",
                        "analyzer": "table_analyzer",
                        "boost": 1.5
                    },
                    "form_content": {
                        "type": "text",
                        "analyzer": "standard",
                        "boost": 1.3
                    },
                    
                    # Structure metadata
                    "structure_metadata": {
                        "type": "object",
                        "properties": {
                            "page_count": {"type": "integer"},
                            "table_count": {"type": "integer"},
                            "form_count": {"type": "integer"},
                            "line_count": {"type": "integer"},
                            "has_tables": {"type": "boolean"},
                            "has_forms": {"type": "boolean"}
                        }
                    },
                    
                    # Search optimization fields
                    "all_content": {
                        "type": "text",
                        "analyzer": "standard"
                    }
                }
            }
        }
        
        try:
            # Check if index exists
            if self.client.indices.exists(index=self.index_name):
                logger.info(f"Index {self.index_name} already exists")
                return True
                
            # Create index with mapping
            response = self.client.indices.create(
                index=self.index_name,
                body=mapping
            )
            
            logger.info(f"Created enhanced index mapping: {response}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create index mapping: {e}")
            return False

    def extract_structure_from_textract(self, textract_response: Dict) -> Dict[str, Any]:
        """Extract structured content from Textract response for enhanced indexing"""
        try:
            blocks = textract_response.get('blocks', [])
            
            # Initialize structure containers
            structure_data = {
                'title_content': [],
                'heading_content': [],
                'table_content': [],
                'form_content': [],
                'regular_content': [],
                'metadata': {
                    'page_count': 0,
                    'table_count': 0,
                    'form_count': 0,
                    'line_count': 0,
                    'has_tables': False,
                    'has_forms': False
                }
            }
            
            # Process blocks by type
            for block in blocks:
                block_type = block.get('BlockType', '')
                confidence = block.get('Confidence', 0)
                text = block.get('Text', '').strip()
                
                if not text or confidence < 50:  # Skip low confidence or empty blocks
                    continue
                
                # Classify content based on Textract structure
                if block_type == 'LINE':
                    structure_data['metadata']['line_count'] += 1
                    
                    # Heuristic classification for titles/headings
                    if self._is_likely_title(text, block):
                        structure_data['title_content'].append(text)
                    elif self._is_likely_heading(text, block):
                        structure_data['heading_content'].append(text)
                    else:
                        structure_data['regular_content'].append(text)
                        
                elif block_type == 'CELL':
                    # Table cell content
                    structure_data['table_content'].append(text)
                    structure_data['metadata']['has_tables'] = True
                    
                elif block_type == 'KEY_VALUE_SET':
                    # Form field content
                    structure_data['form_content'].append(text)
                    structure_data['metadata']['has_forms'] = True
                    
                elif block_type == 'TABLE':
                    structure_data['metadata']['table_count'] += 1
                    
                elif block_type == 'PAGE':
                    structure_data['metadata']['page_count'] += 1
            
            # Count forms
            structure_data['metadata']['form_count'] = len([b for b in blocks if b.get('BlockType') == 'KEY_VALUE_SET'])
            
            logger.info(f"Extracted structure: {structure_data['metadata']}")
            return structure_data
            
        except Exception as e:
            logger.error(f"Failed to extract Textract structure: {e}")
            # Return fallback structure
            return {
                'title_content': [],
                'heading_content': [],
                'table_content': [],
                'form_content': [],
                'regular_content': [],
                'metadata': {
                    'page_count': 1,
                    'table_count': 0,
                    'form_count': 0,
                    'line_count': 0,
                    'has_tables': False,
                    'has_forms': False
                }
            }
    
    def _is_likely_title(self, text: str, block: Dict) -> bool:
        """Heuristic to identify title content"""
        # Check for title indicators
        title_indicators = [
            len(text) < 100,  # Titles are usually short
            text.isupper(),   # All caps often indicates title
            not text.endswith('.'),  # Titles don't end with periods
            any(word in text.lower() for word in ['report', 'analysis', 'study', 'assessment'])
        ]
        
        # Geometry-based checks (if available)
        geometry = block.get('Geometry', {})
        bbox = geometry.get('BoundingBox', {})
        
        # Top of page positioning suggests title
        if bbox.get('Top', 1) < 0.2:  # Top 20% of page
            title_indicators.append(True)
        
        return sum(title_indicators) >= 2
    
    def _is_likely_heading(self, text: str, block: Dict) -> bool:
        """Heuristic to identify heading content"""
        heading_indicators = [
            len(text) < 200,  # Headings are usually short
            text.endswith(':'),  # Often end with colon
            any(char.isdigit() for char in text[:5]),  # Often start with numbers
            text.count(' ') < 10,  # Usually few words
        ]
        
        return sum(heading_indicators) >= 2

    def create_enhanced_document(self, doc_id: str, raw_text: str, 
                               structure_data: Dict, metadata: Dict = None) -> Dict[str, Any]:
        """Create enhanced document for indexing with structure-based boosting"""
        
        # Combine all content types
        all_content_parts = []
        all_content_parts.extend(structure_data.get('title_content', []))
        all_content_parts.extend(structure_data.get('heading_content', []))
        all_content_parts.extend(structure_data.get('table_content', []))
        all_content_parts.extend(structure_data.get('form_content', []))
        all_content_parts.extend(structure_data.get('regular_content', []))
        
        # Create enhanced document
        enhanced_doc = {
            "doc_id": doc_id,
            "content": raw_text,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            
            # Structure-enhanced fields for boosting
            "title_content": " ".join(structure_data.get('title_content', [])),
            "heading_content": " ".join(structure_data.get('heading_content', [])),
            "table_content": " ".join(structure_data.get('table_content', [])),
            "form_content": " ".join(structure_data.get('form_content', [])),
            
            # Combined searchable content
            "all_content": " ".join(all_content_parts),
            
            # Structure metadata
            "structure_metadata": structure_data.get('metadata', {}),
        }
        
        # Add additional metadata if provided
        if metadata:
            enhanced_doc.update(metadata)
        
        return enhanced_doc

    def index_enhanced_document(self, doc_id: str, raw_text: str, 
                              textract_response: Dict, metadata: Dict = None) -> bool:
        """Index document with structure-aware enhancements"""
        try:
            # Extract structure from Textract response
            structure_data = self.extract_structure_from_textract(textract_response)
            
            # Create enhanced document
            enhanced_doc = self.create_enhanced_document(
                doc_id, raw_text, structure_data, metadata
            )
            
            # Index the document
            response = self.client.index(
                index=self.index_name,
                id=doc_id,
                body=enhanced_doc
            )
            
            logger.info(f"Indexed enhanced document {doc_id}: {response['result']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index enhanced document {doc_id}: {e}")
            return False

    def fallback_index_document(self, doc_id: str, raw_text: str, metadata: Dict = None) -> bool:
        """Fallback indexing without structure analysis"""
        try:
            # Create basic document
            basic_doc = {
                "doc_id": doc_id,
                "content": raw_text,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "all_content": raw_text,
                "structure_metadata": {
                    'page_count': 1,
                    'table_count': 0,
                    'form_count': 0,
                    'line_count': raw_text.count('\n'),
                    'has_tables': False,
                    'has_forms': False
                }
            }
            
            if metadata:
                basic_doc.update(metadata)
            
            # Index the document
            response = self.client.index(
                index=self.index_name,
                id=doc_id,
                body=basic_doc
            )
            
            logger.info(f"Indexed basic document {doc_id}: {response['result']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index basic document {doc_id}: {e}")
            return False
