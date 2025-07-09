# Document Structure Schema Explanation
## Date: 2025-07-09T22:30:00Z
## Status: RDFS Schema Design Logic and Rationale

## OVERVIEW

This document explains the design logic and rationale behind the RDFS document structure schema for the GAIP Knowledge Repository. The schema is designed to capture Textract structure elements while supporting hierarchical document organization and efficient URI minting for knowledge graph construction.

## DESIGN PRINCIPLES

### 1. TEXTRACT ALIGNMENT
The schema directly maps to AWS Textract block types to ensure seamless integration with our existing document processing pipeline. Each Textract block type has a corresponding RDFS class.

### 2. HIERARCHICAL STRUCTURE SUPPORT
The schema supports multi-level document hierarchy (Document → Page → Section → Chunk) with clear parent-child relationships and sequencing properties.

### 3. URI MINTING READINESS
All classes and properties are designed to support systematic URI generation based on doc_id with predictable patterns for direct S3 access.

### 4. PROCESSING EFFICIENCY
The schema includes properties that support efficient processing, caching, and provenance tracking for production systems.

---

## CLASS HIERARCHY DESIGN

### CORE DOCUMENT CLASSES

#### kr:Document
**Purpose**: Root class for all processed documents in the knowledge repository
**Rationale**: Provides the foundation for doc_id-based URI minting (sg:Document_{doc_id})
**Key Properties**: Links to pages, sections, and processing metadata

#### kr:DocumentPage  
**Purpose**: Represents individual pages within documents
**Rationale**: Maps directly to Textract PAGE blocks, supports page-level navigation
**Key Properties**: Page number, dimensions, parent document reference

#### kr:DocumentSection
**Purpose**: Logical sections derived from structural analysis
**Rationale**: Enables hierarchical document organization beyond physical page boundaries
**Key Properties**: Hierarchy level, sequence, parent/child relationships

#### kr:DocumentChunk
**Purpose**: Processing chunks optimized for NLP and vector operations
**Rationale**: Bridges document structure with processing requirements, supports S3 direct access
**Key Properties**: S3 location, sequence, chunking strategy, content metrics

### TEXTRACT STRUCTURE CLASSES

#### kr:DocumentStructureElement (Base Class)
**Purpose**: Abstract base for all Textract-derived elements
**Rationale**: Provides common properties (confidence, bounding box, text content) for all structural elements
**Benefits**: Consistent property inheritance, simplified querying

#### Specific Textract Classes
- **kr:TextLine**: Maps to Textract LINE blocks
- **kr:TextWord**: Maps to Textract WORD blocks  
- **kr:Table**: Maps to Textract TABLE blocks
- **kr:TableCell**: Maps to Textract CELL blocks
- **kr:Title**: Maps to Textract TITLE blocks
- **kr:SelectionElement**: Maps to Textract SELECTION_ELEMENT blocks

**Design Rationale**: Direct 1:1 mapping ensures no loss of Textract structural information while providing RDF querying capabilities.

---

## PROPERTY DESIGN LOGIC

### HIERARCHICAL RELATIONSHIPS

#### Document Hierarchy Properties
```turtle
kr:hasPage, kr:hasSection, kr:hasSubsection, kr:hasChunk
```
**Logic**: Top-down containment relationships that mirror document structure
**Benefits**: Enables hierarchical queries, supports navigation patterns

#### Parent Reference Properties  
```turtle
kr:parentSection, kr:parentDocument
```
**Logic**: Bottom-up references for efficient reverse navigation
**Benefits**: Supports context discovery, enables breadcrumb navigation

### SEQUENCING PROPERTIES

#### Ordering Properties
```turtle
kr:pageNumber, kr:sectionSequence, kr:chunkSequence, kr:hierarchyLevel
```
**Logic**: Explicit ordering enables sequential navigation and proper document reconstruction
**Benefits**: Supports "next/previous" navigation, maintains document flow

**Design Decision**: Used positive integers rather than linked lists for better query performance and simpler URI generation.

### TEXTRACT INTEGRATION PROPERTIES

