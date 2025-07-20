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
    structural_metadata JSONB,
    processing_info JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (doc_id) REFERENCES documents (doc_id) ON DELETE CASCADE
);

-- System IDs table for external system references
CREATE TABLE IF NOT EXISTS system_ids (
    doc_id VARCHAR(255) NOT NULL,
    system_name VARCHAR(100) NOT NULL,
    system_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (doc_id, system_name),
    FOREIGN KEY (doc_id) REFERENCES documents (doc_id) ON DELETE CASCADE
);

-- Textract jobs table for tracking async job execution
CREATE TABLE IF NOT EXISTS textract_jobs (
    job_id VARCHAR(255) PRIMARY KEY,
    doc_id VARCHAR(255) NOT NULL,
    source_bucket VARCHAR(255) NOT NULL,
    source_key VARCHAR(1024) NOT NULL,
    output_bucket VARCHAR(255),
    status VARCHAR(50) DEFAULT 'IN_PROGRESS',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    pages_processed INTEGER,
    blocks_extracted INTEGER,
    files_created JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (doc_id) REFERENCES documents (doc_id) ON DELETE CASCADE
);

-- Document processing status table for pipeline tracking
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

-- Keyword indexing status table for tracking keyword extraction and OpenSearch indexing
CREATE TABLE IF NOT EXISTS keyword_indexing_status (
    doc_id VARCHAR(255) PRIMARY KEY,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    notes TEXT,
    opensearch_index_name VARCHAR(255),
    keywords_extracted INTEGER DEFAULT 0,
    processing_started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (doc_id) REFERENCES documents (doc_id) ON DELETE CASCADE
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
    COUNT(c.chunk_id) as total_chunks,
    COUNT(CASE WHEN c.has_chunk THEN 1 END) as chunks_with_content,
    COUNT(CASE WHEN c.has_embedding THEN 1 END) as chunks_with_embeddings
FROM documents d
LEFT JOIN document_metadata m ON d.doc_id = m.doc_id
LEFT JOIN chunks c ON d.doc_id = c.doc_id
GROUP BY d.doc_id, m.doc_id, m.title, m.title_confidence, m.title_source, 
         m.author, m.author_confidence, m.language, m.language_confidence,
         m.creation_date, m.creation_date_confidence, m.modification_date,
         m.modification_date_confidence, m.processing_date, m.structural_metadata, m.processing_info;

-- Processing pipeline status view
DROP VIEW IF EXISTS processing_pipeline_status;
CREATE VIEW processing_pipeline_status AS
SELECT 
    dps.*,
    tj.started_at as textract_started_at,
    tj.completed_at as textract_completed_at,
    tj.pages_processed,
    tj.blocks_extracted,
    tj.files_created as textract_files_created,
    kis.status as keyword_indexing_status,
    kis.keywords_extracted,
    kis.opensearch_index_name,
    kis.processing_started_at as keyword_indexing_started_at,
    kis.processing_completed_at as keyword_indexing_completed_at
FROM document_processing_status dps
LEFT JOIN textract_jobs tj ON dps.text_extraction_job_id = tj.job_id
LEFT JOIN keyword_indexing_status kis ON dps.doc_hash = kis.doc_id;

-- Textract job statistics view
DROP VIEW IF EXISTS textract_job_stats;
CREATE VIEW textract_job_stats AS
SELECT 
    status,
    COUNT(*) as job_count,
    AVG(pages_processed) as avg_pages_processed,
    AVG(blocks_extracted) as avg_blocks_extracted,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))/60) as avg_processing_time_minutes
FROM textract_jobs 
WHERE started_at IS NOT NULL
GROUP BY status;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents (status);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents (created_at);
CREATE INDEX IF NOT EXISTS idx_documents_updated_at ON documents (updated_at);

CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks (doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_has_chunk ON chunks (has_chunk);
CREATE INDEX IF NOT EXISTS idx_chunks_has_embedding ON chunks (has_embedding);

CREATE INDEX IF NOT EXISTS idx_document_metadata_doc_id ON document_metadata (doc_id);
CREATE INDEX IF NOT EXISTS idx_document_metadata_language ON document_metadata (language);
CREATE INDEX IF NOT EXISTS idx_document_metadata_processing_date ON document_metadata (processing_date);

CREATE INDEX IF NOT EXISTS idx_system_ids_doc_id ON system_ids (doc_id);
CREATE INDEX IF NOT EXISTS idx_system_ids_system_name ON system_ids (system_name);

CREATE INDEX IF NOT EXISTS idx_textract_jobs_doc_id ON textract_jobs (doc_id);
CREATE INDEX IF NOT EXISTS idx_textract_jobs_status ON textract_jobs (status);
CREATE INDEX IF NOT EXISTS idx_textract_jobs_started_at ON textract_jobs (started_at);
CREATE INDEX IF NOT EXISTS idx_textract_jobs_completed_at ON textract_jobs (completed_at);

CREATE INDEX IF NOT EXISTS idx_document_processing_status_text_extraction_status ON document_processing_status (text_extraction_status);
CREATE INDEX IF NOT EXISTS idx_document_processing_status_chunking_status ON document_processing_status (chunking_status);
CREATE INDEX IF NOT EXISTS idx_document_processing_status_embedding_status ON document_processing_status (embedding_status);
CREATE INDEX IF NOT EXISTS idx_document_processing_status_ner_status ON document_processing_status (ner_status);

-- Indexes for keyword indexing status table
CREATE INDEX IF NOT EXISTS idx_keyword_indexing_status_status ON keyword_indexing_status (status);
CREATE INDEX IF NOT EXISTS idx_keyword_indexing_status_updated_at ON keyword_indexing_status (updated_at);
CREATE INDEX IF NOT EXISTS idx_keyword_indexing_status_processing_started_at ON keyword_indexing_status (processing_started_at);
CREATE INDEX IF NOT EXISTS idx_keyword_indexing_status_opensearch_index ON keyword_indexing_status (opensearch_index_name);

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

CREATE TRIGGER update_textract_jobs_updated_at 
    BEFORE UPDATE ON textract_jobs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_document_processing_status_updated_at 
    BEFORE UPDATE ON document_processing_status 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger for keyword indexing status table
CREATE TRIGGER update_keyword_indexing_status_updated_at 
    BEFORE UPDATE ON keyword_indexing_status 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE documents IS 'Main documents table with basic document information';
COMMENT ON TABLE chunks IS 'Document chunks with processing status';
COMMENT ON TABLE document_metadata IS 'Enhanced metadata for documents with confidence scores';
COMMENT ON TABLE system_ids IS 'External system identifiers for documents';
COMMENT ON TABLE textract_jobs IS 'Tracks individual async Textract job execution and results';
COMMENT ON TABLE document_processing_status IS 'Tracks overall document processing pipeline status across all stages';
COMMENT ON TABLE keyword_indexing_status IS 'Tracks keyword extraction and OpenSearch indexing status for documents';
COMMENT ON VIEW document_metadata_view IS 'Combined view of documents with metadata and chunk statistics';
COMMENT ON VIEW processing_pipeline_status IS 'Combined view of document processing status with Textract job details and keyword indexing status';
COMMENT ON VIEW textract_job_stats IS 'Statistical summary of Textract job performance by status';
