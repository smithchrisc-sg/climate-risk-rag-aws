# Solution Ingestion Refactoring Design Document

**Created:** 2025-11-05  
**Purpose:** Align CLI solution ingestion with production document structure standards  
**Status:** Design Phase

---

## Overview

The current solution ingestion pipeline requires significant refactoring to match production document structure standards. Based on the hand-worked examples, we need to implement:

1. **Structured pseudo-document generation** with narrative synthesis
2. **Hierarchical chunking** (Section → Paragraph structure)  
3. **Production-compliant RDF** with proper Dublin Core and organizational modeling
4. **URI management** for consistent entity identification

---

## Current vs Target Architecture

### Current Implementation Issues

| Component | Current State | Issues |
|-----------|---------------|---------|
| **Pseudo Document Generator** | Simple field concatenation | No narrative structure, missing section headers |
| **Chunk Generator** | Flat 3-chunk approach | No hierarchical relationships, incorrect granularity |
| **RDF Generator** | Basic document-chunk relationships | Missing Dublin Core, no organization modeling |
| **URI Management** | Ad-hoc URI creation | Inconsistent organization URIs, no minting facility |

### Target Implementation

| Component | Target State | Benefits |
|-----------|--------------|----------|
| **Pseudo Document Generator** | Structured narrative with mad-lib synthesis | Coherent document structure, proper sectioning |
| **Chunk Generator** | Two-level hierarchy (Section → Paragraph) | Matches production schema, enables proper navigation |
| **RDF Generator** | Full Dublin Core + organizational modeling | Production compatibility, rich metadata |
| **URI Management** | Consistent minting facility | Repeatable URIs, proper entity linking |

---

## Detailed Component Changes

## 1. Pseudo Document Generator Refactoring

### Current Implementation
```python
def generate_pseudo_document(self, solution: Solution) -> str:
    # Simple field concatenation
    return f"{solution.name}\n{solution.description}..."
```

### Target Implementation Structure

#### 1.1 Document Template
```
[Title Lines from CSV 'Name']

[Organizations from Public/International/Private columns]

Introduction
[Mad-lib synthesis paragraph using Name, Risk Type, Solution Type, PPP, Country, Organizations, Implementation Date, Themes]

Description  
[Direct from 'Description' column, split by commas into paragraphs]

Key Highlights
[Direct from 'Key Highlights' column, split by commas into paragraphs]

Results
[Direct from 'Results' column, split by commas into paragraphs]

Contact Information
[Structured contact blocks from 'Contact Information' column]
```

#### 1.2 Mad-lib Template
```
This solution, [[Name]] addresses [[Type of Risk]] through [[PPP status]] in [[Country]] 
between [[All Organizations]]. The programs were implemented in [[Year of Implementation]] 
and focus on [[Theme]].
```

#### 1.3 Implementation Changes
- **New class:** `StructuredPseudoDocumentGenerator`
- **Template engine:** For mad-lib synthesis
- **Organization parser:** Extract and format organization lists
- **Contact parser:** Structure contact information blocks
- **Section formatter:** Add explicit section headers

---

## 2. Chunk Generator Refactoring

### Current Implementation
```python
# Flat 3-chunk structure
chunks = [
    {"type": "highlights", "text": solution.key_highlights},
    {"type": "description", "text": solution.description}, 
    {"type": "results", "text": solution.results}
]
```

### Target Implementation Structure

#### 2.1 Hierarchical Chunk Structure
```
Document (sol_example_123abc456xyz)
├── Section: Introduction (chunk_0001)
│   └── Paragraph: Mad-lib content (chunk_0002)
├── Section: Description (chunk_0003)  
│   ├── Paragraph: First description para (chunk_0004)
│   └── Paragraph: Second description para (chunk_0005)
├── Section: Key Highlights (chunk_0006)
│   ├── Paragraph: First highlight para (chunk_0007)
│   └── Paragraph: Second highlight para (chunk_0008)
└── Section: Results (chunk_0009)
    ├── Paragraph: First result para (chunk_0010)
    └── Paragraph: Second result para (chunk_0011)
```

#### 2.2 Chunk Types and Properties
```python
@dataclass
class SectionChunk:
    chunk_id: str           # sol_xxx_chunk_0001
    chunk_type: str         # "section"
    section_name: str       # "Introduction", "Description", etc.
    parent_id: str          # Document ID
    child_chunks: List[str] # List of paragraph chunk IDs
    
@dataclass  
class ParagraphChunk:
    chunk_id: str           # sol_xxx_chunk_0002
    chunk_type: str         # "paragraph" 
    text: str              # Actual paragraph content
    parent_id: str         # Section chunk ID
    sibling_order: int     # Order within section
```

