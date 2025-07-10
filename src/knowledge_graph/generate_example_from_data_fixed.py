#!/usr/bin/env python3
"""
Generate Example Document from Actual Processed Data - FIXED VERSION
Creates TTL representation from real S3 JSON chunk structure
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
        
        # Actual S3 bucket names and structure
        self.text_bucket = 'solve-global-kr-text-new-861276078413-us-east-1'
        self.chunks_bucket = 'solve-global-kr-chunks-861276078413-us-east-1'
        
        # TTL prefixes - Updated for Dublin Core integration
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
# ACTUAL DOCUMENT DATA: {self.doc_id}
# Generated from real S3 JSON chunk structure
# Generated: {datetime.now().isoformat()}
# =============================================================================

"""
        
        try:
            # Get document metadata from actual text file
            doc_metadata = self.get_document_metadata()
            
            # Generate document root
            ttl_content += self.generate_document_root(doc_metadata)
            
            # Get actual chunks from S3 JSON files
            chunks_data = self.get_actual_chunks_data()
            if chunks_data:
                ttl_content += self.generate_sections_and_chunks(chunks_data)
            else:
                ttl_content += "# No chunks data found\n\n"
            
            logger.info(f"Successfully generated TTL document for {self.doc_id}")
            return ttl_content
            
        except Exception as e:
            logger.error(f"Error generating TTL document: {e}")
            raise
    
    def get_document_metadata(self) -> Dict[str, Any]:
        """Get document metadata from actual extracted text file"""
        logger.info("Retrieving document metadata from extracted text")
        
        metadata = {
            'doc_id': self.doc_id,
            'title': f'Document {self.doc_id}',
            'created': datetime.now().isoformat(),
            'word_count': 0,
            'sentence_count': 0,
            'page_count': 0
        }
        
        try:
            # Get actual extracted text file
            text_key = f'extracted_text/{self.doc_id}.txt'
            response = self.s3.get_object(Bucket=self.text_bucket, Key=text_key)
            full_text = response['Body'].read().decode('utf-8')
            
            # Calculate actual metrics
            words = full_text.split()
            metadata['word_count'] = len(words)
            metadata['sentence_count'] = full_text.count('.') + full_text.count('!') + full_text.count('?')
            
            # Count actual pages
            page_markers = full_text.count('--- Page')
            if page_markers > 0:
                metadata['page_count'] = page_markers
            
            # Extract actual title from first meaningful line
            lines = full_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('---') and len(line) > 10 and len(line) < 100:
                    if not re.match(r'^\d+[\.\s]', line):
                        metadata['title'] = line
                        break
                        
            logger.info(f"Document metadata: {metadata['word_count']} words, {metadata['page_count']} pages")
                        
        except Exception as e:
            logger.warning(f"Could not retrieve full text: {e}")
        
        return metadata
    
    def get_actual_chunks_data(self) -> List[Dict[str, Any]]:
        """Get actual chunk data from S3 JSON files"""
        logger.info("Retrieving actual chunks from S3 JSON files")
        
        chunks = []
        try:
            # List all files in the document's S3 folder
            response = self.s3.list_objects_v2(
                Bucket=self.chunks_bucket,
                Prefix=f'{self.doc_id}/'
            )
            
            if 'Contents' not in response:
                logger.warning(f"No files found for document {self.doc_id}")
                return chunks
            
            # Filter for actual chunk JSON files (not metadata files)
            chunk_files = []
            for obj in response['Contents']:
                key = obj['Key']
                # Look for pattern: doc_id/doc_id_chunk_NNNN.json
                if key.endswith('.json') and '_chunk_' in key and not 'metadata' in key:
                    chunk_files.append(obj)
            
            logger.info(f"Found {len(chunk_files)} chunk JSON files")
            
            # Process each chunk file
            for obj in chunk_files:
                key = obj['Key']
                try:
                    # Get chunk JSON content
                    chunk_response = self.s3.get_object(Bucket=self.chunks_bucket, Key=key)
                    chunk_data = json.loads(chunk_response['Body'].read().decode('utf-8'))
                    
                    # Extract chunk information from actual JSON structure
                    chunk_info = self.process_chunk_json(chunk_data, obj)
                    chunks.append(chunk_info)
                    
                except Exception as e:
                    logger.warning(f"Could not process chunk {key}: {e}")
            
            # Sort chunks by actual sequence number
            chunks.sort(key=lambda x: x.get('chunk_sequence', 0))
            logger.info(f"Successfully processed {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error retrieving chunks: {e}")
        
        return chunks
    
    def process_chunk_json(self, chunk_data: Dict, s3_obj: Dict) -> Dict[str, Any]:
        """Process actual chunk JSON structure"""
        
        # Extract data from actual JSON structure
        chunk_info = {
            'chunk_id': chunk_data.get('chunk_id', ''),
            'chunk_sequence': chunk_data.get('chunk_sequence', 0),
            'text': chunk_data.get('text', ''),
            's3_location': f's3://{self.chunks_bucket}/{s3_obj["Key"]}',
            's3_key': s3_obj['Key'],
            'last_modified': s3_obj['LastModified'].isoformat(),
        }
        
        # Calculate metrics from actual text
        text = chunk_info['text']
        chunk_info['word_count'] = len(text.split()) if text else 0
        
        # Get actual sentence count from offsets if available
        offsets = chunk_data.get('offsets', {})
        sentences = offsets.get('sentences', [])
        chunk_info['sentence_count'] = len(sentences)
        
        # Store character offsets if available
        if offsets:
            chunk_info['char_start'] = offsets.get('char_start', 0)
            chunk_info['char_end'] = offsets.get('char_end', 0)
        
        # Infer section from content and sequence
        section_info = self.infer_section_from_content(chunk_info)
        chunk_info.update(section_info)
        
        return chunk_info
    
    def infer_section_from_content(self, chunk_info: Dict) -> Dict[str, Any]:
        """Infer document section from chunk content and sequence"""
        
        text = chunk_info['text'].lower()
        chunk_seq = chunk_info['chunk_sequence']
        
        # Content-based section detection
        if any(keyword in text for keyword in ['procurement plan', 'introduction', 'general', 'approval']):
            return {'section_sequence': 1, 'section_title': 'Introduction and Overview'}
        elif any(keyword in text for keyword in ['prior review', 'threshold', 'procurement method', 'icb', 'ncb']):
            return {'section_sequence': 2, 'section_title': 'Procurement Guidelines'}  
        elif any(keyword in text for keyword in ['implementation', 'schedule', 'effectiveness', 'package']):
            return {'section_sequence': 3, 'section_title': 'Implementation Details'}
        elif any(keyword in text for keyword in ['appendix', 'annex', 'reference', 'attachment']):
            return {'section_sequence': 4, 'section_title': 'Appendices and References'}
        else:
            # Fallback to sequence-based grouping
            if chunk_seq <= 3:
                return {'section_sequence': 1, 'section_title': 'Introduction and Overview'}
            elif chunk_seq <= 8:
                return {'section_sequence': 2, 'section_title': 'Procurement Guidelines'}
            elif chunk_seq <= 15:
                return {'section_sequence': 3, 'section_title': 'Implementation Details'}
            else:
                return {'section_sequence': 4, 'section_title': 'Appendices and References'}
    
    def generate_document_root(self, metadata: Dict[str, Any]) -> str:
        """Generate document root TTL using Dublin Core vocabulary"""
        doc_uri = self.uri_facility.mint_uri(URIType.DOCUMENT, doc_id=self.doc_id)
        
        ttl = f"""# -----------------------------------------------------------------------------
# DOCUMENT ROOT (From Actual S3 Data) - Dublin Core Integration
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
    kr:sentenceCount "{metadata['sentence_count']}"^^xsd:nonNegativeInteger"""
        
        if metadata['page_count'] > 0:
            ttl += f" ;\n    kr:pageCount \"{metadata['page_count']}\"^^xsd:nonNegativeInteger"
        
        ttl += " ."
        
        return ttl + "\n\n"
    
    def generate_sections_and_chunks(self, chunks: List[Dict[str, Any]]) -> str:
        """Generate sections and chunks TTL from actual chunk data"""
        
        ttl = """# -----------------------------------------------------------------------------
# DOCUMENT SECTIONS AND CHUNKS (From Actual S3 JSON Files)
# -----------------------------------------------------------------------------

"""
        
        # Group chunks by inferred sections
        sections = {}
        for chunk in chunks:
            section_seq = chunk['section_sequence']
            if section_seq not in sections:
                sections[section_seq] = {
                    'chunks': [],
                    'title': chunk['section_title']
                }
            sections[section_seq]['chunks'].append(chunk)
        
        # Generate section TTL
        for section_seq in sorted(sections.keys()):
            section_data = sections[section_seq]
            section_chunks = section_data['chunks']
            section_title = section_data['title']
            
            section_uri = self.uri_facility.mint_uri(
                URIType.DOCUMENT_SECTION,
                doc_id=self.doc_id,
                section_sequence=section_seq
            )
            
            # Calculate section metrics from actual chunks
            total_words = sum(chunk['word_count'] for chunk in section_chunks)
            total_sentences = sum(chunk['sentence_count'] for chunk in section_chunks)
            
            ttl += f"""{self.format_uri(section_uri)} a kr:DocumentSection ;
    dcterms:title "{self.escape_ttl_string(section_title)}" ;
    dcterms:isPartOf {self.format_uri(self.uri_facility.mint_uri(URIType.DOCUMENT, doc_id=self.doc_id))} ;
    dcterms:extent "{total_words} words, {total_sentences} sentences" ;
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
        
        # Generate individual chunk TTL
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
            
            # Generate chunk URI with Dublin Core metadata
            ttl += f"""{self.format_uri(chunk_uri)} a kr:DocumentChunk ;
    dcterms:identifier "{chunk_uri.split('/')[-1]}" ;
    dcterms:isPartOf {self.format_uri(section_uri)} ;
    dcterms:title "{self.escape_ttl_string(chunk.get('title', f'Chunk {chunk_seq}'))}" ;
    dcterms:modified "{chunk['last_modified']}"^^xsd:dateTime ;
    dcterms:extent "{chunk['word_count']} words, {chunk['sentence_count']} sentences" ;
    kr:chunkSequence "{chunk_seq}"^^xsd:positiveInteger ;
    kr:parentSection {self.format_uri(section_uri)} ;
    kr:parentDocument {self.format_uri(self.uri_facility.mint_uri(URIType.DOCUMENT, doc_id=self.doc_id))} ;
    kr:wordCount "{chunk['word_count']}"^^xsd:nonNegativeInteger ;
    kr:sentenceCount "{chunk['sentence_count']}"^^xsd:nonNegativeInteger ;
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
    
    def escape_ttl_string(self, text: str) -> str:
        """Escape string for TTL format"""
        if not text:
            return ""
        
        # Replace problematic characters for TTL
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
    """Main function to generate example document from real S3 structure"""
    doc_id = "0032f6cb_f0caef34"  # Our test document
    
    generator = DocumentTTLGenerator(doc_id)
    
    try:
        # Generate TTL content from actual S3 data
        ttl_content = generator.generate_ttl_document()
        
        # Save to file
        output_path = f"../../docs/schema/real_s3_document_{doc_id}.ttl"
        generator.save_ttl_document(ttl_content, output_path)
        
        print(f"✅ Successfully generated TTL document from real S3 structure!")
        print(f"📁 Output saved to: {output_path}")
        print(f"\n📊 First 1500 characters of generated TTL:")
        print("-" * 60)
        print(ttl_content[:1500])
        print("-" * 60)
        
        # Show statistics
        lines = ttl_content.split('\n')
        chunk_lines = [line for line in lines if 'DocumentChunk' in line and ' a kr:' in line]
        section_lines = [line for line in lines if 'DocumentSection' in line and ' a kr:' in line]
        
        print(f"\n📈 Document Statistics:")
        print(f"   - Total TTL lines: {len(lines)}")
        print(f"   - Document sections: {len(section_lines)}")
        print(f"   - Document chunks: {len(chunk_lines)}")
        print(f"   - Generated from real S3 JSON files")
        
    except Exception as e:
        logger.error(f"❌ Failed to generate TTL document: {e}")
        raise

if __name__ == "__main__":
    main()
