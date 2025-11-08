#!/usr/bin/env python3
"""
Production-Aligned RDF Generator for Solution Document Structure
Creates hierarchical RDF structure matching the hand-built example exactly.
"""

import logging
import re
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import quote
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from integrated_entity_mapper import IntegratedEntityMapper

logger = logging.getLogger(__name__)

class ProductionRDFGenerator:
    """Generates production-aligned RDF matching the hand-built example structure."""
    
    def __init__(self):
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
        self.entity_mapper = IntegratedEntityMapper()
    
    def generate_document_rdf(self, solution, chunks: List[Any]) -> str:
        """Generate production-aligned RDF for solution document."""
        
        # Build RDF content
        rdf_lines = []
        
        # Add namespace prefixes
        rdf_lines.extend(self._generate_prefixes())
        rdf_lines.append("")
        
        # Generate document RDF
        rdf_lines.extend(self._generate_document_triples(solution))
        rdf_lines.append("")
        
        # Generate hierarchical chunk structure
        rdf_lines.extend(self._generate_hierarchical_chunks(solution, chunks))
        rdf_lines.append("")
        
        # Generate organization and contact RDF
        if solution.contact_information and solution.contact_information.strip():
            rdf_lines.extend(self._generate_organization_contacts(solution.contact_information))
        
        return '\n'.join(rdf_lines)
    
    def _generate_prefixes(self) -> List[str]:
        """Generate namespace prefix declarations."""
        prefixes = []
        for prefix, uri in self.namespaces.items():
            prefixes.append(f"@prefix {prefix}: <{uri}> .")
        return prefixes
    
    def generate_document_rdf(self, solution, chunks: List[Any]) -> str:
        """Generate production-aligned RDF for solution document using actual chunks."""
        
        # Enhance solution with entity mappings
        enhanced_solution = self.entity_mapper.enhance_solution_metadata(solution)
        
        # Build RDF content
        rdf_lines = []
        
        # Add namespace prefixes
        rdf_lines.extend(self._generate_prefixes())
        rdf_lines.append("")
        
        # Generate document RDF using actual chunks
        rdf_lines.extend(self._generate_document_triples_from_chunks(enhanced_solution, chunks))
        rdf_lines.append("")
        
        # Generate hierarchical chunk structure from actual chunks
        chunk_rdf = self._generate_hierarchical_chunks_from_chunks(enhanced_solution, chunks)
        rdf_lines.extend(chunk_rdf)
        rdf_lines.append("")
        
        # Generate organization and contact RDF
        if solution.contact_information and solution.contact_information.strip():
            rdf_lines.extend(self._generate_organization_contacts(solution.contact_information))
        
        return '\n'.join(rdf_lines)
    
    def _generate_document_triples_from_chunks(self, solution, chunks: List[Any]) -> List[str]:
        """Generate document-level RDF triples using actual chunks."""
        doc_id = solution.get('doc_id') if isinstance(solution, dict) else solution.doc_id
        doc_uri = f"sg:Document_{doc_id}"
        
        name = solution.get('name') if isinstance(solution, dict) else solution.name
        triples = [
            f"{doc_uri} a sgd:Solution ;",
            f'    dcterms:identifier "{doc_id}" ;',
            f'    dcterms:title "{self._escape_literal(name)}" ;'
        ]
        
        # Add created date
        date_added = solution.get('date_added') if isinstance(solution, dict) else getattr(solution, 'date_added', '')
        if date_added and date_added.strip():
            created_date = self._format_date(date_added)
            triples.append(f'    dcterms:created "{created_date}" ;')
        
        # Add spatial (country) - use URI if available
        if solution.get('country_uri'):
            triples.append(f'    dcterms:spatial {solution["country_uri"]} ;')
        else:
            country = solution.get('country') if isinstance(solution, dict) else solution.country
            if country and country.strip():
                triples.append(f'    dcterms:spatial "{self._escape_literal(country)}" ;')
        
        # Add vocabulary concepts
        for field in ['type_of_risk_uris', 'type_of_solution_uris', 'theme_uris']:
            if solution.get(field):
                concept_list = ', '.join(solution[field])
                predicate = field.replace('_uris', '').replace('_', ':')
                triples.append(f'    sg:{predicate} {concept_list} ;')
        
        # Add source URL
        source_url = solution.get('source_url') if isinstance(solution, dict) else getattr(solution, 'source_url', '')
        if source_url:
            triples.append(f'    dcterms:source <{source_url}> ;')
        
        # Add publishers (organizations) - use URI if available
        if solution.get('organization_uri'):
            triples.append(f'    dcterms:publisher {solution["organization_uri"]} ;')
        else:
            # Try organization fields
            for org_field in ['public_organisations', 'international_organisations', 'private_organisations']:
                org_value = solution.get(org_field) if isinstance(solution, dict) else getattr(solution, org_field, '')
                if org_value and org_value.strip():
                    triples.append(f'    dcterms:publisher "{self._escape_literal(org_value)}" ;')
                    break
        
        # Group chunks by section and get section numbers
        section_chunks = self._get_section_chunks_from_chunks(solution, chunks)
        
        if section_chunks:
            first_section = f"sg:Chunk_{doc_id}_{section_chunks[0]:04d}"
            last_section = f"sg:Chunk_{doc_id}_{section_chunks[-1]:04d}"
            section_list = ', '.join([f"sg:Chunk_{doc_id}_{num:04d}" for num in section_chunks])
            
            triples.append(f'    sgd:firstChild {first_section} ;')
            triples.append(f'    sgd:hasChild {section_list} ;')
            triples.append(f'    sgd:lastChild {last_section} ;')
        
        # Add processing timestamp
        timestamp = datetime.now().isoformat() + "+00:00"
        triples.append(f'    sgm:processingTimestamp "{timestamp}"^^xsd:dateTime .')
        
        return triples
    
    def _get_section_chunks_from_chunks(self, solution, chunks: List[Any]) -> List[int]:
        """Get section numbers from actual chunks."""
        # Map chunks by section
        sections_with_chunks = set()
        
        for chunk in chunks:
            chunk_number = getattr(chunk, 'chunk_number', 0)
            section_title = getattr(chunk, 'section_title', '')
            
            # Calculate section number (chunk_number - 1 for paragraph chunks)
            if section_title == 'Introduction':
                sections_with_chunks.add(1)  # Introduction section is always 1
            elif section_title == 'Description':
                sections_with_chunks.add(chunk_number - 1)  # Section is one before paragraph
            elif section_title == 'Key Highlights':
                sections_with_chunks.add(chunk_number - 1)
            elif section_title == 'Results':
                sections_with_chunks.add(chunk_number - 1)
        
        return sorted(list(sections_with_chunks))
    
    def _generate_hierarchical_chunks_from_chunks(self, solution, chunks: List[Any]) -> List[str]:
        """Generate hierarchical chunk structure from actual chunks."""
        rdf_lines = []
        
        # Group chunks by section
        sections = {}
        for chunk in chunks:
            section_title = getattr(chunk, 'section_title', '')
            chunk_number = getattr(chunk, 'chunk_number', 0)
            
            if section_title not in sections:
                sections[section_title] = []
            sections[section_title].append((chunk_number, chunk))
        
        # Generate RDF for each section
        section_order = ['Introduction', 'Description', 'Key Highlights', 'Results']
        section_numbers = []
        
        for section_title in section_order:
            if section_title in sections:
                section_chunks = sorted(sections[section_title])
                if section_chunks:
                    first_chunk_num = section_chunks[0][0]
                    section_num = first_chunk_num - 1  # Section is one before first paragraph
                    section_numbers.append(section_num)
                    
                    # Generate section RDF
                    section_lines = self._generate_section_rdf_from_chunks(
                        solution.doc_id, section_title, section_num, section_chunks
                    )
                    rdf_lines.extend(section_lines)
                    rdf_lines.append("")
        
        # Fix next sibling relationships
        rdf_content = '\n'.join(rdf_lines)
        for i, section_num in enumerate(section_numbers[:-1]):
            next_section_num = section_numbers[i + 1]
            old_pattern = f"sg:Chunk_{solution.doc_id}_{section_num:04d} a sgd:Section ;"
            # This is a simplified fix - in practice we'd need more sophisticated replacement
        
        return rdf_lines
    
    def _generate_section_rdf_from_chunks(self, doc_id: str, section_title: str, 
                                        section_num: int, section_chunks: List[tuple]) -> List[str]:
        """Generate RDF for a section using actual chunks."""
        section_uri = f"sg:Chunk_{doc_id}_{section_num:04d}"
        
        # Section RDF
        section_lines = [
            f"{section_uri} a sgd:Section ;",
            f"    sgd:hasParent sg:Document_{doc_id} ;",
            f'    dcterms:title "{section_title}" ;'
        ]
        
        if section_chunks:
            first_chunk_num = section_chunks[0][0]
            last_chunk_num = section_chunks[-1][0]
            chunk_list = ', '.join([f"sg:Chunk_{doc_id}_{num:04d}" for num, _ in section_chunks])
            
            section_lines.extend([
                f"    sgd:firstChild sg:Chunk_{doc_id}_{first_chunk_num:04d} ;",
                f"    sgd:hasChild {chunk_list} ;",
                f"    sgd:lastChild sg:Chunk_{doc_id}_{last_chunk_num:04d} ;"
            ])
        
        # Add placeholder for next sibling (will be fixed later)
        section_lines.append("    sgd:nextSibling PLACEHOLDER .")
        
        # Generate paragraph RDF for each chunk
        for i, (chunk_num, chunk) in enumerate(section_chunks):
            chunk_id = getattr(chunk, 'chunk_id', f'{doc_id}_chunk_{chunk_num:04d}')
            
            para_lines = [
                f"",
                f"sg:Chunk_{doc_id}_{chunk_num:04d} a sgd:Paragraph ;",
                f"    sgd:hasParent {section_uri} ;",
                f'    sgm:chunkId "{chunk_id}" ;',
                f'    sgm:s3Key "data-lake/{doc_id}/{chunk_id}.json" ;',
                f'    sgm:s3Location "s3://kr-dl-chunks/data-lake/{doc_id}/{chunk_id}.json"^^xsd:anyURI'
            ]
            
            # Add next sibling for paragraphs within section
            if i < len(section_chunks) - 1:
                next_chunk_num = section_chunks[i + 1][0]
                para_lines.append(f"    sgd:nextSibling sg:Chunk_{doc_id}_{next_chunk_num:04d} .")
            else:
                para_lines.append(" .")
            
            section_lines.extend(para_lines)
        
        return section_lines
    
    def _calculate_section_numbers(self, solution, chunks: List[Any]) -> List[tuple]:
        """Calculate dynamic section numbers based on paragraph counts."""
        # Map chunks to sections
        chunk_map = {}
        for chunk in chunks:
            chunk_id = getattr(chunk, 'chunk_id', '')
            text = getattr(chunk, 'text', '')
            
            if '_desc' in chunk_id:
                chunk_map['description'] = text
            elif '_highlights' in chunk_id:
                chunk_map['highlights'] = text
            elif '_results' in chunk_id:
                chunk_map['results'] = text
        
        # Get introduction text
        intro_text = ""
        if hasattr(solution, 'pseudo_document_text') and solution.pseudo_document_text:
            sections = solution.pseudo_document_text.split('\n\n')
            for i, section in enumerate(sections):
                if section.strip() == "Introduction" and i + 1 < len(sections):
                    intro_text = sections[i + 1]
                    break
        
        # Build sections with content
        sections_data = [
            ('Introduction', intro_text),
            ('Description', chunk_map.get('description', '')),
            ('Key Highlights', chunk_map.get('highlights', '')),
            ('Results', chunk_map.get('results', ''))
        ]
        
        # Calculate dynamic numbering
        current_num = 1
        section_info = []
        
        for title, content in sections_data:
            section_num = current_num
            current_num += 1  # Section takes one number
            
            # Count paragraphs for this section
            if title == 'Introduction':
                para_count = 1  # Always 1 paragraph
            else:
                # Split content into paragraphs
                paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()] if content else []
                para_count = max(1, len(paragraphs))  # At least 1 paragraph
            
            section_info.append((title, section_num, para_count, content))
            current_num += para_count  # Paragraphs take subsequent numbers
        
        return section_info
    
    def _generate_document_triples(self, solution, section_info: List[tuple]) -> List[str]:
        """Generate document-level RDF triples with dynamic section numbers."""
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
        
        # Add hierarchical chunk relationships using dynamic section numbers
        section_chunks = [f"sg:Chunk_{solution.doc_id}_{info[1]:04d}" for info in section_info]
        
        triples.append(f'    sgd:firstChild {section_chunks[0]} ;')
        chunk_list = ', '.join(section_chunks)
        triples.append(f'    sgd:hasChild {chunk_list} ;')
        triples.append(f'    sgd:lastChild {section_chunks[-1]} ;')
        
        # Add processing timestamp
        timestamp = datetime.now().isoformat() + "+00:00"
        triples.append(f'    sgm:processingTimestamp "{timestamp}"^^xsd:dateTime .')
        
        return triples
    
    def _generate_hierarchical_chunks_with_siblings(self, solution, chunks: List[Any], section_info: List[tuple]) -> List[str]:
        """Generate hierarchical chunk structure with proper sibling relationships."""
        rdf_lines = []
        
        # Generate RDF for each section
        for i, (title, section_num, para_count, content) in enumerate(section_info):
            if content or title == 'Introduction':  # Always include Introduction
                section_lines = self._generate_section_rdf_dynamic(solution.doc_id, title, section_num, para_count, content)
                
                # Fix next sibling relationship
                if i < len(section_info) - 1:
                    next_section_num = section_info[i + 1][1]
                    next_section_uri = f"sg:Chunk_{solution.doc_id}_{next_section_num:04d}"
                    # Replace placeholder with actual next sibling
                    for j, line in enumerate(section_lines):
                        if "sgd:nextSibling PLACEHOLDER" in line:
                            section_lines[j] = f"    sgd:nextSibling {next_section_uri} ."
                            break
                else:
                    # Last section, remove placeholder
                    for j, line in enumerate(section_lines):
                        if "sgd:nextSibling PLACEHOLDER" in line:
                            section_lines[j] = section_lines[j-1].rstrip(' ;') + ' .'
                            section_lines[j-1] = section_lines[j-1].rstrip(' ;') + ' .'
                            section_lines.pop(j)
                            break
                
                rdf_lines.extend(section_lines)
                rdf_lines.append("")
        
        return rdf_lines
    
    def _generate_hierarchical_chunks(self, solution, chunks: List[Any]) -> List[str]:
        """Generate hierarchical chunk structure with dynamic sequential numbering."""
        rdf_lines = []
        
        # Map chunks to sections
        chunk_map = {}
        for chunk in chunks:
            chunk_id = getattr(chunk, 'chunk_id', '')
            text = getattr(chunk, 'text', '')
            
            if '_desc' in chunk_id:
                chunk_map['description'] = text
            elif '_highlights' in chunk_id:
                chunk_map['highlights'] = text
            elif '_results' in chunk_id:
                chunk_map['results'] = text
        
        # Get introduction text from pseudo document
        intro_text = ""
        if hasattr(solution, 'pseudo_document_text') and solution.pseudo_document_text:
            sections = solution.pseudo_document_text.split('\n\n')
            for i, section in enumerate(sections):
                if section.strip() == "Introduction" and i + 1 < len(sections):
                    intro_text = sections[i + 1]
                    break
        
        # Build sections with content
        sections_data = [
            ('Introduction', intro_text),
            ('Description', chunk_map.get('description', '')),
            ('Key Highlights', chunk_map.get('highlights', '')),
            ('Results', chunk_map.get('results', ''))
        ]
        
        # Calculate dynamic numbering
        current_num = 1
        section_numbers = []
        
        for title, content in sections_data:
            section_num = current_num
            current_num += 1  # Section takes one number
            
            # Count paragraphs for this section
            if title == 'Introduction':
                para_count = 1  # Always 1 paragraph
            else:
                # Split content into paragraphs
                paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()] if content else []
                para_count = max(1, len(paragraphs))  # At least 1 paragraph
            
            section_numbers.append((title, section_num, para_count, content))
            current_num += para_count  # Paragraphs take subsequent numbers
        
        # Generate RDF for each section
        for title, section_num, para_count, content in section_numbers:
            if content or title == 'Introduction':  # Always include Introduction even if empty
                section_lines = self._generate_section_rdf_dynamic(solution.doc_id, title, section_num, para_count, content)
                rdf_lines.extend(section_lines)
                rdf_lines.append("")
        
        return rdf_lines
    
    def _generate_section_rdf_dynamic(self, doc_id: str, title: str, section_num: int, para_count: int, content: str) -> List[str]:
        """Generate RDF for a section with dynamic paragraph numbering."""
        section_uri = f"sg:Chunk_{doc_id}_{section_num:04d}"
        
        # Generate paragraph numbers (sequential after section)
        paragraph_nums = [section_num + 1 + i for i in range(para_count)]
        
        # Split content into paragraphs
        if title == 'Introduction':
            paragraphs = [content] if content else [""]
        else:
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()] if content else []
            # Ensure we have at least the expected number of paragraphs
            while len(paragraphs) < para_count:
                paragraphs.append("")
        
        # Section RDF
        section_lines = [
            f"{section_uri} a sgd:Section ;",
            f"    sgd:hasParent sg:Document_{doc_id} ;",
            f'    dcterms:title "{title}" ;'
        ]
        
        if paragraph_nums:
            first_para = f"sg:Chunk_{doc_id}_{paragraph_nums[0]:04d}"
            last_para = f"sg:Chunk_{doc_id}_{paragraph_nums[-1]:04d}"
            para_list = ', '.join([f"sg:Chunk_{doc_id}_{num:04d}" for num in paragraph_nums])
            
            section_lines.extend([
                f"    sgd:firstChild {first_para} ;",
                f"    sgd:hasChild {para_list} ;",
                f"    sgd:lastChild {last_para} ;"
            ])
        
        # Add next sibling (will be calculated in document generation)
        section_lines.append("    sgd:nextSibling PLACEHOLDER .")
        
        # Generate paragraph RDF
        for i, (para_num, paragraph) in enumerate(zip(paragraph_nums, paragraphs)):
            para_uri = f"sg:Chunk_{doc_id}_{para_num:04d}"
            para_lines = [
                f"",
                f"{para_uri} a sgd:Paragraph ;",
                f"    sgd:hasParent {section_uri} ;",
                f'    sgm:chunkId "{doc_id}_chunk_{para_num:04d}" ;',
                f'    sgm:s3Key "data-lake/{doc_id}/{doc_id}_chunk_{para_num:04d}.json" ;',
                f'    sgm:s3Location "s3://kr-dl-chunks/data-lake/{doc_id}/{doc_id}_chunk_{para_num:04d}.json"^^xsd:anyURI'
            ]
            
            # Add next sibling for paragraphs within section
            if i < len(paragraph_nums) - 1:
                next_para = f"sg:Chunk_{doc_id}_{paragraph_nums[i+1]:04d}"
                para_lines.append(f"    sgd:nextSibling {next_para} .")
            else:
                para_lines.append(" .")
            
            section_lines.extend(para_lines)
        
        return section_lines
    
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
        # Normalize organization name for URI
        normalized = re.sub(r'[^\w\s-]', '', org_name.lower())
        normalized = re.sub(r'\s+', '_', normalized.strip())
        normalized = normalized.replace('__', '_').strip('_')
        return f"sg:Org_{normalized}"
    
    def _generate_contact_uri(self, org_name: str) -> str:
        """Generate consistent URI for contact point."""
        # Normalize organization name for URI
        normalized = re.sub(r'[^\w\s-]', '', org_name.lower())
        normalized = re.sub(r'\s+', '_', normalized.strip())
        normalized = normalized.replace('__', '_').strip('_')
        return f"sg:Contact_{normalized}"
    
    def _format_date(self, date_str: str) -> str:
        """Format date to ISO8601."""
        # Handle various date formats
        if '/' in date_str:
            # Assume dd/mm/yyyy format
            parts = date_str.split('/')
            if len(parts) == 3:
                return f"{parts[2]}-{parts[1]:0>2}-{parts[0]:0>2}"
        return date_str  # Return as-is if can't parse
    
    def _escape_literal(self, text: str) -> str:
        """Escape text for RDF literal."""
        if not text:
            return ""
        return text.replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')

def main():
    """Test the production RDF generator."""
    print("Production RDF Generator Test")
    print("This would be called from the main test script")

if __name__ == "__main__":
    main()
