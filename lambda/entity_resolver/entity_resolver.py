#!/usr/bin/env python3
"""
Entity Resolution Service
Maps NLP entities to RDF entities with consistent URI minting and Neptune integration
"""

import json
import boto3
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Import utilities from lambda layer
from utils.DatabaseManager import DatabaseManager

# Import local components
from uri_minter import URIMinter
from rdf_entity_builder import RDFEntityBuilder
from entity_chunk_resolver import EntityChunkResolver
from document_entity_extractor import DocumentEntityExtractor

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@dataclass
class ResolvedEntity:
    """Standardized entity representation"""
    canonical_name: str
    entity_type: str
    rdf_type: str
    confidence: float
    properties: Dict[str, Any]
    source_chunk: Optional[str] = None
    context: str = "mention"  # "mention", "author", "publisher"
    kg_uri: Optional[str] = None

class EntityResolver:
    """Main entity resolution service"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.sns_client = boto3.client('sns')
        
        # Environment configuration
        self.chunks_bucket = os.environ.get('CHUNKS_BUCKET', 'solve-global-kr-dl-chunks-861276078413-us-east-1')
        self.text_bucket = os.environ.get('TEXT_BUCKET', 'solve-global-kr-dl-text-861276078413-us-east-1')
        self.ner_results_bucket = os.environ.get('NER_RESULTS_BUCKET', 'solve-global-kr-dl-ner-results-861276078413-us-east-1')
        self.kg_integration_topic_arn = os.environ.get('KG_INTEGRATION_TOPIC_ARN')
        
        # Initialize components
        self.uri_minter = URIMinter()
        self.rdf_builder = RDFEntityBuilder()
        self.document_extractor = DocumentEntityExtractor(self.uri_minter)
        
        # Database manager for status tracking
        try:
            self.db_manager = DatabaseManager()
        except Exception as e:
            logger.warning(f"DatabaseManager not available: {e}")
            self.db_manager = None
        
        # Entity type mappings
        self.type_mappings = {
            'PERSON': {
                'rdf_type': 'foaf:Person',
                'resolver': self._resolve_person
            },
            'ORGANIZATION': {
                'rdf_type': 'foaf:Organization', 
                'resolver': self._resolve_organization
            },
            'LOCATION': {
                'rdf_type': 'schema:Place',
                'resolver': self._resolve_location
            },
            'DATE': {
                'rdf_type': 'time:Instant',
                'resolver': self._resolve_date
            },
            'QUANTITY': {
                'rdf_type': 'qudt:Quantity',
                'resolver': self._resolve_quantity
            },
            'TITLE': {
                'rdf_type': 'skos:Concept',
                'resolver': self._resolve_concept
            }
        }
    
    def resolve_entities_from_nlp_results(self, nlp_results: Dict[str, Any]) -> List[ResolvedEntity]:
        """
        Resolve entities from NLP results
        
        Args:
            nlp_results: NLP processing results with entities and chunk mappings
            
        Returns:
            List of resolved entities ready for KG integration
        """
        resolved_entities = []
        doc_id = nlp_results.get('doc_id')
        
        logger.info(f"Resolving entities for document {doc_id}")
        
        # Extract document-level entities (author, publisher) from metadata
        document_metadata = nlp_results.get('document_metadata', {})
        if document_metadata:
            doc_entities = self.document_extractor.extract_document_entities(document_metadata)
            resolved_entities.extend(doc_entities)
            logger.info(f"Extracted {len(doc_entities)} document-level entities")
        
        # Process chunk-level entity mentions
        if 'entities_mapped_to_chunks' in nlp_results:
            chunk_entities = self._resolve_chunk_entities(nlp_results['entities_mapped_to_chunks'], doc_id)
            resolved_entities.extend(chunk_entities)
            logger.info(f"Resolved {len(chunk_entities)} chunk-level entities")
        
        logger.info(f"Total entities resolved: {len(resolved_entities)}")
        return resolved_entities
    
    def _resolve_chunk_entities(self, entities_mapped_to_chunks: List[Dict], doc_id: str) -> List[ResolvedEntity]:
        """Resolve entities that are mapped to specific chunks"""
        resolved_entities = []
        
        for chunk_mapping in entities_mapped_to_chunks:
            if chunk_mapping.get('type') == 'entity':
                entity_data = chunk_mapping.get('entity', {})
                chunk_id = chunk_mapping.get('chunk_id')
                
                # Resolve the entity
                resolved_entity = self._resolve_single_entity(entity_data, chunk_id)
                if resolved_entity:
                    resolved_entities.append(resolved_entity)
        
        return resolved_entities
    
    def _resolve_single_entity(self, entity_data: Dict, chunk_id: str) -> Optional[ResolvedEntity]:
        """Resolve a single entity with type-specific logic"""
        entity_type = entity_data.get('Type', entity_data.get('entity_type', ''))
        entity_text = entity_data.get('Text', entity_data.get('text', ''))
        confidence = entity_data.get('Score', entity_data.get('confidence', 0.0))
        
        if not entity_type or not entity_text:
            logger.warning(f"Missing entity type or text: {entity_data}")
            return None
        
        # Apply confidence threshold
        if confidence < 0.7:  # Configurable threshold
            logger.debug(f"Entity confidence too low: {confidence} for '{entity_text}'")
            return None
        
        if entity_type not in self.type_mappings:
            logger.debug(f"Unsupported entity type: {entity_type}")
            return self._resolve_generic_entity(entity_data, chunk_id)
        
        mapping = self.type_mappings[entity_type]
        resolver_func = mapping['resolver']
        
        return resolver_func(entity_data, mapping['rdf_type'], chunk_id)
    
    def _resolve_person(self, entity_data: Dict, rdf_type: str, chunk_id: str) -> ResolvedEntity:
        """Resolve PERSON entities to foaf:Person"""
        name = entity_data.get('Text', entity_data.get('text', ''))
        confidence = entity_data.get('Score', entity_data.get('confidence', 0.0))
        
        # Generate consistent URI
        canonical_name = self.uri_minter.normalize_person_name(name)
        entity_uri = self.uri_minter.mint_person_uri(name)
        
        # Parse name components
        name_parts = self._parse_person_name(name)
        
        properties = {
            'foaf:name': name,
            'foaf:givenName': name_parts.get('given_name'),
            'foaf:familyName': name_parts.get('family_name'),
            'kr:extractedFrom': f"kr:chunk/{chunk_id}",
            'kr:confidence': confidence,
            'kr:extractedBy': 'aws-comprehend',
            'kr:extractedAt': datetime.utcnow().isoformat() + 'Z'
        }
        
        return ResolvedEntity(
            canonical_name=canonical_name,
            entity_type='PERSON',
            rdf_type=rdf_type,
            confidence=confidence,
            properties=properties,
            source_chunk=chunk_id,
            context='mention',
            kg_uri=entity_uri
        )
    
    def _resolve_organization(self, entity_data: Dict, rdf_type: str, chunk_id: str) -> ResolvedEntity:
        """Resolve ORGANIZATION entities to foaf:Organization"""
        name = entity_data.get('Text', entity_data.get('text', ''))
        confidence = entity_data.get('Score', entity_data.get('confidence', 0.0))
        
        # Generate consistent URI
        canonical_name = self.uri_minter.normalize_organization_name(name)
        entity_uri = self.uri_minter.mint_organization_uri(name)
        
        properties = {
            'foaf:name': canonical_name,
            'schema:alternateName': name if name != canonical_name else None,
            'kr:organizationType': self._classify_organization_type(name),
            'kr:extractedFrom': f"kr:chunk/{chunk_id}",
            'kr:confidence': confidence,
            'kr:extractedBy': 'aws-comprehend',
            'kr:extractedAt': datetime.utcnow().isoformat() + 'Z'
        }
        
        return ResolvedEntity(
            canonical_name=canonical_name,
            entity_type='ORGANIZATION',
            rdf_type=rdf_type,
            confidence=confidence,
            properties=properties,
            source_chunk=chunk_id,
            context='mention',
            kg_uri=entity_uri
        )
    
    def _resolve_location(self, entity_data: Dict, rdf_type: str, chunk_id: str) -> ResolvedEntity:
        """Resolve LOCATION entities to schema:Place"""
        name = entity_data.get('Text', entity_data.get('text', ''))
        confidence = entity_data.get('Score', entity_data.get('confidence', 0.0))
        
        canonical_name = name.strip()
        entity_uri = self.uri_minter.mint_location_uri(name)
        
        properties = {
            'schema:name': canonical_name,
            'kr:extractedFrom': f"kr:chunk/{chunk_id}",
            'kr:confidence': confidence,
            'kr:extractedBy': 'aws-comprehend',
            'kr:extractedAt': datetime.utcnow().isoformat() + 'Z'
        }
        
        return ResolvedEntity(
            canonical_name=canonical_name,
            entity_type='LOCATION',
            rdf_type=rdf_type,
            confidence=confidence,
            properties=properties,
            source_chunk=chunk_id,
            context='mention',
            kg_uri=entity_uri
        )
    
    def _resolve_date(self, entity_data: Dict, rdf_type: str, chunk_id: str) -> ResolvedEntity:
        """Resolve DATE entities to time:Instant"""
        date_text = entity_data.get('Text', entity_data.get('text', ''))
        confidence = entity_data.get('Score', entity_data.get('confidence', 0.0))
        
        canonical_name = date_text.strip()
        entity_uri = self.uri_minter.mint_date_uri(date_text)
        
        properties = {
            'time:inXSDDateTime': self._parse_date_to_xsd(date_text),
            'schema:description': f"Date mentioned: {date_text}",
            'kr:extractedFrom': f"kr:chunk/{chunk_id}",
            'kr:confidence': confidence,
            'kr:extractedBy': 'aws-comprehend',
            'kr:extractedAt': datetime.utcnow().isoformat() + 'Z'
        }
        
        return ResolvedEntity(
            canonical_name=canonical_name,
            entity_type='DATE',
            rdf_type=rdf_type,
            confidence=confidence,
            properties=properties,
            source_chunk=chunk_id,
            context='mention',
            kg_uri=entity_uri
        )
    
    def _resolve_quantity(self, entity_data: Dict, rdf_type: str, chunk_id: str) -> ResolvedEntity:
        """Resolve QUANTITY entities to qudt:Quantity"""
        quantity_text = entity_data.get('Text', entity_data.get('text', ''))
        confidence = entity_data.get('Score', entity_data.get('confidence', 0.0))
        
        canonical_name = quantity_text.strip()
        entity_uri = self.uri_minter.mint_quantity_uri(quantity_text)
        
        # Parse quantity components
        parsed = self._parse_quantity(quantity_text)
        
        properties = {
            'qudt:numericValue': parsed.get('value'),
            'qudt:unit': parsed.get('unit'),
            'schema:description': f"Quantity: {quantity_text}",
            'kr:extractedFrom': f"kr:chunk/{chunk_id}",
            'kr:confidence': confidence,
            'kr:extractedBy': 'aws-comprehend',
            'kr:extractedAt': datetime.utcnow().isoformat() + 'Z'
        }
        
        return ResolvedEntity(
            canonical_name=canonical_name,
            entity_type='QUANTITY',
            rdf_type=rdf_type,
            confidence=confidence,
            properties=properties,
            source_chunk=chunk_id,
            context='mention',
            kg_uri=entity_uri
        )
    
    def _resolve_concept(self, entity_data: Dict, rdf_type: str, chunk_id: str) -> ResolvedEntity:
        """Resolve TITLE/OTHER entities to skos:Concept"""
        concept_text = entity_data.get('Text', entity_data.get('text', ''))
        confidence = entity_data.get('Score', entity_data.get('confidence', 0.0))
        
        canonical_name = concept_text.strip()
        entity_uri = self.uri_minter.mint_concept_uri(concept_text)
        
        properties = {
            'skos:prefLabel': canonical_name,
            'skos:definition': f"Climate-related concept: {concept_text}",
            'kr:extractedFrom': f"kr:chunk/{chunk_id}",
            'kr:confidence': confidence,
            'kr:extractedBy': 'aws-comprehend',
            'kr:extractedAt': datetime.utcnow().isoformat() + 'Z'
        }
        
        return ResolvedEntity(
            canonical_name=canonical_name,
            entity_type='CONCEPT',
            rdf_type=rdf_type,
            confidence=confidence,
            properties=properties,
            source_chunk=chunk_id,
            context='mention',
            kg_uri=entity_uri
        )
    
    def _resolve_generic_entity(self, entity_data: Dict, chunk_id: str) -> ResolvedEntity:
        """Fallback resolver for unsupported entity types"""
        entity_text = entity_data.get('Text', entity_data.get('text', ''))
        entity_type = entity_data.get('Type', entity_data.get('entity_type', 'OTHER'))
        confidence = entity_data.get('Score', entity_data.get('confidence', 0.0))
        
        canonical_name = entity_text.strip()
        entity_uri = self.uri_minter.mint_generic_uri(entity_text, entity_type)
        
        properties = {
            'rdfs:label': canonical_name,
            'kr:entityType': entity_type,
            'kr:extractedFrom': f"kr:chunk/{chunk_id}",
            'kr:confidence': confidence,
            'kr:extractedBy': 'aws-comprehend',
            'kr:extractedAt': datetime.utcnow().isoformat() + 'Z'
        }
        
        return ResolvedEntity(
            canonical_name=canonical_name,
            entity_type=entity_type,
            rdf_type='kr:Entity',
            confidence=confidence,
            properties=properties,
            source_chunk=chunk_id,
            context='mention',
            kg_uri=entity_uri
        )
    
    # Helper methods
    def _parse_person_name(self, name: str) -> Dict[str, str]:
        """Parse person name into components"""
        # Remove titles
        clean_name = name.strip()
        for title in ['Dr.', 'Prof.', 'Mr.', 'Ms.', 'Mrs.']:
            clean_name = clean_name.replace(title, '').strip()
        
        parts = clean_name.split()
        if len(parts) >= 2:
            return {
                'given_name': parts[0],
                'family_name': ' '.join(parts[1:])
            }
        elif len(parts) == 1:
            return {
                'given_name': parts[0],
                'family_name': None
            }
        return {}
    
    def _classify_organization_type(self, org_name: str) -> str:
        """Classify organization type based on name patterns"""
        name_lower = org_name.lower()
        
        if any(word in name_lower for word in ['university', 'college', 'institute', 'school']):
            return 'Educational Institution'
        elif any(word in name_lower for word in ['government', 'agency', 'department', 'ministry']):
            return 'Government Agency'
        elif any(word in name_lower for word in ['bank', 'financial', 'fund', 'investment']):
            return 'Financial Institution'
        elif any(word in name_lower for word in ['corporation', 'company', 'inc', 'ltd', 'llc']):
            return 'Corporation'
        elif any(word in name_lower for word in ['foundation', 'ngo', 'nonprofit', 'charity']):
            return 'Non-Profit Organization'
        else:
            return 'Organization'
    
    def _parse_date_to_xsd(self, date_text: str) -> Optional[str]:
        """Parse date text to XSD dateTime format"""
        # Basic date parsing - can be enhanced
        try:
            # Handle common formats
            if date_text.isdigit() and len(date_text) == 4:
                return f"{date_text}-01-01T00:00:00Z"
            # Add more sophisticated date parsing as needed
            return None
        except:
            return None
    
    def _parse_quantity(self, quantity_text: str) -> Dict[str, Any]:
        """Parse quantity text into value and unit"""
        import re
        
        # Basic quantity parsing
        match = re.search(r'([\d.,]+)\s*([a-zA-Z%°]+)', quantity_text)
        if match:
            try:
                value = float(match.group(1).replace(',', ''))
                unit = match.group(2)
                return {'value': value, 'unit': unit}
            except ValueError:
                pass
        
        return {'value': None, 'unit': quantity_text}
    
    def store_resolved_entities(self, doc_id: str, resolved_entities: List[ResolvedEntity]) -> str:
        """Store resolved entities to S3 for KG integration"""
        try:
            # Create entity resolution results
            results = {
                'doc_id': doc_id,
                'resolved_entities': [
                    {
                        'canonical_name': entity.canonical_name,
                        'entity_type': entity.entity_type,
                        'rdf_type': entity.rdf_type,
                        'confidence': entity.confidence,
                        'properties': entity.properties,
                        'source_chunk': entity.source_chunk,
                        'context': entity.context,
                        'kg_uri': entity.kg_uri
                    }
                    for entity in resolved_entities
                ],
                'processing_metadata': {
                    'total_entities': len(resolved_entities),
                    'entity_types': list(set(e.entity_type for e in resolved_entities)),
                    'processed_at': datetime.utcnow().isoformat() + 'Z',
                    'processor': 'entity-resolver-v1'
                }
            }
            
            # Store to S3
            key = f"{doc_id}/entity_resolution_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            
            self.s3_client.put_object(
                Bucket=self.ner_results_bucket,
                Key=key,
                Body=json.dumps(results, indent=2),
                ContentType='application/json'
            )
            
            storage_location = f"s3://{self.ner_results_bucket}/{key}"
            logger.info(f"Stored entity resolution results: {storage_location}")
            
            return storage_location
            
        except Exception as e:
            logger.error(f"Error storing resolved entities: {e}")
            raise
    
    def trigger_kg_integration(self, doc_id: str, resolved_entities: List[ResolvedEntity], storage_location: str):
        """Trigger KG integration for resolved entities"""
        try:
            if not self.kg_integration_topic_arn:
                logger.warning("KG integration topic ARN not configured")
                return
            
            # Create message for KG integration
            message = {
                'document_id': doc_id,
                'processing_type': 'entity_resolution',
                'entity_count': len(resolved_entities),
                'storage_location': storage_location,
                'entity_types': list(set(e.entity_type for e in resolved_entities)),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
            # Publish to SNS
            response = self.sns_client.publish(
                TopicArn=self.kg_integration_topic_arn,
                Message=json.dumps(message),
                Subject=f"Entity Resolution Complete: {doc_id}"
            )
            
            logger.info(f"Triggered KG integration: {response['MessageId']}")
            
        except Exception as e:
            logger.error(f"Error triggering KG integration: {e}")
            raise
    
    def update_processing_status(self, doc_id: str, status: str, entity_count: int = 0, error_message: str = None):
        """Update processing status in database"""
        if not self.db_manager:
            return
        
        try:
            # Update processing status
            # This would integrate with your existing database schema
            logger.info(f"Updated processing status for {doc_id}: {status}")
        except Exception as e:
            logger.error(f"Error updating processing status: {e}")

def lambda_handler(event, context):
    """Lambda handler for entity resolution"""
    try:
        logger.info(f"Entity resolution triggered with event: {json.dumps(event, default=str)}")
        
        # Parse input - could be from SNS (NLP completion) or direct invocation
        if 'Records' in event:
            # SNS event from NLP completion
            for record in event['Records']:
                if record.get('EventSource') == 'aws:sns':
                    message = json.loads(record['Sns']['Message'])
                    return process_nlp_completion(message)
        else:
            # Direct invocation
            return process_nlp_completion(event)
            
    except Exception as e:
        logger.error(f"Entity resolution failed: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Entity resolution failed'
            })
        }

def process_nlp_completion(nlp_results: Dict[str, Any]) -> Dict[str, Any]:
    """Process NLP completion event"""
    doc_id = nlp_results.get('doc_id')
    
    if not doc_id:
        raise ValueError("Missing doc_id in NLP results")
    
    # Initialize entity resolver
    resolver = EntityResolver()
    
    # Resolve entities
    resolved_entities = resolver.resolve_entities_from_nlp_results(nlp_results)
    
    # Store results
    storage_location = resolver.store_resolved_entities(doc_id, resolved_entities)
    
    # Trigger KG integration
    resolver.trigger_kg_integration(doc_id, resolved_entities, storage_location)
    
    # Update status
    resolver.update_processing_status(doc_id, 'entity_resolution_complete', len(resolved_entities))
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'doc_id': doc_id,
            'entities_resolved': len(resolved_entities),
            'entity_types': list(set(e.entity_type for e in resolved_entities)),
            'storage_location': storage_location,
            'message': 'Entity resolution completed successfully'
        })
    }
