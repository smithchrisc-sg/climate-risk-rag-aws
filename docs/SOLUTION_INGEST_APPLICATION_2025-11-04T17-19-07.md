# Solution Ingestion Application Implementation Plan
**Document Created:** 2025-11-04T17:19:07Z  
**Target Delivery:** November 15, 2025  
**Purpose:** CLI utility to ingest 325 solutions from CSV into PostgreSQL + OpenSearch + Neptune

## Executive Summary

This document outlines the implementation plan for a standalone CLI application that processes solution CSV files into the GAIP Knowledge Repository system. The utility will create pseudo-documents with hierarchical search capabilities, supporting the new API v2.0 specification requiring Solutions with nested related documents.

## Context & Rationale

### Why This Approach
- **Deadline Pressure**: November 15 delivery requires pragmatic one-off solution
- **API v2.0 Requirements**: New hierarchical response structure needs solution content
- **Infrastructure Readiness**: PostgreSQL, OpenSearch, Neptune already support content_type field
- **Risk Mitigation**: Standalone utility avoids disrupting production Lambda functions
- **Future Integration**: Modular design enables reuse in refactored crawler pipeline

### System Integration Points
- **Database**: Uses existing DatabaseManager/DocumentIDManager from database-core-layer
- **Knowledge Graph**: Uses existing KG utilities from knowledge-graph-layer  
- **Search**: Duplicates Lambda indexing logic for keyword/vector operations
- **Data Lake**: Outputs in existing S3 data lake format for development/debugging

## Architecture Overview

### Execution Environment
- **Platform**: EC2 instance within VPC (required for Neptune/OpenSearch access)
- **Deployment**: Standalone Python application with copied layer dependencies
- **Data Flow**: CSV → PostgreSQL + OpenSearch + Neptune + Local Data Lake

### Data Processing Strategy
```
CSV Row → Solution Object → {
    ├── PostgreSQL: Metadata (title, source_url, content_type="solution")
    ├── OpenSearch documents_keyword: Pseudo-document with generated intro
    ├── OpenSearch chunks_vector: 3 chunks (description, highlights, results)
    └── Neptune: KG triples (organizations, risks, themes, locations)
}
```

## Directory Structure

### Project Layout
```
/Users/chris/climate-risk-rag-aws/solution_ingestion/
├── main.py                          # CLI entry point
├── config/
│   ├── __init__.py
│   └── settings.py                  # Environment configuration
├── models/
│   ├── __init__.py
│   ├── solution.py                  # Solution data class
│   └── ingestion_result.py          # Results tracking
├── parsers/
│   ├── __init__.py
│   ├── csv_parser.py                # CSV → Solution objects
│   ├── url_extractor.py             # URL parsing/validation
│   ├── date_parser.py               # dd/mm/yyyy → ISO8601
│   ├── contact_parser.py            # Contact info parsing
│   └── organization_parser.py       # Org normalization
├── generators/
│   ├── __init__.py
│   ├── pseudo_document.py           # Generate keyword document + intro
│   ├── chunk_generator.py           # Generate 3 chunks per solution
│   └── kg_triple_generator.py       # Generate RDF triples
├── indexers/
│   ├── __init__.py
│   ├── keyword_indexer.py           # Duplicate keyword-indexer logic
│   ├── vector_indexer.py            # Duplicate vector-embeddings logic
│   └── opensearch_client.py         # OpenSearch connection utilities
├── processors/
│   ├── __init__.py
│   ├── postgres_processor.py        # Use DatabaseManager/DocumentIDManager
│   ├── opensearch_processor.py      # Coordinate indexing operations
│   └── neptune_processor.py         # Use KG layer utilities
├── utils/
│   ├── __init__.py
│   └── logger.py                    # Logging configuration
├── layers/                          # CLEAN COPIES (no modifications)
│   ├── database-core-layer/         # Copied from production
│   └── knowledge-graph-layer/       # Copied from production
├── input_data/
│   └── solutions.csv                # Input CSV files
├── output_data/                     # Local data lake structure
│   ├── kr-dl-text/data-lake/<sol_id>/raw_text.txt
│   ├── kr-dl-chunks/data-lake/<sol_id>/<sol_id>_chunk_<seq>.json
│   ├── kr-dl-embeddings/data-lake/<sol_id>/<sol_id>_chunk_<seq>_embedding.json
│   └── kr-dl-neptune-ttl/data-lake/<sol_id>/<sol_id>.ttl
├── requirements.txt
├── deploy.sh                        # EC2 deployment script
└── README.md
```

