-- Migration Script: Transition to Audit-First 2-Table Schema
-- Date: July 20, 2025
-- Purpose: Replace complex multi-column schema with simplified audit-first design

-- =====================================================
-- BACKUP EXISTING DATA (RECOMMENDED TO RUN FIRST)
-- =====================================================

-- Create backup tables before migration
CREATE TABLE documents_backup AS SELECT * FROM documents;
-- Add other backup tables as needed for existing data

-- =====================================================
-- DROP EXISTING TABLES (IF THEY EXIST)
-- =====================================================

-- Drop existing tables to start clean
-- WARNING: This will delete all existing data
-- Make sure backups are created first

DROP TABLE IF EXISTS document_processing_status CASCADE;
DROP TABLE IF EXISTS documents CASCADE;

-- Drop any other existing tables that conflict with new schema
-- Add DROP statements here for any legacy tables

-- =====================================================
-- CREATE NEW SCHEMA - DOCUMENTS TABLE
-- =====================================================

CREATE TABLE documents (
    doc_id VARCHAR(32) PRIMARY KEY,
    source_url TEXT NOT NULL,
    original_filename TEXT,
    file_size_bytes BIGINT,
    file_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for documents table
CREATE INDEX idx_documents_source_url ON documents(source_url);
CREATE INDEX idx_documents_created_at ON documents(created_at);
CREATE INDEX idx_documents_file_hash ON documents(file_hash);

-- =====================================================
-- CREATE NEW SCHEMA - DOCUMENT PROCESSING STATUS TABLE
-- =====================================================

CREATE TABLE document_processing_status (
    id SERIAL PRIMARY KEY,
    doc_id VARCHAR(32) REFERENCES documents(doc_id) ON DELETE CASCADE,
    stage VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    system_id VARCHAR(100),
    retry_count INTEGER DEFAULT 0,
    metadata JSONB,
    
    -- Constraints for data integrity
    CONSTRAINT valid_status CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'skipped')),
    CONSTRAINT valid_stage CHECK (stage IN (
        'download',              -- Document downloaded from source URL
        'textract_initiate',     -- Textract job submitted
        'textract_complete',     -- Text extraction completed
        'keyword_index_initiate', -- Keyword indexing job initiated
        'keyword_index_complete', -- Keyword indexing completed
        'chunking',              -- Document split into chunks
        'vector_embedding',      -- Vector embeddings generated
        'vector_indexing',       -- Vector embeddings indexed in OpenSearch
        'nlp_initiate',          -- NLP Processing via comprehend initiated
        'nlp_complete',          -- NLP Processing via comprehend processed to datalake
        'kg_doc_structure',      -- Document Structure semantics added to Knowledge Graph
        'kg_entities',           -- Entities, etc. added to Knowledge Graph
        'validation'             -- Quality checks completed
    ))
);

-- Indexes for document_processing_status table
CREATE INDEX idx_processing_doc_stage_time ON document_processing_status(doc_id, stage, timestamp);
CREATE INDEX idx_processing_stage_status_time ON document_processing_status(stage, status, timestamp);
CREATE INDEX idx_processing_timestamp ON document_processing_status(timestamp);
CREATE INDEX idx_processing_system_id ON document_processing_status(system_id);
CREATE INDEX idx_processing_status_pending ON document_processing_status(status, timestamp) 
    WHERE status IN ('pending', 'in_progress');

-- =====================================================
-- GRANT PERMISSIONS
-- =====================================================

-- Grant permissions to application user (adjust username as needed)
-- GRANT ALL PRIVILEGES ON documents TO your_app_user;
-- GRANT ALL PRIVILEGES ON document_processing_status TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE document_processing_status_id_seq TO your_app_user;

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================

-- Verify tables were created correctly
SELECT table_name, column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name IN ('documents', 'document_processing_status')
ORDER BY table_name, ordinal_position;

-- Verify indexes were created
SELECT indexname, tablename, indexdef 
FROM pg_indexes 
WHERE tablename IN ('documents', 'document_processing_status')
ORDER BY tablename, indexname;

-- Verify constraints
SELECT conname, contype, pg_get_constraintdef(oid) as definition
FROM pg_constraint 
WHERE conrelid IN (
    SELECT oid FROM pg_class WHERE relname IN ('documents', 'document_processing_status')
);

-- =====================================================
-- SAMPLE DATA INSERTION (FOR TESTING)
-- =====================================================

-- Insert sample document
INSERT INTO documents (doc_id, source_url, original_filename, file_size_bytes, file_hash) 
VALUES (
    'a1b2c3d4e5f6g7h8i9j0', 
    'https://example.com/test-document.pdf', 
    'test-document.pdf', 
    1024000, 
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
);

-- Insert sample processing status
INSERT INTO document_processing_status (doc_id, stage, status, system_id) 
VALUES ('a1b2c3d4e5f6g7h8i9j0', 'download', 'completed', NULL);

INSERT INTO document_processing_status (doc_id, stage, status, system_id) 
VALUES ('a1b2c3d4e5f6g7h8i9j0', 'textract_initiate', 'in_progress', 'textract-job-12345');

-- Verify sample data
SELECT * FROM documents;
SELECT * FROM document_processing_status ORDER BY timestamp;

-- =====================================================
-- MIGRATION COMPLETE
-- =====================================================

-- Schema migration completed successfully
-- New audit-first 2-table design is now active
-- All processing status changes will create new rows (insert-only)
-- Document updates will use file hash comparison logic
