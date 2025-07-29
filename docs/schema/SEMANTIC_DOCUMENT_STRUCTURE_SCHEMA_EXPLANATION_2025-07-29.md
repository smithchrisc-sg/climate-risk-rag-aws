# Semantic Document Structure Schema v3.1 - Explanation
**Date**: 2025-07-29  
**Version**: 3.1 - Dublin Core Inheritance and Simplified Navigation  
**Schema File**: `document_structure_schema_v3.ttl`

## Overview

This document explains the semantic document structure schema that maps hierarchical chunker output to RDF triples for knowledge graph storage. Version 3.1 introduces Dublin Core inheritance for standards compliance and simplified sibling navigation for efficient document traversal.

## Key Design Principles

### 1. **Dublin Core Inheritance**
Our document structure properties inherit from established Dublin Core vocabulary:
- `sgd:hasChild` inherits from `dcterms:hasPart`
- `sgd:hasParent` inherits from `dcterms:isPartOf`
- This provides standards compliance and interoperability

### 2. **Semantic vs Processing Separation**
- **`sgd:` namespace**: What the content means semantically
- **`sgm:` namespace**: How it was processed/extracted
- **Dublin Core**: Standard bibliographic metadata

### 3. **Simplified Navigation**
- Only `sgd:nextSibling` for ordered traversal (no `previousSibling`)
- Convenience properties `sgd:firstChild` and `sgd:lastChild`
- Eliminated redundant `sgd:hasSibling` (can derive from navigation)

## Namespace Structure

### Core Namespaces
```turtle
@prefix sgd: <http://solve.global/knowledge-commons/document-structure#> .
@prefix sgm: <http://solve.global/knowledge-commons/process-metadata#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
```

### Property Hierarchy
```
dcterms:hasPart
  └── sgd:hasChild
      ├── sgd:firstChild
      └── sgd:lastChild

dcterms:isPartOf
  └── sgd:hasParent
```

## Semantic Classes

### Document Structure Classes
Maps directly to hierarchical chunker `section_type` values:

| Chunker `section_type` | Semantic Class | Description |
|----------------------|----------------|-------------|
| `title` | `sgd:Section` | Sections with title content |
| `header` | `sgd:Heading` | Section headings |
| `paragraph` | `sgd:Paragraph` | Text paragraphs |
| `list` | `sgd:List` | Enumerated content |
| `table` | `sgd:Table` | Tabular data |
| `figure` | `sgd:Figure` | Visual content |

### Split Paragraph Handling
- `sgd:Paragraph` → parent paragraph that was split
- `sgd:ParagraphPart` → individual parts of split paragraph
- `sgd:partNumber` → sequence within split paragraph
- `sgd:totalParts` → total number of parts

## Relationship Properties

### Core Hierarchical Relationships
```turtle
# Dublin Core level (general)
dcterms:hasPart     # General part-of relationship
dcterms:isPartOf    # General is-part-of relationship

# Document structure level (specific)
sgd:hasChild        # Direct child in document tree
sgd:hasParent       # Direct parent in document tree
sgd:firstChild      # First child in document order
sgd:lastChild       # Last child in document order

# Navigation
sgd:nextSibling     # Next sibling in document order
```

### Split Paragraph Relationships
```turtle
sgd:hasPart         # Paragraph has parts when split
sgd:partNumber      # Part sequence number
sgd:totalParts      # Total number of parts
```

## Processing Metadata Properties

### Storage and Positioning (sgm: namespace)
```turtle
sgm:s3Location      # S3 URI for chunk content
sgm:s3Bucket        # S3 bucket name
sgm:s3Key           # S3 object key
sgm:pageNumber      # Page number (publishing artifact)
sgm:sequenceNumber  # Processing order
```

### Chunker Output Mapping
```turtle
sgm:chunkId         # Original chunk identifier
sgm:chunkIndex      # Sequential chunk index
sgm:originalSectionType     # Original section_type value
sgm:originalHierarchyLevel  # Original hierarchy_level (deprecated)
```

### Content Metrics
```turtle
sgm:characterCount  # Character count
sgm:wordCount       # Word count
sgm:sentenceCount   # Sentence count
```

### Processing Provenance
```turtle
sgm:chunkingStrategy        # Strategy used (layout_based, sentence_based)
sgm:processingTimestamp     # When processed
sgm:textractJobId          # AWS Textract job ID
sgm:textractConfidence     # Textract confidence score
```

## Example RDF Structure

### Document with Children
```turtle
sg:document_064762102bead7b04a39 rdf:type sgd:Document ;
    # Dublin Core metadata
    dcterms:identifier "064762102bead7b04a39" ;
    dcterms:title "Post Disaster Second Financial Sector Stability Credit" ;
    
    # Dublin Core relationships (inherited by sgd:hasChild)
    dcterms:hasPart sg:chunk_0009, sg:chunk_0108 ;
    
    # Document structure relationships
    sgd:hasChild sg:chunk_0009, sg:chunk_0108 ;
    sgd:firstChild sg:chunk_0009 ;
    sgd:lastChild sg:chunk_0108 .
```