## Component Design Details

### 1. CSV Parser (`parsers/csv_parser.py`)
**Purpose**: Parse CSV rows into structured Solution objects
**Key Features**:
- Handle 20 CSV columns (Name, Country, Organizations, Risk Types, etc.)
- Validate required fields (Name, source URL)
- Parse comma-separated values (organizations, themes, risk types)
- Convert dates from dd/mm/yyyy to ISO8601

### 2. Pseudo Document Generator (`generators/pseudo_document.py`)
**Purpose**: Create searchable document content from solution metadata
**Generated Structure**:
```
Title: [Name]
Author: [Combined organizations]
Introduction: Generated paragraph from metadata
Description: [Description field]
Key Highlights: [Key Highlights field]  
Results: [Results field]
```

### 3. Chunk Generator (`generators/chunk_generator.py`)
**Purpose**: Create 3 optimized chunks per solution for vector search
**Chunk Strategy**:
- Chunk 1: Description content
- Chunk 2: Key Highlights content
- Chunk 3: Results content
**Output Format**: Matches existing chunk JSON structure with metadata

### 4. KG Triple Generator (`generators/kg_triple_generator.py`)
**Purpose**: Generate RDF triples using existing KG layer utilities
**Triple Categories**:
- Geographic: Country → GeoNames URIs
- Organizations: Normalized organization URIs with foaf:Organization hierarchy
- Risk/Solution Types: Normalized concept URIs
- Themes: Normalized theme URIs
- Sources: hasOrganizationSource/hasOtherSource relationships
- Temporal: Implementation year, dates added/updated

### 5. Keyword Indexer (`indexers/keyword_indexer.py`)
**Purpose**: Index pseudo-documents in documents_keyword OpenSearch index
**Logic Source**: Duplicated from `/lambda/keyword-indexer/src/structure_aware_processor.py`
**Key Features**:
- Content_type: "solution" field
- Full-text indexing of pseudo-document content
- Metadata preservation

### 6. Vector Indexer (`indexers/vector_indexer.py`)
**Purpose**: Generate embeddings and index chunks in chunks_vector OpenSearch index
**Logic Source**: Duplicated from `/lambda/vector-embeddings-worker/`
**Key Features**:
- Synchronous Bedrock Titan embedding generation
- Content_type: "solution" field
- 1536-dimension vector storage

### 7. Database Processor (`processors/postgres_processor.py`)
**Purpose**: Store solution metadata in PostgreSQL
**Dependencies**: Uses existing DatabaseManager/DocumentIDManager
**Operations**:
- Generate solution IDs with sol_ prefix
- Store metadata in documents table with content_type="solution"

### 8. Neptune Processor (`processors/neptune_processor.py`)
**Purpose**: Load RDF triples into Neptune knowledge graph
**Dependencies**: Uses existing KG layer utilities (KnowledgeGraphManager, TripleManager)
**Operations**:
- Batch triple insertion
- URI normalization and deduplication

## Data Lake Output Format

