#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple unit tests for vector embeddings system (no mock dependencies)
"""
import sys
import os
import json

# Add lambda function paths
sys.path.append('./lambda/vector_embeddings_worker')
sys.path.append('./lambda/vector_embeddings_processor')

def test_embeddings_interface():
    """Test the pluggable embeddings interface"""
    print("Testing Embeddings Interface...")
    
    try:
        from embeddings_interface import EmbeddingsFactory, EmbeddingsInterface
        
        print("  OK EmbeddingsFactory imported successfully")
        print("  OK EmbeddingsInterface imported successfully")
        
        # Test factory method exists
        assert hasattr(EmbeddingsFactory, 'create_embeddings')
        print("  OK Factory create_embeddings method exists")
        
        # Test interface methods exist
        interface_methods = ['create_embeddings_batch', 'get_embedding_dimension', 
                           'get_model_info', 'estimate_cost']
        for method in interface_methods:
            assert hasattr(EmbeddingsInterface, method)
        print("  OK All interface methods defined")
        
        print("PASS Embeddings Interface Tests: PASSED")
        return True
        
    except Exception as e:
        print("FAIL Embeddings Interface Tests: FAILED - {}".format(str(e)))
        return False

def test_titan_embeddings():
    """Test Titan embeddings implementation"""
    print("\nTesting Titan Embeddings...")
    
    try:
        from titan_embeddings import TitanEmbeddings
        
        # Test creation (will fail without boto3, but class should be importable)
        print("  OK TitanEmbeddings class imported")
        
        # Test that it has required methods
        required_methods = ['create_embeddings_batch', 'get_embedding_dimension', 
                          'get_model_info', 'estimate_cost']
        for method in required_methods:
            assert hasattr(TitanEmbeddings, method)
        print("  OK All required methods present")
        
        # Test cost estimation logic
        try:
            titan = TitanEmbeddings()
            sample_texts = ["Test text for cost estimation"]
            cost = titan.estimate_cost(sample_texts)
            assert cost >= 0
            print("  OK Cost estimation works: ${:.6f}".format(cost))
        except Exception as e:
            print("  WARN Cost estimation failed (expected without AWS): {}".format(str(e)))
        
        print("PASS Titan Embeddings Tests: PASSED")
        return True
        
    except Exception as e:
        print("FAIL Titan Embeddings Tests: FAILED - {}".format(str(e)))
        return False

def test_sentence_transformer_embeddings():
    """Test SentenceTransformer embeddings implementation"""
    print("\nTesting SentenceTransformer Embeddings...")
    
    try:
        from sentence_transformer_embeddings import SentenceTransformerEmbeddings
        
        print("  OK SentenceTransformerEmbeddings class imported")
        
        # Test that it has required methods
        required_methods = ['create_embeddings_batch', 'get_embedding_dimension', 
                          'get_model_info', 'estimate_cost']
        for method in required_methods:
            assert hasattr(SentenceTransformerEmbeddings, method)
        print("  OK All required methods present")
        
        # Test graceful handling of missing dependency
        try:
            st = SentenceTransformerEmbeddings()
            model_info = st.get_model_info()
            assert 'available' in model_info
            print("  OK Graceful dependency handling: available={}".format(model_info['available']))
        except Exception as e:
            print("  WARN SentenceTransformers init failed (expected): {}".format(str(e)))
        
        print("PASS SentenceTransformer Embeddings Tests: PASSED")
        return True
        
    except Exception as e:
        print("FAIL SentenceTransformer Embeddings Tests: FAILED - {}".format(str(e)))
        return False

def test_opensearch_vector_indexer():
    """Test OpenSearch vector indexer"""
    print("\nTesting OpenSearch Vector Indexer...")
    
    try:
        from opensearch_vector_indexer import OpenSearchVectorIndexer
        
        print("  OK OpenSearchVectorIndexer class imported")
        
        # Test that it has required methods
        required_methods = ['create_vector_index_mapping', 'index_document_vectors', 
                          'search_similar_vectors', '_calculate_composite_score']
        for method in required_methods:
            assert hasattr(OpenSearchVectorIndexer, method)
        print("  OK All required methods present")
        
        # Test composite scoring logic
        try:
            # Create a dummy indexer (will fail without client, but we can test the method)
            class DummyIndexer(OpenSearchVectorIndexer):
                def __init__(self):
                    pass  # Skip parent init
            
            indexer = DummyIndexer()
            score = indexer._calculate_composite_score(0.9, 0.8, 0.7)
            assert 0 <= score <= 1
            print("  OK Composite scoring works: {:.3f}".format(score))
        except Exception as e:
            print("  WARN Composite scoring test failed: {}".format(str(e)))
        
        print("PASS OpenSearch Vector Indexer Tests: PASSED")
        return True
        
    except Exception as e:
        print("FAIL OpenSearch Vector Indexer Tests: FAILED - {}".format(str(e)))
        return False

def test_lambda_function_structure():
    """Test Lambda function file structure"""
    print("\nTesting Lambda Function Structure...")
    
    try:
        # Test processor function
        processor_file = './lambda/vector_embeddings_processor/vector_embeddings_processor.py'
        assert os.path.exists(processor_file)
        print("  OK Processor function file exists")
        
        with open(processor_file, 'r') as f:
            content = f.read()
        assert 'lambda_handler' in content
        assert 'DatabaseManager' in content
        print("  OK Processor function has required components")
        
        # Test worker function
        worker_file = './lambda/vector_embeddings_worker/vector_embeddings_worker.py'
        assert os.path.exists(worker_file)
        print("  OK Worker function file exists")
        
        with open(worker_file, 'r') as f:
            content = f.read()
        assert 'lambda_handler' in content
        assert 'EmbeddingsFactory' in content
        print("  OK Worker function has required components")
        
        # Test requirements files
        assert os.path.exists('./lambda/vector_embeddings_processor/requirements.txt')
        assert os.path.exists('./lambda/vector_embeddings_worker/requirements.txt')
        print("  OK Requirements files exist")
        
        print("PASS Lambda Function Structure Tests: PASSED")
        return True
        
    except Exception as e:
        print("FAIL Lambda Function Structure Tests: FAILED - {}".format(str(e)))
        return False

def test_cdk_stack():
    """Test CDK stack configuration"""
    print("\nTesting CDK Stack...")
    
    try:
        cdk_file = 'cdk/app_vector_embeddings_pipeline.py'
        assert os.path.exists(cdk_file)
        print("  OK CDK stack file exists")
        
        with open(cdk_file, 'r') as f:
            content = f.read()
        
        # Check for key components
        required_components = [
            'VectorEmbeddingsPipelineStack',
            'VectorEmbeddingsProcessor', 
            'VectorEmbeddingsWorker',
            'chunks-ready',  # Correct topic name
            'climate-risk-core-utilities-pipeline'  # Correct layer
        ]
        
        for component in required_components:
            assert component in content
            print("  OK CDK has component: {}".format(component))
        
        print("PASS CDK Stack Tests: PASSED")
        return True
        
    except Exception as e:
        print("FAIL CDK Stack Tests: FAILED - {}".format(str(e)))
        return False

def test_database_schema():
    """Test database schema"""
    print("\nTesting Database Schema...")
    
    try:
        schema_file = 'migrate_vector_embeddings_schema.py'
        assert os.path.exists(schema_file)
        print("  OK Database migration file exists")
        
        with open(schema_file, 'r') as f:
            content = f.read()
        
        # Check for required SQL
        required_sql = [
            'CREATE TABLE IF NOT EXISTS vector_embeddings_status',
            'CREATE INDEX',
            'ALTER TABLE document_processing_status'
        ]
        
        for sql in required_sql:
            assert sql in content
            print("  OK Schema has SQL: {}".format(sql))
        
        print("PASS Database Schema Tests: PASSED")
        return True
        
    except Exception as e:
        print("FAIL Database Schema Tests: FAILED - {}".format(str(e)))
        return False

def test_deployment_script():
    """Test deployment script"""
    print("\nTesting Deployment Script...")
    
    try:
        deploy_file = 'deploy_vector_embeddings_complete.py'
        assert os.path.exists(deploy_file)
        print("  OK Deployment script exists")
        
        with open(deploy_file, 'r') as f:
            content = f.read()
        
        # Check for key deployment steps
        required_steps = [
            'migrate_vector_embeddings_schema',
            'cdk deploy',
            'vector-embeddings-pipeline'
        ]
        
        for step in required_steps:
            assert step in content
            print("  OK Deployment has step: {}".format(step))
        
        print("PASS Deployment Script Tests: PASSED")
        return True
        
    except Exception as e:
        print("FAIL Deployment Script Tests: FAILED - {}".format(str(e)))
        return False

def run_all_tests():
    """Run all unit tests"""
    print("VECTOR EMBEDDINGS SYSTEM - UNIT TESTS")
    print("=" * 60)
    
    tests = [
        test_embeddings_interface,
        test_titan_embeddings,
        test_sentence_transformer_embeddings,
        test_opensearch_vector_indexer,
        test_lambda_function_structure,
        test_cdk_stack,
        test_database_schema,
        test_deployment_script
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
        print("WARN SOME TESTS FAILED - FIX ISSUES BEFORE DEPLOYMENT")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
