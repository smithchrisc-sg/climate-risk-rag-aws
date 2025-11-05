-- SQL queries to check solution documents in the database

-- 1. Check if any solution documents exist
SELECT COUNT(*) as solution_count 
FROM documents 
WHERE content_type = 'solution';

-- 2. List all solution documents with basic info
SELECT doc_id, title, source_url, created_at, updated_at
FROM documents 
WHERE content_type = 'solution'
ORDER BY created_at DESC
LIMIT 20;

-- 3. Check for documents with solution-like IDs (sol_ prefix)
SELECT doc_id, title, source_url, content_type, created_at
FROM documents 
WHERE doc_id LIKE 'sol_%'
ORDER BY created_at DESC;

-- 4. Check for any documents that might be from our CSV files
SELECT doc_id, title, source_url, content_type, created_at
FROM documents 
WHERE source_url LIKE '%health_original%' 
   OR source_url LIKE '%mortality_original%'
   OR source_url LIKE '%natural_catastrophe%'
   OR source_url LIKE '%cyber_original%'
   OR source_url LIKE '%retirement_original%'
ORDER BY created_at DESC;

-- 5. Get total document count and breakdown by content_type
SELECT 
    content_type,
    COUNT(*) as count,
    MIN(created_at) as first_created,
    MAX(created_at) as last_created
FROM documents 
GROUP BY content_type
ORDER BY count DESC;

-- 6. Check for any documents created today
SELECT doc_id, title, source_url, content_type, created_at
FROM documents 
WHERE DATE(created_at) = CURRENT_DATE
ORDER BY created_at DESC;

-- 7. Look for documents with specific patterns in source_url
SELECT doc_id, title, source_url, content_type, created_at
FROM documents 
WHERE source_url LIKE 'solution://%'
ORDER BY created_at DESC
LIMIT 10;
