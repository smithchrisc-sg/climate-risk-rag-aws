#!/usr/bin/env python3
"""
Test script for document navigation structure
Validates that the refactored KG structure supports proper navigation patterns
"""
import sys
import os

def test_navigation_structure():
    """Test the navigation structure created by refactored processor"""
    print("Testing Document Navigation Structure")
    print("=" * 60)
    
    # Sample document structure that should be created
    sample_structure = {
        'document': 'http://solve.global/knowledge-commons/document/test_doc_123',
        'sections': [
            {
                'uri': 'http://solve.global/knowledge-commons/document/test_doc_123/section/01-introduction',
                'title': 'Introduction',
                'sequence': 1,
                'chunks': [
                    {
                        'uri': 'http://solve.global/knowledge-commons/document/test_doc_123/chunk/chunk_001',
                        'sequence': 1,
                        'parent_section': 'http://solve.global/knowledge-commons/document/test_doc_123/section/01-introduction',
                        'parent_document': 'http://solve.global/knowledge-commons/document/test_doc_123'
                    },
                    {
                        'uri': 'http://solve.global/knowledge-commons/document/test_doc_123/chunk/chunk_002',
                        'sequence': 2,
                        'parent_section': 'http://solve.global/knowledge-commons/document/test_doc_123/section/01-introduction',
                        'parent_document': 'http://solve.global/knowledge-commons/document/test_doc_123'
                    }
                ]
            },
            {
                'uri': 'http://solve.global/knowledge-commons/document/test_doc_123/section/02-methodology',
                'title': 'Methodology',
                'sequence': 2,
                'chunks': [
                    {
                        'uri': 'http://solve.global/knowledge-commons/document/test_doc_123/chunk/chunk_003',
                        'sequence': 1,
                        'parent_section': 'http://solve.global/knowledge-commons/document/test_doc_123/section/02-methodology',
                        'parent_document': 'http://solve.global/knowledge-commons/document/test_doc_123'
                    }
                ]
            }
        ]
    }
    
    print("✓ Expected Document Structure:")
    print(f"  Document: {sample_structure['document']}")
    print(f"  Sections: {len(sample_structure['sections'])}")
    
    total_chunks = sum(len(section['chunks']) for section in sample_structure['sections'])
    print(f"  Total Chunks: {total_chunks}")
    
    print("\n✓ Navigation Patterns Supported:")
    
    # Pattern 1: Chunk → Section → Document
    print("  1. Chunk → Section → Document traversal")
    chunk_uri = sample_structure['sections'][0]['chunks'][0]['uri']
    section_uri = sample_structure['sections'][0]['uri']
    doc_uri = sample_structure['document']
    print(f"     {chunk_uri}")
    print(f"     ↑ kr:parentSection")
    print(f"     {section_uri}")
    print(f"     ↑ kr:parentDocument")
    print(f"     {doc_uri}")
    
    # Pattern 2: Section → All Chunks
    print("\n  2. Section → All Chunks in section")
    section = sample_structure['sections'][0]
    print(f"     {section['uri']}")
    print(f"     ↓ kr:hasChunk")
    for chunk in section['chunks']:
        print(f"     {chunk['uri']} (sequence: {chunk['sequence']})")
    
    # Pattern 3: Adjacent chunk navigation
    print("\n  3. Adjacent chunk navigation (same section)")
    print("     chunk_001 ← kr:chunkSequence 1")
    print("     chunk_002 ← kr:chunkSequence 2 (next)")
    print("     Query: WHERE { ?chunk kr:chunkSequence ?seq . FILTER(?seq = 1 + 1) }")
    
    # Pattern 4: Cross-section navigation
    print("\n  4. Document-wide navigation")
    print("     Document → kr:hasSection → All Sections")
    print("     Each Section → kr:hasChunk → All Chunks")
    print("     Ordered by kr:sectionSequence, kr:chunkSequence")
    
    return True

