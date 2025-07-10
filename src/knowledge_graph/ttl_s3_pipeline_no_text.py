#!/usr/bin/env python3
"""
TTL S3 Pipeline - No Text Content Version
Generate TTL files without kr:textContent to avoid UTF-8 issues
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

class TTLPipelineNoText(DocumentTTLGenerator):
    """TTL pipeline that excludes textContent to avoid UTF-8 encoding issues"""
    
    def __init__(self, doc_id: str, aws_profile: str = 'solve-global'):
        super().__init__(doc_id, aws_profile)
        self.uri_facility = URIMintingFacility()
    
    def generate_chunks_ttl(self, doc_id: str, chunks_data: List[Dict]) -> str:
        """Generate TTL for all chunks WITHOUT textContent"""
        
        ttl_content = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix sg: <http://solve.global/knowledge-commons/> .
@prefix kr: <http://solve.global/knowledge-commons/schema#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix dcterms: <http://purl.org/dc/terms/> .

"""
        
        ttl_content += f"""# =============================================================================
# DOCUMENT CHUNKS: {doc_id} (NO TEXT CONTENT)
# Generated: {datetime.now().isoformat()}
# Note: kr:textContent excluded to avoid UTF-8 encoding issues
# Full text available via kr:s3Location
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
            
            # Generate chunk TTL WITHOUT textContent
            ttl_content += f"""{self.format_uri(chunk_uri)} a kr:DocumentChunk ;
    kr:chunkSequence "{chunk_seq}"^^xsd:positiveInteger ;
    kr:parentSection {self.format_uri(section_uri)} ;
    kr:parentDocument {self.format_uri(doc_uri)} ;
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

def main():
    """Test the no-text TTL generation"""
    
    doc_id = "0032f6cb_f0caef34"
    
    print(f"🚀 TTL PIPELINE (NO TEXT CONTENT) - Processing Document: {doc_id}")
    print("=" * 60)
    
    try:
        generator = TTLPipelineNoText(doc_id)
        
        # Get document metadata and chunks
        doc_metadata = generator.get_document_metadata()
        chunks_data = generator.get_actual_chunks_data()
        
        if not chunks_data:
            print("❌ No chunks found")
            return False
        
        # Generate TTL files without text content
        document_ttl = generator.generate_document_structure_ttl(doc_id, doc_metadata, chunks_data)
        chunks_ttl = generator.generate_chunks_ttl(doc_id, chunks_data)
        
        # Save files locally for inspection
        with open('/tmp/document_no_text.ttl', 'w', encoding='utf-8') as f:
            f.write(document_ttl)
        
        with open('/tmp/chunks_no_text.ttl', 'w', encoding='utf-8') as f:
            f.write(chunks_ttl)
        
        print("✅ TTL files generated successfully!")
        print(f"📁 Document TTL: {len(document_ttl)} bytes")
        print(f"📁 Chunks TTL: {len(chunks_ttl)} bytes")
        print(f"📊 Chunks processed: {len(chunks_data)}")
        print(f"💾 Files saved to /tmp/ for inspection")
        
        # Show sample of chunks TTL
        print(f"\n📋 Sample chunks TTL (first 500 chars):")
        print("-" * 50)
        print(chunks_ttl[:500])
        print("-" * 50)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
