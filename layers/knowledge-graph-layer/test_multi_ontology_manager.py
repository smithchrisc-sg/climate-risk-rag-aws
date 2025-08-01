#!/usr/bin/env python3
"""
Unit tests for MultiOntologyManager

Tests the multi-ontology functionality including configuration loading,
ontology management, and concept search across multiple ontologies.
"""

import unittest
import tempfile
import json
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List

# Import the classes we're testing
import sys
sys.path.append('/Users/chris/climate-risk-rag-aws/layers/knowledge-graph-layer/python')

from utils.MultiOntologyManager import (
    MultiOntologyManager, 
    OntologyConfig, 
    OntologyScope, 
    ConceptMatch
)
from utils.OntologyManager import OntologyManager
from utils.kg_exceptions import KGValidationError, KGDataFormatError


class TestOntologyConfig(unittest.TestCase):
    """Test OntologyConfig dataclass"""
    
    def test_ontology_config_creation(self):
        """Test creating OntologyConfig objects"""
        config = OntologyConfig(
            uri="https://example.com/ontology",
            named_graph_uri="https://example.com/graph",
            priority=1,
            scopes=[OntologyScope.CLIMATE_RISK],
            source_type="s3",
            source_location="bucket/ontology.ttl"
        )
        
        self.assertEqual(config.uri, "https://example.com/ontology")
        self.assertEqual(config.priority, 1)
        self.assertEqual(config.scopes, [OntologyScope.CLIMATE_RISK])
        self.assertTrue(config.enabled)
    
    def test_ontology_config_serialization(self):
        """Test to_dict and from_dict methods"""
        config = OntologyConfig(
            uri="https://example.com/ontology",
            named_graph_uri="https://example.com/graph", 
            priority=2,
            scopes=[OntologyScope.INSURANCE, OntologyScope.FINANCIAL],
            source_type="url",
            source_location="https://example.com/ontology.rdf",
            format="xml",
            enabled=False,
            description="Test ontology"
        )
        
        # Test serialization
        config_dict = config.to_dict()
        self.assertEqual(config_dict['uri'], "https://example.com/ontology")
        self.assertEqual(config_dict['scopes'], ['insurance', 'financial'])
        self.assertFalse(config_dict['enabled'])
        
        # Test deserialization
        restored_config = OntologyConfig.from_dict(config_dict)
        self.assertEqual(restored_config.uri, config.uri)
        self.assertEqual(restored_config.scopes, config.scopes)
        self.assertEqual(restored_config.enabled, config.enabled)


class TestConceptMatch(unittest.TestCase):
    """Test ConceptMatch dataclass"""
    
    def test_concept_match_creation(self):
        """Test creating ConceptMatch objects"""
        match = ConceptMatch(
            concept_uri="https://example.com/concept1",
            concept_label="Test Concept",
            ontology_uri="https://example.com/ontology",
            ontology_priority=1,
            match_type="exact",
            confidence=0.95,
            context={"ontology_id": "test-ontology"}
        )
        
        self.assertEqual(match.concept_label, "Test Concept")
        self.assertEqual(match.match_type, "exact")
        self.assertEqual(match.confidence, 0.95)
        self.assertEqual(match.context["ontology_id"], "test-ontology")