### File Structure (Development/Debug)
```
output_data/
├── kr-dl-text/data-lake/sol_abc123/raw_text.txt
├── kr-dl-chunks/data-lake/sol_abc123/
│   ├── sol_abc123_chunk_0001.json
│   ├── sol_abc123_chunk_0002.json
│   └── sol_abc123_chunk_0003.json
├── kr-dl-embeddings/data-lake/sol_abc123/
│   ├── sol_abc123_chunk_0001_embedding.json
│   ├── sol_abc123_chunk_0002_embedding.json
│   └── sol_abc123_chunk_0003_embedding.json
└── kr-dl-neptune-ttl/data-lake/sol_abc123/sol_abc123.ttl
```

### JSON Format Specifications
**Chunk JSON**:
```json
{
  "chunk_id": "sol_abc123_chunk_0001",
  "doc_id": "sol_abc123",
  "chunk_index": 1,
  "text": "Description content...",
  "character_count": 1164,
  "page_numbers": [1],
  "section_types": ["description"],
  "hierarchy_levels": [1],
  "table_count": 0,
  "list_count": 0,
  "semantic_context": "",
  "overlap_with_previous": false,
  "overlap_with_next": true
}
```

**Embedding JSON**:
```json
{
  "chunk_id": "sol_abc123_chunk_0001",
  "doc_id": "sol_abc123",
  "chunk_index": 1,
  "text": "Description content...",
  "embedding": [0.005989, -0.168980, ...],
  "character_count": 1164,
  "embedding_model": "amazon.titan-embed-text-v1",
  "embedding_dimension": 1536,
  "embedding_created_at": "2025-11-04T17:19:07Z"
}
```

## Configuration Requirements

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# OpenSearch
OPENSEARCH_ENDPOINT=https://vpc-solve-global-kr-search-*.us-east-1.es.amazonaws.com
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=veqpat-kegba2-zapbyZ

# Neptune
NEPTUNE_ENDPOINT=solve-global-kr-neptune-cluster.cluster-*.neptune.amazonaws.com
NEPTUNE_PORT=8182

# AWS
AWS_REGION=us-east-1
AWS_PROFILE=solve-global

# Bedrock
BEDROCK_REGION=us-east-1
EMBEDDING_MODEL=amazon.titan-embed-text-v1
```

### Dependencies (`requirements.txt`)
```
boto3>=1.26.0
psycopg2-binary>=2.9.0
opensearch-py>=2.0.0
requests>=2.28.0
pandas>=1.5.0
python-dateutil>=2.8.0
```

## Deployment Strategy

### Local Development Setup
1. Create directory structure under `/Users/chris/climate-risk-rag-aws/solution_ingestion/`
2. Copy clean layer code from production
3. Set up local data lake directories
4. Configure environment variables
5. Test with sample CSV data

### EC2 Deployment Process
```bash
# 1. Package application
tar -czf solution_ingestion.tar.gz solution_ingestion/

# 2. Copy to EC2
scp solution_ingestion.tar.gz ec2-user@<ec2-ip>:~/

# 3. Deploy on EC2
ssh ec2-user@<ec2-ip>
tar -xzf solution_ingestion.tar.gz
cd solution_ingestion
pip3 install -r requirements.txt
export PYTHONPATH="./layers/database-core-layer/python:./layers/knowledge-graph-layer/python:$PYTHONPATH"

