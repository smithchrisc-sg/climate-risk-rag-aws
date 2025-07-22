#!/usr/bin/env python3
"""
Document TTL Generator for Lambda Functions
Generates TTL representations from processed document data using Dublin Core vocabulary.
Modernized for standardized deployment process.
"""

import boto3
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import re

# Configure logging
logger = logging.getLogger(__name__)

class DocumentTTLGenerator:
    """Generate TTL representation from processed document data using Dublin Core"""
    
    def __init__(self, doc_id: str, enhanced_metadata: Dict = None):
        self.doc_id = doc_id
        self.enhanced_metadata = enhanced_metadata or {}
        self.s3 = boto3.client('s3', region_name='us-east-1')
        
        # S3 buckets
        self.chunks_bucket = os.environ.get('CHUNKS_BUCKET', 'solve-global-kr-dl-chunks-861276078413-us-east-1')
        self.text_bucket = os.environ.get('TEXT_BUCKET', 'solve-global-kr-dl-text-861276078413-us-east-1')
        
        logger.info(f"Initialized TTL generator for document: {doc_id}")
    
    def generate_document_structure_ttl(self) -> str:
        """Generate TTL for document structure using Dublin Core vocabulary"""
        
        try:
            # Load document chunks and metadata
            chunks_data = self.load_chunks_data()
            
            # Generate TTL content
            ttl_content = self.build_ttl_content(chunks_data)
            
            logger.info(f"Generated TTL content ({len(ttl_content)} characters) for document: {self.doc_id}")
            return ttl_content
            
        except Exception as e:
            logger.error(f"Error generating TTL for {self.doc_id}: {str(e)}")
            raise
    
    def load_chunks_data(self) -> Dict[str, Any]:
        """Load chunks and metadata from S3"""
        
        try:
            chunks_data = {
                'chunks': [],
                'metadata': {},
                'document_info': {}
            }
            
            # Get data locations from enhanced metadata
            data_locations = self.enhanced_metadata.get('data_locations', {})
            chunks_location = data_locations.get('chunks_location', '')
            
            if chunks_location:
                # Parse S3 location
                if chunks_location.startswith('s3://'):
                    bucket_and_prefix = chunks_location[5:]
                    bucket_name = bucket_and_prefix.split('/')[0]
                    prefix = '/'.join(bucket_and_prefix.split('/')[1:])
                    
                    # List all chunk files
                    response = self.s3.list_objects_v2(
                        Bucket=bucket_name,
                        Prefix=prefix
                    )
                    
                    for obj in response.get('Contents', []):
                        key = obj['Key']
                        if key.endswith('.json'):
                            if key.endswith('metadata.json'):
                                # Load metadata
                                metadata_obj = self.s3.get_object(Bucket=bucket_name, Key=key)
                                chunks_data['metadata'] = json.loads(metadata_obj['Body'].read().decode('utf-8'))
                            elif 'chunk_' in key:
                                # Load chunk
                                chunk_obj = self.s3.get_object(Bucket=bucket_name, Key=key)
                                chunk_data = json.loads(chunk_obj['Body'].read().decode('utf-8'))
                                chunks_data['chunks'].append(chunk_data)
            
            # Sort chunks by chunk_id for consistent ordering
            chunks_data['chunks'].sort(key=lambda x: x.get('chunk_id', ''))
            
            logger.info(f"Loaded {len(chunks_data['chunks'])} chunks for document: {self.doc_id}")
            return chunks_data
            
        except Exception as e:
            logger.error(f"Error loading chunks data for {self.doc_id}: {str(e)}")
            # Return minimal structure to allow TTL generation to continue
            return {
                'chunks': [],
                'metadata': {},
                'document_info': {}
            }
    
    def build_ttl_content(self, chunks_data: Dict[str, Any]) -> str:
        """Build TTL content using Dublin Core vocabulary"""
        
        # TTL prefixes
        prefixes = """@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix cr: <http://climate-risk.org/ontology/> .

"""
        
        # Document URI
        doc_uri = f"<http://climate-risk.org/documents/{self.doc_id}>"
        
        # Build document description
        document_ttl = f"""{doc_uri} a dcterms:Text ;
    dc:identifier "{self.doc_id}" ;
    dcterms:created "{datetime.utcnow().isoformat()}Z"^^xsd:dateTime ;
    dcterms:modified "{datetime.utcnow().isoformat()}Z"^^xsd:dateTime ;
    cr:processingStage "kg_doc_structure" ;
"""
        
        # Add metadata if available
        metadata = chunks_data.get('metadata', {})
        if metadata:
            document_info = metadata.get('document_info', {})
            if document_info.get('title'):
                document_ttl += f'    dc:title "{self.escape_ttl_string(document_info["title"])}" ;\n'
            if document_info.get('source_url'):
                document_ttl += f'    dc:source <{document_info["source_url"]}> ;\n'
            
            chunking_config = metadata.get('chunking_config', {})
            if chunking_config:
                document_ttl += f'    cr:chunkingMethod "{chunking_config.get("method", "unknown")}" ;\n'
                document_ttl += f'    cr:maxChunkSize {chunking_config.get("max_chunk_size", 0)} ;\n'
        
        # Add processing metadata
        processing_metadata = self.enhanced_metadata.get('processing_metadata', {})
        if processing_metadata:
            chunks_created = processing_metadata.get('chunks_created', 0)
            document_ttl += f'    cr:chunksCreated {chunks_created} ;\n'
        
        # Close document description
        document_ttl = document_ttl.rstrip(' ;\n') + ' .\n\n'
        
        # Build chunks descriptions
        chunks_ttl = ""
        for i, chunk in enumerate(chunks_data.get('chunks', [])):
            chunk_id = chunk.get('chunk_id', f'chunk_{i:03d}')
            chunk_uri = f"<http://climate-risk.org/documents/{self.doc_id}/chunks/{chunk_id}>"
            
            chunk_ttl = f"""{chunk_uri} a cr:DocumentChunk ;
    dc:identifier "{chunk_id}" ;
    dcterms:isPartOf {doc_uri} ;
    cr:chunkIndex {i} ;
"""
            
            # Add chunk content (truncated for TTL)
            content = chunk.get('content', '')
            if content:
                # Truncate and escape content for TTL
                truncated_content = content[:500] + ('...' if len(content) > 500 else '')
                chunk_ttl += f'    dcterms:abstract "{self.escape_ttl_string(truncated_content)}" ;\n'
                chunk_ttl += f'    cr:contentLength {len(content)} ;\n'
            
            # Add structural information
            if chunk.get('section_title'):
                chunk_ttl += f'    cr:sectionTitle "{self.escape_ttl_string(chunk["section_title"])}" ;\n'
            
            if chunk.get('chunk_type'):
                chunk_ttl += f'    cr:chunkType "{chunk["chunk_type"]}" ;\n'
            
            # Add position information
            if chunk.get('start_char') is not None:
                chunk_ttl += f'    cr:startPosition {chunk["start_char"]} ;\n'
            if chunk.get('end_char') is not None:
                chunk_ttl += f'    cr:endPosition {chunk["end_char"]} ;\n'
            
            # Close chunk description
            chunk_ttl = chunk_ttl.rstrip(' ;\n') + ' .\n\n'
            chunks_ttl += chunk_ttl
        
        # Combine all TTL content
        full_ttl = prefixes + document_ttl + chunks_ttl
        
        return full_ttl
    
    def escape_ttl_string(self, text: str) -> str:
        """Escape string for TTL format"""
        if not text:
            return ""
        
        # Replace problematic characters
        text = text.replace('\\', '\\\\')
        text = text.replace('"', '\\"')
        text = text.replace('\n', '\\n')
        text = text.replace('\r', '\\r')
        text = text.replace('\t', '\\t')
        
        return text
    
    def generate_ttl_document(self) -> str:
        """Legacy method name for compatibility"""
        return self.generate_document_structure_ttl()
