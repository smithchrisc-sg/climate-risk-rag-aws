# Semantic Document Structure Schema Explanation
## Date: 2025-07-28
## Status: Updated Semantic Model with Hierarchical Chunker Integration

## OVERVIEW

This document explains the updated semantic document structure schema for the GAIP Knowledge Repository. The schema has been redesigned to focus on **semantic meaning** rather than processing artifacts, while integrating seamlessly with our new hierarchical layout-based chunker.

## KEY DESIGN CHANGES

### 1. SEMANTIC-FIRST APPROACH
- **Focus on meaning**: Classes represent what content IS (Paragraph, Section, Table) rather than how it's processed
- **Clean separation**: Processing metadata moved to separate `sgm:` namespace
- **Natural relationships**: Tree structure based on semantic containment, not technical hierarchy levels

### 2. NAMESPACE REORGANIZATION
- **`sgd:`** - Semantic document structure classes and relationships
- **`sgm:`** - Processing metadata and technical details  
- **`sgi:`** - Impact ontology (future use for domain entities)

### 3. HIERARCHICAL CHUNKER INTEGRATION
- Direct mapping from chunker `section_type` values to semantic classes
- Support for split paragraphs with `ParagraphPart` relationships
- Tree-based navigation without explicit hierarchy levels

---

## SEMANTIC CLASS DESIGN

### CORE PRINCIPLE: SEMANTIC MEANING OVER PROCESSING ARTIFACTS

The schema represents **what content means** in the document context:

#### sgd:Section
**Semantic Meaning**: A logical section of the document that groups related content
**Content**: Typically contains title-like text ("ABBREVIATIONS AND ACRONYMS", "I. INTRODUCTION")
**Chunker Mapping**: `section_type: "title"` → `sgd:Section`

#### sgd:Paragraph  
**Semantic Meaning**: A coherent paragraph expressing a particular idea or concept
**Content**: Complete thoughts suitable for vector embeddings
**Chunker Mapping**: `section_type: "paragraph"` → `sgd:Paragraph`

#### sgd:ParagraphPart
**Semantic Meaning**: Part of a paragraph that was split for processing while maintaining semantic unity
**Content**: Portion of original paragraph with sentence overlap
**Chunker Mapping**: `is_split_paragraph: true` → `sgd:Paragraph` with `sgd:ParagraphPart` children

#### sgd:Heading
**Semantic Meaning**: Section headings that organize document content
**Chunker Mapping**: `section_type: "header"` → `sgd:Heading`

#### sgd:List, sgd:Table, sgd:Figure
**Semantic Meaning**: Specialized content types with distinct presentation
**Chunker Mapping**: Direct mapping from respective `section_type` values

---

## RELATIONSHIP MODEL

### TREE-BASED SEMANTIC STRUCTURE

The schema uses tree relationships to represent semantic containment:

```turtle
# Semantic tree structure
sgd:hasChild     # Parent → Child relationship
sgd:hasParent    # Child → Parent relationship  
sgd:hasSibling   # Sibling relationships
sgd:contains     # General containment
sgd:partOf       # Part-of relationships
```

### NO EXPLICIT HIERARCHY LEVELS
- Removed `hierarchyLevel` property - use tree traversal instead
- Natural hierarchy emerges from parent-child relationships
- More flexible for diverse document structures

### SPLIT PARAGRAPH HANDLING
```turtle
# Semantic paragraph (no direct content)
:paragraph_123 a sgd:Paragraph ;
    sgd:hasPart :paragraph_123_part1, :paragraph_123_part2 .

# Actual content parts
:paragraph_123_part1 a sgd:ParagraphPart ;
    sgd:partOf :paragraph_123 ;
    sgd:partNumber 1 ;
    sgd:totalParts 2 ;
    sgd:s3Location "s3://bucket/paragraph_123_part1.json" .
```

---

## PROCESSING METADATA SEPARATION

### CLEAN NAMESPACE SEPARATION

**Semantic Layer (`sgd:`)**: What the content means
```turtle
chunk_0009 a sgd:Section ;
    dcterms:title "ABBREVIATIONS AND ACRONYMS" ;
    sgd:hasChild chunk_0000, chunk_0001 ;
    sgd:s3Location "s3://bucket/chunk_0009.json" .
```

**Processing Layer (`sgm:`)**: How we processed it
```turtle
chunk_0009 sgm:chunkId "064762102bead7b04a39_chunk_0009" ;
           sgm:chunkIndex 9 ;
           sgm:originalSectionType "title" ;
           sgm:characterCount 28 ;
           sgm:chunkingStrategy "layout_based" ;
           sgm:processingTimestamp "2025-07-28T12:49:49Z" .
```

### BENEFITS OF SEPARATION
1. **Clean semantic queries**: Find all Paragraphs without processing noise
2. **Processing transparency**: Technical details available when needed
3. **Schema evolution**: Can change processing without affecting semantics
4. **Performance**: Semantic queries don't need to filter processing metadata

---

## CHUNKER OUTPUT MAPPING

### DIRECT MAPPING FROM HIERARCHICAL CHUNKER

Our hierarchical chunker output maps cleanly to semantic classes:

| Chunker Output | Semantic Class | Meaning |
|----------------|----------------|---------|
| `section_type: "title"` | `sgd:Section` | Document section with title content |
| `section_type: "header"` | `sgd:Heading` | Section heading |
| `section_type: "paragraph"` | `sgd:Paragraph` | Text paragraph |
| `section_type: "list"` | `sgd:List` | Enumerated content |
| `section_type: "table"` | `sgd:Table` | Tabular data |
| `section_type: "figure"` | `sgd:Figure` | Visual content |

### RELATIONSHIP MAPPING