#### Structural Properties
```turtle
kr:hasTextLine, kr:hasWord, kr:hasTable, kr:hasCell, kr:hasTitle
```
**Logic**: Preserve complete Textract structural hierarchy for detailed analysis
**Benefits**: Enables fine-grained queries, supports table extraction, maintains formatting context

#### Geometric Properties
```turtle
kr:boundingBox, kr:pageHeight, kr:pageWidth
```
**Logic**: Preserve spatial relationships for layout-aware processing
**Benefits**: Supports visual document analysis, enables region-based queries

### CONTENT AND METADATA PROPERTIES

#### Content Properties
```turtle
kr:textContent, kr:wordCount, kr:sentenceCount
```
**Logic**: Store extracted content with metrics for processing optimization
**Benefits**: Enables content-based filtering, supports chunk size optimization

#### Quality Properties
```turtle
kr:confidence
```
**Logic**: Preserve Textract confidence scores for quality assessment
**Benefits**: Enables quality-based filtering, supports error detection

### S3 INTEGRATION PROPERTIES

#### Storage Properties
```turtle
kr:s3Location, kr:s3Bucket, kr:s3Key
```
**Logic**: Direct links to S3 storage for efficient content retrieval
**Benefits**: Enables direct S3 access from URIs, supports distributed processing

**Design Decision**: Separate bucket and key properties allow flexible S3 organization while maintaining direct access capability.

### PROCESSING METADATA PROPERTIES

#### Provenance Properties
```turtle
kr:processingTimestamp, kr:textractJobId, kr:chunkingStrategy
```
**Logic**: Track processing history for debugging and quality control
**Benefits**: Enables processing audit trails, supports system monitoring

---

## URI MINTING DESIGN CONSIDERATIONS

### SYSTEMATIC URI PATTERNS

The schema is designed to support predictable URI patterns based on doc_id:

#### Document Level
```turtle
sg:Document_{doc_id} a kr:Document
```

#### Page Level  
```turtle
sg:Document_{doc_id}_Page_{page_number} a kr:DocumentPage
```

#### Section Level
```turtle
sg:Document_{doc_id}_Section_{section_sequence} a kr:DocumentSection
sg:Document_{doc_id}_Section_{parent_sequence}_{child_sequence} a kr:DocumentSection
```

#### Chunk Level
```turtle
sg:Document_{doc_id}_Section_{section_sequence}_Chunk_{chunk_sequence} a kr:DocumentChunk
```

#### S3 Direct Access
```turtle
sg:Document_{doc_id}_Section_{section_sequence}_Chunk_{chunk_sequence} kr:s3Location "s3://bucket/path/to/chunk"
```

### URI DESIGN BENEFITS

1. **PREDICTABLE PATTERNS**: URIs follow consistent naming conventions
2. **HIERARCHICAL ENCODING**: URI structure reflects document hierarchy
3. **S3 INTEGRATION**: Chunk URIs can directly resolve to S3 locations
4. **COLLISION AVOIDANCE**: doc_id-based prefixes prevent URI conflicts
5. **HUMAN READABLE**: URIs are interpretable by developers and users

---

## SCHEMA EXTENSIBILITY

### EXTENSION POINTS

#### Additional Textract Elements
The schema can easily accommodate new Textract block types by:
1. Creating new subclasses of kr:DocumentStructureElement
2. Adding specific properties as needed
3. Maintaining inheritance of common properties

#### Custom Document Types
Domain-specific document types can extend the base classes:
```turtle
gaip:InsurancePolicy rdfs:subClassOf kr:Document
gaip:RiskAssessment rdfs:subClassOf kr:Document
```

#### Processing Enhancements
New processing metadata can be added without schema changes:
```turtle
kr:nlpProcessingMetadata, kr:vectorEmbeddingMetadata
```

### BACKWARD COMPATIBILITY

The schema design ensures backward compatibility by:
1. Using RDFS rather than OWL for flexibility
2. Avoiding restrictive constraints
3. Supporting optional properties
4. Maintaining stable core class hierarchy

