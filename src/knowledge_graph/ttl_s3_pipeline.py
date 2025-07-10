#!/usr/bin/env python3
"""
TTL S3 Pipeline
Generate TTL files from processed documents and upload to S3 for Neptune bulk loading
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
from generate_example_from_data_fixed import DocumentTTLGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TTLPipeline:
    """Pipeline for generating and uploading TTL files to S3 for Neptune bulk loading"""
    
    def __init__(self, aws_profile: str = 'solve-global'):
        self.session = boto3.Session(profile_name=aws_profile)
        self.s3 = self.session.client('s3', region_name='us-east-1')
        
        # S3 buckets
        self.ttl_bucket = 'solve-global-kr-neptune-ttl-861276078413-us-east-1'
        self.chunks_bucket = 'solve-global-kr-chunks-861276078413-us-east-1'
        self.text_bucket = 'solve-global-kr-text-new-861276078413-us-east-1'
        
        # TTL generation
        self.uri_facility = URIMintingFacility()
        
    def generate_document_ttl_files(self, doc_id: str) -> Dict[str, str]:
        """Generate separate TTL files for a document"""
        logger.info(f"Generating TTL files for document: {doc_id}")
        
        # Use our existing TTL generator
        generator = DocumentTTLGenerator(doc_id)
        
        try:
            # Get document metadata and chunks
            doc_metadata = generator.get_document_metadata()
            chunks_data = generator.get_actual_chunks_data()
            
            if not chunks_data:
                raise ValueError(f"No chunks found for document {doc_id}")
            
            # Generate separate TTL files
            ttl_files = {}
            
            # 1. Document root and sections TTL
            document_ttl = self.generate_document_structure_ttl(doc_id, doc_metadata, chunks_data)
            ttl_files['document.ttl'] = document_ttl
            
            # 2. Chunks TTL (separate for easier management)
            chunks_ttl = self.generate_chunks_ttl(doc_id, chunks_data)
            ttl_files['chunks.ttl'] = chunks_ttl
            
            # 3. Metadata JSON
            metadata = self.generate_metadata(doc_id, doc_metadata, chunks_data)
            ttl_files['metadata.json'] = json.dumps(metadata, indent=2)
            
            logger.info(f"Generated {len(ttl_files)} files for document {doc_id}")
            return ttl_files
            
        except Exception as e:
            logger.error(f"Error generating TTL files for {doc_id}: {e}")
            raise
    
    def generate_document_structure_ttl(self, doc_id: str, metadata: Dict, chunks_data: List[Dict]) -> str:
        """Generate TTL for document root and sections only"""
        
        ttl_content = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix sg: <http://solve.global/knowledge-commons/> .
@prefix kr: <http://solve.global/knowledge-commons/schema#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix dcterms: <http://purl.org/dc/terms/> .

"""
        
        ttl_content += f"""# =============================================================================
# DOCUMENT STRUCTURE: {doc_id}
# Generated: {datetime.now().isoformat()}
# =============================================================================

"""
        
        # Document root
        doc_uri = self.uri_facility.mint_uri(URIType.DOCUMENT, doc_id=doc_id)
        ttl_content += f"""{self.format_uri(doc_uri)} a kr:Document ;
    dcterms:title "{self.escape_ttl_string(metadata['title'])}" ;
    dcterms:created "{metadata['created']}"^^xsd:dateTime ;
    kr:processingTimestamp "{datetime.now().isoformat()}"^^xsd:dateTime ;
    kr:wordCount "{metadata['word_count']}"^^xsd:nonNegativeInteger ;
    kr:sentenceCount "{metadata['sentence_count']}"^^xsd:nonNegativeInteger"""
        
        if metadata.get('page_count', 0) > 0:
            ttl_content += f" ;\n    kr:pageCount \"{metadata['page_count']}\"^^xsd:nonNegativeInteger"
        
        ttl_content += " .\n\n"
        
        # Group chunks by section for section generation
        sections = {}
        for chunk in chunks_data:
            section_seq = chunk['section_sequence']
            if section_seq not in sections:
                sections[section_seq] = {
                    'chunks': [],
                    'title': chunk['section_title']
                }
            sections[section_seq]['chunks'].append(chunk)
        
        # Generate sections
        for section_seq in sorted(sections.keys()):
            section_data = sections[section_seq]
            section_chunks = section_data['chunks']
            section_title = section_data['title']
            
            section_uri = self.uri_facility.mint_uri(
                URIType.DOCUMENT_SECTION,
                doc_id=doc_id,
                section_sequence=section_seq
            )
            
            # Calculate section metrics
            total_words = sum(chunk['word_count'] for chunk in section_chunks)
            total_sentences = sum(chunk['sentence_count'] for chunk in section_chunks)
            
            ttl_content += f"""{self.format_uri(section_uri)} a kr:DocumentSection ;
    dcterms:title "{self.escape_ttl_string(section_title)}" ;
    kr:sectionSequence "{section_seq}"^^xsd:positiveInteger ;
    kr:hierarchyLevel "1"^^xsd:positiveInteger ;
    kr:parentDocument {self.format_uri(doc_uri)} ;
    kr:wordCount "{total_words}"^^xsd:nonNegativeInteger ;
    kr:sentenceCount "{total_sentences}"^^xsd:nonNegativeInteger"""
            
            # Add chunk references
            for chunk in section_chunks:
                chunk_uri = self.uri_facility.mint_uri(
                    URIType.DOCUMENT_CHUNK,
                    doc_id=doc_id,
                    section_sequence=section_seq,
                    chunk_sequence=chunk['chunk_sequence']
                )
                ttl_content += f" ;\n    kr:hasChunk {self.format_uri(chunk_uri)}"
            
            ttl_content += " .\n\n"
        
        return ttl_content
    
    def generate_chunks_ttl(self, doc_id: str, chunks_data: List[Dict]) -> str:
        """Generate TTL for all chunks"""
        
        ttl_content = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix sg: <http://solve.global/knowledge-commons/> .