### Section with Ordered Children
```turtle
sg:chunk_0009 rdf:type sgd:Section ;
    # Dublin Core semantic metadata
    dcterms:title "ABBREVIATIONS AND ACRONYMS" ;
    dcterms:isPartOf sg:document_064762102bead7b04a39 ;
    
    # Dublin Core relationships
    dcterms:hasPart sg:chunk_0000, sg:chunk_0001, sg:chunk_0002 ;
    
    # Document structure relationships
    sgd:hasChild sg:chunk_0000, sg:chunk_0001, sg:chunk_0002 ;
    sgd:firstChild sg:chunk_0000 ;
    sgd:lastChild sg:chunk_0002 ;
    
    # Processing metadata
    sgm:s3Location <s3://chunks-bucket/.../chunk_0009.json> ;
    sgm:pageNumber 1 ;
    sgm:chunkId "064762102bead7b04a39_chunk_0009" ;
    sgm:originalSectionType "title" ;
    sgm:chunkingStrategy "layout_based" .
```

### Ordered Sibling Navigation
```turtle
# First paragraph
sg:chunk_0000 rdf:type sgd:Paragraph ;
    sgd:hasParent sg:chunk_0009 ;
    sgd:nextSibling sg:chunk_0001 ;
    sgm:sequenceNumber 0 .

# Middle paragraph
sg:chunk_0001 rdf:type sgd:Paragraph ;
    sgd:hasParent sg:chunk_0009 ;
    sgd:nextSibling sg:chunk_0002 ;
    sgm:sequenceNumber 1 .

# Last paragraph
sg:chunk_0002 rdf:type sgd:Paragraph ;
    sgd:hasParent sg:chunk_0009 ;
    # No nextSibling - this is last
    sgm:sequenceNumber 2 .
```

## Query Patterns

### Dublin Core Level Queries
```sparql
# Find all parts of a document (general)
SELECT ?part WHERE {
    sg:document_064762102bead7b04a39 dcterms:hasPart ?part .
}

# Find what a paragraph is part of (general)
SELECT ?parent WHERE {
    sg:chunk_0000 dcterms:isPartOf ?parent .
}
```

### Document Structure Level Queries
```sparql
# Find direct children (specific)
SELECT ?child WHERE {
    sg:chunk_0009 sgd:hasChild ?child .
}

# Find first and last children (convenient)
SELECT ?first ?last WHERE {
    sg:chunk_0009 sgd:firstChild ?first ;
                  sgd:lastChild ?last .
}
```

### Navigation Queries
```sparql
# Forward traversal - all following siblings
SELECT ?following WHERE {
    sg:chunk_0000 sgd:nextSibling+ ?following .
}

# Backward traversal - find previous sibling
SELECT ?previous WHERE {
    ?previous sgd:nextSibling sg:chunk_0001 .
}

# Find all siblings (derived)
SELECT ?sibling WHERE {
    ?parent sgd:hasChild sg:chunk_0001 .
    ?parent sgd:hasChild ?sibling .
    FILTER(?sibling != sg:chunk_0001)
}
```

### Mixed Level Queries
```sparql
# Combine Dublin Core and document structure
SELECT ?document ?paragraph ?next WHERE {
    ?document dcterms:hasPart ?paragraph .
    ?paragraph a sgd:Paragraph .
    ?paragraph sgd:nextSibling ?next .
}
```

## Benefits of This Design

### Standards Compliance
- **Dublin Core inheritance** provides interoperability
- **OWL property hierarchy** enables semantic reasoning
- **Standard vocabularies** work with existing tools

### Query Flexibility
- **Multiple abstraction levels** for different use cases
- **Efficient navigation** with minimal storage
- **Backward compatibility** with Dublin Core tools

### Maintenance Simplicity
- **Single source of truth** for relationships
- **No redundant properties** to synchronize
- **Clear semantic separation** between meaning and processing

### Performance Benefits
- **Fewer triples** to store and query
- **Optimized traversal** patterns
- **Reduced complexity** in relationship management

## Implementation Notes

### Property Assertion Strategy
We explicitly assert both Dublin Core and document structure properties:
```python
# Assert both levels for compatibility
graph.add((parent_uri, DCTERMS.hasPart, child_uri))
graph.add((parent_uri, self.sgd_ns.hasChild, child_uri))
```

### Chunker Integration
The schema maps directly to hierarchical chunker output:
- `section_type` → semantic class
- `parent_chunk_id` → `sgd:hasParent`
- `child_chunk_ids` → `sgd:hasChild`
- `chunk_index` → `sgm:sequenceNumber`

### Split Paragraph Processing
Split paragraphs create `ParagraphPart` instances with:
- `sgd:partOf` relationship to parent paragraph
- `sgd:partNumber` for ordering
- `sgd:totalParts` for context

This design provides a robust, standards-compliant foundation for semantic document structure representation while maintaining the simplicity and efficiency needed for large-scale document processing.
