#!/usr/bin/env python3
"""
Generate Example Document from Actual Processed Data
Creates TTL representation from real Textract output and chunking results
"""

import boto3
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import re

# Add the knowledge graph module to path
sys.path.append(os.path.dirname(__file__))
from uri_minter import URIMintingFacility, URIType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentTTLGenerator:
    """Generate TTL representation from actual processed document data"""
    
    def __init__(self, doc_id: str, aws_profile: str = 'solve-global'):
        self.doc_id = doc_id
        self.session = boto3.Session(profile_name=aws_profile)
        self.s3 = self.session.client('s3', region_name='us-east-1')
        self.uri_facility = URIMintingFacility()
        
        # S3 bucket names (updated with actual structure)
        self.text_bucket = 'solve-global-kr-text-new-861276078413-us-east-1'
        self.chunks_bucket = 'solve-global-kr-chunks-861276078413-us-east-1'
        self.documents_bucket = 'solve-global-kr-documents-861276078413-us-east-1'
        
        # TTL prefixes
        self.ttl_prefixes = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix sg: <http://solve.global/knowledge-commons/> .
@prefix kr: <http://solve.global/knowledge-commons/schema#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix dcterms: <http://purl.org/dc/terms/> .

"""
    
    def generate_ttl_document(self) -> str:
        """Generate complete TTL document from actual data"""
        logger.info(f"Generating TTL document for {self.doc_id}")
        
        ttl_content = self.ttl_prefixes
        ttl_content += f"""# =============================================================================
# ACTUAL DOCUMENT DATA: {self.doc_id}
# Generated from real Textract output and chunking results
# Generated: {datetime.now().isoformat()}
# =============================================================================

"""
        
        try:
            # Get document metadata
            doc_metadata = self.get_document_metadata()
            
            # Generate document root
            ttl_content += self.generate_document_root(doc_metadata)
            
            # Get and generate chunks
            chunks_data = self.get_chunks_data()
            if chunks_data:
                ttl_content += self.generate_chunks_section(chunks_data)
            else:
                ttl_content += "# No chunks data found\n\n"
            
            logger.info(f"Successfully generated TTL document for {self.doc_id}")
            return ttl_content
            
        except Exception as e:
            logger.error(f"Error generating TTL document: {e}")
            raise
    
    def get_document_metadata(self) -> Dict[str, Any]:
        """Get document metadata from S3"""
        logger.info("Retrieving document metadata")
        
        metadata = {
            'doc_id': self.doc_id,
            'title': f'Document {self.doc_id}',
            'created': datetime.now().isoformat(),
            'word_count': 0,
            'sentence_count': 0,
            'page_count': 0
        }
        
        # Try to get full text to calculate metrics
        try:
            text_key = f'extracted_text/{self.doc_id}.txt'
            response = self.s3.get_object(Bucket=self.text_bucket, Key=text_key)
            full_text = response['Body'].read().decode('utf-8')
            
            # Calculate basic metrics
            metadata['word_count'] = len(full_text.split())
            metadata['sentence_count'] = full_text.count('.') + full_text.count('!') + full_text.count('?')
            
            # Count pages from text
            page_count = full_text.count('--- Page')
            if page_count > 0:
                metadata['page_count'] = page_count
            
            # Try to extract title from first meaningful line
            lines = full_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('---') and len(line) > 10 and len(line) < 100:
                    # Clean up the line for title
                    if not re.match(r'^\d+[\.\s]', line):  # Not a numbered item
                        metadata['title'] = line
                        break
                        
        except Exception as e:
            logger.warning(f"Could not retrieve full text: {e}")
        
        return metadata
    
    def get_chunks_data(self) -> List[Dict[str, Any]]:
        """Get actual chunk data from S3"""
        logger.info("Retrieving chunks data")
        
        chunks = []
        try:
            # List all chunk files for this document
            response = self.s3.list_objects_v2(
                Bucket=self.chunks_bucket,
                Prefix=f'{self.doc_id}/'
            )
            
            if 'Contents' not in response:
                logger.warning(f"No chunks found for document {self.doc_id}")
                return chunks
            
            chunk_files = [obj for obj in response['Contents'] 
                          if '_chunk_' in obj['Key'] and obj['Key'].endswith('.json')]
            
            logger.info(f"Found {len(chunk_files)} chunk files")
            
            for obj in chunk_files:
                key = obj['Key']
                try:
                    # Get chunk content
                    chunk_response = self.s3.get_object(Bucket=self.chunks_bucket, Key=key)
                    chunk_data = json.loads(chunk_response['Body'].read().decode('utf-8'))
                    
                    # Extract chunk information
                    chunk_info = {
                        'chunk_id': chunk_data.get('chunk_id', ''),
                        'chunk_sequence': chunk_data.get('chunk_sequence', 0),
                        'text': chunk_data.get('text', ''),
                        'word_count': len(chunk_data.get('text', '').split()),
                        'sentence_count': len(chunk_data.get('offsets', {}).get('sentences', [])),
                        's3_location': f's3://{self.chunks_bucket}/{key}',
                        'last_modified': obj['LastModified'].isoformat(),
                        'char_start': chunk_data.get('offsets', {}).get('char_start', 0),
                        'char_end': chunk_data.get('offsets', {}).get('char_end', 0)
                    }
                    
                    # Infer section information from chunk sequence
                    # For now, we'll create logical sections based on chunk groups
                    chunk_seq = chunk_info['chunk_sequence']
                    if chunk_seq <= 3:
                        chunk_info['section_sequence'] = 1
                        chunk_info['section_title'] = 'Introduction and Overview'
                    elif chunk_seq <= 8:
                        chunk_info['section_sequence'] = 2
                        chunk_info['section_title'] = 'Procurement Guidelines'
                    elif chunk_seq <= 15:
                        chunk_info['section_sequence'] = 3
                        chunk_info['section_title'] = 'Implementation Details'
                    else:
                        chunk_info['section_sequence'] = 4
                        chunk_info['section_title'] = 'Appendices and References'
                    
                    chunks.append(chunk_info)
                    
                except Exception as e:
                    logger.warning(f"Could not process chunk {key}: {e}")
            
            # Sort chunks by sequence
            chunks.sort(key=lambda x: x.get('chunk_sequence', 0))
            logger.info(f"Retrieved {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error retrieving chunks: {e}")
        
        return chunks
    
    def generate_document_root(self, metadata: Dict[str, Any]) -> str:
        """Generate document root TTL"""
        doc_uri = self.uri_facility.mint_uri(URIType.DOCUMENT, doc_id=self.doc_id)
        
        ttl = f"""# -----------------------------------------------------------------------------
