# Climate Risk RAG Project Context

## Project Overview
The Climate Risk RAG (Retrieval-Augmented Generation) system is designed to process climate risk documents, extract meaningful information, and make it available for search and analysis. The system uses a pipeline architecture to process documents through various stages including text extraction, chunking, embedding, and indexing.

## Current Status
As of July 16, 2025, we have successfully implemented and integrated the following components:

1. **Document Processing Pipeline**:
   - Text extraction using AWS Textract
   - Smart structured chunking with sentence-based overlap
   - Keyword indexing
   - Vector embeddings (in progress)

2. **Key Improvements**:
   - Implemented SimplifiedSmartChunker for better document chunking
   - Reduced chunk count from 2,709 to 271 per document (average)
   - Increased average chunk size from 49 to 491 characters
   - Added sentence-based overlap (5 sentences per chunk with 2 sentence overlap)

3. **Infrastructure**:
   - AWS Lambda functions for each processing stage
   - S3 buckets for document storage
   - PostgreSQL database for metadata and status tracking
   - OpenSearch for vector search (in progress)
   - Neptune for knowledge graph (in progress)

## Architecture
The system follows a serverless event-driven architecture:

1. **Document Ingestion**:
   - Documents are uploaded to S3
   - S3 event triggers the document processing pipeline

2. **Processing Pipeline**:
   - Text extraction Lambda extracts text from documents
   - Text chunker Lambda splits text into semantic chunks
   - Keyword indexer Lambda extracts keywords from chunks
   - Vector embeddings Lambda creates embeddings for chunks
   - Knowledge graph Lambda builds relationships between entities

3. **Storage**:
   - S3 for raw documents, extracted text, and chunks
   - PostgreSQL for metadata and processing status
   - OpenSearch for vector search
   - Neptune for knowledge graph

## Recent Changes
1. **Smart Chunking Improvements**:
   - Implemented SimplifiedSmartChunker that respects document structure
   - Added sentence-based chunking with overlap
   - Reduced chunk count while increasing chunk quality
   - Fixed issues with tiny chunks and improved semantic coherence

2. **Pipeline Stability**:
   - Added cleanup script to ensure clean test environment
   - Fixed Lambda layer and function configuration issues
   - Improved error handling and logging

## Known Issues
1. **Vector Embeddings**:
   - VPC configuration issues with vector embeddings Lambda
   - Need to update Lambda layers for vector embeddings

2. **Knowledge Graph**:
   - Neptune integration needs testing
   - Entity extraction needs improvement

## Testing
We have implemented a testing framework that:
1. Cleans up all data before running tests
2. Selects test documents based on criteria
3. Runs the pipeline on test documents
4. Verifies the results at each stage

The `run_test_with_cleanup.py` script automates this process.