# 4. Execute
python3 main.py --csv-path input_data/solutions.csv --output-dir output_data/
```

## Code Safety Measures

### Layer Code Protection
- **Clean Copy Strategy**: Copy layer directories without modifications
- **Import Only**: Use existing utilities via Python imports
- **No Modifications**: Never alter production layer code
- **Version Control**: Keep layer copies in separate directory structure

### Lambda Logic Duplication
- **Isolated Implementation**: Duplicate indexing logic in separate modules
- **No Lambda Dependencies**: Remove async/SNS messaging patterns
- **Synchronous Processing**: Convert to direct function calls
- **Interface Preservation**: Maintain core processing logic patterns

## Execution Approach

### Processing Pipeline
1. **Parse CSV**: Load and validate solution data
2. **Generate Content**: Create pseudo-documents and chunks
3. **Process Metadata**: Store in PostgreSQL via DatabaseManager
4. **Index Keywords**: Store pseudo-documents in documents_keyword
5. **Generate Embeddings**: Create vectors via Bedrock Titan
6. **Index Vectors**: Store chunks in chunks_vector
7. **Generate Triples**: Create RDF using KG utilities
8. **Load Knowledge Graph**: Store triples in Neptune
9. **Output Data Lake**: Write files for development/debug

### Error Handling
- **Batch Processing**: Process solutions individually with error isolation
- **Rollback Capability**: Track processing state for partial recovery
- **Logging**: Comprehensive logging for debugging and monitoring
- **Validation**: Input validation and data quality checks

### Performance Considerations
- **Batch Size**: Process solutions in configurable batches
- **Rate Limiting**: Respect Bedrock/OpenSearch rate limits
- **Connection Pooling**: Reuse database/service connections
- **Memory Management**: Stream processing for large CSV files

## Testing Strategy

### Unit Testing
- **Parser Testing**: Validate CSV parsing with sample data
- **Generator Testing**: Verify pseudo-document and chunk generation
- **Indexer Testing**: Mock OpenSearch operations
- **Processor Testing**: Mock database and Neptune operations

### Integration Testing
- **End-to-End**: Process sample solutions through complete pipeline
- **Data Validation**: Verify output format matches existing patterns
- **Service Integration**: Test connections to PostgreSQL/OpenSearch/Neptune

### Deployment Testing
- **EC2 Environment**: Validate deployment and execution on target environment
- **Layer Integration**: Verify clean layer code imports work correctly
- **Configuration**: Test environment variable and credential setup

## Risk Mitigation

### Technical Risks
- **Layer Dependencies**: Clean copy strategy prevents production code contamination
- **Service Limits**: Rate limiting and batch processing prevent service overload
- **Data Quality**: Input validation and error handling ensure data integrity
- **Environment Issues**: Comprehensive configuration and deployment documentation

### Operational Risks
- **Deadline Pressure**: Modular design enables parallel development
- **Integration Complexity**: Reuse of existing utilities reduces implementation risk
- **Testing Coverage**: Comprehensive testing strategy ensures reliability
- **Rollback Plan**: Isolated processing enables easy rollback of failed operations

## Success Criteria

### Functional Requirements
- ✅ Process 325 solutions from CSV format
- ✅ Generate pseudo-documents with introduction paragraphs
- ✅ Create 3 chunks per solution for vector search
- ✅ Store metadata in PostgreSQL with content_type="solution"
- ✅ Index content in OpenSearch with proper content_type filtering
- ✅ Generate and store RDF triples in Neptune knowledge graph
- ✅ Output data lake files for development/debugging

### Quality Requirements
- ✅ No modifications to production layer code
- ✅ Consistent data formats with existing pipeline
- ✅ Comprehensive error handling and logging
- ✅ Successful deployment and execution on EC2
- ✅ Integration with existing search and API infrastructure

### Delivery Requirements
- ✅ Complete implementation by November 15, 2025
- ✅ Documentation for deployment and operation
- ✅ Testing validation of all components
- ✅ Ready for integration with API v2.0 hierarchical responses

## Next Steps

1. **Create Directory Structure**: Set up project layout and copy layer code
2. **Implement Core Models**: Solution data class and configuration
3. **Build CSV Parser**: Handle 20-column CSV format with validation
4. **Develop Generators**: Pseudo-document, chunk, and triple generation
5. **Implement Indexers**: Duplicate Lambda logic for OpenSearch operations
6. **Build Processors**: Database and Neptune integration using existing layers
7. **Create CLI Interface**: Main application with argument parsing
8. **Deploy and Test**: EC2 deployment with end-to-end validation
9. **Integration**: Connect with API v2.0 for hierarchical responses

---
**Document Status**: Ready for Implementation  
**Next Review**: Upon completion of directory structure and core models
