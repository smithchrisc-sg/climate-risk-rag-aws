-- PostgreSQL Schema for Climate Risk RAG System
-- Converted from SQLite schema with PostgreSQL optimizations

-- Enable UUID extension for better ID generation if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Base documents table
CREATE TABLE IF NOT EXISTS documents (
    doc_id VARCHAR(255) PRIMARY KEY,
    url TEXT UNIQUE,
    qdrant_id TEXT,
    opensearch_id TEXT,
    kg_id TEXT,
    original_filename TEXT,
    pdf_path TEXT,
    text_path TEXT,
    chunking_complete BOOLEAN DEFAULT FALSE,
    download_date TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chunks table
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id VARCHAR(255) PRIMARY KEY,
    doc_id VARCHAR(255) NOT NULL,
    chunk_index INTEGER,
    has_chunk BOOLEAN DEFAULT FALSE,
    has_embedding BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (doc_id) REFERENCES documents (doc_id) ON DELETE CASCADE
);

-- Enhanced metadata table
CREATE TABLE IF NOT EXISTS document_metadata (
    doc_id VARCHAR(255) PRIMARY KEY,
    title TEXT,
    title_confidence DECIMAL(5,4),
    title_source VARCHAR(100),
    author TEXT,
    author_confidence DECIMAL(5,4),
    author_source VARCHAR(100),
    language VARCHAR(10),
    language_confidence DECIMAL(5,4),
    creation_date TIMESTAMP WITH TIME ZONE,
    creation_date_confidence DECIMAL(5,4),
    modification_date TIMESTAMP WITH TIME ZONE,
    modification_date_confidence DECIMAL(5,4),
    processing_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    structural_metadata JSONB,  -- JSON field for structural metadata
    processing_info JSONB,      -- JSON field for processing info
    raw_metadata JSONB,         -- JSON field for raw metadata
    metadata_quality DECIMAL(5,4),
    metadata_source VARCHAR(100),
    indexing_info JSONB,        -- JSON field for indexing metadata
    last_indexed TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);

-- System IDs table for tracking external system identifiers
CREATE TABLE IF NOT EXISTS system_ids (
    doc_id VARCHAR(255) NOT NULL,
    system_name VARCHAR(100) NOT NULL,
    system_id TEXT NOT NULL,
    last_indexed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    indexing_status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (doc_id, system_name),
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);

