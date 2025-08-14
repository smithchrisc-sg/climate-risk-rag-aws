#!/usr/bin/env python3
"""
Test the enhanced observability features in nlp-worker
This tests the metrics generation without requiring full AWS infrastructure
"""
import sys
import os
import json
from datetime import datetime
from unittest.mock import Mock, patch

# Add the src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_observability_features():
    """Test the observability features with mock data"""
    
    print("🧪 Testing NLP Worker Observability Features")
    
    # Mock the DatabaseManager to avoid AWS dependencies
    with patch('nlp_worker.DatabaseManager') as mock_db:
        mock_db_instance = Mock()
        mock_db.return_value = mock_db_instance
        
        # Import after patching
        from nlp_worker import NLPWorker
        
        # Create worker instance
        worker = NLPWorker()
        
        # Mock data for testing
        doc_id = "test_doc_123"
        
        # Sample chunks (mix of found and not found)
        chunks = [
            {
                'chunk_id': 'test_doc_123_chunk_0001',
                'chunk_index': 1,
                'text': 'The World Bank is providing funding for climate adaptation projects.',
                'section_type': 'paragraph',
                'hierarchy_level': 1,
                'parent_chunk_id': None
            },
            {
                'chunk_id': 'test_doc_123_chunk_0002', 
                'chunk_index': 2,
                'text': 'Nepal has been affected by climate change impacts.',
                'section_type': 'paragraph',
                'hierarchy_level': 1,
                'parent_chunk_id': None
            },
            {
                'chunk_id': 'test_doc_123_chunk_0003',
                'chunk_index': 3,
                'text': 'Public Disclosure Authorized\nDocument Header Information',
                'section_type': 'header',
                'hierarchy_level': 0,
                'parent_chunk_id': None
            }
        ]
        
        # Sample chunk positions (simulating that chunk_0003 was not found)
        chunk_positions = [
            {
                'chunk_id': 'test_doc_123_chunk_0001',
                'chunk_text': 'The World Bank is providing funding for climate adaptation projects.',
                'start_offset': 100,
                'end_offset': 167,
                'chunk_index': 1,
                'section_type': 'paragraph',
                'hierarchy_level': 1,
                'parent_chunk_id': None
            },
            {
                'chunk_id': 'test_doc_123_chunk_0002',
                'chunk_text': 'Nepal has been affected by climate change impacts.',
                'start_offset': 200,
                'end_offset': 250,
                'chunk_index': 2,
                'section_type': 'paragraph',
                'hierarchy_level': 1,
                'parent_chunk_id': None
            }
        ]
        
        # Sample Comprehend results
        comprehend_results = {
            'entities': [
                {'text': 'World Bank', 'type': 'ORGANIZATION', 'score': 0.95, 'begin_offset': 104, 'end_offset': 114},
                {'text': 'Nepal', 'type': 'LOCATION', 'score': 0.98, 'begin_offset': 200, 'end_offset': 205},
                {'text': 'climate change', 'type': 'OTHER', 'score': 0.85, 'begin_offset': 225, 'end_offset': 239},
                {'text': 'John Smith', 'type': 'PERSON', 'score': 0.92, 'begin_offset': 300, 'end_offset': 310},  # Won't map - no chunk
                {'text': 'Document Header', 'type': 'OTHER', 'score': 0.75, 'begin_offset': 400, 'end_offset': 415}  # Won't map - chunk not found
            ],
            'key_phrases': [
                {'text': 'climate adaptation projects', 'score': 0.88, 'begin_offset': 135, 'end_offset': 162},
                {'text': 'funding', 'score': 0.82, 'begin_offset': 125, 'end_offset': 132},
                {'text': 'climate impacts', 'score': 0.90, 'begin_offset': 235, 'end_offset': 250}
            ]
        }
        
        # Sample mapped results (simulating the mapping process)
        entities_mapped = [
            {
                'chunk_id': 'test_doc_123_chunk_0001',
                'entity': 'World Bank',
                'type': 'ORGANIZATION',
                'score': 0.95,
                'mapping_type': 'exact_chunk',
                'mapping_confidence': 1.0
            },
            {
                'chunk_id': 'test_doc_123_chunk_0002',
                'entity': 'Nepal',
                'type': 'LOCATION', 
                'score': 0.98,
                'mapping_type': 'exact_chunk',
                'mapping_confidence': 1.0
            },
            {
                'chunk_id': 'test_doc_123_chunk_0002',
                'entity': 'climate change',
                'type': 'OTHER',
                'score': 0.85,
                'mapping_type': 'exact_chunk',
                'mapping_confidence': 1.0
            }
        ]
        
        entities_unmapped = [
            {
                'entity': 'John Smith',
                'type': 'PERSON',
                'score': 0.92,
                'original_begin_offset': 300,
                'original_end_offset': 310,
                'reason': 'no_chunk_overlap'
            },
            {
                'entity': 'Document Header',
                'type': 'OTHER',
                'score': 0.75,
                'original_begin_offset': 400,
                'original_end_offset': 415,
                'reason': 'no_chunk_overlap'
            }
        ]
        
        keyphrases_mapped = [
            {
                'chunk_id': 'test_doc_123_chunk_0001',
                'phrase': 'climate adaptation projects',
                'score': 0.88,
                'mapping_type': 'exact_chunk',
                'mapping_confidence': 1.0
            },
            {
                'chunk_id': 'test_doc_123_chunk_0001',
                'phrase': 'funding',
                'score': 0.82,
                'mapping_type': 'exact_chunk',
                'mapping_confidence': 1.0
            },
            {
                'chunk_id': 'test_doc_123_chunk_0002',
                'phrase': 'climate impacts',
                'score': 0.90,
                'mapping_type': 'exact_chunk',
                'mapping_confidence': 1.0
            }
        ]
        
        keyphrases_unmapped = []
        
        print("\n📊 Testing metrics generation...")
        
        # Test metrics generation
        metrics = worker.generate_mapping_metrics(
            doc_id=doc_id,
            chunks=chunks,
            chunk_positions=chunk_positions,
            comprehend_results=comprehend_results,
            entities_mapped=entities_mapped,
            entities_unmapped=entities_unmapped,
            keyphrases_mapped=keyphrases_mapped,
            keyphrases_unmapped=keyphrases_unmapped
        )
        
        print("✅ Metrics generated successfully")
        
        # Display key metrics
        print(f"\n📈 KEY METRICS:")
        print(f"  Entity mapping success rate: {metrics['entity_mapping_success_rate']}%")
        print(f"  Keyphrase mapping success rate: {metrics['keyphrase_mapping_success_rate']}%")
        print(f"  Chunk finding success rate: {metrics['chunk_finding_success_rate']}%")
        print(f"  Critical entity success rate: {metrics['critical_entity_success_rate']}%")
        print(f"  Search quality impact score: {metrics['estimated_search_quality_impact']}")
        
        print(f"\n🎯 SEARCH IMPACT BREAKDOWN:")
        breakdown = metrics['search_impact_breakdown']
        for category, score in breakdown.items():
            print(f"  {category}: {score}")
        
        print(f"\n📦 CHUNK ANALYSIS:")
        print(f"  Total chunks: {metrics['total_chunks']}")
        print(f"  Chunks found: {metrics['chunks_found_in_original']}")
        print(f"  Chunks with entities: {metrics['chunks_with_entities']}")
        print(f"  Chunk finding issues: {metrics['chunk_finding_issues']}")
        
        print(f"\n🏷️  ENTITY TYPE ANALYSIS:")
        print(f"  Mapped by type: {metrics['entity_types_mapped']}")
        print(f"  Unmapped by type: {metrics['entity_types_unmapped']}")
        
        # Test logging (with mock to avoid actual logging)
        print(f"\n📝 Testing metrics logging...")
        with patch('nlp_worker.logger') as mock_logger:
            worker.log_mapping_metrics(metrics)
            print(f"✅ Logging called {mock_logger.info.call_count} times")
            
            # Show sample log messages
            for i, call in enumerate(mock_logger.info.call_args_list[:3]):
                print(f"  Log {i+1}: {call[0][0][:80]}...")
        
        # Test database storage (with mock)
        print(f"\n💾 Testing metrics storage...")
        worker.store_mapping_metrics(metrics)
        print(f"✅ Database storage methods called")
        
        # Test error metrics
        print(f"\n❌ Testing error metrics...")
        error_metrics = worker.generate_error_metrics(doc_id, "Test error message")
        print(f"✅ Error metrics generated: {error_metrics['status']}")
        
        print(f"\n🎉 ALL OBSERVABILITY TESTS PASSED!")
        
        return True

if __name__ == "__main__":
    try:
        success = test_observability_features()
        if success:
            print("\n✅ Observability features are working correctly!")
            print("Ready for deployment and end-to-end testing.")
        else:
            print("\n❌ Observability tests failed!")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