#### 2.3 Implementation Changes
- **New class:** `HierarchicalChunkGenerator`
- **Paragraph splitter:** Split sections by comma/period patterns
- **Chunk ID sequencing:** Sequential numbering across all chunks
- **Relationship tracking:** Parent-child and sibling relationships
- **S3 path generation:** Proper bucket/key structure for each chunk

---

## 3. RDF Generator Refactoring

### Current Implementation
```python
# Basic document-chunk relationships
doc_uri = self.SG[f"Document_{solution.doc_id}"]
graph.add((doc_uri, RDF.type, self.SGD.Document))
```

### Target Implementation Structure

#### 3.1 Namespace Alignment
```python
self.sg_ns = Namespace("http://solve.global/knowledge-commons/")
self.sgd_ns = Namespace("http://solve.global/knowledge-commons/document-structure#")  
self.sgm_ns = Namespace("http://solve.global/knowledge-commons/process-metadata#")
self.dcterms_ns = DCTERMS
```

#### 3.2 Document-Level RDF Pattern
```turtle
sg:Document_sol_example_123abc456xyz a sgd:Solution ;
    dcterms:created "2025-09-24" ;
    dcterms:identifier "sol_example_123abc456xyz" ;
    dcterms:title "Solution Name" ;
    dcterms:source <first_organizational_source> ;
    dcterms:references <additional_sources> ;
    dcterms:spatial "Country" ;
    dcterms:publisher sg:Org_publisher1, sg:Org_publisher2 ;
    sgd:firstChild sg:Chunk_sol_xxx_0001 ;
    sgd:lastChild sg:Chunk_sol_xxx_0009 ;
    sgd:hasChild sg:Chunk_sol_xxx_0001, sg:Chunk_sol_xxx_0003, ... ;
```

#### 3.3 Hierarchical Chunk RDF Pattern
```turtle
# Section Chunk
sg:Chunk_sol_xxx_0001 a sgd:Section ;
    dcterms:title "Introduction" ;
    sgd:hasParent sg:Document_sol_xxx ;
    sgd:firstChild sg:Chunk_sol_xxx_0002 ;
    sgd:lastChild sg:Chunk_sol_xxx_0002 ;
    sgd:nextSibling sg:Chunk_sol_xxx_0003 ;

# Paragraph Chunk  
sg:Chunk_sol_xxx_0002 a sgd:Paragraph ;
    sgd:hasParent sg:Chunk_sol_xxx_0001 ;
    sgm:chunkId "sol_xxx_chunk_0002" ;
    sgm:s3Location "s3://kr-dl-chunks/data-lake/sol_xxx/sol_xxx_chunk_0002.json"^^xsd:anyURI ;
```

#### 3.4 Organization and Contact RDF Pattern
```turtle
sg:Org_state_governments a org:Organization ;
    skos:prefLabel "State Governments" ;
    schema:contactPoint sg:Contact_state_governments ;

sg:Contact_state_governments a schema:ContactPoint ;
    schema:email "info@qra.qld.gov.au" ;
    schema:telephone "1800 110 841" ;
```

#### 3.5 Implementation Changes
- **New class:** `ProductionCompliantRDFGenerator`
- **URI minting:** Consistent organization and contact URI generation
- **Dublin Core integration:** Proper dcterms properties
- **Hierarchical relationships:** Section-paragraph structure
- **Organization parser:** Extract and model contact information
- **Source URL handling:** Primary source vs references distinction

---

## 4. URI Management System

### Current Implementation
```python
# Ad-hoc URI creation
doc_uri = self.SG[f"Document_{solution.doc_id}"]
```

### Target Implementation

#### 4.1 URI Minting Facility
```python
class URIMinter:
    def mint_document_uri(self, doc_id: str) -> URIRef:
        return URIRef(f"{self.sg_ns}Document_{doc_id}")
    
    def mint_chunk_uri(self, doc_id: str, chunk_number: int) -> URIRef:
        return URIRef(f"{self.sg_ns}Chunk_{doc_id}_{chunk_number:04d}")
    
    def mint_organization_uri(self, org_name: str) -> URIRef:
        # Normalize organization name to URI-safe format
        normalized = self._normalize_org_name(org_name)
        return URIRef(f"{self.sg_ns}Org_{normalized}")
    
    def mint_contact_uri(self, org_name: str) -> URIRef:
        normalized = self._normalize_org_name(org_name)  
        return URIRef(f"{self.sg_ns}Contact_{normalized}")
```