---

## INTEGRATION WITH EXISTING SYSTEM

### TEXTRACT PROCESSING INTEGRATION

The schema maps directly to our existing Textract processing:
- **Document**: Maps to processed PDF document
- **Page**: Maps to Textract PAGE blocks
- **TextLine**: Maps to Textract LINE blocks
- **Table**: Maps to Textract TABLE blocks

### CHUNKING INTEGRATION

The schema supports our smart structured chunking:
- **DocumentSection**: Logical sections from structure analysis
- **DocumentChunk**: Processing chunks within sections
- **Sequencing**: Maintains chunk order within sections

### S3 STORAGE INTEGRATION

The schema integrates with our S3 storage architecture:
- **Direct Access**: Chunk URIs resolve to S3 locations
- **Bucket Organization**: Supports existing bucket structure
- **Processing Pipeline**: Maintains existing S3 workflows

---

## QUERY PATTERNS SUPPORTED

### HIERARCHICAL QUERIES
```sparql
# Find all chunks in a specific section
SELECT ?chunk WHERE {
    sg:Document_123_Section_2 kr:hasChunk ?chunk .
}
```

### SEQUENTIAL QUERIES
```sparql
# Find next chunk in sequence
SELECT ?nextChunk WHERE {
    ?chunk kr:chunkSequence ?seq ;
           kr:parentSection ?section .
    ?nextChunk kr:chunkSequence ?nextSeq ;
               kr:parentSection ?section .
    FILTER(?nextSeq = ?seq + 1)
}
```

### CONTENT QUERIES
```sparql
# Find chunks with specific word count range
SELECT ?chunk WHERE {
    ?chunk a kr:DocumentChunk ;
           kr:wordCount ?count .
    FILTER(?count >= 100 && ?count <= 500)
}
```

### S3 ACCESS QUERIES
```sparql
# Get S3 location for direct access
SELECT ?s3Location WHERE {
    sg:Document_123_Section_2_Chunk_1 kr:s3Location ?s3Location .
}
```

---

## PERFORMANCE CONSIDERATIONS

### INDEXING STRATEGY

Recommended indexes for efficient queries:
1. **Document ID indexes**: Fast document-level queries
2. **Sequence indexes**: Efficient sequential navigation
3. **Parent-child indexes**: Fast hierarchical traversal
4. **Content size indexes**: Efficient filtering by chunk characteristics

### QUERY OPTIMIZATION

The schema supports query optimization through:
1. **Direct property paths**: Avoid complex graph traversals
2. **Explicit sequencing**: Use integers rather than linked lists
3. **Cached relationships**: Parent references for reverse navigation
4. **Selective properties**: Optional detailed properties for performance tuning

---

## VALIDATION AND QUALITY CONTROL

### SCHEMA VALIDATION

The schema supports validation through:
1. **Required properties**: Core properties for essential functionality
2. **Data type constraints**: XSD types for data validation
3. **Relationship constraints**: Domain/range specifications
4. **Confidence tracking**: Quality metrics for all elements

### CONSISTENCY CHECKS

The schema enables consistency validation:
1. **Sequence integrity**: Verify sequential numbering
2. **Hierarchy consistency**: Validate parent-child relationships
3. **S3 reference validity**: Verify S3 locations exist
4. **Content metrics accuracy**: Validate word/sentence counts

---

## CONCLUSION

This RDFS schema provides a robust foundation for capturing document structure while supporting the dual traversal knowledge graph strategy. The design balances:

- **TEXTRACT FIDELITY**: Complete preservation of structural information
- **HIERARCHICAL ORGANIZATION**: Support for complex document structures  
- **URI MINTING EFFICIENCY**: Systematic, predictable URI patterns
- **S3 INTEGRATION**: Direct access to stored content
- **QUERY PERFORMANCE**: Optimized for common access patterns
- **EXTENSIBILITY**: Ready for future enhancements

The schema serves as the foundation for Phase 1 implementation, focusing on document structure capture while preparing for future ontology integration and entity extraction capabilities.
