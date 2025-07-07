"""
S3 Data Lake Manager - Manages NLP results storage in structured S3 data lake
Implements S3-first architecture with no content duplication in database
"""
import boto3
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class S3DataLakeManager:
    """Manages NLP results in S3 Data Lake with structured organization"""
    
    def __init__(self, bucket_name: Optional[str] = None):
        """Initialize S3 data lake manager"""
        self.s3_client = boto3.client('s3')
        self.bucket_name = bucket_name or os.environ.get(
            'NER_RESULTS_BUCKET', 
            'solve-global-kr-ner-results-861276078413-us-east-1'
        )
        
        logger.info(f"Initialized S3 Data Lake Manager for bucket: {self.bucket_name}")
    
    def store_complete_nlp_results(self, doc_id: str, mapped_results: Dict[str, Any]) -> str:
        """
        Store complete NLP results in structured S3 data lake
        
        Returns:
            S3 key of the primary complete results file
        """
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_prefix = f"{doc_id}/"
        
        try:
            # 1. Store complete results with all offset mappings
            complete_data = self._prepare_complete_results(mapped_results, timestamp)
            complete_key = f"{base_prefix}nlp_complete_{timestamp}.json"
            self._store_json_file(complete_key, complete_data)
            
            # 2. Store entities separately for easy querying
            entities_data = self._prepare_entities_data(mapped_results, timestamp)
            entities_key = f"{base_prefix}entities_{timestamp}.json"
            self._store_json_file(entities_key, entities_data)
            
            # 3. Store key phrases separately
            phrases_data = self._prepare_phrases_data(mapped_results, timestamp)
            phrases_key = f"{base_prefix}key_phrases_{timestamp}.json"
            self._store_json_file(phrases_key, phrases_data)
            
            # 4. Store detailed offset mappings for Knowledge Graph construction
            offset_data = self._prepare_offset_mappings(mapped_results, timestamp)
            offset_key = f"{base_prefix}offset_mappings_{timestamp}.json"
            self._store_json_file(offset_key, offset_data)
            
            # 5. Store processing metadata
            metadata = self._prepare_processing_metadata(mapped_results, timestamp, {
                'complete_results': complete_key,
                'entities': entities_key,
                'key_phrases': phrases_key,
                'offset_mappings': offset_key
            })
            metadata_key = f"{base_prefix}processing_metadata_{timestamp}.json"
            self._store_json_file(metadata_key, metadata)
            
            logger.info(f"Successfully stored NLP results for {doc_id} in S3 data lake")
            return complete_key  # Return primary file location for database reference
            
        except Exception as e:
            logger.error(f"Error storing NLP results for {doc_id}: {str(e)}")
            raise
    
    def _prepare_complete_results(self, mapped_results: Dict[str, Any], timestamp: str) -> Dict[str, Any]:
        """Prepare complete results data structure"""
        
        # Calculate summary statistics
        entities = [m for m in mapped_results['chunk_mappings'] if m['type'] == 'entity']
        key_phrases = [m for m in mapped_results['chunk_mappings'] if m['type'] == 'key_phrase']
        
        entity_types = {}
        for entity in entities:
            entity_type = entity['entity_type']
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        
        chunks_with_entities = len(set([m['chunk_id'] for m in mapped_results['chunk_mappings']]))
        
        return {
            'doc_id': mapped_results['doc_id'],
            'provider': mapped_results['provider'],
            'processed_at': mapped_results['processed_at'],
            'processing_cost': mapped_results['processing_cost'],
            'processing_duration': mapped_results.get('processing_duration', 0.0),
            'text_length': mapped_results.get('text_length', 0),
            'chunk_mappings': mapped_results['chunk_mappings'],
            'mapping_statistics': mapped_results.get('mapping_statistics', {}),
            'summary': {
                'total_entities': len(entities),
                'total_key_phrases': len(key_phrases),
                'entity_types': entity_types,
                'chunks_with_nlp_results': chunks_with_entities,
                'avg_confidence_entities': self._calculate_avg_confidence(entities),
                'avg_confidence_phrases': self._calculate_avg_confidence(key_phrases)
            },
            'storage_metadata': {
                'stored_at': datetime.now().isoformat(),
                'storage_timestamp': timestamp,
                'bucket': self.bucket_name,
                'data_lake_version': '1.0'
            }
        }
    
    def _prepare_entities_data(self, mapped_results: Dict[str, Any], timestamp: str) -> Dict[str, Any]:
        """Prepare entities-only data structure"""
        
        entities = [m for m in mapped_results['chunk_mappings'] if m['type'] == 'entity']
        
        # Calculate entity statistics
        entity_types = {}
        confidence_distribution = {'high': 0, 'medium': 0, 'low': 0}
        
        for entity in entities:
            # Count by type
            entity_type = entity['entity_type']
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
            
            # Confidence distribution
            confidence = entity['confidence']
            if confidence >= 0.8:
                confidence_distribution['high'] += 1
            elif confidence >= 0.5:
                confidence_distribution['medium'] += 1
            else:
                confidence_distribution['low'] += 1
        
        return {
            'doc_id': mapped_results['doc_id'],
            'provider': mapped_results['provider'],
            'processed_at': mapped_results['processed_at'],
            'entities': entities,
            'entity_summary': {
                'total_count': len(entities),
                'types': entity_types,
                'confidence_distribution': confidence_distribution,
                'avg_confidence': self._calculate_avg_confidence(entities)
            },
            'storage_metadata': {
                'stored_at': datetime.now().isoformat(),
                'storage_timestamp': timestamp,
                'data_type': 'entities_only'
            }
        }
    
    def _prepare_phrases_data(self, mapped_results: Dict[str, Any], timestamp: str) -> Dict[str, Any]:
        """Prepare key phrases-only data structure"""
        
        key_phrases = [m for m in mapped_results['chunk_mappings'] if m['type'] == 'key_phrase']
        
        # Calculate phrase statistics
        chunks_covered = len(set([p['chunk_id'] for p in key_phrases]))
        avg_confidence = self._calculate_avg_confidence(key_phrases)
        
        return {
            'doc_id': mapped_results['doc_id'],
            'provider': mapped_results['provider'],
            'processed_at': mapped_results['processed_at'],
            'key_phrases': key_phrases,
            'phrase_summary': {
                'total_count': len(key_phrases),
                'avg_confidence': avg_confidence,
                'chunks_covered': chunks_covered,
                'phrases_per_chunk': len(key_phrases) / chunks_covered if chunks_covered > 0 else 0
            },
            'storage_metadata': {
                'stored_at': datetime.now().isoformat(),
                'storage_timestamp': timestamp,
                'data_type': 'key_phrases_only'
            }
        }
    
    def _prepare_offset_mappings(self, mapped_results: Dict[str, Any], timestamp: str) -> Dict[str, Any]:
        """Prepare detailed offset mappings for Knowledge Graph construction"""
        
        offset_mappings = []
        
        for mapping in mapped_results['chunk_mappings']:
            offset_mappings.append({
                'chunk_id': mapping['chunk_id'],
                'chunk_index': mapping['chunk_index'],
                'type': mapping['type'],
                'text': mapping['text'],
                'document_offsets': {
                    'begin': mapping['document_begin_offset'],
                    'end': mapping['document_end_offset']
                },
                'chunk_offsets': {
                    'begin': mapping['chunk_begin_offset'],
                    'end': mapping['chunk_end_offset']
                },
                'metadata': {
                    'confidence': mapping.get('confidence', 0.0),
                    'entity_type': mapping.get('entity_type', None),
                    'mapping_quality': mapping.get('mapping_quality', 'unknown')
                }
            })
        
        return {
            'doc_id': mapped_results['doc_id'],
            'processed_at': mapped_results['processed_at'],
            'offset_mappings': offset_mappings,
            'mapping_statistics': mapped_results.get('mapping_statistics', {}),
            'storage_metadata': {
                'stored_at': datetime.now().isoformat(),
                'storage_timestamp': timestamp,
                'data_type': 'offset_mappings',
                'purpose': 'knowledge_graph_construction'
            }
        }
    
    def _prepare_processing_metadata(self, mapped_results: Dict[str, Any], timestamp: str, file_locations: Dict[str, str]) -> Dict[str, Any]:
        """Prepare processing metadata"""
        
        entities_count = len([m for m in mapped_results['chunk_mappings'] if m['type'] == 'entity'])
        phrases_count = len([m for m in mapped_results['chunk_mappings'] if m['type'] == 'key_phrase'])
        
        return {
            'doc_id': mapped_results['doc_id'],
            'provider': mapped_results['provider'],
            'processed_at': mapped_results['processed_at'],
            'processing_cost': mapped_results['processing_cost'],
            'processing_duration': mapped_results.get('processing_duration', 0.0),
            'results_summary': {
                'entities_count': entities_count,
                'key_phrases_count': phrases_count,
                'total_nlp_items': entities_count + phrases_count
            },
            'files': file_locations,
            'storage_metadata': {
                'stored_at': datetime.now().isoformat(),
                'storage_timestamp': timestamp,
                'bucket': self.bucket_name,
                'data_lake_tier': 'nlp_results'
            }
        }
    
    def _calculate_avg_confidence(self, items: list) -> float:
        """Calculate average confidence score for a list of items"""
        if not items:
            return 0.0
        
        confidences = [item.get('confidence', 0.0) for item in items]
        return sum(confidences) / len(confidences)
    
    def _store_json_file(self, s3_key: str, data: Dict[str, Any]):
        """Store JSON data in S3 with proper metadata"""
        
        json_data = json.dumps(data, indent=2, default=str, ensure_ascii=False)
        
        # Prepare S3 metadata
        metadata = {
            'doc_id': data.get('doc_id', ''),
            'provider': data.get('provider', ''),
            'processed_at': data.get('processed_at', ''),
            'data_type': data.get('storage_metadata', {}).get('data_type', 'nlp_results')
        }
        
        # Remove None values and ensure string values
        metadata = {k: str(v) for k, v in metadata.items() if v is not None}
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_data.encode('utf-8'),
                ContentType='application/json',
                ContentEncoding='utf-8',
                Metadata=metadata,
                ServerSideEncryption='AES256'  # Encrypt at rest
            )
            
            logger.debug(f"Stored {len(json_data)} bytes to s3://{self.bucket_name}/{s3_key}")
            
        except Exception as e:
            logger.error(f"Error storing file to S3: {str(e)}")
            raise
    
    def retrieve_nlp_results(self, doc_id: str, result_type: str = 'complete') -> Optional[Dict[str, Any]]:
        """
        Retrieve NLP results from S3 data lake
        
        Args:
            doc_id: Document ID
            result_type: 'complete', 'entities', 'key_phrases', 'offset_mappings', or 'metadata'
        """
        
        try:
            # List files for this document
            prefix = f"{doc_id}/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                logger.warning(f"No NLP results found for document {doc_id}")
                return None
            
            # Find the most recent file of the requested type
            target_files = [
                obj for obj in response['Contents'] 
                if f"{result_type}_" in obj['Key'] or (result_type == 'complete' and 'nlp_complete_' in obj['Key'])
            ]
            
            if not target_files:
                logger.warning(f"No {result_type} results found for document {doc_id}")
                return None
            
            # Get the most recent file
            latest_file = max(target_files, key=lambda x: x['LastModified'])
            
            # Retrieve and parse the file
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=latest_file['Key']
            )
            
            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)
            
            logger.info(f"Retrieved {result_type} results for {doc_id} from {latest_file['Key']}")
            return data
            
        except Exception as e:
            logger.error(f"Error retrieving NLP results for {doc_id}: {str(e)}")
            return None
    
    def list_processed_documents(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List documents that have been processed for NLP"""
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Delimiter='/',
                MaxKeys=limit
            )
            
            documents = []
            
            if 'CommonPrefixes' in response:
                for prefix in response['CommonPrefixes']:
                    doc_id = prefix['Prefix'].rstrip('/')
                    
                    # Get metadata for this document
                    try:
                        metadata = self.retrieve_nlp_results(doc_id, 'metadata')
                        if metadata:
                            documents.append({
                                'doc_id': doc_id,
                                'processed_at': metadata.get('processed_at'),
                                'provider': metadata.get('provider'),
                                'entities_count': metadata.get('results_summary', {}).get('entities_count', 0),
                                'key_phrases_count': metadata.get('results_summary', {}).get('key_phrases_count', 0),
                                'processing_cost': metadata.get('processing_cost', 0.0)
                            })
                    except Exception as e:
                        logger.warning(f"Could not retrieve metadata for {doc_id}: {str(e)}")
                        documents.append({
                            'doc_id': doc_id,
                            'processed_at': None,
                            'provider': 'unknown',
                            'entities_count': 0,
                            'key_phrases_count': 0,
                            'processing_cost': 0.0
                        })
            
            logger.info(f"Found {len(documents)} processed documents in NLP data lake")
            return documents
            
        except Exception as e:
            logger.error(f"Error listing processed documents: {str(e)}")
            return []
