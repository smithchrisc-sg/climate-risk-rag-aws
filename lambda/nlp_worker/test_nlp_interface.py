#!/usr/bin/env python3
"""
Unit tests for NLP interface architecture
Tests the pluggable provider system and core functionality
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime

# Import components to test
from nlp_interface import NLPProvider, NLPProcessorFactory, NLPProcessor, CostTracker
from comprehend_provider import ComprehendProvider
from offset_mapper import OffsetMapper

class MockNLPProvider(NLPProvider):
    """Mock NLP provider for testing"""
    
    def detect_entities(self, text):
        return [
            {
                'text': 'climate change',
                'type': 'EVENT',
                'confidence': 0.95,
                'begin_offset': 10,
                'end_offset': 24
            }
        ]
    
    def extract_key_phrases(self, text):
        return [
            {
                'text': 'global warming',
                'confidence': 0.88,
                'begin_offset': 30,
                'end_offset': 44
            }
        ]
    
    def get_provider_name(self):
        return "mock"
    
    def estimate_cost(self, text):
        return len(text) * 0.0001
    
    def get_text_limits(self):
        return {
            'max_text_length': 5000,
            'recommended_chunk_size': 4500
        }

class TestNLPInterface(unittest.TestCase):
    """Test NLP interface and factory"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_provider = MockNLPProvider()
        self.test_text = "This is a test document about climate change and global warming effects."
    
    def test_nlp_provider_interface(self):
        """Test that mock provider implements interface correctly"""
        
        # Test entity detection
        entities = self.mock_provider.detect_entities(self.test_text)
        self.assertIsInstance(entities, list)
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0]['text'], 'climate change')
        self.assertEqual(entities[0]['type'], 'EVENT')
        
        # Test key phrase extraction
        phrases = self.mock_provider.extract_key_phrases(self.test_text)
        self.assertIsInstance(phrases, list)
        self.assertEqual(len(phrases), 1)
        self.assertEqual(phrases[0]['text'], 'global warming')
        
        # Test provider name
        self.assertEqual(self.mock_provider.get_provider_name(), 'mock')
        
        # Test cost estimation
        cost = self.mock_provider.estimate_cost(self.test_text)
        self.assertGreater(cost, 0)
        
        # Test text limits
        limits = self.mock_provider.get_text_limits()
        self.assertIn('max_text_length', limits)
        self.assertIn('recommended_chunk_size', limits)
    
    def test_nlp_processor_factory(self):
        """Test NLP processor factory"""
        
        # Register mock provider
        NLPProcessorFactory.register_provider('mock', MockNLPProvider)
        
        # Test provider creation
        processor = NLPProcessorFactory.create_processor('mock')
        self.assertIsInstance(processor, NLPProcessor)
        self.assertEqual(processor.provider.get_provider_name(), 'mock')
        
        # Test unknown provider
        with self.assertRaises(ValueError):
            NLPProcessorFactory.create_processor('unknown')
        
        # Test list available providers
        providers = NLPProcessorFactory.list_available_providers()
        self.assertIn('mock', providers)
    
    def test_nlp_processor(self):
        """Test NLP processor functionality"""
        
        processor = NLPProcessor(self.mock_provider)
        
        # Test document processing
        results = processor.process_document('test_doc', self.test_text)
        
        self.assertEqual(results['doc_id'], 'test_doc')
        self.assertEqual(results['provider'], 'mock')
        self.assertIn('entities', results)
        self.assertIn('key_phrases', results)
        self.assertIn('processing_cost', results)
        self.assertIn('processed_at', results)
        self.assertIn('text_length', results)
        
        # Verify entities and phrases
        self.assertEqual(len(results['entities']), 1)
        self.assertEqual(len(results['key_phrases']), 1)
        self.assertEqual(results['text_length'], len(self.test_text))
        
        # Test cost tracking
        cost_summary = processor.get_cost_summary()
        self.assertIn('total_cost', cost_summary)
        self.assertIn('processing_count', cost_summary)
        self.assertEqual(cost_summary['provider'], 'mock')
    
    def test_cost_tracker(self):
        """Test cost tracking functionality"""
        
        tracker = CostTracker('test_provider')
        
        # Test initial state
        self.assertEqual(tracker.get_total_cost(), 0.0)
        
        # Add processing costs
        tracker.add_processing_cost(1000, 0.10)
        tracker.add_processing_cost(2000, 0.20)
        
        # Test total cost
        self.assertEqual(tracker.get_total_cost(), 0.30)
        
        # Test cost summary
        summary = tracker.get_cost_summary()
        self.assertEqual(summary['total_cost'], 0.30)
        self.assertEqual(summary['processing_count'], 2)
        self.assertEqual(summary['total_characters'], 3000)
        self.assertEqual(summary['provider'], 'test_provider')

