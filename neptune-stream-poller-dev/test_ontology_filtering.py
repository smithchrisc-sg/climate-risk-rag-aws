#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for enhanced ontology filtering in Neptune Stream Poller.

Tests both geonames and climate risk ontology filtering logic to ensure:
1. Existing geonames functionality remains unchanged
2. New climate risk filtering works correctly
3. Feature flags control filtering behavior
4. Pattern-based property detection works as expected
"""

import unittest
import os
from unittest.mock import Mock, patch
from rdflib.term import URIRef, Literal, BNode
from rdflib import Namespace

# Import the handler class
import sys
sys.path.append('/Users/chris/climate-risk-rag-aws/neptune-stream-poller-dev')
from neptune_to_es.neptune_sparql_es_handler import ElasticSearchSparqlHandler


class TestOntologyFiltering(unittest.TestCase):
    """Test suite for ontology-specific filtering logic"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.handler = ElasticSearchSparqlHandler()
        
        # Mock statement elements for testing
        self.geonames_subject = URIRef("http://sws.geonames.org/1701668/")
        self.climate_risk_concept = URIRef("http://solve.global/knowledge-commons/climate-risk-ontology#MangroveRestoration")
        self.climate_risk_property = URIRef("http://solve.global/knowledge-commons/climate-risk-ontology#hasCharacteristic")
        
        # Mock record data
        self.mock_record_data = {"statement": "test statement"}

    def test_geonames_filtering_enabled_by_default(self):
        """Test that geonames filtering is enabled by default"""
        with patch.dict(os.environ, {}, clear=True):
            result = self.handler._is_geonames_filtering_enabled()
            self.assertTrue(result)

    def test_climate_risk_filtering_disabled_by_default(self):
        """Test that climate risk filtering is disabled by default for safety"""
        with patch.dict(os.environ, {}, clear=True):
            result = self.handler._is_climate_risk_filtering_enabled()
            self.assertFalse(result)

    def test_feature_flags_control_filtering(self):
        """Test that environment variables control filtering behavior"""
        # Test enabling climate risk filtering
        with patch.dict(os.environ, {'ENABLE_CLIMATE_RISK_FILTERING': 'true'}):
            self.assertTrue(self.handler._is_climate_risk_filtering_enabled())
        
        # Test disabling geonames filtering
        with patch.dict(os.environ, {'ENABLE_GEONAMES_FILTERING': 'false'}):
            self.assertFalse(self.handler._is_geonames_filtering_enabled())

    def test_geonames_label_predicate_acceptance(self):
        """Test that geonames filter accepts name-related predicates"""
        mock_statement_elements = {
            'subject': self.geonames_subject,
            'predicate': URIRef("http://www.geonames.org/ontology#name"),
            'object': Literal("Manila")
        }
        
        with patch.dict(os.environ, {'ENABLE_GEONAMES_FILTERING': 'true'}):
            result = self.handler._filter_geonames_records(
                self.mock_record_data, 
                mock_statement_elements, 
                "http://www.geonames.org/ontology#name"
            )
            self.assertTrue(result)

    def test_geonames_non_name_predicate_rejection(self):
        """Test that geonames filter rejects non-name predicates"""
        mock_statement_elements = {
            'subject': self.geonames_subject,
            'predicate': URIRef("http://www.geonames.org/ontology#population"),
            'object': Literal("1780000")
        }
        
        with patch.dict(os.environ, {'ENABLE_GEONAMES_FILTERING': 'true'}):
            result = self.handler._filter_geonames_records(
                self.mock_record_data,
                mock_statement_elements,
                "http://www.geonames.org/ontology#population"
            )
            self.assertFalse(result)

    def test_climate_risk_label_predicate_detection(self):
        """Test climate risk label predicate detection"""
        test_cases = [
            ("http://www.w3.org/2000/01/rdf-schema#label", True),
            ("http://www.w3.org/2004/02/skos/core#prefLabel", True),
            ("http://www.w3.org/2004/02/skos/core#altLabel", True),
            ("http://purl.org/dc/elements/1.1/title", True),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#hasCharacteristic", False),
        ]
        
        for predicate_uri, expected in test_cases:
            with self.subTest(predicate=predicate_uri):
                result = self.handler._is_climate_risk_label_predicate(predicate_uri)
                self.assertEqual(result, expected)

    def test_climate_risk_property_pattern_detection(self):
        """Test pattern-based detection of climate risk properties"""
        test_cases = [
            # Properties (should return True)
            ("http://solve.global/knowledge-commons/climate-risk-ontology#hasCharacteristic", True),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#mitigatesImpact", True),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#addressesRisk", True),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#providesService", True),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#requiresStakeholderEngagement", True),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#implementsStrategy", True),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#enhancesResilience", True),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#causesImpact", True),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#containsFeature", True),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#experiencesClimateEvent", True),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#drivesRisk", True),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#operatesIn", True),
            
            # Concepts (should return False)
            ("http://solve.global/knowledge-commons/climate-risk-ontology#MangroveRestoration", False),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#AcademicInstitution", False),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#ClimateRisk", False),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#Stakeholder", False),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#Airport", False),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#Building", False),
            
            # Non-climate-risk URIs (should return False)
            ("http://www.geonames.org/ontology#name", False),
            ("http://www.w3.org/2000/01/rdf-schema#label", False),
        ]
        
        for uri, expected in test_cases:
            with self.subTest(uri=uri):
                result = self.handler._is_climate_risk_property(uri)
                self.assertEqual(result, expected, f"Failed for URI: {uri}")

    def test_climate_risk_concept_filtering_accepts_labels(self):
        """Test that climate risk filter accepts label predicates for concepts"""
        mock_statement_elements = {
            'subject': self.climate_risk_concept,
            'predicate': URIRef("http://www.w3.org/2000/01/rdf-schema#label"),
            'object': Literal("Mangrove Restoration")
        }
        
        with patch.dict(os.environ, {'ENABLE_CLIMATE_RISK_FILTERING': 'true'}):
            result = self.handler._filter_climate_risk_records(
                self.mock_record_data,
                mock_statement_elements,
                "http://www.w3.org/2000/01/rdf-schema#label"
            )
            self.assertTrue(result)

    def test_climate_risk_property_filtering_rejects_properties(self):
        """Test that climate risk filter rejects property subjects"""
        mock_statement_elements = {
            'subject': self.climate_risk_property,
            'predicate': URIRef("http://www.w3.org/2000/01/rdf-schema#label"),
            'object': Literal("has characteristic")
        }
        
        with patch.dict(os.environ, {'ENABLE_CLIMATE_RISK_FILTERING': 'true'}):
            result = self.handler._filter_climate_risk_records(
                self.mock_record_data,
                mock_statement_elements,
                "http://www.w3.org/2000/01/rdf-schema#label"
            )
            self.assertFalse(result)

    def test_climate_risk_non_label_predicate_rejection(self):
        """Test that climate risk filter rejects non-label predicates"""
        mock_statement_elements = {
            'subject': self.climate_risk_concept,
            'predicate': URIRef("http://www.w3.org/2000/01/rdf-schema#comment"),
            'object': Literal("A restoration strategy")
        }
        
        with patch.dict(os.environ, {'ENABLE_CLIMATE_RISK_FILTERING': 'true'}):
            result = self.handler._filter_climate_risk_records(
                self.mock_record_data,
                mock_statement_elements,
                "http://www.w3.org/2000/01/rdf-schema#comment"
            )
            self.assertFalse(result)

    def test_should_index_record_orchestration_geonames(self):
        """Test that _should_index_record correctly routes to geonames filtering"""
        mock_statement_elements = {
            'subject': self.geonames_subject,
            'predicate': URIRef("http://www.geonames.org/ontology#name"),
            'object': Literal("Manila")
            # No graph - should route to geonames
        }
        
        with patch.dict(os.environ, {'ENABLE_GEONAMES_FILTERING': 'true'}):
            result = self.handler._should_index_record(
                self.mock_record_data,
                mock_statement_elements,
                "http://www.geonames.org/ontology#name"
            )
            self.assertTrue(result)

    def test_should_index_record_orchestration_climate_risk(self):
        """Test that _should_index_record correctly routes to climate risk filtering"""
        mock_statement_elements = {
            'subject': self.climate_risk_concept,
            'predicate': URIRef("http://www.w3.org/2000/01/rdf-schema#label"),
            'object': Literal("Mangrove Restoration"),
            'graph': URIRef("http://solve.global/knowledge-commons/climate-risk-ontology")
        }
        
        with patch.dict(os.environ, {'ENABLE_CLIMATE_RISK_FILTERING': 'true'}):
            result = self.handler._should_index_record(
                self.mock_record_data,
                mock_statement_elements,
                "http://www.w3.org/2000/01/rdf-schema#label"
            )
            self.assertTrue(result)

    def test_disabled_filtering_behavior(self):
        """Test behavior when filtering is disabled via feature flags"""
        mock_statement_elements = {
            'subject': self.climate_risk_concept,
            'predicate': URIRef("http://www.w3.org/2000/01/rdf-schema#label"),
            'object': Literal("Mangrove Restoration"),
            'graph': URIRef("http://solve.global/knowledge-commons/climate-risk-ontology")
        }
        
        # Test with climate risk filtering disabled
        with patch.dict(os.environ, {'ENABLE_CLIMATE_RISK_FILTERING': 'false'}):
            result = self.handler._filter_climate_risk_records(
                self.mock_record_data,
                mock_statement_elements,
                "http://www.w3.org/2000/01/rdf-schema#label"
            )
            self.assertFalse(result)
        
        # Test with geonames filtering disabled
        geonames_statement = {
            'subject': self.geonames_subject,
            'predicate': URIRef("http://www.geonames.org/ontology#name"),
            'object': Literal("Manila")
        }
        
        with patch.dict(os.environ, {'ENABLE_GEONAMES_FILTERING': 'false'}):
            result = self.handler._filter_geonames_records(
                self.mock_record_data,
                geonames_statement,
                "http://www.geonames.org/ontology#name"
            )
            self.assertFalse(result)

    def test_edge_case_property_patterns(self):
        """Test edge cases in property pattern detection"""
        edge_cases = [
            # Properties with compound names
            ("http://solve.global/knowledge-commons/climate-risk-ontology#hasLandCover", True),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#implementsAdaptationStrategy", True),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#directlyContributesTo", True),
            
            # Concepts that might look like properties but aren't
            ("http://solve.global/knowledge-commons/climate-risk-ontology#Capacity", False),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#Resilience", False),
            ("http://solve.global/knowledge-commons/climate-risk-ontology#Influence", False),
            
            # URIs without the climate risk namespace
            ("http://example.org/hasProperty", False),
            ("http://www.w3.org/2000/01/rdf-schema#hasValue", False),
        ]
        
        for uri, expected in edge_cases:
            with self.subTest(uri=uri):
                result = self.handler._is_climate_risk_property(uri)
                self.assertEqual(result, expected, f"Edge case failed for URI: {uri}")


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests for realistic filtering scenarios"""
    
    def setUp(self):
        self.handler = ElasticSearchSparqlHandler()
    
    def test_mixed_ontology_processing(self):
        """Test processing records from both ontologies"""
        # This would be an integration test that processes actual record streams
        # For now, we'll test the orchestration logic
        pass
    
    def test_performance_impact(self):
        """Test that new filtering doesn't significantly impact performance"""
        # This would measure processing time for large batches
        # For now, we'll ensure the logic is efficient
        pass


if __name__ == '__main__':
    # Set up test environment
    print("Running ontology filtering tests...")
    print("=" * 60)
    
    # Run the tests
    unittest.main(verbosity=2)
