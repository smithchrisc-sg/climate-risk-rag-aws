#!/usr/bin/env python3
"""
Fix Column Name Mismatch in Text Chunker
Change chunks_count back to chunks_created to match database schema
"""

import os
import shutil
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_column_name_mismatch():
    """Fix the column name mismatch between code and database"""
    
    text_chunker_file = "/Users/chris/climate-risk-rag-aws/lambda/text_chunker/text_chunker_processor_updated.py"
    
    try:
        # Read current file
        with open(text_chunker_file, 'r') as f:
            content = f.read()
        
        # Fix 1: Change chunks_count to chunks_created in SQL
        content = content.replace(
            "INSERT INTO text_chunking_status (doc_id, status, chunks_count, message, updated_at)",
            "INSERT INTO text_chunking_status (doc_id, status, chunks_created, message, updated_at)"
        )
        
        content = content.replace(
            "chunks_count = EXCLUDED.chunks_count,",
            "chunks_created = EXCLUDED.chunks_created,"
        )
        
        # Fix 2: Change parameter name in function signature
        content = content.replace(
            "def update_processing_status(self, doc_id: str, status: str, chunks_count: int, message: str):",
            "def update_processing_status(self, doc_id: str, status: str, chunks_created: int, message: str):"
        )
        
        # Fix 3: Update the fallback error handling to use correct column name
        content = content.replace(
            'if "chunks_count" in str(schema_error):',
            'if "chunks_created" in str(schema_error):'
        )
        
        content = content.replace(
            'logger.warning("chunks_count column missing, trying without it...")',
            'logger.warning("chunks_created column missing, trying without it...")'
        )
        
        # Fix 4: Update function calls to use correct parameter name
        content = content.replace(
            "self.update_processing_status(doc_id, 'PROCESSING', 0, 'Starting text chunking')",
            "self.update_processing_status(doc_id, 'PROCESSING', 0, 'Starting text chunking')"
        )
        
        content = content.replace(
            "self.update_processing_status(doc_id, 'SUCCESS', len(chunks), 'Text chunking completed successfully')",
            "self.update_processing_status(doc_id, 'SUCCESS', len(chunks), 'Text chunking completed successfully')"
        )
        
        content = content.replace(
            "self.update_processing_status(doc_id, 'FAILED', 0, str(e))",
            "self.update_processing_status(doc_id, 'FAILED', 0, str(e))"
        )
        
        # Write fixed content
        with open(text_chunker_file, 'w') as f:
            f.write(content)
        
        logger.info("✅ Column name mismatch fixes applied successfully")
        logger.info("✅ Changed chunks_count to chunks_created to match database schema")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to fix column name mismatch: {e}")
        raise

if __name__ == "__main__":
    fix_column_name_mismatch()
