#!/usr/bin/env python3
"""
Integrated RDF and Chunk Generator for Solution Ingestion

🏭 PRODUCTION GENERATOR: This is the ONLY generator used in production.
🏭 All RDF generation and chunk creation goes through this class.
🏭 Do not use any other generators - they are deprecated.

Creates RDF structure while simultaneously generating chunk JSON files.
This ensures perfect consistency and preserves all structural information.
Integrates with EntityMapper for proper URI generation and semantic alignment.
"""

import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import DCTERMS, RDF, XSD

logger = logging.getLogger(__name__)

# Define namespaces
SG = Namespace("http://solve.global/knowledge-commons/")
SGD = Namespace("http://solve.global/knowledge-commons/document-structure#")
SGM = Namespace("http://solve.global/knowledge-commons/process-metadata#")

@dataclass
class IntegratedChunk:
    """Chunk object with all information needed for embeddings and data lake."""
    chunk_id: str           # e.g., "sol_abc123_chunk_0002"
    doc_id: str            # e.g., "sol_abc123"
    chunk_number: int      # e.g., 2
    text: str              # The actual content
    section_title: str     # e.g., "Introduction", "Description"
    character_count: int
    metadata: Dict[str, Any]
    s3_key: str            # S3 path for this chunk
    s3_location: str       # Full S3 URI

