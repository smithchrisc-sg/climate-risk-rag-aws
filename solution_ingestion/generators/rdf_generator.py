"""
RDF Generator for Solution Document Structure
Maps pseudo-documents and chunks to semantic RDF structure
"""

import json
import logging
import sys
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

# We'll need to install rdflib separately since we can't use the layer version
# pip install rdflib
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS
from models.solution import Solution

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RDFGenerator:
    """Generates RDF for solution document structure"""
    
    def __init__(self):
        # Define namespaces
        self.SG = Namespace("http://solve.global/knowledge-commons/")
        self.SGD = Namespace("http://solve.global/knowledge-commons/document-structure#")
        self.SGM = Namespace("http://solve.global/knowledge-commons/process-metadata#")
        
        # Initialize graph
        self.graph = Graph()
        self._bind_namespaces()
    
    def _bind_namespaces(self):
        """Bind namespaces to graph"""
        self.graph.bind("sg", self.SG)
        self.graph.bind("sgd", self.SGD)
        self.graph.bind("sgm", self.SGM)
        self.graph.bind("dcterms", DCTERMS)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("xsd", XSD)
    
    def generate_document_rdf(self, solution: Solution, chunks: List[Dict[str, Any]]) -> str:
        """Generate RDF for a solution document and its chunks"""
        
        # Create document URI
        doc_uri = self.SG[f"Document_{solution.doc_id}"]
        
        # Add document triples
        self._add_document_triples(doc_uri, solution)
        
        # Add chunk triples
        chunk_uris = []
        for chunk in chunks:
            chunk_uri = self._add_chunk_triples(doc_uri, solution, chunk)
            chunk_uris.append(chunk_uri)
        
        # Add document-chunk relationships
        self._add_document_relationships(doc_uri, chunk_uris)
        
        return self.graph.serialize(format='turtle')
    
    def _add_document_triples(self, doc_uri: URIRef, solution: Solution):
        """Add document-level RDF triples"""
        
        # Document type
        self.graph.add((doc_uri, RDF.type, self.SGD.Document))
        
        # Dublin Core metadata
        self.graph.add((doc_uri, DCTERMS.identifier, Literal(solution.doc_id)))
        self.graph.add((doc_uri, DCTERMS.title, Literal(solution.name)))
        self.graph.add((doc_uri, DCTERMS.description, Literal(solution.description)))
        self.graph.add((doc_uri, DCTERMS.source, Literal(solution.source_url)))
        
        # Processing metadata
        timestamp = datetime.now().isoformat() + "Z"
        self.graph.add((doc_uri, self.SGM.processingTimestamp, Literal(timestamp, datatype=XSD.dateTime)))
        
        # Content metrics from pseudo-document
        if hasattr(solution, 'pseudo_document_text') and solution.pseudo_document_text:
            char_count = len(solution.pseudo_document_text)
            word_count = len(solution.pseudo_document_text.split())
            self.graph.add((doc_uri, self.SGM.characterCount, Literal(char_count, datatype=XSD.nonNegativeInteger)))
            self.graph.add((doc_uri, self.SGM.wordCount, Literal(word_count, datatype=XSD.nonNegativeInteger)))
        
        # Solution-specific metadata
        if solution.public_organisations:
            self.graph.add((doc_uri, DCTERMS.publisher, Literal(solution.public_organisations)))
        
        if solution.country:
            self.graph.add((doc_uri, DCTERMS.spatial, Literal(solution.country)))
        
        if solution.date_added:
            self.graph.add((doc_uri, DCTERMS.created, Literal(solution.date_added)))
    
    def _add_chunk_triples(self, doc_uri: URIRef, solution: Solution, chunk: Dict[str, Any]) -> URIRef:
        """Add chunk-level RDF triples"""
        
        # Create chunk URI
        chunk_uri = self.SG[f"Chunk_{chunk['chunk_id']}"]
        
        # Determine chunk type based on chunk_id suffix
        chunk_type = self._get_chunk_type(chunk['chunk_id'])
        self.graph.add((chunk_uri, RDF.type, chunk_type))
        
        # Dublin Core metadata
        chunk_title = self._get_chunk_title(chunk['chunk_id'])
        self.graph.add((chunk_uri, DCTERMS.title, Literal(chunk_title)))
        self.graph.add((chunk_uri, DCTERMS.isPartOf, doc_uri))
        
        # Content
        self.graph.add((chunk_uri, DCTERMS.description, Literal(chunk['text'])))
        
        # Processing metadata
        self.graph.add((chunk_uri, self.SGM.chunkId, Literal(chunk['chunk_id'])))
        self.graph.add((chunk_uri, self.SGM.characterCount, Literal(chunk['character_count'], datatype=XSD.nonNegativeInteger)))
        
        # S3 location (simulated for local development)
        s3_key = f"data-lake/{solution.doc_id}/{chunk['chunk_id']}.json"
        s3_uri = f"s3://kr-dl-chunks/{s3_key}"
        self.graph.add((chunk_uri, self.SGM.s3Location, Literal(s3_uri, datatype=XSD.anyURI)))
        self.graph.add((chunk_uri, self.SGM.s3Bucket, Literal("kr-dl-chunks")))
        self.graph.add((chunk_uri, self.SGM.s3Key, Literal(s3_key)))
        
        # Chunk sequence based on type
        sequence = self._get_chunk_sequence(chunk['chunk_id'])
        self.graph.add((chunk_uri, self.SGM.sequenceNumber, Literal(sequence, datatype=XSD.positiveInteger)))
        
        # Processing timestamp
        timestamp = datetime.now().isoformat() + "Z"
        self.graph.add((chunk_uri, self.SGM.processingTimestamp, Literal(timestamp, datatype=XSD.dateTime)))
        
        return chunk_uri
    
    def _add_document_relationships(self, doc_uri: URIRef, chunk_uris: List[URIRef]):
        """Add document-chunk relationships"""
        
        # Add hasChild relationships
        for chunk_uri in chunk_uris:
            self.graph.add((doc_uri, self.SGD.hasChild, chunk_uri))
            self.graph.add((chunk_uri, self.SGD.hasParent, doc_uri))
        
        # Add first/last child if chunks exist
        if chunk_uris:
            self.graph.add((doc_uri, self.SGD.firstChild, chunk_uris[0]))
            self.graph.add((doc_uri, self.SGD.lastChild, chunk_uris[-1]))
        
        # Add sibling relationships
        for i, chunk_uri in enumerate(chunk_uris[:-1]):
            next_chunk = chunk_uris[i + 1]
            self.graph.add((chunk_uri, self.SGD.nextSibling, next_chunk))
    
    def _get_chunk_type(self, chunk_id: str) -> URIRef:
        """Determine RDF type based on chunk ID"""
        if chunk_id.endswith('_desc'):
            return self.SGD.Section  # Description section
        elif chunk_id.endswith('_highlights'):
            return self.SGD.Section  # Key highlights section
        elif chunk_id.endswith('_results'):
            return self.SGD.Section  # Results section
        else:
            return self.SGD.Section  # Default to section
    
    def _get_chunk_title(self, chunk_id: str) -> str:
        """Generate human-readable title for chunk"""
        if chunk_id.endswith('_desc'):
            return "Description"
        elif chunk_id.endswith('_highlights'):
            return "Key Highlights"
        elif chunk_id.endswith('_results'):
            return "Results"
        else:
            return "Content Section"
    
    def _get_chunk_sequence(self, chunk_id: str) -> int:
        """Get sequence number based on chunk type"""
        if chunk_id.endswith('_desc'):
            return 1
        elif chunk_id.endswith('_highlights'):
            return 2
        elif chunk_id.endswith('_results'):
            return 3
        else:
            return 1
    
    def generate_batch_rdf(self, solutions_with_chunks: List[tuple]) -> str:
        """Generate RDF for multiple solutions and their chunks"""
        
        for solution, chunks in solutions_with_chunks:
            self.generate_document_rdf(solution, chunks)
        
        return self.graph.serialize(format='turtle')
    
    def clear_graph(self):
        """Clear the RDF graph"""
        self.graph = Graph()
        self._bind_namespaces()
