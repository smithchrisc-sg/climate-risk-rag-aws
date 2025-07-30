#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Knowledge Graph Layer
Validates layer structure and basic functionality
"""
import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add the layer to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

class TestKnowledgeGraphLayer(unittest.TestCase):
    """Test suite for Knowledge Graph Layer components"""
    
    def test_imports(self):
        """Test that all components can be imported"""
        try:
            from utils.KnowledgeGraphManager import KnowledgeGraphManager
            from utils.URIManager import URIManager
            from utils.SPARQLQueryBuilder import SPARQLQueryBuilder
            from utils.OntologyManager import OntologyManager
            from utils.TripleManager import TripleManager
            from utils.kg_exceptions import (
                KGConnectionError, KGQueryError, KGInsertError,
                KGValidationError, KGAuthenticationError
            )
            print("PASS: All imports successful")
        except ImportError as e:
            self.fail("Import failed: {}".format(e))
    
    def test_uri_manager(self):
        """Test URIManager functionality"""
        from utils.URIManager import URIManager
        
        uri_manager = URIManager()
        
        # Test document URI generation
        doc_uri = uri_manager.mint_document_uri("test_doc_123")
        self.assertTrue(doc_uri.startswith("http://solve.global/knowledge-commons/document/"))
        self.assertIn("test_doc_123", doc_uri)
        
        # Test chunk URI generation
        chunk_uri = uri_manager.mint_chunk_uri("test_doc_123", "chunk_456")
        self.assertTrue(chunk_uri.startswith("http://solve.global/knowledge-commons/chunk/"))
        self.assertIn("test_doc_123", chunk_uri)
        self.assertIn("chunk_456", chunk_uri)
        
        # Test concept mention URI generation
        mention_uri = uri_manager.mint_concept_mention_uri("chunk_456", "http://example.org/concept", 100)
        self.assertTrue(mention_uri.startswith("http://solve.global/knowledge-commons/mention/"))
        
        # Test prefix generation
        ttl_prefixes = uri_manager.get_prefixes_ttl()
        self.assertIn("@prefix kcc:", ttl_prefixes)
        self.assertIn("@prefix dcterms:", ttl_prefixes)
        
        sparql_prefixes = uri_manager.get_prefixes_sparql()
        self.assertIn("PREFIX kcc:", sparql_prefixes)
        self.assertIn("PREFIX dcterms:", sparql_prefixes)
        
        print("PASS: URIManager tests passed")
    
    def test_sparql_query_builder(self):
        """Test SPARQLQueryBuilder functionality"""
        from utils.SPARQLQueryBuilder import SPARQLQueryBuilder
        from utils.URIManager import URIManager
        
        uri_manager = URIManager()
        query_builder = SPARQLQueryBuilder(uri_manager)
        
        # Test document concept query
        concept_uris = ["http://example.org/concept1", "http://example.org/concept2"]
        query = query_builder.build_document_concept_query(concept_uris, limit=10)
        self.assertIn("SELECT", query)
        self.assertIn("concept1", query)
        self.assertIn("concept2", query)
        self.assertIn("LIMIT 10", query)
        
        # Test co-occurrence query
        cooc_query = query_builder.build_co_occurrence_query("http://example.org/concept1")
        self.assertIn("SELECT", cooc_query)
        self.assertIn("kcc:hasCoOccurrence", cooc_query)
        
        # Test document summary query
        summary_query = query_builder.build_document_summary_query("test_doc")
        self.assertIn("SELECT", summary_query)
        self.assertIn("kcc:hasConceptMention", summary_query)
        
        # Test literal escaping
        escaped = query_builder.escape_literal('Test "quoted" text')
        self.assertIn('\\"', escaped)
        
        print("PASS: SPARQLQueryBuilder tests passed")
    
    @patch.dict(os.environ, {
        'NEPTUNE_ENDPOINT': 'test-neptune.amazonaws.com',
        'NEPTUNE_PORT': '8182',
        'AWS_REGION': 'us-east-1'
    })
    @patch('boto3.Session')
    @patch('requests.post')
    def test_knowledge_graph_manager_init(self, mock_post, mock_session):
        """Test KnowledgeGraphManager initialization"""
        from utils.KnowledgeGraphManager import KnowledgeGraphManager
        
        # Mock AWS credentials
        mock_creds = Mock()
        mock_creds.access_key = 'test_key'
        mock_creds.secret_key = 'test_secret'
        mock_creds.token = 'test_token'
        mock_session.return_value.get_credentials.return_value = mock_creds
        
        # Mock successful connection test
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'results': {
                'bindings': [{'count': {'type': 'literal', 'value': '100'}}]
            }
        }
        mock_post.return_value = mock_response
        
        # Initialize KG manager
        kg_manager = KnowledgeGraphManager()
        
        # Test that components are initialized
        self.assertIsNotNone(kg_manager.uri_manager)
        self.assertIsNotNone(kg_manager.query_builder)
        self.assertIsNotNone(kg_manager.ontology_manager)
        self.assertIsNotNone(kg_manager.triple_manager)
        
        # Test connection info
        conn_info = kg_manager.get_connection_info()
        self.assertEqual(conn_info['neptune_endpoint'], 'test-neptune.amazonaws.com')
        self.assertEqual(conn_info['neptune_port'], '8182')
        
        print("PASS: KnowledgeGraphManager initialization tests passed")
    
    def test_exceptions(self):
        """Test that all exceptions are properly defined"""
        from utils.kg_exceptions import (
            KGBaseException, KGConnectionError, KGQueryError, 
            KGInsertError, KGValidationError, KGAuthenticationError,
            KGTimeoutError, KGDataFormatError
        )
        
        # Test exception hierarchy
        self.assertTrue(issubclass(KGConnectionError, KGBaseException))
        self.assertTrue(issubclass(KGQueryError, KGBaseException))
        self.assertTrue(issubclass(KGInsertError, KGBaseException))
        self.assertTrue(issubclass(KGValidationError, KGBaseException))
        self.assertTrue(issubclass(KGAuthenticationError, KGBaseException))
        
        # Test exception instantiation
        try:
            raise KGConnectionError("Test connection error")
        except KGConnectionError as e:
            self.assertEqual(str(e), "Test connection error")
        
        print("PASS: Exception tests passed")
    
    def test_validation_functions(self):
        """Test validation functions"""
        from utils.URIManager import URIManager
        from utils.kg_exceptions import KGValidationError
        
        uri_manager = URIManager()
        
        # Test URI validation
        self.assertTrue(uri_manager.is_valid_uri("http://example.org/test"))
        self.assertTrue(uri_manager.is_valid_uri("https://example.org/test"))
        self.assertFalse(uri_manager.is_valid_uri("not-a-uri"))
        self.assertFalse(uri_manager.is_valid_uri(""))
        
        # Test namespace consistency
        test_uri = "http://solve.global/knowledge-commons/document/test"
        self.assertTrue(uri_manager.validate_namespace_consistency(test_uri))
        
        bad_uri = "http://other.domain/document/test"
        self.assertFalse(uri_manager.validate_namespace_consistency(bad_uri))
        
        print("PASS: Validation function tests passed")

def run_tests():
    """Run all tests"""
    print("Testing Knowledge Graph Layer v1.0.0")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestKnowledgeGraphLayer)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    print("=" * 50)
    if result.wasSuccessful():
        print("SUCCESS: All tests passed! Layer is ready for deployment.")
        return True
    else:
        print("FAILURE: Some tests failed. Please fix issues before deployment.")
        print("Failures: {}".format(len(result.failures)))
        print("Errors: {}".format(len(result.errors)))
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
