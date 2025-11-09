#!/usr/bin/env python3
"""
Clean RDFLib-based RDF Generator
"""

from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import DCTERMS, RDF, XSD
from datetime import datetime
from typing import List, Any

# Define namespaces
SG = Namespace("http://solve.global/knowledge-commons/")
SGD = Namespace("http://solve.global/knowledge-commons/document-structure#")
SGM = Namespace("http://solve.global/knowledge-commons/process-metadata#")
GN = Namespace("http://www.geonames.org/")

class RDFGenerator:
    """Clean RDFLib-based RDF generator."""
    
    def __init__(self):
        from .entity_mapper import EntityMapper
        self.entity_mapper = EntityMapper()
    
    def generate_document_graph(self, solution) -> Graph:
        """Generate RDF graph for solution document only (no chunks)."""
        
        # Enhance solution with entity mappings
        enhanced_solution = self.entity_mapper.enhance_solution_metadata(solution)
        
        # Create graph
        g = Graph()
        
        # Bind namespaces
        g.bind("dcterms", DCTERMS)
        g.bind("sg", SG)
        g.bind("sgd", SGD)
        g.bind("sgm", SGM)
        g.bind("gn", GN)
        
        # Document URI
        doc_id = enhanced_solution['doc_id']
        doc_uri = SG[f"Document_{doc_id}"]
        
        # Document type
        g.add((doc_uri, RDF.type, SGD.Solution))
        
        # Basic metadata
        g.add((doc_uri, DCTERMS.identifier, Literal(doc_id)))
        g.add((doc_uri, DCTERMS.title, Literal(enhanced_solution['name'])))
        
        # Date
        if enhanced_solution.get('date_added'):
            g.add((doc_uri, DCTERMS.created, Literal(enhanced_solution['date_added'])))
        
        # Geography - use mapped geography URI if available
        if enhanced_solution.get('mapped_geography'):
            if isinstance(enhanced_solution['mapped_geography'], URIRef):
                g.add((doc_uri, DCTERMS.spatial, enhanced_solution['mapped_geography']))
            else:
                g.add((doc_uri, DCTERMS.spatial, Literal(enhanced_solution['mapped_geography'])))
        elif enhanced_solution.get('country'):
            g.add((doc_uri, DCTERMS.spatial, Literal(enhanced_solution['country'])))
        
        # Source URL
        if enhanced_solution.get('source_url'):
            g.add((doc_uri, DCTERMS.source, URIRef(enhanced_solution['source_url'])))
        
        # Description - first sentence of description field
        if enhanced_solution.get('description'):
            desc_text = enhanced_solution['description'].strip()
            if desc_text:
                # Get first sentence
                first_sentence = desc_text.split('.')[0] + '.' if '.' in desc_text else desc_text
                g.add((doc_uri, DCTERMS.description, Literal(first_sentence)))
        
        # Publisher - single primary publisher
        if enhanced_solution.get('primary_publisher_uri'):
            g.add((doc_uri, DCTERMS.publisher, enhanced_solution['primary_publisher_uri']))
        
        # Associated organizations - separate triple for each
        if enhanced_solution.get('mapped_organizations'):
            for org in enhanced_solution['mapped_organizations']:
                if org.get('uri'):
                    g.add((doc_uri, SG.associatedOrganization, org['uri']))
        
        # Risk types
        if enhanced_solution.get('risk_type_uris'):
            for risk_uri in enhanced_solution['risk_type_uris']:
                g.add((doc_uri, SG.riskType, risk_uri))
        
        # Solution types
        if enhanced_solution.get('solution_type_uris'):
            for solution_uri in enhanced_solution['solution_type_uris']:
                g.add((doc_uri, SG.solutionType, solution_uri))
        
        # Themes
        if enhanced_solution.get('theme_uris'):
            for theme_uri in enhanced_solution['theme_uris']:
                g.add((doc_uri, SG.theme, theme_uri))
        
        # Implementation years
        if enhanced_solution.get('implementation_years'):
            for year in enhanced_solution['implementation_years']:
                g.add((doc_uri, SG.implementationYear, Literal(year, datatype=XSD.gYear)))
        
        # Additional references (parse from organization_sources and other_sources)
        references = self._extract_additional_references(enhanced_solution)
        for ref_url in references:
            g.add((doc_uri, DCTERMS.references, URIRef(ref_url)))
        
        # Processing timestamp
        timestamp = datetime.now().isoformat() + "+00:00"
        g.add((doc_uri, SGM.processingTimestamp, Literal(timestamp, datatype=XSD.dateTime)))
        
        return g
    
    def _extract_additional_references(self, enhanced_solution) -> List[str]:
        """Extract additional reference URLs from organization_sources and other_sources."""
        import re
        references = []
        
        # URL pattern
        url_pattern = r'https?://[^\s,;]+'
        
        # Check organization_sources for additional URLs (skip the first one used as dcterms:source)
        org_sources = enhanced_solution.get('organization_sources', '')
        if org_sources:
            urls = re.findall(url_pattern, org_sources)
            if len(urls) > 1:  # Skip first URL (already used as dcterms:source)
                references.extend(urls[1:])
        
        # Check other_sources for URLs
        other_sources = enhanced_solution.get('other_sources', '')
        if other_sources:
            urls = re.findall(url_pattern, other_sources)
            references.extend(urls)
        
        return references
    
    def generate_document_rdf(self, solution, chunks: List[Any]) -> str:
        """Generate RDF for solution document with chunks (for backward compatibility)."""
        
        g = self.generate_document_graph(solution)
        doc_id = solution.doc_id if hasattr(solution, 'doc_id') else solution.id
        doc_uri = SG[f"Document_{doc_id}"]
        
        # Chunk structure (simplified)
        if chunks:
            chunk_uris = []
            for i, chunk in enumerate(chunks[:4], 1):  # Limit to first 4 chunks
                chunk_uri = SG[f"Chunk_{doc_id}_{i:04d}"]
                chunk_uris.append(chunk_uri)
                g.add((chunk_uri, RDF.type, SGD.Section))
                g.add((chunk_uri, SGD.hasParent, doc_uri))
                g.add((chunk_uri, DCTERMS.title, Literal(f"Section {i}")))
            
            if chunk_uris:
                g.add((doc_uri, SGD.firstChild, chunk_uris[0]))
                g.add((doc_uri, SGD.lastChild, chunk_uris[-1]))
                for chunk_uri in chunk_uris:
                    g.add((doc_uri, SGD.hasChild, chunk_uri))
        
        # Serialize to Turtle
        return g.serialize(format='turtle')