#### 4.2 Organization Name Normalization
```python
def _normalize_org_name(self, name: str) -> str:
    # "WA Department of Fire and Emergency Services (DFES)" -> "dfes-wa"
    # "State Governments" -> "state_governments"
    # Consistent, repeatable URI generation
```

---

## 5. Data Flow Architecture

### Current Flow
```
CSV Row → Solution Object → Simple Pseudo Doc → 3 Flat Chunks → Basic RDF
```

### Target Flow  
```
CSV Row → Solution Object → Structured Pseudo Doc → Hierarchical Chunks → Production RDF
    ↓
Organization Extraction → URI Minting → Contact Modeling → Dublin Core Metadata
```

### Processing Pipeline
1. **CSV Parsing:** Extract solution data with multi-value field handling
2. **Pseudo Document Generation:** Create structured narrative with mad-lib synthesis
3. **Hierarchical Chunking:** Generate section and paragraph chunks with relationships
4. **URI Minting:** Create consistent URIs for all entities
5. **RDF Generation:** Build production-compliant knowledge graph structure
6. **Validation:** Verify RDF structure matches production schema

---

## 6. Implementation Plan

### Phase 1: Pseudo Document Generator (Priority: High)
- [ ] Create `StructuredPseudoDocumentGenerator` class
- [ ] Implement mad-lib template engine
- [ ] Add organization list formatting
- [ ] Add contact information structuring
- [ ] Test with example solution row

### Phase 2: Hierarchical Chunk Generator (Priority: High)  
- [ ] Create `HierarchicalChunkGenerator` class
- [ ] Implement section-paragraph chunking
- [ ] Add relationship tracking
- [ ] Generate proper chunk IDs and S3 paths
- [ ] Test hierarchical structure

### Phase 3: URI Minting Facility (Priority: Medium)
- [ ] Create `URIMinter` class
- [ ] Implement organization name normalization
- [ ] Add consistent URI generation patterns
- [ ] Test URI repeatability

### Phase 4: Production RDF Generator (Priority: High)
- [ ] Create `ProductionCompliantRDFGenerator` class  
- [ ] Implement Dublin Core metadata patterns
- [ ] Add hierarchical RDF relationships
- [ ] Integrate organization and contact modeling
- [ ] Add RDF validation

### Phase 5: Integration and Testing (Priority: High)
- [ ] Update main pipeline to use new components
- [ ] Test with example solution row
- [ ] Validate RDF output matches hand-worked example
- [ ] Performance testing with multiple solutions

### Phase 6: Data Lake Integration (Priority: Medium)
- [ ] Update `DataLakeWriter` for hierarchical chunks
- [ ] Ensure proper S3 path structure
- [ ] Test chunk file generation and organization

---

## 7. Testing Strategy

### Unit Testing
- **Pseudo Document Generator:** Test mad-lib synthesis, section formatting
- **Chunk Generator:** Test hierarchical relationships, ID generation
- **URI Minter:** Test normalization, repeatability
- **RDF Generator:** Test RDF structure, validation

### Integration Testing  
- **End-to-end pipeline:** CSV → RDF with example solution row
- **RDF validation:** Compare output to hand-worked example
- **S3 structure:** Verify proper data lake organization

### Validation Criteria
- [ ] Generated pseudo document matches example structure
- [ ] Chunk hierarchy matches two-level pattern
- [ ] RDF output validates with RDFLib parser
- [ ] Organization URIs are consistent and repeatable
- [ ] All Dublin Core metadata properly populated

---

## 8. Risk Mitigation

### Backward Compatibility
- Keep existing components during refactoring
- Use feature flags to switch between old/new implementations
- Maintain existing data lake structure during transition

### Performance Considerations
- URI minting should be fast and deterministic
- RDF generation should handle multiple solutions efficiently
- Chunk processing should scale with solution complexity

### Error Handling
- Graceful degradation for malformed CSV data
- Validation errors should not crash pipeline
- Clear error messages for debugging

---

## 9. Success Metrics

### Functional Requirements
- [ ] Generated RDF matches production schema exactly
- [ ] All example solution fields properly mapped
- [ ] Hierarchical chunk structure correctly implemented
- [ ] Organization and contact information properly modeled

### Quality Requirements  
- [ ] RDF validates without errors
- [ ] URIs are consistent across runs
- [ ] Performance acceptable for 600+ solutions
- [ ] Code maintainable and well-documented

### Integration Requirements
- [ ] Works with existing OpenSearch indexing
- [ ] Compatible with Neptune ingestion
- [ ] Maintains data lake structure
- [ ] Preserves embeddings generation capability

---

This refactoring will bring the solution ingestion pipeline to production standards while maintaining compatibility with existing downstream systems.
