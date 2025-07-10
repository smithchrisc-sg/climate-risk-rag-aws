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
        
        # S3 bucket names
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
            ttl_content += self.generate_chunks_section(chunks_data)
            
            # Get Textract structure if available
            textract_data = self.get_textract_structure()
            if textract_data:
                ttl_content += self.generate_textract_elements(textract_data)
            
            logger.info(f"Successfully generated TTL document for {self.doc_id}")
            return ttl_content
            
        except Exception as e:
            logger.error(f"Error generating TTL document: {e}")
            raise
    
    def get_document_metadata(self) -> Dict[str, Any]:
        """Get document metadata from S3"""
        logger.info("Retrieving document metadata")
        
        # Try to get document info from various sources
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
            text_key = f'{self.doc_id}.txt'
            response = self.s3.get_object(Bucket=self.text_bucket, Key=text_key)
            full_text = response['Body'].read().decode('utf-8')
            
            # Calculate basic metrics
            metadata['word_count'] = len(full_text.split())
            metadata['sentence_count'] = full_text.count('.') + full_text.count('!') + full_text.count('?')
            
            # Try to extract title from first line
            first_lines = full_text.split('\n')[:5]
            for line in first_lines:
                line = line.strip()
                if len(line) > 10 and len(line) < 100:  # Reasonable title length
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
            
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('.txt'):
                    try:
                        # Get chunk content
                        chunk_response = self.s3.get_object(Bucket=self.chunks_bucket, Key=key)
                        chunk_text = chunk_response['Body'].read().decode('utf-8')
                        
                        # Parse chunk info from key
                        chunk_info = self.parse_chunk_key(key)
                        chunk_info.update({
                            'text': chunk_text,
                            'word_count': len(chunk_text.split()),
                            'sentence_count': chunk_text.count('.') + chunk_text.count('!') + chunk_text.count('?'),
                            's3_location': f's3://{self.chunks_bucket}/{key}',
                            'last_modified': obj['LastModified'].isoformat()
                        })
                        
                        chunks.append(chunk_info)
                        
                    except Exception as e:
                        logger.warning(f"Could not process chunk {key}: {e}")
            
            # Sort chunks by section and sequence
            chunks.sort(key=lambda x: (x.get('section_sequence', 0), x.get('chunk_sequence', 0)))
            logger.info(f"Retrieved {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error retrieving chunks: {e}")
        
        return chunks
    
    def parse_chunk_key(self, key: str) -> Dict[str, Any]:
        """Parse chunk information from S3 key"""
        # Expected format: doc_id/section_X_chunk_Y.txt or similar
        parts = key.split('/')
        filename = parts[-1].replace('.txt', '')
        
        chunk_info = {
            'section_sequence': 1,
            'chunk_sequence': 1,
            'section_title': 'Unknown Section'
        }
        
        # Try to parse section and chunk numbers
        if 'section_' in filename and 'chunk_' in filename:
            try:
                section_part = filename.split('section_')[1].split('_chunk_')[0]
                chunk_part = filename.split('_chunk_')[1]
                
                # Handle subsections (e.g., section_2_1_chunk_3)
                if '_' in section_part:
                    section_parts = section_part.split('_')
                    chunk_info['section_sequence'] = int(section_parts[0])
                    chunk_info['subsection_sequence'] = int(section_parts[1])
                else:
                    chunk_info['section_sequence'] = int(section_part)
                
                chunk_info['chunk_sequence'] = int(chunk_part)
                
            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse chunk key {key}: {e}")
        
        return chunk_info
    
    def get_textract_structure(self) -> Optional[Dict[str, Any]]:
        """Get Textract structure data if available"""
        logger.info("Attempting to retrieve Textract structure")
        
        # Try various possible locations for Textract data
        possible_keys = [
            f'{self.doc_id}_textract.json',
            f'{self.doc_id}/textract_output.json',
            f'textract/{self.doc_id}.json'
        ]
        
        for key in possible_keys:
            try:
                response = self.s3.get_object(Bucket=self.documents_bucket, Key=key)
                textract_data = json.loads(response['Body'].read().decode('utf-8'))
                logger.info(f"Found Textract data at {key}")
                return textract_data
            except Exception:
                continue
        
        logger.warning("No Textract structure data found")
        return None
    
    def generate_document_root(self, metadata: Dict[str, Any]) -> str:
        """Generate document root TTL"""
        doc_uri = self.uri_facility.mint_uri(URIType.DOCUMENT, doc_id=self.doc_id)
        
        ttl = f"""# -----------------------------------------------------------------------------
# DOCUMENT ROOT
# -----------------------------------------------------------------------------

{self.format_uri(doc_uri)} a kr:Document ;
    dcterms:title "{metadata['title']}" ;
    dcterms:created "{metadata['created']}"^^xsd:dateTime ;
    kr:processingTimestamp "{datetime.now().isoformat()}"^^xsd:dateTime ;
    kr:wordCount "{metadata['word_count']}"^^xsd:nonNegativeInteger ;
    kr:sentenceCount "{metadata['sentence_count']}"^^xsd:nonNegativeInteger ."""
        
        return ttl + "\n\n"
    
    def generate_chunks_section(self, chunks: List[Dict[str, Any]]) -> str:
        """Generate chunks section TTL"""
        if not chunks:
            return "# No chunks found\n\n"
        
        ttl = """# -----------------------------------------------------------------------------
# DOCUMENT CHUNKS (From Actual Processing Results)
# -----------------------------------------------------------------------------

"""
        
        # Group chunks by section
        sections = {}
        for chunk in chunks:
            section_key = chunk['section_sequence']
            if 'subsection_sequence' in chunk:
                section_key = f"{section_key}_{chunk['subsection_sequence']}"
            
            if section_key not in sections:
                sections[section_key] = []
            sections[section_key].append(chunk)
        
        # Generate section URIs first
        for section_key, section_chunks in sections.items():
            section_parts = str(section_key).split('_')
            section_seq = int(section_parts[0])
            subsection_seq = int(section_parts[1]) if len(section_parts) > 1 else None
            
            section_uri = self.uri_facility.mint_uri(
                URIType.DOCUMENT_SECTION,
                doc_id=self.doc_id,
                section_sequence=section_seq,
                subsection_sequence=subsection_seq
            )
            
            section_title = f"Section {section_key}"
            hierarchy_level = 2 if subsection_seq else 1
            
            # Calculate section metrics
            total_words = sum(chunk['word_count'] for chunk in section_chunks)
            total_sentences = sum(chunk['sentence_count'] for chunk in section_chunks)
            
            ttl += f"""{self.format_uri(section_uri)} a kr:DocumentSection ;
    dcterms:title "{section_title}" ;
    kr:sectionSequence "{section_seq}"^^xsd:positiveInteger ;
    kr:hierarchyLevel "{hierarchy_level}"^^xsd:positiveInteger ;
    kr:parentDocument {self.format_uri(self.uri_facility.mint_uri(URIType.DOCUMENT, doc_id=self.doc_id))} ;
    kr:wordCount "{total_words}"^^xsd:nonNegativeInteger ;
    kr:sentenceCount "{total_sentences}"^^xsd:nonNegativeInteger"""
            
            # Add chunk references
            for chunk in section_chunks:
                chunk_uri = self.uri_facility.mint_uri(
                    URIType.DOCUMENT_CHUNK,
                    doc_id=self.doc_id,
                    section_sequence=section_seq,
                    subsection_sequence=subsection_seq,
                    chunk_sequence=chunk['chunk_sequence']
                )
                ttl += f" ;\n    kr:hasChunk {self.format_uri(chunk_uri)}"
            
            ttl += " .\n\n"
        
        # Generate individual chunks
        for chunk in chunks:
            section_seq = chunk['section_sequence']
            subsection_seq = chunk.get('subsection_sequence')
            chunk_seq = chunk['chunk_sequence']
            
            chunk_uri = self.uri_facility.mint_uri(
                URIType.DOCUMENT_CHUNK,
                doc_id=self.doc_id,
                section_sequence=section_seq,
                subsection_sequence=subsection_seq,
                chunk_sequence=chunk_seq
            )
            
            section_uri = self.uri_facility.mint_uri(
                URIType.DOCUMENT_SECTION,
                doc_id=self.doc_id,
                section_sequence=section_seq,
                subsection_sequence=subsection_seq
            )
            
            # Truncate text for TTL (first 200 chars)
            display_text = chunk['text'][:200].replace('"', '\\"').replace('\n', ' ')
            if len(chunk['text']) > 200:
                display_text += "..."
            
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
    kr:s3Key "{chunk['s3_location'].split('/')[-1]}" ;
    kr:processingTimestamp "{chunk['last_modified']}"^^xsd:dateTime .

"""
        
        return ttl
    
    def generate_textract_elements(self, textract_data: Dict[str, Any]) -> str:
        """Generate Textract elements TTL (basic implementation)"""
        ttl = """# -----------------------------------------------------------------------------
# TEXTRACT STRUCTURE ELEMENTS (Sample)
# -----------------------------------------------------------------------------

"""
        
        # This is a simplified implementation - would need full Textract parsing
        # for complete structure
        ttl += f"# Textract data available but not fully parsed in this example\n"
        ttl += f"# Blocks found: {len(textract_data.get('Blocks', []))}\n\n"
        
        return ttl
    
    def format_uri(self, uri: str) -> str:
        """Format URI for TTL output"""
        if uri.startswith('http://solve.global/knowledge-commons/'):
            return uri.replace('http://solve.global/knowledge-commons/', 'sg:')
        return f"<{uri}>"
    
    def save_ttl_document(self, ttl_content: str, output_path: str):
        """Save TTL document to file"""
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
        print(f"\nFirst 1000 characters of generated TTL:")
        print("-" * 50)
        print(ttl_content[:1000])
        print("-" * 50)
        
    except Exception as e:
        logger.error(f"Failed to generate TTL document: {e}")
        raise

if __name__ == "__main__":
    main()