| Chunker Field | Semantic Property | Processing Property |
|---------------|-------------------|-------------------|
| `parent_chunk_id` | `sgd:hasParent` | `sgm:chunkId` (for reference) |
| `child_chunk_ids` | `sgd:hasChild` | - |
| `sibling_chunk_ids` | `sgd:hasSibling` | - |
| `is_split_paragraph` | `sgd:hasPart` → `sgd:ParagraphPart` | `sgm:isSplitParagraph` |
| `split_part` | `sgd:partNumber` | - |
| `total_splits` | `sgd:totalParts` | - |

---

## STORAGE MODEL

### UNIFIED S3 STORAGE WITH SEMANTIC CLASSES

All content is stored as S3 chunks, but each chunk represents a semantic element:

```turtle
# All stored as chunks, semantically different
chunk_0009 a sgd:Section ;           # Title content in S3
    sgd:s3Location "s3://bucket/chunk_0009.json" .

chunk_0000 a sgd:Paragraph ;         # Paragraph content in S3
    sgd:s3Location "s3://bucket/chunk_0000.json" .

chunk_0166 a sgd:Table ;             # Table content in S3
    sgd:s3Location "s3://bucket/chunk_0166.json" .
```

### BENEFITS
- **Semantic queries**: "Find all Tables in this Section"
- **Efficient storage**: Uniform S3 chunk storage regardless of semantic type
- **Rich relationships**: Tree navigation for document structure
- **Vector embeddings**: Paragraphs are ideal units for embeddings

---

## QUERY PATTERNS

### SEMANTIC QUERIES

```sparql
# Find all paragraphs in a section
SELECT ?paragraph WHERE {
    ?section a sgd:Section ;
             dcterms:title "Introduction" ;
             sgd:hasChild ?paragraph .
    ?paragraph a sgd:Paragraph .
}

# Navigate document tree
SELECT ?child WHERE {
    sg:chunk_0009 sgd:hasChild ?child .
    ?child a sgd:Paragraph .
}

# Find split paragraphs
SELECT ?part WHERE {
    ?paragraph a sgd:Paragraph ;
               sgd:hasPart ?part .
    ?part a sgd:ParagraphPart .
}
```

### PROCESSING QUERIES

```sparql
# Find chunks by processing characteristics
SELECT ?element WHERE {
    ?element sgm:chunkingStrategy "layout_based" ;
             sgm:characterCount ?count .
    FILTER(?count > 100)
}

# Get processing provenance
SELECT ?timestamp ?strategy WHERE {
    sg:chunk_0009 sgm:processingTimestamp ?timestamp ;
                  sgm:chunkingStrategy ?strategy .
}
```

---

## DUBLIN CORE INTEGRATION

### STANDARD METADATA VOCABULARY

The schema continues to use Dublin Core for standard document metadata:

```turtle
sg:document_123 a sgd:Document ;
    # Standard bibliographic metadata
    dcterms:identifier "064762102bead7b04a39" ;
    dcterms:title "Post Disaster Financial Sector Credit" ;
    dcterms:creator "World Bank" ;
    dcterms:issued "2015-04-01"^^xsd:date ;
    dcterms:format "application/pdf" ;
    dcterms:language "en" ;
    
    # Processing timestamps
    dcterms:modified "2025-07-28T12:49:49Z"^^xsd:dateTime ;
    
    # Source provenance
    dcterms:source <s3://source-bucket/original.pdf> ;
    dcterms:provenance "Processed via hierarchical layout chunker" .
```

---

## ENTITY ANCHORING PREPARATION

### READY FOR NLP ENTITY INTEGRATION

The semantic structure provides clean anchoring points for NLP entities:

```turtle
# Future entity integration (sgi: namespace)
sgi:WorldBank a sgi:Organization ;
    sgi:mentionedIn sg:chunk_0001 ;        # Direct chunk reference
    sgi:hasContext sg:chunk_0009 ;         # Parent section context
    sgi:inSection "ABBREVIATIONS AND ACRONYMS" .  # Semantic context
```

### BENEFITS FOR ENTITY MAPPING
1. **Clean anchoring**: Entities link to semantic elements, not processing artifacts
2. **Contextual hierarchy**: Parent-child relationships provide context chains
3. **Section filtering**: Entity queries can filter by semantic section types
4. **Paragraph focus**: Entities primarily anchor to Paragraphs (ideal for embeddings)

---

## IMPLEMENTATION STRATEGY

### DOCUMENT STRUCTURE KG PROCESSOR UPDATES

The `document-structure-kg-processor` needs updates to:

1. **Map chunker output** to semantic classes based on `section_type`
2. **Create tree relationships** from `parent_chunk_id` and `child_chunk_ids`
3. **Handle split paragraphs** by creating `ParagraphPart` relationships
4. **Separate metadata** into semantic vs. processing namespaces
5. **Generate URIs** following semantic patterns

### BACKWARD COMPATIBILITY

- Existing processing metadata preserved in `sgm:` namespace
- S3 storage patterns unchanged
- URI patterns can be migrated incrementally
- Queries can target either semantic or processing layers

---

## CONCLUSION

This semantic-first schema design provides:

- **Clean semantic model**: Focus on document meaning rather than processing artifacts
- **Hierarchical chunker integration**: Direct mapping from chunker output to semantic structure
- **Processing transparency**: Technical details available but separated
- **Entity readiness**: Clean anchoring points for NLP entity integration
- **Query flexibility**: Semantic queries without processing noise
- **Storage efficiency**: Uniform S3 chunks with rich semantic metadata

The schema serves as the foundation for semantic document understanding while maintaining full integration with our hierarchical chunking pipeline and preparing for advanced entity extraction and knowledge graph construction.
