-- TextExtractor PostgreSQL Schema
-- Tables for tracking async Textract jobs and document processing status

-- Table for tracking individual Textract jobs
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

-- Indexes for textract_jobs
CREATE INDEX IF NOT EXISTS idx_textract_jobs_doc_hash ON textract_jobs(doc_hash);
CREATE INDEX IF NOT EXISTS idx_textract_jobs_status ON textract_jobs(status);
CREATE INDEX IF NOT EXISTS idx_textract_jobs_started_at ON textract_jobs(started_at);
CREATE INDEX IF NOT EXISTS idx_textract_jobs_completed_at ON textract_jobs(completed_at);

-- Table for tracking overall document processing pipeline status
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

-- Indexes for document_processing_status
CREATE INDEX IF NOT EXISTS idx_doc_processing_text_status ON document_processing_status(text_extraction_status);
CREATE INDEX IF NOT EXISTS idx_doc_processing_chunking_status ON document_processing_status(chunking_status);
CREATE INDEX IF NOT EXISTS idx_doc_processing_embedding_status ON document_processing_status(embedding_status);
CREATE INDEX IF NOT EXISTS idx_doc_processing_ner_status ON document_processing_status(ner_status);
CREATE INDEX IF NOT EXISTS idx_doc_processing_created_at ON document_processing_status(created_at);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers to automatically update updated_at
CREATE TRIGGER update_textract_jobs_updated_at 
    BEFORE UPDATE ON textract_jobs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_document_processing_status_updated_at 
    BEFORE UPDATE ON document_processing_status 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- View for monitoring processing pipeline
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

-- View for Textract job statistics
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

-- Sample queries for monitoring

-- Check processing pipeline status
-- SELECT * FROM processing_pipeline_status WHERE text_extraction_status = 'IN_PROGRESS';

-- Check failed jobs
-- SELECT * FROM textract_jobs WHERE status = 'FAILED' ORDER BY started_at DESC;

-- Get processing statistics
-- SELECT * FROM textract_job_stats;

-- Find documents stuck in processing
-- SELECT doc_hash, filename, text_extraction_status, 
--        EXTRACT(EPOCH FROM (NOW() - updated_at))/3600 as hours_since_update
-- FROM document_processing_status 
-- WHERE text_extraction_status = 'IN_PROGRESS' 
--   AND updated_at < NOW() - INTERVAL '1 hour'
-- ORDER BY updated_at;

-- Clean up old completed jobs (run periodically)
-- DELETE FROM textract_jobs 
-- WHERE status IN ('SUCCEEDED', 'FAILED') 
--   AND completed_at < NOW() - INTERVAL '30 days';

COMMENT ON TABLE textract_jobs IS 'Tracks individual async Textract job execution and results';
COMMENT ON TABLE document_processing_status IS 'Tracks overall document processing pipeline status across all stages';
COMMENT ON VIEW processing_pipeline_status IS 'Combined view of document processing status with Textract job details';
COMMENT ON VIEW textract_job_stats IS 'Statistical summary of Textract job performance by status';