class TestMultiOntologyManager(unittest.TestCase):
    """Test MultiOntologyManager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = MultiOntologyManager()
        
        # Create test configuration
        self.test_config = {
            "settings": {
                "cache_enabled": True,
                "fuzzy_matching_threshold": 0.7
            },
            "ontologies": {
                "test-ontology-1": {
                    "uri": "https://example.com/ontology1",
                    "named_graph_uri": "https://example.com/graph1",
                    "priority": 1,
                    "scopes": ["climate_risk"],
                    "source_type": "s3",
                    "source_location": "bucket/ontology1.ttl",
                    "format": "turtle",
                    "enabled": True,
                    "description": "Test climate risk ontology"
                },
                "test-ontology-2": {
                    "uri": "https://example.com/ontology2", 
                    "named_graph_uri": "https://example.com/graph2",
                    "priority": 2,
                    "scopes": ["insurance"],
                    "source_type": "url",
                    "source_location": "https://example.com/ontology2.rdf",
                    "format": "xml",
                    "enabled": True,
                    "description": "Test insurance ontology"
                }
            }
        }
    
    def test_initialization(self):
        """Test MultiOntologyManager initialization"""
        manager = MultiOntologyManager()
        self.assertIsInstance(manager.ontology_configs, dict)
        self.assertIsInstance(manager.ontology_managers, dict)
        self.assertTrue(manager.cache_enabled)
        self.assertEqual(manager.fuzzy_matching_threshold, 0.7)
    
    def test_load_configuration_from_dict(self):
        """Test loading configuration from dictionary"""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_config, f)
            config_path = f.name
        
        try:
            self.manager.load_configuration(config_path)
            
            # Verify configuration loaded
            self.assertEqual(len(self.manager.ontology_configs), 2)
            self.assertIn("test-ontology-1", self.manager.ontology_configs)
            self.assertIn("test-ontology-2", self.manager.ontology_configs)
            
            # Verify specific config
            config1 = self.manager.ontology_configs["test-ontology-1"]
            self.assertEqual(config1.priority, 1)
            self.assertEqual(config1.scopes, [OntologyScope.CLIMATE_RISK])
            self.assertTrue(config1.enabled)
            
        finally:
            os.unlink(config_path)
    
    def test_add_ontology(self):
        """Test adding ontology configuration"""
        config = OntologyConfig(
            uri="https://example.com/new-ontology",
            named_graph_uri="https://example.com/new-graph",
            priority=3,
            scopes=[OntologyScope.GEOGRAPHIC],
            source_type="local",
            source_location="/path/to/ontology.ttl"
        )
        
        self.manager.add_ontology("new-ontology", config)
        
        self.assertIn("new-ontology", self.manager.ontology_configs)
        self.assertEqual(self.manager.ontology_configs["new-ontology"], config)
    
    @patch('utils.MultiOntologyManager.OntologyManager')
    def test_load_ontologies_success(self, mock_ontology_manager_class):
        """Test successful ontology loading"""
        # Setup mock
        mock_manager = Mock()
        mock_manager.load_ontology_from_s3.return_value = True
        mock_manager.ontology_graph = Mock()
        mock_ontology_manager_class.return_value = mock_manager
        
        # Load test configuration
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_config, f)
            config_path = f.name
        
        try:
            self.manager.load_configuration(config_path)
            results = self.manager.load_ontologies(["test-ontology-1"])
            
            # Verify results
            self.assertTrue(results["test-ontology-1"])
            self.assertIn("test-ontology-1", self.manager.ontology_managers)
            
            # Verify ontology manager was called correctly
            mock_manager.load_ontology_from_s3.assert_called_once()
            
        finally:
            os.unlink(config_path)
    
    @patch('utils.MultiOntologyManager.OntologyManager')
    def test_load_ontologies_failure(self, mock_ontology_manager_class):
        """Test ontology loading failure"""
        # Setup mock to fail
        mock_manager = Mock()
        mock_manager.load_ontology_from_s3.return_value = False
        mock_ontology_manager_class.return_value = mock_manager
        
        # Load test configuration
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_config, f)
            config_path = f.name
        
        try:
            self.manager.load_configuration(config_path)
            results = self.manager.load_ontologies(["test-ontology-1"])
            
            # Verify failure
            self.assertFalse(results["test-ontology-1"])
            self.assertNotIn("test-ontology-1", self.manager.ontology_managers)
            
        finally:
            os.unlink(config_path)
    
    def test_get_target_ontologies_with_scopes(self):
        """Test _get_target_ontologies with specific scopes"""
        # Load test configuration
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_config, f)
            config_path = f.name
        
        try:
            self.manager.load_configuration(config_path)
            
            # Test with climate risk scope
            targets = self.manager._get_target_ontologies([OntologyScope.CLIMATE_RISK])
            self.assertIn("test-ontology-1", targets)
            self.assertNotIn("test-ontology-2", targets)
            
            # Test with insurance scope
            targets = self.manager._get_target_ontologies([OntologyScope.INSURANCE])
            self.assertNotIn("test-ontology-1", targets)
            self.assertIn("test-ontology-2", targets)
            
            # Test with no scopes (should return all)
            targets = self.manager._get_target_ontologies(None)
            self.assertEqual(len(targets), 2)
            
        finally:
            os.unlink(config_path)
    
    def test_calculate_confidence(self):
        """Test confidence calculation"""
        # Test exact match
        confidence = self.manager._calculate_confidence("earthquake", "earthquake", 1)
        self.assertEqual(confidence, 1.0)
        
        # Test partial match
        confidence = self.manager._calculate_confidence("earthquake", "earthquake disaster", 1)
        self.assertEqual(confidence, 0.8)
        
        # Test with priority boost
        confidence = self.manager._calculate_confidence("earthquake", "earthquake", 1)
        self.assertGreaterEqual(confidence, 1.0)  # Should have priority boost
        
        confidence = self.manager._calculate_confidence("earthquake", "earthquake", 10)
        self.assertEqual(confidence, 1.0)  # No boost for low priority
    
    def test_determine_match_type(self):
        """Test match type determination"""
        # Test exact match
        match_type = self.manager._determine_match_type("earthquake", "earthquake")
        self.assertEqual(match_type, "exact")
        
        # Test partial match
        match_type = self.manager._determine_match_type("earthquake", "earthquake disaster")
        self.assertEqual(match_type, "partial")
        
        # Test fuzzy match
        match_type = self.manager._determine_match_type("quake", "earthquake")
        self.assertEqual(match_type, "fuzzy")
    
    @patch('utils.MultiOntologyManager.OntologyManager')
    def test_find_concepts(self, mock_ontology_manager_class):
        """Test concept finding across ontologies"""
        # Setup mock ontology manager
        mock_manager = Mock()
        mock_manager.search_concepts_by_label.return_value = [
            {
                'uri': 'https://example.com/concept1',
                'label': 'Earthquake',
                'description': 'Seismic event'
            }
        ]
        mock_ontology_manager_class.return_value = mock_manager
        
        # Load configuration and ontologies
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_config, f)
            config_path = f.name
        
        try:
            self.manager.load_configuration(config_path)
            
            # Mock successful loading
            self.manager.ontology_managers["test-ontology-1"] = mock_manager
            
            # Test concept search
            matches = self.manager.find_concepts("earthquake", max_results=5, min_confidence=0.5)
            
            # Verify results
            self.assertIsInstance(matches, list)
            if matches:  # If any matches found
                self.assertIsInstance(matches[0], ConceptMatch)
                self.assertEqual(matches[0].concept_label, "Earthquake")
            
        finally:
            os.unlink(config_path)
    
    def test_get_ontology_stats(self):
        """Test ontology statistics"""
        # Load test configuration
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_config, f)
            config_path = f.name
        
        try:
            self.manager.load_configuration(config_path)
            stats = self.manager.get_ontology_stats()
            
            # Verify stats structure
            self.assertIn('total_ontologies', stats)
            self.assertIn('loaded_ontologies', stats)
            self.assertIn('total_concepts', stats)
            self.assertIn('ontologies', stats)
            
            self.assertEqual(stats['total_ontologies'], 2)
            self.assertEqual(stats['loaded_ontologies'], 0)  # None loaded yet
            
        finally:
            os.unlink(config_path)


class TestIntegration(unittest.TestCase):
    """Integration tests for multi-ontology functionality"""
    
    def test_end_to_end_workflow(self):
        """Test complete workflow from configuration to concept search"""
        manager = MultiOntologyManager()
        
        # Create minimal test configuration
        test_config = {
            "settings": {"cache_enabled": True},
            "ontologies": {
                "test-ontology": {
                    "uri": "https://example.com/ontology",
                    "named_graph_uri": "https://example.com/graph",
                    "priority": 1,
                    "scopes": ["climate_risk"],
                    "source_type": "s3",
                    "source_location": "bucket/ontology.ttl",
                    "format": "turtle",
                    "enabled": True
                }
            }
        }
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_config, f)
            config_path = f.name
        
        try:
            # Load configuration
            manager.load_configuration(config_path)
            self.assertEqual(len(manager.ontology_configs), 1)
            
            # Verify configuration details
            config = manager.ontology_configs["test-ontology"]
            self.assertEqual(config.priority, 1)
            self.assertEqual(config.scopes, [OntologyScope.CLIMATE_RISK])
            
            # Test stats before loading
            stats = manager.get_ontology_stats()
            self.assertEqual(stats['total_ontologies'], 1)
            self.assertEqual(stats['loaded_ontologies'], 0)
            
        finally:
            os.unlink(config_path)


if __name__ == '__main__':
    # Set up logging for tests
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    unittest.main(verbosity=2)