# DOCUMENT ROOT
# -----------------------------------------------------------------------------

{self.format_uri(doc_uri)} a kr:Document ;
    dcterms:title "{self.escape_ttl_string(metadata['title'])}" ;
    dcterms:created "{metadata['created']}"^^xsd:dateTime ;
    kr:processingTimestamp "{datetime.now().isoformat()}"^^xsd:dateTime ;
    kr:wordCount "{metadata['word_count']}"^^xsd:nonNegativeInteger ;
    kr:sentenceCount "{metadata['sentence_count']}"^^xsd:nonNegativeInteger"""
        
        if metadata['page_count'] > 0:
            ttl += f" ;\n    kr:pageCount \"{metadata['page_count']}\"^^xsd:nonNegativeInteger"
        
        ttl += " ."
        
        return ttl + "\n\n"
    
    def generate_chunks_section(self, chunks: List[Dict[str, Any]]) -> str:
        """Generate chunks section TTL"""
        if not chunks:
            return "# No chunks found\n\n"
        
        ttl = """# -----------------------------------------------------------------------------
# DOCUMENT SECTIONS AND CHUNKS (From Actual Processing Results)
# -----------------------------------------------------------------------------

"""
        
        # Group chunks by section
        sections = {}
        for chunk in chunks:
            section_key = chunk['section_sequence']
            if section_key not in sections:
                sections[section_key] = {
                    'chunks': [],
                    'title': chunk['section_title']
                }
            sections[section_key]['chunks'].append(chunk)
        
        # Generate section URIs first
        for section_seq, section_data in sections.items():
            section_uri = self.uri_facility.mint_uri(
                URIType.DOCUMENT_SECTION,
                doc_id=self.doc_id,
                section_sequence=section_seq
            )
            
            section_chunks = section_data['chunks']
            section_title = section_data['title']
            
            # Calculate section metrics
            total_words = sum(chunk['word_count'] for chunk in section_chunks)
            total_sentences = sum(chunk['sentence_count'] for chunk in section_chunks)
            
            ttl += f"""{self.format_uri(section_uri)} a kr:DocumentSection ;
    dcterms:title "{self.escape_ttl_string(section_title)}" ;
    kr:sectionSequence "{section_seq}"^^xsd:positiveInteger ;
    kr:hierarchyLevel "1"^^xsd:positiveInteger ;
    kr:parentDocument {self.format_uri(self.uri_facility.mint_uri(URIType.DOCUMENT, doc_id=self.doc_id))} ;
    kr:wordCount "{total_words}"^^xsd:nonNegativeInteger ;
    kr:sentenceCount "{total_sentences}"^^xsd:nonNegativeInteger"""
            
            # Add chunk references
            for chunk in section_chunks:
                chunk_uri = self.uri_facility.mint_uri(
                    URIType.DOCUMENT_CHUNK,
                    doc_id=self.doc_id,
                    section_sequence=section_seq,
                    chunk_sequence=chunk['chunk_sequence']
                )
                ttl += f" ;\n    kr:hasChunk {self.format_uri(chunk_uri)}"
            
            ttl += " .\n\n"
        
        # Generate individual chunks
        for chunk in chunks:
            section_seq = chunk['section_sequence']
            chunk_seq = chunk['chunk_sequence']
            
            chunk_uri = self.uri_facility.mint_uri(
                URIType.DOCUMENT_CHUNK,
                doc_id=self.doc_id,
                section_sequence=section_seq,
                chunk_sequence=chunk_seq
            )
            
            section_uri = self.uri_facility.mint_uri(
                URIType.DOCUMENT_SECTION,
                doc_id=self.doc_id,
                section_sequence=section_seq
            )
            
            # Truncate text for TTL (first 200 chars)
            display_text = chunk['text'][:200]
            if len(chunk['text']) > 200:
                display_text += "..."
            display_text = self.escape_ttl_string(display_text)
            
            # Extract S3 key from location
            s3_key = chunk['s3_location'].split('/')[-1]
            
            ttl += f"""{self.format_uri(chunk_uri)} a kr:DocumentChunk ;
    kr:chunkSequence "{chunk_seq}"^^xsd:positiveInteger ;
    kr:parentSection {self.format_uri(section_uri)} ;
    kr:parentDocument {self.format_uri(self.uri_facility.mint_uri(URIType.DOCUMENT, doc_id=self.doc_id))} ;
    kr:textContent "{display_text}" ;
    kr:wordCount "{chunk['word_count']}"^^xsd:nonNegativeInteger ;
    kr:sentenceCount "{chunk['sentence_count']}"^^xsd:nonNegativeInteger ;
    kr:chunkingStrategy "smart_structured" ;
    kr:s3Location "{chunk['s3_location']}"^^xsd:anyURI ;
    kr:s3Bucket "{self.chunks_bucket}" ;
    kr:s3Key "{s3_key}" ;
    kr:processingTimestamp "{chunk['last_modified']}"^^xsd:dateTime .

