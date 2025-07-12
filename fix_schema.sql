-- Fix Database Schema: Add missing chunks_count column
-- Check if table exists and add column if missing

DO $$
BEGIN
    -- Check if table exists
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'text_chunking_status') THEN
        -- Check if chunks_count column exists
        IF NOT EXISTS (SELECT FROM information_schema.columns 
                      WHERE table_name = 'text_chunking_status' 
                      AND column_name = 'chunks_count') THEN
            -- Add the missing column
            ALTER TABLE text_chunking_status ADD COLUMN chunks_count INTEGER DEFAULT 0;
            RAISE NOTICE 'Added chunks_count column to text_chunking_status table';
        ELSE
            RAISE NOTICE 'chunks_count column already exists';
        END IF;
    ELSE
        -- Create the table if it doesn't exist
        CREATE TABLE text_chunking_status (
            doc_id VARCHAR(255) PRIMARY KEY,
            status VARCHAR(50) NOT NULL,
            chunks_count INTEGER DEFAULT 0,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        RAISE NOTICE 'Created text_chunking_status table with chunks_count column';
    END IF;
END
$$;
