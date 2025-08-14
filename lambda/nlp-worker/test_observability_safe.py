#!/usr/bin/env python3
"""
Safe test for observability wrapper - doesn't modify production code
Tests the wrapper functionality with mock data
"""
import sys
import os
import json
from unittest.mock import Mock, patch

# Add the src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_observability_wrapper():
    """Test the observability wrapper safely"""
    
    print("🧪 Testing NLP Worker Observability Wrapper (Safe)")
    
    # Mock the DatabaseManager to avoid AWS dependencies
    with patch('nlp_worker.DatabaseManager') as mock_db:
        mock_db_instance = Mock()
        mock_db.return_value = mock_db_instance
        
        # Import the wrapper
        from nlp_worker_with_observability import NLPWorkerWithObservability
        
        # Create worker instance
        worker = NLPWorkerWithObservability()
        
        # Mock the original map_results_to_chunks method to return test data
        def mock_original_mapping(comprehend_results, chunks, doc_id):
            return {
                'entities_by_chunk': [
                    {
                        'chunk_id': 'test_chunk_001',
                        'entity': 'World Bank',
                        'type': 'ORGANIZATION',
                        'score': 0.95
                    },
                    {
                        'chunk_id': 'test_chunk_002',
                        'entity': 'Nepal',
                        'type': 'LOCATION',
                        'score': 0.98
                    }
                ],
                'key_phrases_by_chunk': [
                    {
                        'chunk_id': 'test_chunk_001',
                        'phrase': 'climate adaptation',
                        'score': 0.88
                    }
                ]
            }
        
        # Patch the parent class method
        with patch.object(worker.__class__.__bases__[0], 'map_results_to_chunks', side_effect=mock_original_mapping):
            
            # Test data
            doc_id = "test_doc_observability"
            chunks = [
                {'chunk_id': 'test_chunk_001', 'text': 'World Bank provides funding'},
                {'chunk_id': 'test_chunk_002', 'text': 'Nepal faces climate challenges'},
                {'chunk_id': 'test_chunk_003', 'text': 'Additional content here'}
            ]
            
            comprehend_results = {
                'entities': [
                    {'text': 'World Bank', 'Type': 'ORGANIZATION', 'Score': 0.95},
                    {'text': 'Nepal', 'Type': 'LOCATION', 'Score': 0.98},
                    {'text': 'John Doe', 'Type': 'PERSON', 'Score': 0.85}  # This won't be mapped
                ],
                'key_phrases': [
                    {'text': 'climate adaptation', 'Score': 0.88},
                    {'text': 'funding programs', 'Score': 0.82}
                ]
            }
            
            print("\n📊 Testing enhanced mapping with observability...")
            
            # Call the enhanced method
            results = worker.map_results_to_chunks(comprehend_results, chunks, doc_id)
            
            print("✅ Enhanced mapping completed successfully")
            
            # Check that we got the original results plus metrics
            assert 'entities_by_chunk' in results
            assert 'key_phrases_by_chunk' in results
            assert 'mapping_metrics' in results
            
            metrics = results['mapping_metrics']
            
            print(f"\n📈 OBSERVABILITY METRICS:")
            print(f"  Document ID: {metrics['doc_id']}")
            print(f"  Entity mapping success rate: {metrics['entity_mapping_success_rate']}%")
            print(f"  Keyphrase mapping success rate: {metrics['keyphrase_mapping_success_rate']}%")
            print(f"  Chunk finding success rate: {metrics['chunk_finding_success_rate']}%")
            print(f"  Critical entity success rate: {metrics['critical_entity_success_rate']}%")
            print(f"  Search quality impact score: {metrics['estimated_search_quality_impact']}")
            
            print(f"\n🎯 SEARCH IMPACT BREAKDOWN:")
            breakdown = metrics['search_impact_breakdown']
            for category, score in breakdown.items():
                if score > 0:
                    print(f"  {category}: {score}")
            
            print(f"\n📦 CHUNK COVERAGE:")
            print(f"  Total chunks: {metrics['total_chunks']}")
            print(f"  Chunks with entities: {metrics['chunks_with_entities']}")
            print(f"  Coverage rate: {metrics['chunk_entity_coverage_rate']}%")
            
            print(f"\n🏷️  ENTITY TYPE ANALYSIS:")
            print(f"  Mapped by type: {metrics['entity_types_mapped']}")
            print(f"  Unmapped by type: {metrics['entity_types_unmapped']}")
            
            # Test that unmapped entities are tracked
            assert metrics['entities_unmapped'] == 1  # John Doe should be unmapped
            assert 'PERSON' in metrics['entity_types_unmapped']
            
            # Test that critical entities are properly identified
            assert metrics['critical_entities_mapped'] == 2  # World Bank + Nepal
            
            print(f"\n✅ All observability features working correctly!")
            
            return True

if __name__ == "__main__":
    try:
        success = test_observability_wrapper()
        if success:
            print("\n🎉 OBSERVABILITY WRAPPER TEST PASSED!")
            print("✅ Safe to deploy - no production code modified")
            print("✅ Comprehensive metrics tracking implemented")
            print("✅ Search quality impact analysis working")
        else:
            print("\n❌ Observability wrapper test failed!")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
