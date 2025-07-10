#!/usr/bin/env python3
"""
Document TTL Generator for Lambda Functions
Adapted from /src/knowledge_graph/generate_example_from_data_fixed.py for Lambda use

This module generates TTL representations from processed document data using Dublin Core vocabulary.
Designed for use within Lambda functions with proper error handling and logging.
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

# Add layers to path for shared utilities
sys.path.append('/opt/python')

try:
    from uri_minter import URIMintingFacility, URIType
except ImportError:
    # For local testing or if URI minter is not in layer
    logger.warning("URI minter not available, using simplified URI generation")
    URIMintingFacility = None
    URIType = None

class DocumentTTLGenerator:
    """Generate TTL representation from actual processed document data"""
    
    def __init__(self, doc_id: str, aws_session=None):
        self.doc_id = doc_id
        
        # Use provided session or create new one
        if aws_session:
            self.session = aws_session
            self.s3 = aws_session.client('s3', region_name='us-east-1')
        else:
            self.s3 = boto3.client('s3', region_name='us-east-1')
        
        # Initialize URI facility if available
        if URIMintingFacility:
            self.uri_facility = URIMintingFacility()
        else:
            self.uri_facility = None
        
        # S3 bucket names from environment or defaults
        self.text_bucket = os.environ.get('TEXT_BUCKET', 'solve-global-kr-text-new-861276078413-us-east-1')
        self.chunks_bucket = os.environ.get('CHUNKS_BUCKET', 'solve-global-kr-chunks-861276078413-us-east-1')
        
        # TTL prefixes with Dublin Core integration
        self.ttl_prefixes = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix sg: <http://solve.global/knowledge-commons/> .
@prefix kr: <http://solve.global/knowledge-commons/schema#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .

"""
    
    def generate_ttl_document(self) -> str:
        """Generate complete TTL document from actual S3 data"""
        logger.info(f"Generating TTL document for {self.doc_id}")
        
        ttl_content = self.ttl_prefixes
        ttl_content += f"""# =============================================================================
# DOCUMENT STRUCTURE TTL: {self.doc_id}
# Generated from processed document data using Dublin Core vocabulary
# Generated: {datetime.now().isoformat()}
# =============================================================================

"""
        
        try:
            # Get document metadata from actual text file
            doc_metadata = self.get_document_metadata()
            
            # Generate document root with Dublin Core terms
            ttl_content += self.generate_document_root(doc_metadata)
            
            # Get actual chunks from S3 JSON files
            chunks_data = self.get_actual_chunks_data()
            if chunks_data:
                ttl_content += self.generate_sections_and_chunks(chunks_data)
            else:
                ttl_content += "# No chunks data found\n\n"
            
            logger.info(f"Successfully generated TTL document for {self.doc_id}: {len(ttl_content)} characters")
            return ttl_content
            
        except Exception as e:
            logger.error(f"Error generating TTL document for {self.doc_id}: {str(e)}")
            raise
    
    def get_document_metadata(self) -> Dict[str, Any]:
        """Get document metadata from extracted text file"""
        
        try:
            logger.info(f"Retrieving document metadata from extracted text")
            
            # Get extracted text file
            text_key = f"extracted_text/{self.doc_id}.txt"
            
            try:
                response = self.s3.get_object(Bucket=self.text_bucket, Key=text_key)
                text_content = response['Body'].read().decode('utf-8')
                
                # Calculate basic statistics
                words = text_content.split()
                sentences = text_content.count('.') + text_content.count('!') + text_content.count('?')
                
                # Get file metadata
                head_response = self.s3.head_object(Bucket=self.text_bucket, Key=text_key)
                last_modified = head_response['LastModified'].isoformat()
                
                # Extract title (first non-empty line, cleaned up)
                lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                title = lines[0] if lines else f"Document {self.doc_id}"
                title = re.sub(r'\s+', ' ', title)  # Clean up whitespace
                
                metadata = {
                    'title': title,
                    'word_count': len(words),
                    'sentence_count': max(sentences, 1),  # At least 1 sentence
                    'created': last_modified,
                    'page_count': self.estimate_page_count(len(words))
                }
                
                logger.info(f"Document metadata: {metadata['word_count']} words, {metadata['page_count']} pages")
                return metadata
                
            except self.s3.exceptions.NoSuchKey:
                logger.warning(f"Text file not found: {text_key}, using defaults")
                return {
                    'title': f"Document {self.doc_id}",
                    'word_count': 0,
                    'sentence_count': 0,
                    'created': datetime.now().isoformat(),
                    'page_count': 1
                }
                
        except Exception as e:
            logger.error(f"Error retrieving document metadata: {str(e)}")
            raise
    
    def estimate_page_count(self, word_count: int) -> int:
        """Estimate page count from word count (roughly 250 words per page)"""
        return max(1, (word_count + 249) // 250)
    
    def get_actual_chunks_data(self) -> List[Dict[str, Any]]:
        """Get actual chunk data from S3 JSON files"""
        
        try:
            logger.info(f"Retrieving actual chunks from S3 JSON files")
            
            # List all chunk files for this document
            prefix = f"{self.doc_id}/"
            
            response = self.s3.list_objects_v2(
                Bucket=self.chunks_bucket,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                logger.warning(f"No chunk files found for document {self.doc_id}")
                return []
            
            # Filter for chunk JSON files
            chunk_files = [
                obj for obj in response['Contents'] 
                if obj['Key'].endswith('.json') and 'chunk_' in obj['Key']
            ]
            
            logger.info(f"Found {len(chunk_files)} chunk JSON files")
            
            chunks = []
            for chunk_file in sorted(chunk_files, key=lambda x: x['Key']):
                try:
                    # Get chunk data
                    chunk_response = self.s3.get_object(
                        Bucket=self.chunks_bucket,
                        Key=chunk_file['Key']
                    )
                    
                    chunk_data = json.loads(chunk_response['Body'].read().decode('utf-8'))
                    
                    # Add S3 metadata
                    chunk_data['s3_key'] = chunk_file['Key']
                    chunk_data['s3_location'] = f"s3://{self.chunks_bucket}/{chunk_file['Key']}"
                    chunk_data['last_modified'] = chunk_file['LastModified'].isoformat()
                    
                    # Extract chunk sequence from filename
                    filename = os.path.basename(chunk_file['Key'])
                    chunk_match = re.search(r'chunk_(\d+)', filename)
                    if chunk_match:
                        chunk_data['chunk_sequence'] = int(chunk_match.group(1))
                    else:
                        chunk_data['chunk_sequence'] = len(chunks) + 1
                    
                    chunks.append(chunk_data)
                    
                except Exception as e:
                    logger.error(f"Error processing chunk file {chunk_file['Key']}: {str(e)}")
                    continue
            
            logger.info(f"Successfully processed {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error retrieving chunks data: {str(e)}")
            return []
    
    def generate_document_root(self, metadata: Dict[str, Any]) -> str:
        """Generate document root TTL using Dublin Core vocabulary"""
        
        doc_uri = self.mint_uri('DOCUMENT', doc_id=self.doc_id)
        
        ttl = f"""# -----------------------------------------------------------------------------
# DOCUMENT ROOT - Dublin Core Integration
# -----------------------------------------------------------------------------

{self.format_uri(doc_uri)} a kr:Document, foaf:Document ;
    dcterms:identifier "{self.doc_id}" ;
    dcterms:title "{self.escape_ttl_string(metadata['title'])}" ;
    dcterms:created "{metadata['created']}"^^xsd:dateTime ;
    dcterms:modified "{datetime.now().isoformat()}"^^xsd:dateTime ;
    dcterms:format "application/pdf" ;
    dcterms:extent "{metadata['page_count']} pages" ;
    dcterms:language "en" ;
    dcterms:source <s3://{self.text_bucket}/extracted_text/{self.doc_id}.txt> ;
    dcterms:provenance "Processed via AWS Textract, chunked, and analyzed" ;
    kr:wordCount "{metadata['word_count']}"^^xsd:nonNegativeInteger ;
    kr:sentenceCount "{metadata['sentence_count']}"^^xsd:nonNegativeInteger ;
    kr:pageCount "{metadata['page_count']}"^^xsd:nonNegativeInteger .

"""
        return ttl
    
    def generate_sections_and_chunks(self, chunks: List[Dict[str, Any]]) -> str:
        """Generate sections and chunks TTL from actual chunk data"""
        
        ttl = """# -----------------------------------------------------------------------------
# DOCUMENT SECTIONS AND CHUNKS - Dublin Core Integration
# -----------------------------------------------------------------------------

"""
        
        # Group chunks by section
        sections = {}
        for chunk in chunks:
            section_seq = self.determine_section_sequence(chunk)
            if section_seq not in sections:
                sections[section_seq] = []
            sections[section_seq].append(chunk)
        
        # Generate TTL for each section
        for section_seq in sorted(sections.keys()):
            section_chunks = sections[section_seq]
            section_title = self.determine_section_title(section_seq)
            
            # Generate section TTL
            section_uri = self.mint_uri('DOCUMENT_SECTION', doc_id=self.doc_id, section_sequence=section_seq)
            
            total_words = sum(chunk.get('word_count', 0) for chunk in section_chunks)
            total_sentences = sum(chunk.get('sentence_count', 0) for chunk in section_chunks)
            
            ttl += f"""{self.format_uri(section_uri)} a kr:DocumentSection ;
    dcterms:title "{self.escape_ttl_string(section_title)}" ;
    dcterms:isPartOf {self.format_uri(self.mint_uri('DOCUMENT', doc_id=self.doc_id))} ;
    dcterms:extent "{total_words} words, {total_sentences} sentences" ;
    kr:sectionSequence "{section_seq}"^^xsd:positiveInteger ;
    kr:hierarchyLevel "1"^^xsd:positiveInteger ;
    kr:wordCount "{total_words}"^^xsd:nonNegativeInteger ;
    kr:sentenceCount "{total_sentences}"^^xsd:nonNegativeInteger"""
            
            # Add chunk references
            for chunk in section_chunks:
                chunk_uri = self.mint_uri('DOCUMENT_CHUNK', 
                    doc_id=self.doc_id, 
                    section_sequence=section_seq,
                    chunk_sequence=chunk['chunk_sequence'])
                ttl += f" ;\n    kr:hasChunk {self.format_uri(chunk_uri)}"
            
            ttl += " .\n\n"
            
            # Generate chunk TTL
            for chunk in section_chunks:
                chunk_seq = chunk['chunk_sequence']
                chunk_uri = self.mint_uri('DOCUMENT_CHUNK',
                    doc_id=self.doc_id,
                    section_sequence=section_seq,
                    chunk_sequence=chunk_seq)
                
                ttl += f"""{self.format_uri(chunk_uri)} a kr:DocumentChunk ;
    dcterms:identifier "{chunk_uri.split('/')[-1]}" ;
    dcterms:isPartOf {self.format_uri(section_uri)} ;
    dcterms:title "{self.escape_ttl_string(chunk.get('title', f'Chunk {chunk_seq}'))}" ;
    dcterms:modified "{chunk['last_modified']}"^^xsd:dateTime ;
    dcterms:extent "{chunk.get('word_count', 0)} words, {chunk.get('sentence_count', 0)} sentences" ;
    kr:chunkSequence "{chunk_seq}"^^xsd:positiveInteger ;
    kr:parentSection {self.format_uri(section_uri)} ;
    kr:parentDocument {self.format_uri(self.mint_uri('DOCUMENT', doc_id=self.doc_id))} ;
    kr:wordCount "{chunk.get('word_count', 0)}"^^xsd:nonNegativeInteger ;
    kr:sentenceCount "{chunk.get('sentence_count', 0)}"^^xsd:nonNegativeInteger ;
    kr:chunkingStrategy "smart_structured" ;
    kr:s3Location "{chunk['s3_location']}"^^xsd:anyURI ;
    kr:s3Bucket "{self.chunks_bucket}" ;
    kr:s3Key "{chunk['s3_key']}" """
                
                # Add character offsets if available
                if 'char_start' in chunk and 'char_end' in chunk:
                    ttl += f" ;\n    kr:characterStart \"{chunk['char_start']}\"^^xsd:nonNegativeInteger"
                    ttl += f" ;\n    kr:characterEnd \"{chunk['char_end']}\"^^xsd:nonNegativeInteger"
                
                ttl += " .\n\n"
        
        return ttl
    
    def determine_section_sequence(self, chunk: Dict[str, Any]) -> int:
        """Determine section sequence for a chunk"""
        # Simple logic: first 5 chunks = section 1, next 5 = section 2, etc.
        chunk_seq = chunk.get('chunk_sequence', 1)
        return ((chunk_seq - 1) // 5) + 1
    
    def determine_section_title(self, section_seq: int) -> str:
        """Determine section title based on sequence"""
        section_titles = {
            1: "Executive Summary",
            2: "Main Content", 
            3: "Analysis and Findings",
            4: "Appendices and References"
        }
        return section_titles.get(section_seq, f"Section {section_seq}")
    
    def mint_uri(self, uri_type: str, **kwargs) -> str:
        """Mint URI using facility or simple pattern"""
        if self.uri_facility and URIType:
            # Use proper URI minting facility
            type_enum = getattr(URIType, uri_type, None)
            if type_enum:
                return self.uri_facility.mint_uri(type_enum, **kwargs)
        
        # Fallback to simple URI pattern
        base = "sg:"
        if uri_type == 'DOCUMENT':
            return f"{base}Document_{kwargs['doc_id']}"
        elif uri_type == 'DOCUMENT_SECTION':
            return f"{base}Document_{kwargs['doc_id']}_Section_{kwargs['section_sequence']}"
        elif uri_type == 'DOCUMENT_CHUNK':
            return f"{base}Document_{kwargs['doc_id']}_Section_{kwargs['section_sequence']}_Chunk_{kwargs['chunk_sequence']}"
        else:
            return f"{base}{uri_type}_{kwargs.get('doc_id', 'unknown')}"
    
    def format_uri(self, uri: str) -> str:
        """Format URI for TTL output"""
        return uri if uri.startswith('<') else uri
    
    def escape_ttl_string(self, text: str) -> str:
        """Escape string for TTL output"""
        if not text:
            return ""
        # Escape quotes and backslashes
        return text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
