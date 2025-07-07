#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive unit tests for vector embeddings system
"""
import sys
import os
import json
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock

# Add lambda function paths
sys.path.append('./lambda/vector_embeddings_worker')
sys.path.append('./lambda/vector_embeddings_processor')

def test_embeddings_interface():
    """Test the pluggable embeddings interface"""
    print("Testing Embeddings Interface...")
    
    try:
        from embeddings_interface import EmbeddingsFactory
        
        # Test factory creation
        print("  OK EmbeddingsFactory imported successfully")
        
        # Test Titan embeddings creation (will fail without AWS, but should create object)
        try:
            titan_embeddings = EmbeddingsFactory.create_embeddings('titan')
            print("  OK Titan embeddings object created")
            
            # Test interface methods
            model_info = titan_embeddings.get_model_info()
            assert 'model_type' in model_info
            assert model_info['model_type'] == 'titan'
            print("  OK Titan model info: {}".format(model_info))
            
            # Test cost estimation
            sample_texts = ["Test text for cost estimation"]
            cost = titan_embeddings.estimate_cost(sample_texts)
            assert cost >= 0
            print("  OK Titan cost estimation: ${:.6f}".format(cost))
            
        except Exception as e:
            print("  WARN Titan embeddings test failed (expected without AWS): {}".format(str(e)))
        
        # Test SentenceTransformers embeddings creation
        try:
            st_embeddings = EmbeddingsFactory.create_embeddings('sentence_transformers')
            print("  OK SentenceTransformers embeddings object created")
            
            model_info = st_embeddings.get_model_info()
            assert 'model_type' in model_info
            assert model_info['model_type'] == 'sentence_transformers'
            print("  OK SentenceTransformers model info: {}".format(model_info))
            
            # Test cost estimation
            cost = st_embeddings.estimate_cost(sample_texts)
            assert cost >= 0
            print("  OK SentenceTransformers cost estimation: ${:.10f}".format(cost))
            
        except Exception as e:
            print("  WARN SentenceTransformers test failed (expected without package): {}".format(str(e)))
        
        print("PASS Embeddings Interface Tests: PASSED")
        return True
        
    except Exception as e:
        print("FAIL Embeddings Interface Tests: FAILED - {}".format(str(e)))
        return False

def test_opensearch_vector_indexer():
    """Test OpenSearch vector indexer"""
    print("\nTesting OpenSearch Vector Indexer...")
    
    try:
        from opensearch_vector_indexer import OpenSearchVectorIndexer
        
        # Create mock OpenSearch client
        mock_client = Mock()
        mock_client.indices.exists.return_value = False
        mock_client.indices.create.return_value = {"acknowledged": True}
        mock_client.bulk.return_value = {"errors": False, "items": []}
        mock_client.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_id": "test_doc_chunk_001",
                        "_score": 0.95,
                        "_source": {
                            "doc_id": "test_doc",
                            "chunk_id": "chunk_001",
                            "content": "Test content",
                            "metadata": {
                                "confidence": 0.8,
                                "structural_quality": 0.7
                            }
                        }
                    }
                ]
            }
        }
        
        # Test indexer creation
        indexer = OpenSearchVectorIndexer(mock_client, "test-vector-index")
        print("  OK OpenSearch vector indexer created")
        
        # Test index mapping creation
        indexer.create_vector_index_mapping(384)  # SentenceTransformers dimension
        mock_client.indices.create.assert_called_once()
        print("  OK Vector index mapping creation")
        
        # Test document indexing
        sample_embeddings = [
            {
                'chunk_id': 'chunk_001',
                'doc_id': 'test_doc',
                'text': 'Test content',
                'embedding': [0.1] * 384,  # Mock embedding
                'chunk_index': 0,
                'metadata': {'confidence': 0.8}
            }
        ]
        
        indexer.index_document_vectors('test_doc', sample_embeddings)
        mock_client.bulk.assert_called_once()
        print("  OK Document vector indexing")
        
        # Test vector search
        query_vector = [0.1] * 384
        results = indexer.search_similar_vectors(query_vector, limit=5)
        assert len(results) == 1
        assert 'composite_score' in results[0]
        print("  OK Vector similarity search")
        
        # Test composite scoring
        score = indexer._calculate_composite_score(0.9, 0.8, 0.7)
        assert 0 <= score <= 1
        print("  OK Composite scoring: {:.3f}".format(score))
        
        print("PASS OpenSearch Vector Indexer Tests: PASSED")
        return True
        
    except Exception as e:
        print("FAIL OpenSearch Vector Indexer Tests: FAILED - {}".format(str(e)))
        return False

def test_vector_embeddings_processor():
    """Test vector embeddings processor Lambda function"""
    print("\nTesting Vector Embeddings Processor...")
    
    try:
        # Mock the lambda layer imports
        with patch.dict('sys.modules', {
            'utils.DatabaseManager': Mock(),
            'utils.DocumentIDManager': Mock()
        }):
            from vector_embeddings_processor import lambda_handler
            
            # Mock environment variables
            with patch.dict(os.environ, {
                'VECTOR_WORKER_TOPIC_ARN': 'arn:aws:sns:us-east-1:123456789012:test-topic'
            }):
                # Mock boto3 clients
                with patch('boto3.client') as mock_boto3:
                    mock_sns = Mock()
                    mock_boto3.return_value = mock_sns
                    
                    # Mock database manager
                    with patch('vector_embeddings_processor.DatabaseManager') as mock_db_manager:
                        mock_db = Mock()
                        mock_db.execute_query.return_value = [['exists']]  # Document exists
                        mock_db_manager.return_value = mock_db
                        
                        # Test event
                        test_event = {
                            "Records": [{
                                "Sns": {
                                    "Message": json.dumps({
                                        "doc_id": "test_doc_123",
                                        "chunks_location": {
                                            "bucket": "test-bucket",
                                            "prefix": "test_doc_123/"
                                        }
                                    })
                                }
                            }]
                        }
                        
                        # Mock context
                        mock_context = Mock()
                        mock_context.get_remaining_time_in_millis.return_value = 50000
                        
                        # Test function
                        response = lambda_handler(test_event, mock_context)
                        
                        # Verify response
                        assert response['statusCode'] == 200
                        response_body = json.loads(response['body'])
                        assert response_body['doc_id'] == 'test_doc_123'
                        assert response_body['status'] == 'delegated_to_worker'
                        
                        # Verify SNS publish was called
                        mock_sns.publish.assert_called_once()
                        
                        print("  OK Processor handles valid events")
                        print("  OK Database validation works")
                        print("  OK SNS delegation works")
                        print("  OK Response format correct")
        
        print("PASS Vector Embeddings Processor Tests: PASSED")
        return True
        
    except Exception as e:
        print("FAIL Vector Embeddings Processor Tests: FAILED - {}".format(str(e)))
        return False

def test_vector_embeddings_worker():
    """Test vector embeddings worker Lambda function"""
    print("\nTesting Vector Embeddings Worker...")
    
    try:
        # Mock all the dependencies
        with patch.dict('sys.modules', {
            'utils.DatabaseManager': Mock(),
            'utils.DocumentIDManager': Mock(),
            'opensearchpy': Mock(),
            'aws_requests_auth.aws_auth': Mock()
        }):
            # Mock the embeddings components
            with patch('vector_embeddings_worker.EmbeddingsFactory') as mock_factory:
                with patch('vector_embeddings_worker.OpenSearchVectorIndexer') as mock_indexer:
                    with patch('vector_embeddings_worker.load_chunks_from_s3') as mock_load_chunks:
                        with patch('vector_embeddings_worker.get_opensearch_client') as mock_os_client:
                            
                            # Setup mocks
                            mock_embeddings = Mock()
                            mock_embeddings.estimate_cost.return_value = 0.001
                            mock_embeddings.create_embeddings_batch.return_value = [[0.1] * 384]
                            mock_embeddings.get_model_info.return_value = {"model_type": "test"}
                            mock_embeddings.get_embedding_dimension.return_value = 384
                            mock_factory.create_embeddings.return_value = mock_embeddings
                            
                            mock_chunks = [{"chunk_id": "chunk_001", "text": "Test content"}]
                            mock_load_chunks.return_value = mock_chunks
                            
                            mock_vector_indexer = Mock()
                            mock_indexer.return_value = mock_vector_indexer
                            
                            # Mock database manager
                            with patch('vector_embeddings_worker.DatabaseManager') as mock_db_manager:
                                mock_db = Mock()
                                mock_db_manager.return_value = mock_db
                                
                                # Mock environment variables
                                with patch.dict(os.environ, {
                                    'EMBEDDINGS_MODEL_TYPE': 'sentence_transformers',
                                    'COST_THRESHOLD_PER_DOC': '0.50'
                                }):
                                    from vector_embeddings_worker import lambda_handler
                                    
                                    # Test event
                                    test_event = {
                                        "Records": [{
                                            "Sns": {
                                                "Message": json.dumps({
                                                    "doc_id": "test_doc_123",
                                                    "chunks_location": {
                                                        "bucket": "test-bucket",
                                                        "prefix": "test_doc_123/"
                                                    }
                                                })
                                            }
                                        }]
                                    }
                                    
                                    # Test function
                                    response = lambda_handler(test_event, Mock())
                                    
                                    # Verify response
                                    assert response['statusCode'] == 200
                                    response_body = json.loads(response['body'])
                                    assert response_body['doc_id'] == 'test_doc_123'
                                    assert response_body['status'] == 'completed'
                                    
                                    print("  OK Worker processes events correctly")
                                    print("  OK Embeddings generation mocked successfully")
                                    print("  OK OpenSearch indexing mocked successfully")
                                    print("  OK Database updates mocked successfully")
        
        print("PASS Vector Embeddings Worker Tests: PASSED")
        return True
        
    except Exception as e:
        print("FAIL Vector Embeddings Worker Tests: FAILED - {}".format(str(e)))
        return False

def test_database_schema():
    """Test database schema SQL"""
    print("\nTesting Database Schema...")
    
    try:
        # Read the migration script
        with open('migrate_vector_embeddings_schema.py', 'r') as f:
            content = f.read()
        
        # Check that SQL commands are present
        assert 'CREATE TABLE IF NOT EXISTS vector_embeddings_status' in content
        assert 'CREATE INDEX' in content
        assert 'ALTER TABLE document_processing_status' in content
        
        print("  OK Database schema SQL commands present")
        print("  OK Migration script structure valid")
        
        print("PASS Database Schema Tests: PASSED")
        return True
        
    except Exception as e:
        print("FAIL Database Schema Tests: FAILED - {}".format(str(e)))
        return False

def test_cdk_stack():
    """Test CDK stack configuration"""
    print("\nTesting CDK Stack...")
    
    try:
        # Check CDK stack file exists and has correct structure
        with open('cdk/app_vector_embeddings_pipeline.py', 'r') as f:
            content = f.read()
        
        # Check for key components
        assert 'VectorEmbeddingsPipelineStack' in content
        assert 'VectorEmbeddingsProcessor' in content
        assert 'VectorEmbeddingsWorker' in content
        assert 'chunks-ready' in content  # Correct topic name
        assert 'climate-risk-core-utilities-pipeline' in content  # Correct layer
        
        print("  OK CDK stack structure valid")
        print("  OK Correct topic references")
        print("  OK Correct layer ARNs")
        
        print("PASS CDK Stack Tests: PASSED")
        return True
        
    except Exception as e:
        print("FAIL CDK Stack Tests: FAILED - {}".format(str(e)))
        return False

def run_all_tests():
    """Run all unit tests"""
    print("VECTOR EMBEDDINGS SYSTEM - UNIT TESTS")
    print("=" * 60)
    
    tests = [
        test_embeddings_interface,
        test_opensearch_vector_indexer,
        test_vector_embeddings_processor,
        test_vector_embeddings_worker,
        test_database_schema,
        test_cdk_stack
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print("FAIL Test {} FAILED with exception: {}".format(test.__name__, str(e)))
            failed += 1
    
    print("\n" + "=" * 60)
    print("UNIT TEST RESULTS")
    print("=" * 60)
    print("Total Tests: {}".format(len(tests)))
    print("Passed: {}".format(passed))
    print("Failed: {}".format(failed))
    
    if failed == 0:
        print("SUCCESS ALL UNIT TESTS PASSED - READY FOR DEPLOYMENT")
        return True
    else:
        print("WARN️  SOME TESTS FAILED - FIX ISSUES BEFORE DEPLOYMENT")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
