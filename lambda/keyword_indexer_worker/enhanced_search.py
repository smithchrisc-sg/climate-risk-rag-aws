#!/usr/bin/env python3
"""
Enhanced Search Query Builder
Creates structure-aware search queries with intelligent boosting
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class EnhancedSearchBuilder:
    """
    Creates search queries that leverage structure-based boosting
    """
    
    def __init__(self):
        # Default boost values optimized for climate risk documents
        self.default_boosts = {
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

    def create_structure_aware_search_query(self, query: str, 
                                          boost_preferences: Dict = None,
                                          filters: Dict = None) -> Dict:
        """Create search query that leverages structure-based boosting"""
        
        boosts = {**self.default_boosts, **(boost_preferences or {})}
        
        # Build the main query with structure-aware boosting
        should_clauses = []
        
        # 1. Title (highest boost)
        should_clauses.append({
            "match": {
                "title": {
                    "query": query,
                    "boost": boosts['title']
                }
            }
        })
        
        # 2. Headings (high boost)
        should_clauses.append({
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
        })
        
        # 3. Key sections (high boost)
        should_clauses.append({
            "match": {
                "structure_metadata.key_sections": {
                    "query": query,
                    "boost": boosts['key_sections']
                }
            }
        })
        
        # 4. Key-value pairs
        should_clauses.append({
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
        })
        
        # 5. Tables
        should_clauses.append({
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
        })
        
        # 6. Lists
        should_clauses.append({
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
        })
        
        # 7. General content (base boost)
        should_clauses.append({
            "match": {
                "content": {
                    "query": query,
                    "boost": boosts['content']
                }
            }
        })
        
        # Build the complete query
        search_body = {
            "query": {
                "bool": {
                    "should": should_clauses,
                    "minimum_should_match": 1
                }
            },
            "highlight": {
                "fields": {
                    "content": {
                        "fragment_size": 150,
                        "number_of_fragments": 2,
                        "type": "unified"
                    },
                    "title": {
                        "fragment_size": 0,
                        "number_of_fragments": 0,
                        "type": "unified"
                    },
                    "headings.text": {
                        "fragment_size": 100,
                        "number_of_fragments": 1,
                        "type": "unified"
                    },
                    "structure_metadata.key_sections": {
                        "fragment_size": 100,
                        "number_of_fragments": 1,
                        "type": "unified"
                    }
                }
            },
            "_source": [
                "doc_id", "title", "author", "language",
                "structure_metadata", "processing.overall_confidence",
                "indexed_at"
            ]
        }
        
        # Add filters if provided
        if filters:
            filter_clauses = []
            
            # Document type filter
            if 'document_type' in filters:
                filter_clauses.append({
                    "term": {
                        "structure_metadata.document_type": filters['document_type']
                    }
                })
            
            # Confidence filter
            if 'min_confidence' in filters:
                filter_clauses.append({
                    "range": {
                        "processing.overall_confidence": {
                            "gte": filters['min_confidence']
                        }
                    }
                })
            
            # Structure availability filter
            if 'has_structure' in filters:
                filter_clauses.append({
                    "term": {
                        "structure_metadata.structure_available": filters['has_structure']
                    }
                })
            
            # Add filters to query
            if filter_clauses:
                search_body["query"]["bool"]["filter"] = filter_clauses
        
        return search_body

    def create_fallback_search_query(self, query: str) -> Dict:
        """Create fallback search query for documents without structure"""
        
        search_body = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "match": {
                                "title": {
                                    "query": query,
                                    "boost": 2.0
                                }
                            }
                        },
                        {
                            "match": {
                                "content": {
                                    "query": query,
                                    "boost": 1.0
                                }
                            }
                        }
                    ],
                    "filter": [
                        {
                            "term": {
                                "structure_metadata.structure_available": False
                            }
                        }
                    ]
                }
            },
            "highlight": {
                "fields": {
                    "content": {
                        "fragment_size": 150,
                        "number_of_fragments": 3,
                        "type": "unified"
                    },
                    "title": {
                        "fragment_size": 0,
                        "number_of_fragments": 0,
                        "type": "unified"
                    }
                }
            }
        }
        
        return search_body

    def create_hybrid_search_query(self, query: str) -> Dict:
        """Create hybrid query that works well for both structured and unstructured docs"""
        
        search_body = {
            "query": {
                "bool": {
                    "should": [
                        # High boost for structured content
                        {
                            "bool": {
                                "should": [
                                    {
                                        "match": {
                                            "title": {
                                                "query": query,
                                                "boost": 3.0
                                            }
                                        }
                                    },
                                    {
                                        "nested": {
                                            "path": "headings",
                                            "query": {
                                                "match": {
                                                    "headings.text": {
                                                        "query": query,
                                                        "boost": 2.5
                                                    }
                                                }
                                            }
                                        }
                                    },
                                    {
                                        "match": {
                                            "structure_metadata.key_sections": {
                                                "query": query,
                                                "boost": 2.2
                                            }
                                        }
                                    }
                                ],
                                "filter": [
                                    {
                                        "term": {
                                            "structure_metadata.structure_available": True
                                        }
                                    }
                                ]
                            }
                        },
                        # Standard boost for unstructured content
                        {
                            "bool": {
                                "should": [
                                    {
                                        "match": {
                                            "title": {
                                                "query": query,
                                                "boost": 2.0
                                            }
                                        }
                                    },
                                    {
                                        "match": {
                                            "content": {
                                                "query": query,
                                                "boost": 1.0
                                            }
                                        }
                                    }
                                ],
                                "filter": [
                                    {
                                        "term": {
                                            "structure_metadata.structure_available": False
                                        }
                                    }
                                ]
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

    def analyze_search_results(self, results: Dict) -> Dict:
        """Analyze search results to provide insights about structure usage"""
        
        if not results or 'hits' not in results:
            return {}
        
        hits = results['hits']['hits']
        total_hits = len(hits)
        
        if total_hits == 0:
            return {"total_hits": 0}
        
        # Analyze structure availability
        structured_docs = 0
        unstructured_docs = 0
        
        for hit in hits:
            source = hit.get('_source', {})
            structure_meta = source.get('structure_metadata', {})
            
            if structure_meta.get('structure_available', False):
                structured_docs += 1
            else:
                unstructured_docs += 1
        
        analysis = {
            "total_hits": total_hits,
            "structured_documents": structured_docs,
            "unstructured_documents": unstructured_docs,
            "structure_coverage": structured_docs / total_hits if total_hits > 0 else 0,
            "avg_confidence": sum(
                hit.get('_source', {}).get('processing', {}).get('overall_confidence', 0)
                for hit in hits
            ) / total_hits if total_hits > 0 else 0
        }
        
        return analysis