-- TextExtractor job tracking tables (from TextExtractor async architecture)
CREATE TABLE IF NOT EXISTS textract_jobs (
    job_id VARCHAR(255) PRIMARY KEY,
    doc_hash VARCHAR(64) NOT NULL,
    source_bucket VARCHAR(255) NOT NULL,
    source_key VARCHAR(1024) NOT NULL,
    output_bucket VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'IN_PROGRESS',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    pages_processed INTEGER,
    blocks_extracted INTEGER,
    files_created JSONB,
    textract_model_version VARCHAR(50),
    feature_types JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document processing pipeline status tracking
CREATE TABLE IF NOT EXISTS document_processing_status (
    doc_hash VARCHAR(64) PRIMARY KEY,
    filename VARCHAR(1024) NOT NULL,
    source_bucket VARCHAR(255) NOT NULL,
    source_key VARCHAR(1024) NOT NULL,
    
    -- Text extraction status
    text_extraction_status VARCHAR(50) DEFAULT 'PENDING',
    text_extraction_job_id VARCHAR(255),
    text_extraction_completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Downstream processing status
    chunking_status VARCHAR(50) DEFAULT 'PENDING',
    chunking_completed_at TIMESTAMP WITH TIME ZONE,
    
    embedding_status VARCHAR(50) DEFAULT 'PENDING',
    embedding_completed_at TIMESTAMP WITH TIME ZONE,
    
    ner_status VARCHAR(50) DEFAULT 'PENDING',
    ner_completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Foreign key constraint
    CONSTRAINT fk_text_extraction_job 
        FOREIGN KEY (text_extraction_job_id) 
        REFERENCES textract_jobs(job_id)
        ON DELETE SET NULL
);

-- Create comprehensive view combining documents, metadata, and chunk info
DROP VIEW IF EXISTS document_metadata_view;
CREATE VIEW document_metadata_view AS
SELECT 
    d.*,
    m.title,
    m.title_confidence,
    m.title_source,
    m.author,
    m.author_confidence,
    m.language,
    m.language_confidence,
    m.creation_date,
    m.creation_date_confidence,
    m.modification_date,
    m.modification_date_confidence,
    m.processing_date,
    m.structural_metadata,
    m.processing_info,
    m.metadata_quality,
    m.metadata_source,
    m.indexing_info,
    m.last_indexed,
    COUNT(c.chunk_id) as chunk_count,
    SUM(CASE WHEN c.has_embedding THEN 1 ELSE 0 END) as embedding_count
FROM documents d
LEFT JOIN document_metadata m ON d.doc_id = m.doc_id
LEFT JOIN chunks c ON d.doc_id = c.doc_id
GROUP BY d.doc_id, m.doc_id;

-- Processing pipeline status view
CREATE OR REPLACE VIEW processing_pipeline_status AS
SELECT 
    dps.doc_hash,
    dps.filename,
    dps.source_bucket,
    dps.source_key,
    dps.text_extraction_status,
    tj.job_id as textract_job_id,
    tj.started_at as textract_started_at,
    tj.completed_at as textract_completed_at,
    tj.pages_processed,
    tj.blocks_extracted,
    tj.error_message as textract_error,
    dps.chunking_status,
    dps.embedding_status,
    dps.ner_status,
    dps.created_at,
    dps.updated_at
FROM document_processing_status dps
LEFT JOIN textract_jobs tj ON dps.text_extraction_job_id = tj.job_id
ORDER BY dps.created_at DESC;

-- Textract job statistics view
CREATE OR REPLACE VIEW textract_job_stats AS
SELECT 
    status,
    COUNT(*) as job_count,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_processing_time_seconds,
    AVG(pages_processed) as avg_pages_processed,
    AVG(blocks_extracted) as avg_blocks_extracted,
    MIN(started_at) as earliest_job,
    MAX(completed_at) as latest_completion
FROM textract_jobs 
WHERE started_at IS NOT NULL
GROUP BY status
ORDER BY job_count DESC;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_url ON documents(url);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_updated_at ON documents(updated_at);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_has_embedding ON chunks(has_embedding);
CREATE INDEX IF NOT EXISTS idx_metadata_quality ON document_metadata(metadata_quality);
CREATE INDEX IF NOT EXISTS idx_metadata_updated_at ON document_metadata(updated_at);
CREATE INDEX IF NOT EXISTS idx_system_ids_lookup ON system_ids(system_name, system_id);
CREATE INDEX IF NOT EXISTS idx_system_ids_status ON system_ids(indexing_status, system_name);
CREATE INDEX IF NOT EXISTS idx_textract_jobs_doc_hash ON textract_jobs(doc_hash);
CREATE INDEX IF NOT EXISTS idx_textract_jobs_status ON textract_jobs(status);
CREATE INDEX IF NOT EXISTS idx_textract_jobs_started_at ON textract_jobs(started_at);
CREATE INDEX IF NOT EXISTS idx_doc_processing_text_status ON document_processing_status(text_extraction_status);
CREATE INDEX IF NOT EXISTS idx_doc_processing_chunking_status ON document_processing_status(chunking_status);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers to automatically update updated_at
CREATE TRIGGER update_documents_updated_at 
    BEFORE UPDATE ON documents 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chunks_updated_at 
    BEFORE UPDATE ON chunks 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_document_metadata_updated_at 
    BEFORE UPDATE ON document_metadata 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_ids_updated_at 
    BEFORE UPDATE ON system_ids 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_textract_jobs_updated_at 
    BEFORE UPDATE ON textract_jobs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_document_processing_status_updated_at 
    BEFORE UPDATE ON document_processing_status 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE documents IS 'Main documents table with basic document information';
COMMENT ON TABLE chunks IS 'Document chunks with processing status';
COMMENT ON TABLE document_metadata IS 'Enhanced metadata for documents with confidence scores';
COMMENT ON TABLE system_ids IS 'External system identifiers for documents';
COMMENT ON TABLE textract_jobs IS 'Tracks individual async Textract job execution and results';
COMMENT ON TABLE document_processing_status IS 'Tracks overall document processing pipeline status across all stages';
COMMENT ON VIEW document_metadata_view IS 'Combined view of documents with metadata and chunk statistics';
COMMENT ON VIEW processing_pipeline_status IS 'Combined view of document processing status with Textract job details';
COMMENT ON VIEW textract_job_stats IS 'Statistical summary of Textract job performance by status';
