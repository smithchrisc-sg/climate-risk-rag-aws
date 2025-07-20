"""
Amazon Comprehend Provider - Implementation of NLP interface for AWS Comprehend
Handles entity detection and key phrase extraction with cost optimization
"""
import boto3
from typing import List, Dict, Any
from nlp_interface import NLPProvider
import logging
import time

logger = logging.getLogger(__name__)

class ComprehendProvider(NLPProvider):
    """Amazon Comprehend implementation of NLP provider"""
    
    # Comprehend pricing (as of 2025)
    ENTITY_DETECTION_COST_PER_UNIT = 0.0001  # $0.0001 per unit (100 characters)
    KEY_PHRASES_COST_PER_UNIT = 0.0001       # $0.0001 per unit (100 characters)
    
    # Comprehend limits
    MAX_TEXT_LENGTH = 5000  # 5000 characters per request
    RECOMMENDED_CHUNK_SIZE = 4500  # Leave buffer for word boundaries
    
    def __init__(self, region_name: str = 'us-east-1'):
        """Initialize Comprehend client"""
        self.comprehend = boto3.client('comprehend', region_name=region_name)
        self.region_name = region_name
        logger.info(f"Initialized Comprehend provider in region {region_name}")
    
    def detect_entities(self, text: str) -> List[Dict[str, Any]]:
        """Detect entities using Amazon Comprehend"""
        
        if not text or not text.strip():
            return []
        
        # Handle text length limits
        if len(text) > self.MAX_TEXT_LENGTH:
            logger.info(f"Text length {len(text)} exceeds Comprehend limit, processing in chunks")
            return self._process_long_text_entities(text)
        
        try:
            response = self.comprehend.detect_entities(
                Text=text,
                LanguageCode='en'
            )
            
            entities = []
            for entity in response['Entities']:
                entities.append({
                    'text': entity['Text'],
                    'type': entity['Type'],
                    'confidence': entity['Score'],
                    'begin_offset': entity['BeginOffset'],
                    'end_offset': entity['EndOffset']
                })
            
            logger.debug(f"Detected {len(entities)} entities in text of length {len(text)}")
            return entities
            
        except Exception as e:
            logger.error(f"Error in Comprehend entity detection: {str(e)}")
            raise
    
    def extract_key_phrases(self, text: str) -> List[Dict[str, Any]]:
        """Extract key phrases using Amazon Comprehend"""
        
        if not text or not text.strip():
            return []
        
        # Handle text length limits
        if len(text) > self.MAX_TEXT_LENGTH:
            logger.info(f"Text length {len(text)} exceeds Comprehend limit, processing in chunks")
            return self._process_long_text_phrases(text)
        
        try:
            response = self.comprehend.detect_key_phrases(
                Text=text,
                LanguageCode='en'
            )
            
            phrases = []
            for phrase in response['KeyPhrases']:
                phrases.append({
                    'text': phrase['Text'],
                    'confidence': phrase['Score'],
                    'begin_offset': phrase['BeginOffset'],
                    'end_offset': phrase['EndOffset']
                })
            
            logger.debug(f"Extracted {len(phrases)} key phrases in text of length {len(text)}")
            return phrases
            
        except Exception as e:
            logger.error(f"Error in Comprehend key phrase extraction: {str(e)}")
            raise
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return "comprehend"
    
    def estimate_cost(self, text: str) -> float:
        """Estimate processing cost for given text"""
        if not text:
            return 0.0
        
        # Calculate units (100 characters per unit)
        units = max(1, len(text) / 100)
        
        # Cost for both entity detection and key phrase extraction
        entity_cost = units * self.ENTITY_DETECTION_COST_PER_UNIT
        phrases_cost = units * self.KEY_PHRASES_COST_PER_UNIT
        
        total_cost = entity_cost + phrases_cost
        
        logger.debug(f"Estimated cost for {len(text)} characters: ${total_cost:.6f}")
        return total_cost
    
    def get_text_limits(self) -> Dict[str, int]:
        """Return text processing limits for Comprehend"""
        return {
            'max_text_length': self.MAX_TEXT_LENGTH,
            'recommended_chunk_size': self.RECOMMENDED_CHUNK_SIZE
        }
    
    def _process_long_text_entities(self, text: str) -> List[Dict[str, Any]]:
        """Process long text by splitting while maintaining global offsets"""
        entities = []
        
        for chunk_start, chunk_text in self._split_text_with_offsets(text):
            try:
                # Add small delay to avoid rate limiting
                time.sleep(0.1)
                
                chunk_entities = self.detect_entities(chunk_text)
                
                # Adjust offsets to global document positions
                for entity in chunk_entities:
                    entity['begin_offset'] += chunk_start
                    entity['end_offset'] += chunk_start
                    entities.append(entity)
                    
            except Exception as e:
                logger.error(f"Error processing text chunk at offset {chunk_start}: {str(e)}")
                # Continue processing other chunks
                continue
        
        logger.info(f"Processed long text ({len(text)} chars) in chunks, found {len(entities)} entities")
        return entities
    
    def _process_long_text_phrases(self, text: str) -> List[Dict[str, Any]]:
        """Process long text for key phrases while maintaining global offsets"""
        phrases = []
        
        for chunk_start, chunk_text in self._split_text_with_offsets(text):
            try:
                # Add small delay to avoid rate limiting
                time.sleep(0.1)
                
                chunk_phrases = self.extract_key_phrases(chunk_text)
                
                # Adjust offsets to global document positions
                for phrase in chunk_phrases:
                    phrase['begin_offset'] += chunk_start
                    phrase['end_offset'] += chunk_start
                    phrases.append(phrase)
                    
            except Exception as e:
                logger.error(f"Error processing text chunk at offset {chunk_start}: {str(e)}")
                # Continue processing other chunks
                continue
        
        logger.info(f"Processed long text ({len(text)} chars) in chunks, found {len(phrases)} key phrases")
        return phrases
    
    def _split_text_with_offsets(self, text: str):
        """Split text into chunks while preserving word boundaries and tracking offsets"""
        chunk_size = self.RECOMMENDED_CHUNK_SIZE
        current_pos = 0
        
        while current_pos < len(text):
            # Calculate end position
            end_pos = min(current_pos + chunk_size, len(text))
            
            # If not at end of text, find word boundary
            if end_pos < len(text):
                # Look backwards for space to avoid cutting words
                while end_pos > current_pos and text[end_pos] not in [' ', '\n', '\t', '.', '!', '?']:
                    end_pos -= 1
                
                # If no word boundary found, use original end position
                if end_pos == current_pos:
                    end_pos = current_pos + chunk_size
            
            chunk_text = text[current_pos:end_pos].strip()
            
            if chunk_text:  # Only yield non-empty chunks
                yield current_pos, chunk_text
            
            current_pos = end_pos
            
            # Skip whitespace at the beginning of next chunk
            while current_pos < len(text) and text[current_pos] in [' ', '\n', '\t']:
                current_pos += 1
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get Comprehend service information"""
        return {
            'service': 'Amazon Comprehend',
            'region': self.region_name,
            'max_text_length': self.MAX_TEXT_LENGTH,
            'entity_detection_cost_per_unit': self.ENTITY_DETECTION_COST_PER_UNIT,
            'key_phrases_cost_per_unit': self.KEY_PHRASES_COST_PER_UNIT,
            'supported_languages': ['en'],  # Currently only English
            'features': ['entity_detection', 'key_phrase_extraction']
        }