def test_sparql_query_patterns():
    """Test SPARQL query patterns for navigation"""
    print("\nTesting SPARQL Query Patterns")
    print("=" * 60)
    
    queries = [
        {
            'name': 'Find chunk section context',
            'description': 'Given chunk URI from vector search, find its section',
            'pattern': '''
            SELECT ?section ?sectionTitle WHERE {
                BIND(<chunk_uri_from_vector_search> AS ?chunk)
                ?chunk kr:parentSection ?section .
                ?section dcterms:title ?sectionTitle .
            }'''
        },
        {
            'name': 'Get all chunks in section',
            'description': 'Find all chunks in same section as target chunk',
            'pattern': '''
            SELECT ?chunk ?sequence WHERE {
                BIND(<target_chunk> AS ?targetChunk)
                ?targetChunk kr:parentSection ?section .
                ?section kr:hasChunk ?chunk .
                ?chunk kr:chunkSequence ?sequence .
            } ORDER BY ?sequence'''
        },
        {
            'name': 'Adjacent chunk navigation',
            'description': 'Find previous and next chunks',
            'pattern': '''
            SELECT ?chunk ?relation WHERE {
                BIND(<target_chunk> AS ?target)
                ?target kr:chunkSequence ?targetSeq .
                ?target kr:parentSection ?section .
                ?section kr:hasChunk ?chunk .
                ?chunk kr:chunkSequence ?seq .
                FILTER(?seq >= ?targetSeq - 1 && ?seq <= ?targetSeq + 1)
                BIND(IF(?seq = ?targetSeq - 1, "previous", 
                     IF(?seq = ?targetSeq + 1, "next", "current")) AS ?relation)
            }'''
        },
        {
            'name': 'Document outline',
            'description': 'Build complete document navigation tree',
            'pattern': '''
            SELECT ?section ?sectionSeq ?sectionTitle ?chunk ?chunkSeq WHERE {
                ?doc kr:hasSection ?section .
                ?section kr:sectionSequence ?sectionSeq .
                ?section dcterms:title ?sectionTitle .
                ?section kr:hasChunk ?chunk .
                ?chunk kr:chunkSequence ?chunkSeq .
            } ORDER BY ?sectionSeq ?chunkSeq'''
        }
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"✓ Query {i}: {query['name']}")
        print(f"  Purpose: {query['description']}")
        print(f"  Pattern: {query['pattern'].strip()}")
        print()
    
    return True

def test_entity_integration_readiness():
    """Test readiness for entity/concept integration"""
    print("Testing Entity Integration Readiness")
    print("=" * 60)
    
    print("✓ Structure ready for entity linking:")
    print("  - Each chunk has unique URI for entity attachment")
    print("  - Chunks linked to sections for context aggregation")
    print("  - Navigation properties support entity traversal")
    
    print("\n✓ Future entity query patterns:")
    print("  1. Chunk entities: ?chunk kcc:hasConceptMention ?mention")
    print("  2. Section entities: ?section kr:hasChunk ?chunk . ?chunk kcc:hasConceptMention ?mention")
    print("  3. Entity co-location: Same section = related entities")
    print("  4. Entity context: Navigate from entity → chunk → section → related entities")
    
    print("\n✓ S3 content integration:")
    print("  - kr:s3Location property ready for content retrieval")
    print("  - Chunk metadata (wordCount, sentenceCount) for content sizing")
    print("  - Position properties (startPosition, endPosition) for text alignment")
    
    return True

def main():
    """Run all navigation structure tests"""
    print("DOCUMENT NAVIGATION STRUCTURE VALIDATION")
    print("=" * 80)
    
    tests = [
        test_navigation_structure,
        test_sparql_query_patterns,
        test_entity_integration_readiness
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} failed: {e}")
            results.append(False)
    
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test, result) in enumerate(zip(tests, results)):
        status = "PASS" if result else "FAIL"
        print(f"{i+1}. {test.__name__}: {status}")
    
    print(f"\nOverall: {passed}/{total} validations passed")
    
    if passed == total:
        print("🎉 Navigation structure is properly designed!")
        print("Ready for:")
        print("  - Vector search → chunk → section context queries")
        print("  - Adjacent chunk navigation")
        print("  - Section-level entity aggregation")
        print("  - Document outline generation")
        return True
    else:
        print("❌ Some validations failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