@prefix kr: <http://solve.global/knowledge-commons/schema#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix dcterms: <http://purl.org/dc/terms/> .

"""
        
        ttl_content += f"""# =============================================================================
# DOCUMENT CHUNKS: {doc_id}
# Generated: {datetime.now().isoformat()}
# =============================================================================

"""
        
        # Generate individual chunks
        for chunk in chunks_data:
            section_seq = chunk['section_sequence']
            chunk_seq = chunk['chunk_sequence']
            
            chunk_uri = self.uri_facility.mint_uri(
                URIType.DOCUMENT_CHUNK,
                doc_id=doc_id,
                section_sequence=section_seq,
                chunk_sequence=chunk_seq
            )
            
            section_uri = self.uri_facility.mint_uri(
                URIType.DOCUMENT_SECTION,
                doc_id=doc_id,
                section_sequence=section_seq
            )
            
            doc_uri = self.uri_facility.mint_uri(URIType.DOCUMENT, doc_id=doc_id)
            
            # Use first 300 chars of text for content preview
            display_text = chunk['text'][:300] if chunk['text'] else ""
            if len(chunk.get('text', '')) > 300:
                display_text += "..."
            display_text = self.escape_ttl_string(display_text)
            
            ttl_content += f"""{self.format_uri(chunk_uri)} a kr:DocumentChunk ;
    kr:chunkSequence "{chunk_seq}"^^xsd:positiveInteger ;
    kr:parentSection {self.format_uri(section_uri)} ;
    kr:parentDocument {self.format_uri(doc_uri)} ;
    kr:textContent "{display_text}" ;
    kr:wordCount "{chunk['word_count']}"^^xsd:nonNegativeInteger ;
    kr:sentenceCount "{chunk['sentence_count']}"^^xsd:nonNegativeInteger ;
    kr:chunkingStrategy "smart_structured" ;
    kr:s3Location "{chunk['s3_location']}"^^xsd:anyURI ;
    kr:s3Bucket "{self.chunks_bucket}" ;
    kr:s3Key "{chunk['s3_key']}" ;
    kr:processingTimestamp "{chunk['last_modified']}"^^xsd:dateTime"""
            
            # Add character offsets if available
            if 'char_start' in chunk and 'char_end' in chunk:
                ttl_content += f" ;\n    kr:characterStart \"{chunk['char_start']}\"^^xsd:nonNegativeInteger"
                ttl_content += f" ;\n    kr:characterEnd \"{chunk['char_end']}\"^^xsd:nonNegativeInteger"
            
            ttl_content += " .\n\n"
        
        return ttl_content
    
    def generate_metadata(self, doc_id: str, doc_metadata: Dict, chunks_data: List[Dict]) -> Dict:
        """Generate metadata for the TTL files"""
        
        return {
            'doc_id': doc_id,
            'generated_at': datetime.now().isoformat(),
            'document_metadata': doc_metadata,
            'statistics': {
                'total_chunks': len(chunks_data),
                'total_sections': len(set(chunk['section_sequence'] for chunk in chunks_data)),
                'total_words': sum(chunk['word_count'] for chunk in chunks_data),
                'total_sentences': sum(chunk['sentence_count'] for chunk in chunks_data)
            },
            'files': {
                'document.ttl': 'Document structure and sections',
                'chunks.ttl': 'All document chunks',
                'metadata.json': 'This metadata file'
            },
            's3_locations': {
                'ttl_bucket': self.ttl_bucket,
                'chunks_bucket': self.chunks_bucket,
                'text_bucket': self.text_bucket
            }
        }
    
    def upload_ttl_files(self, doc_id: str, ttl_files: Dict[str, str]) -> Dict[str, str]:
        """Upload TTL files to S3"""
        logger.info(f"Uploading TTL files for document {doc_id}")
        
        s3_locations = {}
        
        for filename, content in ttl_files.items():
            s3_key = f"documents/{doc_id}/{filename}"
            
            try:
                self.s3.put_object(
                    Bucket=self.ttl_bucket,
                    Key=s3_key,
                    Body=content.encode('utf-8'),
                    ContentType='text/turtle' if filename.endswith('.ttl') else 'application/json'
                )
                
                s3_location = f"s3://{self.ttl_bucket}/{s3_key}"
                s3_locations[filename] = s3_location
                logger.info(f"Uploaded {filename} to {s3_location}")
                
            except Exception as e:
                logger.error(f"Failed to upload {filename}: {e}")
                raise
        
        return s3_locations
    
    def process_document(self, doc_id: str) -> Dict[str, Any]:
        """Complete pipeline: generate TTL files and upload to S3"""
        logger.info(f"Processing document {doc_id} for Neptune loading")
        
        try:
            # Generate TTL files
            ttl_files = self.generate_document_ttl_files(doc_id)
            
            # Upload to S3
            s3_locations = self.upload_ttl_files(doc_id, ttl_files)
            
            # Return processing summary
            result = {
                'doc_id': doc_id,
                'status': 'success',
                'processed_at': datetime.now().isoformat(),
                'files_generated': list(ttl_files.keys()),
                's3_locations': s3_locations,
                'statistics': {
                    'document_ttl_size': len(ttl_files['document.ttl']),
                    'chunks_ttl_size': len(ttl_files['chunks.ttl']),
                    'metadata_size': len(ttl_files['metadata.json'])
                }
            }
            
            logger.info(f"Successfully processed document {doc_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process document {doc_id}: {e}")
            return {
                'doc_id': doc_id,
                'status': 'error',
                'error': str(e),
                'processed_at': datetime.now().isoformat()
            }
    
    def escape_ttl_string(self, text: str) -> str:
        """Escape string for TTL format"""
        if not text:
            return ""
        
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

def main():
    """Main function to process a document"""
    
    # Test with our sample document
    doc_id = "0032f6cb_f0caef34"
    
    print(f"🚀 TTL S3 PIPELINE - Processing Document: {doc_id}")
    print("=" * 60)
    
    pipeline = TTLPipeline()
    
    try:
        result = pipeline.process_document(doc_id)
        
        if result['status'] == 'success':
            print("✅ Document processing completed successfully!")
            print(f"📁 Files generated: {', '.join(result['files_generated'])}")
            print(f"📊 Statistics:")
            print(f"   - Document TTL: {result['statistics']['document_ttl_size']:,} bytes")
            print(f"   - Chunks TTL: {result['statistics']['chunks_ttl_size']:,} bytes")
            print(f"   - Metadata: {result['statistics']['metadata_size']:,} bytes")
            print(f"🔗 S3 Locations:")
            for filename, location in result['s3_locations'].items():
                print(f"   - {filename}: {location}")
            
            return True
        else:
            print(f"❌ Document processing failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Pipeline error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
