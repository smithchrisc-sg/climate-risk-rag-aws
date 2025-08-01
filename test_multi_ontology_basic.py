#!/usr/bin/env python3
"""
Basic unit tests for MultiOntologyManager classes without external dependencies
"""

import unittest
import tempfile
import json
import os
import sys

# Add the layer path
sys.path.append('/Users/chris/climate-risk-rag-aws/layers/knowledge-graph-layer/python')

# Test the basic classes without importing the full module
class TestOntologyScope(unittest.TestCase):
    """Test OntologyScope enum"""
    
    def test_ontology_scope_values(self):
        """Test that OntologyScope enum has expected values"""
        from utils.MultiOntologyManager import OntologyScope
        
        expected_scopes = ['climate_risk', 'insurance', 'financial', 'geographic', 'general']
        actual_scopes = [scope.value for scope in OntologyScope]
        
        for expected in expected_scopes:
            self.assertIn(expected, actual_scopes)


class TestOntologyConfig(unittest.TestCase):
    """Test OntologyConfig dataclass"""
    
    def test_ontology_config_creation(self):
        """Test creating OntologyConfig objects"""
        from utils.MultiOntologyManager import OntologyConfig, OntologyScope
        
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
        self.assertEqual(config.format, "turtle")  # Default value
    
    def test_ontology_config_serialization(self):
        """Test to_dict and from_dict methods"""
        from utils.MultiOntologyManager import OntologyConfig, OntologyScope
        
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
        self.assertEqual(config_dict['format'], 'xml')
        
        # Test deserialization
        restored_config = OntologyConfig.from_dict(config_dict)
        self.assertEqual(restored_config.uri, config.uri)
        self.assertEqual(restored_config.scopes, config.scopes)
        self.assertEqual(restored_config.enabled, config.enabled)
        self.assertEqual(restored_config.format, config.format)


class TestConceptMatch(unittest.TestCase):
    """Test ConceptMatch dataclass"""
    
    def test_concept_match_creation(self):
        """Test creating ConceptMatch objects"""
        from utils.MultiOntologyManager import ConceptMatch
        
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