class IntegratedRDFChunkGenerator:
    """Generates RDF structure while simultaneously creating chunk JSON files."""
    
    def __init__(self, output_base_path: str = "output_data"):
        self.output_base_path = Path(output_base_path)
        
        # Ensure chunk output directory exists
        self.chunk_output_dir = self.output_base_path / "kr-dl-chunks" / "data-lake"
        self.chunk_output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_document_rdf_and_chunks(self, solution) -> Tuple[str, List[IntegratedChunk]]:
        """Generate RDF and chunks simultaneously, returning both."""
        
        # Use RDFGenerator for document-level RDF (it will do its own entity mapping)
        from .rdf_generator import RDFGenerator
        rdf_gen = RDFGenerator()
        document_graph = rdf_gen.generate_document_graph(solution)
        
        # Parse solution content into sections
        sections_data = self._parse_solution_sections(solution)
        
        # Calculate section and paragraph numbering
        section_structure = self._calculate_section_structure(sections_data)
        
        # Generate hierarchical structure and chunks simultaneously
        chunks = []
        chunk_graph = self._generate_sections_and_chunks(solution, section_structure, chunks)
        
        # Combine document and chunk graphs
        final_graph = document_graph + chunk_graph
        
        # Add chunk relationships to document
        self._add_chunk_relationships_to_document(final_graph, solution, section_structure)
        
        # Generate organization and contact RDF (no chunks needed)
        if solution.contact_information and solution.contact_information.strip():
            contact_graph = self._generate_organization_contacts(solution.contact_information)
            final_graph += contact_graph
        
        rdf_content = final_graph.serialize(format='turtle')
        
        logger.info(f"Generated RDF ({len(rdf_content)} chars) and {len(chunks)} chunks for {solution.doc_id}")
        return rdf_content, chunks
    
    def _parse_solution_sections(self, solution) -> List[Tuple[str, str]]:
        """Parse solution into sections with content."""
        sections = []
        
        # Build sections list using actual Solution fields
        sections.append(("Introduction", getattr(solution, 'name', '')))
        sections.append(("Description", getattr(solution, 'description', '')))
        sections.append(("Key Highlights", getattr(solution, 'key_highlights', '')))
        sections.append(("Results", getattr(solution, 'results', '')))
        
        return sections
    
    def _calculate_section_structure(self, sections_data: List[Tuple[str, str]]) -> List[Tuple[str, int, int, str, List[str]]]:
        """Calculate section numbers and paragraph structure."""
        current_num = 1
        structure = []
        
        for title, content in sections_data:
            section_num = current_num
            current_num += 1  # Section takes one number
            
            # Split content into paragraphs by single newlines
            if title == 'Introduction':
                paragraphs = [content] if content else [""]
            else:
                paragraphs = [p.strip() for p in content.splitlines() if p.strip()] if content else []
                if not paragraphs:
                    paragraphs = [""]  # Ensure at least one paragraph
            
            para_count = len(paragraphs)
            structure.append((title, section_num, para_count, content, paragraphs))
            current_num += para_count  # Paragraphs take subsequent numbers
        
        return structure
    
    def _generate_sections_and_chunks(self, solution, section_structure, chunks: List[IntegratedChunk]) -> Graph:
        """Generate section RDF and chunk files simultaneously."""
        g = Graph()
        
        # Bind namespaces
        g.bind("dcterms", DCTERMS)
        g.bind("sg", SG)
        g.bind("sgd", SGD)
        g.bind("sgm", SGM)
        g.bind("xsd", XSD)
        
        for i, (title, section_num, para_count, content, paragraphs) in enumerate(section_structure):
            if content or title == 'Introduction':  # Always include Introduction
                
                # Generate paragraph numbers
                paragraph_nums = [section_num + 1 + j for j in range(para_count)]
                
                # Generate section RDF
                section_uri = SG[f"Chunk_{solution.doc_id}_{section_num:04d}"]
                doc_uri = SG[f"Document_{solution.doc_id}"]
                
                g.add((section_uri, RDF.type, SGD.Section))
                g.add((section_uri, SGD.hasParent, doc_uri))
                g.add((section_uri, DCTERMS.title, Literal(title)))
                
                if paragraph_nums:
                    first_para = SG[f"Chunk_{solution.doc_id}_{paragraph_nums[0]:04d}"]
                    last_para = SG[f"Chunk_{solution.doc_id}_{paragraph_nums[-1]:04d}"]
                    
                    g.add((section_uri, SGD.firstChild, first_para))
                    g.add((section_uri, SGD.lastChild, last_para))
                    
                    for num in paragraph_nums:
                        para_uri = SG[f"Chunk_{solution.doc_id}_{num:04d}"]
                        g.add((section_uri, SGD.hasChild, para_uri))
                
                # Add next sibling
                if i < len(section_structure) - 1:
                    next_section_num = section_structure[i + 1][1]
                    next_section_uri = SG[f"Chunk_{solution.doc_id}_{next_section_num:04d}"]
                    g.add((section_uri, SGD.nextSibling, next_section_uri))
                
                # Generate paragraph RDF and chunks simultaneously
                for j, (para_num, paragraph_text) in enumerate(zip(paragraph_nums, paragraphs)):
                    chunk_id = f"{solution.doc_id}_chunk_{para_num:04d}"
                    s3_key = f"data-lake/{solution.doc_id}/{chunk_id}.json"
                    s3_location = f"s3://kr-dl-chunks/{s3_key}"
                    
                    # Generate paragraph RDF
                    para_uri = SG[f"Chunk_{solution.doc_id}_{para_num:04d}"]
                    
                    g.add((para_uri, RDF.type, SGD.Paragraph))
                    g.add((para_uri, SGD.hasParent, section_uri))
                    g.add((para_uri, SGM.chunkId, Literal(chunk_id)))
                    g.add((para_uri, SGM.s3Key, Literal(s3_key)))
                    g.add((para_uri, SGM.s3Location, Literal(s3_location, datatype=XSD.anyURI)))
                    
                    # Add next sibling for paragraphs
                    if j < len(paragraph_nums) - 1:
                        next_para = SG[f"Chunk_{solution.doc_id}_{paragraph_nums[j+1]:04d}"]
                        g.add((para_uri, SGD.nextSibling, next_para))
                    
                    # Create chunk object and JSON file simultaneously
                    chunk = self._create_chunk_and_file(
                        solution, chunk_id, para_num, paragraph_text, title, s3_key, s3_location
                    )
                    chunks.append(chunk)
        
        return g
    
    def _add_chunk_relationships_to_document(self, graph: Graph, solution, section_structure):
        """Add chunk relationship triples to document."""
        doc_uri = SG[f"Document_{solution.doc_id}"]
        
        # Get valid sections (with content or Introduction)
        section_chunks = [info[1] for info in section_structure if info[2] > 0 or info[0] == 'Introduction']
        
        if section_chunks:
            first_section = SG[f"Chunk_{solution.doc_id}_{section_chunks[0]:04d}"]
            last_section = SG[f"Chunk_{solution.doc_id}_{section_chunks[-1]:04d}"]
            
            graph.add((doc_uri, SGD.firstChild, first_section))
            graph.add((doc_uri, SGD.lastChild, last_section))
            
            for section_num in section_chunks:
                section_uri = SG[f"Chunk_{solution.doc_id}_{section_num:04d}"]
                graph.add((doc_uri, SGD.hasChild, section_uri))
    
    def _create_chunk_and_file(self, solution, chunk_id: str, chunk_number: int, 
                              text: str, section_title: str, s3_key: str, s3_location: str) -> IntegratedChunk:
        """Create chunk object and write JSON file simultaneously."""
        
        # Create chunk metadata
        metadata = {
            'solution_id': solution.id,
            'source_file': solution.source_file,
            'row_number': solution.row_number,
            'solution_name': solution.name,
            'country': solution.country,
            'type_of_risk': solution.type_of_risk,
            'type_of_solution': solution.type_of_solution,
            'theme': solution.theme,
            'year_of_implementation': solution.year_of_implementation,
            'ppp': solution.ppp,
            'source_url': solution.source_url,
            'section_title': section_title,
            'chunk_number': chunk_number,
            'content_type': 'solution_paragraph',
            'processing_timestamp': datetime.now().isoformat() + "+00:00"
        }
        
        # Create chunk object
        chunk = IntegratedChunk(
            chunk_id=chunk_id,
            doc_id=solution.doc_id,
            chunk_number=chunk_number,
            text=text,
            section_title=section_title,
            character_count=len(text),
            metadata=metadata,
            s3_key=s3_key,
            s3_location=s3_location
        )
        
        # Write chunk JSON file
        self._write_chunk_json(chunk)
        
        return chunk
    
    def _write_chunk_json(self, chunk: IntegratedChunk):
        """Write chunk JSON file to data lake."""
        chunk_dir = self.chunk_output_dir / chunk.doc_id
        chunk_dir.mkdir(parents=True, exist_ok=True)
        
        chunk_file = chunk_dir / f"{chunk.chunk_id}.json"
        
        chunk_data = {
            'chunk_id': chunk.chunk_id,
            'doc_id': chunk.doc_id,
            'chunk_number': chunk.chunk_number,
            'text': chunk.text,
            'section_title': chunk.section_title,
            'character_count': chunk.character_count,
            'metadata': chunk.metadata,
            's3_key': chunk.s3_key,
            's3_location': chunk.s3_location
        }
        
        with open(chunk_file, 'w', encoding='utf-8') as f:
            json.dump(chunk_data, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"Wrote chunk file: {chunk_file}")
    
    def _generate_organization_contacts(self, contact_info: str) -> Graph:
        """Generate organization and contact RDF from contact information."""
        g = Graph()
        
        # Bind namespaces
        g.bind("org", Namespace("http://www.w3.org/ns/org#"))
        g.bind("schema", Namespace("http://schema.org/"))
        g.bind("skos", Namespace("http://www.w3.org/2004/02/skos/core#"))
        g.bind("sg", SG)
        
        ORG = Namespace("http://www.w3.org/ns/org#")
        SCHEMA = Namespace("http://schema.org/")
        SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
        
        # Parse contact information
        contacts = self._parse_contact_info(contact_info)
        
        for contact in contacts:
            org_uri = self._generate_org_uri(contact['organization'])
            contact_uri = self._generate_contact_uri(contact['organization'])
            
            # Organization RDF
            g.add((org_uri, RDF.type, ORG.Organization))
            g.add((org_uri, SKOS.prefLabel, Literal(contact["organization"])))
            g.add((org_uri, SCHEMA.contactPoint, contact_uri))
            
            # Contact point RDF
            g.add((contact_uri, RDF.type, SCHEMA.ContactPoint))
            
            if contact.get('email'):
                g.add((contact_uri, SCHEMA.email, Literal(contact["email"])))
            if contact.get('phone'):
                g.add((contact_uri, SCHEMA.telephone, Literal(contact["phone"])))
        
        return g
    
    def _parse_contact_info(self, contact_info: str) -> List[Dict[str, str]]:
        """Parse contact information into structured data."""
        contacts = []
        
        # Split by organization entries
        org_blocks = re.split(r'Organization:\s*', contact_info)
        
        for block in org_blocks[1:]:  # Skip first empty split
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            if not lines:
                continue
                
            contact = {'organization': lines[0].rstrip(',')}
            
            for line in lines[1:]:
                if line.startswith('Email:'):
                    email = line.replace('Email:', '').strip().rstrip(',')
                    if email and email != 'Not provided':
                        contact['email'] = email
                elif line.startswith('Contact Number:'):
                    phone = line.replace('Contact Number:', '').strip().rstrip(',')
                    if phone and phone != 'Not provided':
                        contact['phone'] = phone
            
            contacts.append(contact)
        
        return contacts
    
    def _generate_org_uri(self, org_name: str) -> URIRef:
        """Generate consistent URI for organization."""
        normalized = re.sub(r'[^\w\s-]', '', org_name.lower())
        normalized = re.sub(r'\s+', '_', normalized.strip())
        normalized = normalized.replace('__', '_').strip('_')
        return SG[f"Org_{normalized}"]
    
    def _generate_contact_uri(self, org_name: str) -> URIRef:
        """Generate consistent URI for contact point."""
        normalized = re.sub(r'[^\w\s-]', '', org_name.lower())
        normalized = re.sub(r'\s+', '_', normalized.strip())
        normalized = normalized.replace('__', '_').strip('_')
        return SG[f"Contact_{normalized}"]