"""
        
        return ttl
    
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
    
    def format_uri(self, uri: str) -> str:
        """Format URI for TTL output"""
        if uri.startswith('http://solve.global/knowledge-commons/'):
            return uri.replace('http://solve.global/knowledge-commons/', 'sg:')
        return f"<{uri}>"
    
    def save_ttl_document(self, ttl_content: str, output_path: str):
        """Save TTL document to file"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ttl_content)
        logger.info(f"Saved TTL document to {output_path}")

def main():
    """Main function to generate example document"""
    doc_id = "0032f6cb_f0caef34"  # Our test document
    
    generator = DocumentTTLGenerator(doc_id)
    
    try:
        # Generate TTL content
        ttl_content = generator.generate_ttl_document()
        
        # Save to file
        output_path = f"../../docs/schema/actual_document_{doc_id}.ttl"
        generator.save_ttl_document(ttl_content, output_path)
        
        print(f"Successfully generated TTL document from actual data!")
        print(f"Output saved to: {output_path}")
        print(f"\nFirst 1500 characters of generated TTL:")
        print("-" * 60)
        print(ttl_content[:1500])
        print("-" * 60)
        
        # Show some statistics
        lines = ttl_content.split('\n')
        chunk_lines = [line for line in lines if 'DocumentChunk' in line]
        section_lines = [line for line in lines if 'DocumentSection' in line]
        
        print(f"\nDocument Statistics:")
        print(f"- Total lines: {len(lines)}")
        print(f"- Sections: {len(section_lines)}")
        print(f"- Chunks: {len(chunk_lines)}")
        
    except Exception as e:
        logger.error(f"Failed to generate TTL document: {e}")
        raise

if __name__ == "__main__":
    main()