class TestMultiOntologyManagerBasic(unittest.TestCase):
    """Test basic MultiOntologyManager functionality without external dependencies"""
    
    def test_initialization(self):
        """Test MultiOntologyManager initialization"""
        from utils.MultiOntologyManager import MultiOntologyManager
        
        manager = MultiOntologyManager()
        self.assertIsInstance(manager.ontology_configs, dict)
        self.assertIsInstance(manager.ontology_managers, dict)
        self.assertTrue(manager.cache_enabled)
        self.assertEqual(manager.fuzzy_matching_threshold, 0.7)
    
    def test_load_configuration_from_file(self):
        """Test loading configuration from file"""
        from utils.MultiOntologyManager import MultiOntologyManager, OntologyScope
        
        # Create test configuration
        test_config = {
            "settings": {
                "cache_enabled": True,
                "fuzzy_matching_threshold": 0.8
            },
            "ontologies": {
                "test-ontology": {
                    "uri": "https://example.com/ontology",
                    "named_graph_uri": "https://example.com/graph",
                    "priority": 1,
                    "scopes": ["climate_risk"],
                    "source_type": "s3",
                    "source_location": "bucket/ontology.ttl",
                    "format": "turtle",
                    "enabled": True,
                    "description": "Test ontology"
                }
            }
        }
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_config, f)
            config_path = f.name
        
        try:
            manager = MultiOntologyManager()
            manager.load_configuration(config_path)
            
            # Verify configuration loaded
            self.assertEqual(len(manager.ontology_configs), 1)
            self.assertIn("test-ontology", manager.ontology_configs)
            
            # Verify specific config
            config = manager.ontology_configs["test-ontology"]
            self.assertEqual(config.priority, 1)
            self.assertEqual(config.scopes, [OntologyScope.CLIMATE_RISK])
            self.assertTrue(config.enabled)
            
            # Verify settings
            self.assertTrue(manager.cache_enabled)
            self.assertEqual(manager.fuzzy_matching_threshold, 0.8)
            
        finally:
            os.unlink(config_path)
    
    def test_add_ontology(self):
        """Test adding ontology configuration"""
        from utils.MultiOntologyManager import MultiOntologyManager, OntologyConfig, OntologyScope
        
        manager = MultiOntologyManager()
        
        config = OntologyConfig(
            uri="https://example.com/new-ontology",
            named_graph_uri="https://example.com/new-graph",
            priority=3,
            scopes=[OntologyScope.GEOGRAPHIC],
            source_type="local",
            source_location="/path/to/ontology.ttl"
        )
        
        manager.add_ontology("new-ontology", config)
        
        self.assertIn("new-ontology", manager.ontology_configs)
        self.assertEqual(manager.ontology_configs["new-ontology"], config)
    
    def test_get_target_ontologies(self):
        """Test _get_target_ontologies method"""
        from utils.MultiOntologyManager import MultiOntologyManager, OntologyConfig, OntologyScope
        
        manager = MultiOntologyManager()
        
        # Add test configurations
        config1 = OntologyConfig(
            uri="https://example.com/ontology1",
            named_graph_uri="https://example.com/graph1",
            priority=1,
            scopes=[OntologyScope.CLIMATE_RISK],
            source_type="s3",
            source_location="bucket/ontology1.ttl"
        )
        
        config2 = OntologyConfig(
            uri="https://example.com/ontology2",
            named_graph_uri="https://example.com/graph2",
            priority=2,
            scopes=[OntologyScope.INSURANCE],
            source_type="s3",
            source_location="bucket/ontology2.ttl"
        )
        
        manager.add_ontology("ontology1", config1)
        manager.add_ontology("ontology2", config2)
        
        # Test with specific scopes
        targets = manager._get_target_ontologies([OntologyScope.CLIMATE_RISK])
        self.assertIn("ontology1", targets)
        self.assertNotIn("ontology2", targets)
        
        targets = manager._get_target_ontologies([OntologyScope.INSURANCE])
        self.assertNotIn("ontology1", targets)
        self.assertIn("ontology2", targets)
        
        # Test with no scopes (should return empty since no ontologies loaded)
        targets = manager._get_target_ontologies(None)
        self.assertEqual(len(targets), 0)  # No loaded ontologies
    
    def test_confidence_calculation(self):
        """Test confidence calculation"""
        from utils.MultiOntologyManager import MultiOntologyManager
        
        manager = MultiOntologyManager()
        
        # Test exact match
        confidence = manager._calculate_confidence("earthquake", "earthquake", 1)
        self.assertGreaterEqual(confidence, 1.0)  # Should be 1.0 + priority boost
        
        # Test partial match
        confidence = manager._calculate_confidence("earthquake", "earthquake disaster", 1)
        self.assertGreaterEqual(confidence, 0.8)  # Should be 0.8 + priority boost
        
        # Test with different priorities
        confidence_high_priority = manager._calculate_confidence("earthquake", "earthquake", 1)
        confidence_low_priority = manager._calculate_confidence("earthquake", "earthquake", 10)
        
        self.assertGreaterEqual(confidence_high_priority, confidence_low_priority)
    
    def test_match_type_determination(self):
        """Test match type determination"""
        from utils.MultiOntologyManager import MultiOntologyManager
        
        manager = MultiOntologyManager()
        
        # Test exact match
        match_type = manager._determine_match_type("earthquake", "earthquake")
        self.assertEqual(match_type, "exact")
        
        # Test partial match
        match_type = manager._determine_match_type("earthquake", "earthquake disaster")
        self.assertEqual(match_type, "partial")
        
        match_type = manager._determine_match_type("disaster", "earthquake disaster")
        self.assertEqual(match_type, "partial")
        
        # Test fuzzy match
        match_type = manager._determine_match_type("quake", "earthquake")
        self.assertEqual(match_type, "fuzzy")


class TestConfigurationValidation(unittest.TestCase):
    """Test configuration validation"""
    
    def test_invalid_configuration_format(self):
        """Test handling of invalid configuration format"""
        from utils.MultiOntologyManager import MultiOntologyManager
        from utils.kg_exceptions import KGDataFormatError
        
        # Create invalid config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            config_path = f.name
        
        try:
            manager = MultiOntologyManager()
            with self.assertRaises(KGDataFormatError):
                manager.load_configuration(config_path)
        finally:
            os.unlink(config_path)
    
    def test_missing_configuration_file(self):
        """Test handling of missing configuration file"""
        from utils.MultiOntologyManager import MultiOntologyManager
        from utils.kg_exceptions import KGDataFormatError
        
        manager = MultiOntologyManager()
        with self.assertRaises(KGDataFormatError):
            manager.load_configuration("/nonexistent/config.json")


if __name__ == '__main__':
    # Set up logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise in tests
    
    # Run tests
    unittest.main(verbosity=2)
