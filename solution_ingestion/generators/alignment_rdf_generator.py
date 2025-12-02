"""
Alignment RDF Generator
Generates RDF triples for ontology alignment metadata.
"""

import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class AlignmentRDFGenerator:
    """Generate RDF triples for ontology alignments."""
    
    def generate(self, doc_id: str, extraction: Dict, confidence: float, chunks_by_section: Dict) -> str:
        """Generate RDF triples for alignment."""
        
        # Build RDF content
        rdf_parts = [
            self._generate_prefixes(),
            self._generate_direct_assertions(doc_id, extraction),
            self._generate_provenance(doc_id, confidence),
            self._generate_extraction_details(doc_id, extraction)
        ]
        
        return '\n\n'.join(filter(None, rdf_parts))
    
    def _generate_prefixes(self) -> str:
        """Generate RDF prefixes."""
        return """@prefix sg: <http://solve.global/knowledge-commons/> .
@prefix sgm: <http://solve.global/knowledge-commons/process-metadata#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> ."""
    
    def _generate_direct_assertions(self, doc_id: str, extraction: Dict) -> str:
        """Generate direct solution assertions (what queries need)."""
        solution_uri = f"sg:Document_{doc_id}"
        assertions = []
        
        # Risk assertions
        risks = extraction.get('risks', [])
        if risks:
            risk_uris = ', '.join([self._sanitize_uri(r['uri']) for r in risks])
            assertions.append(f"    sg:addressesRisk {risk_uris}")
        
        # Mechanism assertions
        mechanisms = extraction.get('mechanisms', [])
        if mechanisms:
            mech_uris = ', '.join([self._sanitize_uri(m['uri']) for m in mechanisms])
            assertions.append(f"    sg:providesMechanism {mech_uris}")
        
        # Impact assertions
        impacts = extraction.get('impacts', [])
        if impacts:
            impact_uris = ', '.join([self._sanitize_uri(i['uri']) for i in impacts])
            assertions.append(f"    sg:hasImpact {impact_uris}")
        
        # Country assertions
        countries = extraction.get('countries', [])
        if countries:
            country_uris = ', '.join([f"<{c['uri']}>" for c in countries])
            assertions.append(f"    dcterms:spatial {country_uris}")
        
        if not assertions:
            return ""
        
        assertions_str = ' ;\n'.join(assertions)
        return f"""# Direct solution assertions
{solution_uri}
{assertions_str} ."""
    
    def _generate_provenance(self, doc_id: str, confidence: float) -> str:
        """Generate provenance metadata."""
        solution_uri = f"sg:Document_{doc_id}"
        alignment_uri = f"sgm:alignment_{doc_id}"
        timestamp = datetime.now().isoformat()
        
        return f"""# Provenance metadata
{solution_uri} sgm:hasAlignment {alignment_uri} .

{alignment_uri}
    a sgm:OntologyAlignment ;
    sgm:extractionMethod "llm+rules" ;
    sgm:overallConfidence "{confidence:.4f}"^^xsd:decimal ;
    dcterms:created "{timestamp}"^^xsd:dateTime ."""
    
    def _generate_extraction_details(self, doc_id: str, extraction: Dict) -> str:
        """Generate detailed extraction evidence."""
        alignment_uri = f"sgm:alignment_{doc_id}"
        details = []
        extraction_counter = 1
        
        # Risk extractions
        for risk in extraction.get('risks', []):
            ext_uri = f"sgm:extraction_risk_{doc_id}_{extraction_counter:03d}"
            details.append(self._format_risk_extraction(ext_uri, risk))
            extraction_counter += 1
        
        # Mechanism extractions
        for mechanism in extraction.get('mechanisms', []):
            ext_uri = f"sgm:extraction_mechanism_{doc_id}_{extraction_counter:03d}"
            details.append(self._format_mechanism_extraction(ext_uri, mechanism))
            extraction_counter += 1
        
        # Impact extractions
        for impact in extraction.get('impacts', []):
            ext_uri = f"sgm:extraction_impact_{doc_id}_{extraction_counter:03d}"
            details.append(self._format_impact_extraction(ext_uri, impact))
            extraction_counter += 1
        
        # Country extractions
        for country in extraction.get('countries', []):
            ext_uri = f"sgm:extraction_country_{doc_id}_{extraction_counter:03d}"
            details.append(self._format_country_extraction(ext_uri, country))
            extraction_counter += 1
        
        if not details:
            return ""
        
        # Link extractions to alignment
        extraction_uris = [d.split('\n')[0] for d in details]
        extraction_list = ',\n        '.join(extraction_uris)
        
        header = f"""{alignment_uri} sgm:hasExtraction
        {extraction_list} ."""
        
        return f"""# Detailed extraction evidence\n{header}\n\n""" + '\n\n'.join(details)
    
    def _format_risk_extraction(self, ext_uri: str, risk: Dict) -> str:
        """Format risk extraction details."""
        chunk_uri = self._get_first_chunk_uri(risk.get('chunk_uris', []))
        risk_uri = self._sanitize_uri(risk['uri'])
        
        return f"""{ext_uri}
    a sgm:RiskExtraction ;
    sgm:extractedConcept {risk_uri} ;
    sgm:confidence "{risk.get('confidence', 0.0):.4f}"^^xsd:decimal ;
    sgm:evidence "{self._escape_literal(risk.get('evidence', ''))}" ;
    sgm:sourceChunk {chunk_uri} ;
    sgm:extractionMethod "{risk.get('source', 'llm')}" ."""
    
    def _format_mechanism_extraction(self, ext_uri: str, mechanism: Dict) -> str:
        """Format mechanism extraction details."""
        chunk_uri = self._get_first_chunk_uri(mechanism.get('chunk_uris', []))
        mech_uri = self._sanitize_uri(mechanism['uri'])
        
        return f"""{ext_uri}
    a sgm:MechanismExtraction ;
    sgm:extractedConcept {mech_uri} ;
    sgm:confidence "{mechanism.get('confidence', 0.0):.4f}"^^xsd:decimal ;
    sgm:evidence "{self._escape_literal(mechanism.get('evidence', ''))}" ;
    sgm:sourceChunk {chunk_uri} ;
    sgm:extractionMethod "{mechanism.get('source', 'llm')}" ."""
    
    def _format_impact_extraction(self, ext_uri: str, impact: Dict) -> str:
        """Format impact extraction details."""
        chunk_uri = self._get_first_chunk_uri(impact.get('chunk_uris', []))
        impact_uri = self._sanitize_uri(impact['uri'])
        
        return f"""{ext_uri}
    a sgm:ImpactExtraction ;
    sgm:extractedConcept {impact_uri} ;
    sgm:confidence "{impact.get('confidence', 0.0):.4f}"^^xsd:decimal ;
    sgm:evidence "{self._escape_literal(impact.get('evidence', ''))}" ;
    sgm:sourceChunk {chunk_uri} ;
    sgm:extractionMethod "{impact.get('source', 'llm')}" ."""
    
    def _format_country_extraction(self, ext_uri: str, country: Dict) -> str:
        """Format country extraction details."""
        chunk_uri = self._get_first_chunk_uri(country.get('chunk_uris', []))
        
        return f"""{ext_uri}
    a sgm:CountryExtraction ;
    sgm:extractedConcept <{country['uri']}> ;
    sgm:confidence "{country.get('confidence', 0.0):.4f}"^^xsd:decimal ;
    sgm:evidence "{self._escape_literal(country.get('evidence', ''))}" ;
    sgm:sourceChunk {chunk_uri} ;
    sgm:extractionMethod "{country.get('source', 'llm')}" ."""
    
    def _get_first_chunk_uri(self, chunk_uris: List[str]) -> str:
        """Get first chunk URI or unknown."""
        if not chunk_uris:
            return "sg:unknown"
        
        chunk_uri = chunk_uris[0]
        
        # Extract chunk identifier from URI (everything after last /)
        if '/' in chunk_uri:
            chunk_id = chunk_uri.split('/')[-1]
        elif ':' in chunk_uri:
            chunk_id = chunk_uri.split(':')[-1]
        else:
            chunk_id = chunk_uri
        
        return f"sg:{chunk_id}"
    
    def _sanitize_uri(self, uri: str) -> str:
        """Sanitize URI to remove invalid characters."""
        if not uri:
            return "sg:Unknown"
        
        # If it's already a full URI with angle brackets, return as-is
        if uri.startswith('<') and uri.endswith('>'):
            return uri
        
        # Extract the local part after the prefix
        if ':' in uri:
            prefix, local = uri.split(':', 1)
        else:
            prefix = 'sg'
            local = uri
        
        # Remove invalid URI characters: parentheses, slashes, commas, spaces, etc.
        # Keep only alphanumeric, hyphens, and underscores
        sanitized = ''.join(char if (char.isalnum() or char in '-_') else '' for char in local)
        
        # If empty after sanitization, use Unknown
        if not sanitized:
            return f"{prefix}:Unknown"
        
        return f"{prefix}:{sanitized}"
    
    def _escape_literal(self, text: str) -> str:
        """Escape special characters in RDF literals."""
        if not text:
            return ""
        
        # Escape in specific order to avoid double-escaping
        escaped = (text
            .replace('\\', '\\\\')   # Backslashes first
            .replace('"', '\\"')      # Quotes
            .replace('\n', '\\n')     # Newlines (keep as escaped \n, not space)
            .replace('\r', '')        # Remove carriage returns
            .replace('\t', ' ')       # Tabs to spaces
        )
        
        # Remove other problematic characters that break Turtle syntax
        # Parentheses, commas, ampersands are OK in literals, but remove control chars
        escaped = ''.join(char for char in escaped if ord(char) >= 32 or char in '\n\t')
        
        # Truncate to reasonable length
        return escaped[:200]
