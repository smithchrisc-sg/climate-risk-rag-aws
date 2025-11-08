#!/usr/bin/env python3
"""
Integrated RDF and Chunk Generator for Solution Ingestion
Creates RDF structure while simultaneously generating chunk JSON files.
This ensures perfect consistency and preserves all structural information.
"""

import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

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
        self.namespaces = {
            'dcterms': 'http://purl.org/dc/terms/',
            'org': 'http://www.w3.org/ns/org#',
            'schema': 'http://schema.org/',
            'skos': 'http://www.w3.org/2004/02/skos/core#',
            'xsd': 'http://www.w3.org/2001/XMLSchema#',
            'sg': 'http://solve.global/knowledge-commons/',
            'sgd': 'http://solve.global/knowledge-commons/document-structure#',
            'sgm': 'http://solve.global/knowledge-commons/process-metadata#'
        }
        
        # Ensure chunk output directory exists
        self.chunk_output_dir = self.output_base_path / "kr-dl-chunks" / "data-lake"
        self.chunk_output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_document_rdf_and_chunks(self, solution) -> Tuple[str, List[IntegratedChunk]]:
        """Generate RDF and chunks simultaneously, returning both."""
        
        # Parse solution content into sections
        sections_data = self._parse_solution_sections(solution)
        
        # Calculate section and paragraph numbering
        section_structure = self._calculate_section_structure(sections_data)
        
        # Build RDF while creating chunks
        rdf_lines = []
        chunks = []
        
        # Add namespace prefixes
        rdf_lines.extend(self._generate_prefixes())
        rdf_lines.append("")
        
        # Generate document RDF
        rdf_lines.extend(self._generate_document_triples(solution, section_structure))
        rdf_lines.append("")
        
        # Generate hierarchical structure and chunks simultaneously
        section_rdf, section_chunks = self._generate_sections_and_chunks(solution, section_structure)
        rdf_lines.extend(section_rdf)
        chunks.extend(section_chunks)
        rdf_lines.append("")
        
        # Generate organization and contact RDF (no chunks needed)
        if solution.contact_information and solution.contact_information.strip():
            rdf_lines.extend(self._generate_organization_contacts(solution.contact_information))
        
        rdf_content = '\n'.join(rdf_lines)
        
        logger.info(f"Generated RDF ({len(rdf_content)} chars) and {len(chunks)} chunks for {solution.doc_id}")
        return rdf_content, chunks
    
    def _parse_solution_sections(self, solution) -> List[Tuple[str, str]]:
        """Parse solution into sections with content."""
        sections = []
        
        # Get introduction from pseudo document
        intro_text = ""
        if hasattr(solution, 'pseudo_document_text') and solution.pseudo_document_text:
            doc_sections = solution.pseudo_document_text.split('\n\n')
            for i, section in enumerate(doc_sections):
                if section.strip() == "Introduction" and i + 1 < len(doc_sections):
                    intro_text = doc_sections[i + 1]
                    break
        
        # Build sections list
        sections.append(('Introduction', intro_text))
        sections.append(('Description', solution.description if solution.description else ''))
        sections.append(('Key Highlights', solution.key_highlights if solution.key_highlights else ''))
        sections.append(('Results', solution.results if solution.results else ''))
        
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
    
    def _generate_sections_and_chunks(self, solution, section_structure) -> Tuple[List[str], List[IntegratedChunk]]:
        """Generate section RDF and chunk files simultaneously."""
        rdf_lines = []
        chunks = []
        
        for i, (title, section_num, para_count, content, paragraphs) in enumerate(section_structure):
            if content or title == 'Introduction':  # Always include Introduction
                
                # Generate paragraph numbers
                paragraph_nums = [section_num + 1 + j for j in range(para_count)]
                
                # Generate section RDF
                section_uri = f"sg:Chunk_{solution.doc_id}_{section_num:04d}"
                section_lines = [
                    f"{section_uri} a sgd:Section ;",
                    f"    sgd:hasParent sg:Document_{solution.doc_id} ;",
                    f'    dcterms:title "{title}" ;'
                ]
                
                if paragraph_nums:
                    first_para = f"sg:Chunk_{solution.doc_id}_{paragraph_nums[0]:04d}"
                    last_para = f"sg:Chunk_{solution.doc_id}_{paragraph_nums[-1]:04d}"
                    para_list = ', '.join([f"sg:Chunk_{solution.doc_id}_{num:04d}" for num in paragraph_nums])
                    
                    section_lines.extend([
                        f"    sgd:firstChild {first_para} ;",
                        f"    sgd:hasChild {para_list} ;",
                        f"    sgd:lastChild {last_para} ;"
                    ])
                
                # Add next sibling
                if i < len(section_structure) - 1:
                    next_section_num = section_structure[i + 1][1]
                    section_lines.append(f"    sgd:nextSibling sg:Chunk_{solution.doc_id}_{next_section_num:04d} .")
                else:
                    section_lines[-1] = section_lines[-1].rstrip(' ;') + ' .'
                
                rdf_lines.extend(section_lines)
                
                # Generate paragraph RDF and chunks simultaneously
                for j, (para_num, paragraph_text) in enumerate(zip(paragraph_nums, paragraphs)):
                    chunk_id = f"{solution.doc_id}_chunk_{para_num:04d}"
                    s3_key = f"data-lake/{solution.doc_id}/{chunk_id}.json"
                    s3_location = f"s3://kr-dl-chunks/{s3_key}"
                    
                    # Generate paragraph RDF
                    para_lines = [
                        f"",
                        f"sg:Chunk_{solution.doc_id}_{para_num:04d} a sgd:Paragraph ;",
                        f"    sgd:hasParent {section_uri} ;",
                        f'    sgm:chunkId "{chunk_id}" ;',
                        f'    sgm:s3Key "{s3_key}" ;',
                        f'    sgm:s3Location "{s3_location}"^^xsd:anyURI'
                    ]
                    
                    # Add next sibling for paragraphs
                    if j < len(paragraph_nums) - 1:
                        next_para = f"sg:Chunk_{solution.doc_id}_{paragraph_nums[j+1]:04d}"
                        para_lines.append(f"    sgd:nextSibling {next_para} .")
                    else:
                        para_lines.append(" .")
                    
                    rdf_lines.extend(para_lines)
                    
                    # Create chunk object and JSON file simultaneously
                    chunk = self._create_chunk_and_file(
                        solution, chunk_id, para_num, paragraph_text, title, s3_key, s3_location
                    )
                    chunks.append(chunk)
                
                rdf_lines.append("")
        
        return rdf_lines, chunks
    
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
    
    def _generate_prefixes(self) -> List[str]:
        """Generate namespace prefix declarations."""
        prefixes = []
        for prefix, uri in self.namespaces.items():
            prefixes.append(f"@prefix {prefix}: <{uri}> .")
        return prefixes
    
    def _generate_document_triples(self, solution, section_structure) -> List[str]:
        """Generate document-level RDF triples."""
        doc_uri = f"sg:Document_{solution.doc_id}"
        
        triples = [
            f"{doc_uri} a sgd:Solution ;",
            f'    dcterms:identifier "{solution.doc_id}" ;',
            f'    dcterms:title "{self._escape_literal(solution.name)}" ;'
        ]
        
        # Add created date
        if solution.date_added and solution.date_added.strip():
            created_date = self._format_date(solution.date_added)
            triples.append(f'    dcterms:created "{created_date}" ;')
        
        # Add spatial (country)
        if solution.country and solution.country.strip():
            triples.append(f'    dcterms:spatial "{self._escape_literal(solution.country)}" ;')
        
        # Add source URL
        if solution.source_url:
            triples.append(f'    dcterms:source <{solution.source_url}> ;')
        
        # Add publishers (organizations)
        publishers = self._extract_organization_uris(solution)
        if publishers:
            publisher_list = ', '.join(publishers)
            triples.append(f'    dcterms:publisher {publisher_list} ;')
        
        # Add section relationships
        section_chunks = [info[1] for info in section_structure if info[2] > 0 or info[0] == 'Introduction']
        
        if section_chunks:
            first_section = f"sg:Chunk_{solution.doc_id}_{section_chunks[0]:04d}"
            last_section = f"sg:Chunk_{solution.doc_id}_{section_chunks[-1]:04d}"
            section_list = ', '.join([f"sg:Chunk_{solution.doc_id}_{num:04d}" for num in section_chunks])
            
            triples.append(f'    sgd:firstChild {first_section} ;')
            triples.append(f'    sgd:hasChild {section_list} ;')
            triples.append(f'    sgd:lastChild {last_section} ;')
        
        # Add processing timestamp
        timestamp = datetime.now().isoformat() + "+00:00"
        triples.append(f'    sgm:processingTimestamp "{timestamp}"^^xsd:dateTime .')
        
        return triples
    
    def _generate_organization_contacts(self, contact_info: str) -> List[str]:
        """Generate organization and contact RDF from contact information."""
        rdf_lines = []
        
        # Parse contact information
        contacts = self._parse_contact_info(contact_info)
        
        for contact in contacts:
            org_uri = self._generate_org_uri(contact['organization'])
            contact_uri = self._generate_contact_uri(contact['organization'])
            
            # Organization RDF
            org_lines = [
                f"",
                f"{org_uri} a org:Organization ;",
                f'    skos:prefLabel "{self._escape_literal(contact["organization"])}" ;',
                f"    schema:contactPoint {contact_uri} ."
            ]
            rdf_lines.extend(org_lines)
            
            # Contact point RDF
            contact_lines = [
                f"",
                f"{contact_uri} a schema:ContactPoint ;"
            ]
            
            if contact.get('email'):
                contact_lines.append(f'    schema:email "{contact["email"]}" ;')
            if contact.get('phone'):
                contact_lines.append(f'    schema:telephone "{contact["phone"]}" .')
            else:
                contact_lines[-1] = contact_lines[-1].rstrip(' ;') + ' .'
            
            rdf_lines.extend(contact_lines)
        
        return rdf_lines
    
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
    
    def _extract_organization_uris(self, solution) -> List[str]:
        """Extract organization URIs for publishers."""
        orgs = []
        
        for org_field in [solution.public_organisations, solution.international_organisations, solution.private_organisations]:
            if org_field and org_field.strip():
                field_orgs = [org.strip() for org in org_field.split(',') if org.strip()]
                orgs.extend(field_orgs)
        
        return [self._generate_org_uri(org) for org in orgs]
    
    def _generate_org_uri(self, org_name: str) -> str:
        """Generate consistent URI for organization."""
        normalized = re.sub(r'[^\w\s-]', '', org_name.lower())
        normalized = re.sub(r'\s+', '_', normalized.strip())
        normalized = normalized.replace('__', '_').strip('_')
        return f"sg:Org_{normalized}"
    
    def _generate_contact_uri(self, org_name: str) -> str:
        """Generate consistent URI for contact point."""
        normalized = re.sub(r'[^\w\s-]', '', org_name.lower())
        normalized = re.sub(r'\s+', '_', normalized.strip())
        normalized = normalized.replace('__', '_').strip('_')
        return f"sg:Contact_{normalized}"
    
    def _format_date(self, date_str: str) -> str:
        """Format date to ISO8601."""
        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                return f"{parts[2]}-{parts[1]:0>2}-{parts[0]:0>2}"
        return date_str
    
    def _escape_literal(self, text: str) -> str:
        """Escape text for RDF literal."""
        if not text:
            return ""
        return text.replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')

def main():
    """Test the integrated RDF and chunk generator."""
    print("Integrated RDF and Chunk Generator Test")
    print("This would be called from the main test script")

if __name__ == "__main__":
    main()