class TestComprehendProvider(unittest.TestCase):
    """Test Amazon Comprehend provider"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_text = "Amazon Web Services provides cloud computing services."
    
    @patch('boto3.client')
    def test_comprehend_provider_initialization(self, mock_boto3):
        """Test Comprehend provider initialization"""
        
        mock_client = Mock()
        mock_boto3.return_value = mock_client
        
        provider = ComprehendProvider()
        
        self.assertEqual(provider.get_provider_name(), 'comprehend')
        mock_boto3.assert_called_with('comprehend', region_name='us-east-1')
    
    @patch('boto3.client')
    def test_detect_entities(self, mock_boto3):
        """Test entity detection with Comprehend"""
        
        mock_client = Mock()
        mock_boto3.return_value = mock_client
        
        # Mock Comprehend response
        mock_client.detect_entities.return_value = {
            'Entities': [
                {
                    'Text': 'Amazon Web Services',
                    'Type': 'ORGANIZATION',
                    'Score': 0.95,
                    'BeginOffset': 0,
                    'EndOffset': 19
                }
            ]
        }
        
        provider = ComprehendProvider()
        entities = provider.detect_entities(self.test_text)
        
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0]['text'], 'Amazon Web Services')
        self.assertEqual(entities[0]['type'], 'ORGANIZATION')
        self.assertEqual(entities[0]['confidence'], 0.95)
        self.assertEqual(entities[0]['begin_offset'], 0)
        self.assertEqual(entities[0]['end_offset'], 19)
    
    @patch('boto3.client')
    def test_extract_key_phrases(self, mock_boto3):
        """Test key phrase extraction with Comprehend"""
        
        mock_client = Mock()
        mock_boto3.return_value = mock_client
        
        # Mock Comprehend response
        mock_client.detect_key_phrases.return_value = {
            'KeyPhrases': [
                {
                    'Text': 'cloud computing services',
                    'Score': 0.88,
                    'BeginOffset': 29,
                    'EndOffset': 53
                }
            ]
        }
        
        provider = ComprehendProvider()
        phrases = provider.extract_key_phrases(self.test_text)
        
        self.assertEqual(len(phrases), 1)
        self.assertEqual(phrases[0]['text'], 'cloud computing services')
        self.assertEqual(phrases[0]['confidence'], 0.88)
        self.assertEqual(phrases[0]['begin_offset'], 29)
        self.assertEqual(phrases[0]['end_offset'], 53)
    
    def test_cost_estimation(self):
        """Test cost estimation for Comprehend"""
        
        provider = ComprehendProvider()
        
        # Test cost for 1000 characters
        cost = provider.estimate_cost('a' * 1000)
        expected_cost = (1000 / 100) * (0.0001 + 0.0001)  # Entity + Key phrases
        self.assertAlmostEqual(cost, expected_cost, places=6)
        
        # Test cost for empty text
        cost = provider.estimate_cost('')
        self.assertEqual(cost, 0.0)
    
    def test_text_limits(self):
        """Test text processing limits"""
        
        provider = ComprehendProvider()
        limits = provider.get_text_limits()
        
        self.assertEqual(limits['max_text_length'], 5000)
        self.assertEqual(limits['recommended_chunk_size'], 4500)

class TestOffsetMapper(unittest.TestCase):
    """Test offset mapping functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.full_text = "Climate change is a major global issue. Rising temperatures affect ecosystems worldwide."
        self.chunks = [
            {
                'chunk_id': 'chunk_001',
                'chunk_index': 0,
                'text': 'Climate change is a major global issue.'
            },
            {
                'chunk_id': 'chunk_002', 
                'chunk_index': 1,
                'text': 'Rising temperatures affect ecosystems worldwide.'
            }
        ]
        
        self.nlp_results = {
            'doc_id': 'test_doc',
            'provider': 'test',
            'processed_at': datetime.now().isoformat(),
            'processing_cost': 0.01,
            'entities': [
                {
                    'text': 'Climate change',
                    'type': 'EVENT',
                    'confidence': 0.95,
                    'begin_offset': 0,
                    'end_offset': 14
                }
            ],
            'key_phrases': [
                {
                    'text': 'global issue',
                    'confidence': 0.88,
                    'begin_offset': 27,
                    'end_offset': 39
                }
            ]
        }
    
    def test_offset_mapper_initialization(self):
        """Test offset mapper initialization"""
        
        mapper = OffsetMapper(self.full_text, self.chunks)
        
        self.assertEqual(len(mapper.chunk_offsets), 2)
        self.assertEqual(mapper.chunk_offsets[0]['chunk_id'], 'chunk_001')
        self.assertEqual(mapper.chunk_offsets[0]['start_offset'], 0)
        self.assertEqual(mapper.chunk_offsets[0]['end_offset'], 39)
    
    def test_chunk_mapping(self):
        """Test mapping NLP results to chunks"""
        
        mapper = OffsetMapper(self.full_text, self.chunks)
        mapped_results = mapper.map_to_chunks(self.nlp_results)
        
        self.assertEqual(mapped_results['doc_id'], 'test_doc')
        self.assertIn('chunk_mappings', mapped_results)
        self.assertIn('mapping_statistics', mapped_results)
        
        # Check that entities and phrases were mapped
        chunk_mappings = mapped_results['chunk_mappings']
        self.assertGreater(len(chunk_mappings), 0)
        
        # Find entity mapping
        entity_mapping = next((m for m in chunk_mappings if m['type'] == 'entity'), None)
        self.assertIsNotNone(entity_mapping)
        self.assertEqual(entity_mapping['text'], 'Climate change')
        self.assertEqual(entity_mapping['chunk_id'], 'chunk_001')
    
    def test_mapping_quality_report(self):
        """Test mapping quality reporting"""
        
        mapper = OffsetMapper(self.full_text, self.chunks)
        report = mapper.get_mapping_quality_report()
        
        self.assertIn('total_chunks', report)
        self.assertIn('mapped_chunks', report)
        self.assertIn('mapping_success_rate', report)
        self.assertIn('document_length', report)
        
        self.assertEqual(report['total_chunks'], 2)
        self.assertEqual(report['document_length'], len(self.full_text))

if __name__ == '__main__':
    # Set up logging for tests
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    unittest.main(verbosity=2)
