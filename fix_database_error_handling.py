#!/usr/bin/env python3
"""
Add Graceful Database Error Handling to Text Chunker
"""

import os
import shutil
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_database_error_handling():
    """Add graceful error handling for database schema issues"""
    
    text_chunker_file = "/Users/chris/climate-risk-rag-aws/lambda/text_chunker/text_chunker_processor_updated.py"
    
    try:
        # Read current file
        with open(text_chunker_file, 'r') as f:
            content = f.read()
        
        # Replace the update_processing_status method with better error handling
        old_method = '''    def update_processing_status(self, doc_id: str, status: str, chunks_count: int, message: str):
        """Update processing status in database"""
        
        if not self.db_manager:
            return
        
        try:
            conn = self.db_manager.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO text_chunking_status (doc_id, status, chunks_count, message, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (doc_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        chunks_count = EXCLUDED.chunks_count,
                        message = EXCLUDED.message,
                        updated_at = EXCLUDED.updated_at
                """, (doc_id, status, chunks_count, message, datetime.utcnow()))
                
                conn.commit()
                logger.info(f"Updated chunking status: {doc_id} -> {status}")
                
        except Exception as e:
            logger.error(f"Error updating processing status: {e}")
            # Don't raise - allow processing to continue even if status update fails'''
        
        new_method = '''    def update_processing_status(self, doc_id: str, status: str, chunks_count: int, message: str):
        """Update processing status in database with graceful error handling"""
        
        if not self.db_manager:
            logger.warning("Database manager not available, skipping status update")
            return
        
        try:
            conn = self.db_manager.get_connection()
            with conn.cursor() as cursor:
                # First try with chunks_count column
                try:
                    cursor.execute("""
                        INSERT INTO text_chunking_status (doc_id, status, chunks_count, message, updated_at)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (doc_id) DO UPDATE SET
                            status = EXCLUDED.status,
                            chunks_count = EXCLUDED.chunks_count,
                            message = EXCLUDED.message,
                            updated_at = EXCLUDED.updated_at
                    """, (doc_id, status, chunks_count, message, datetime.utcnow()))
                    
                except Exception as schema_error:
                    if "chunks_count" in str(schema_error):
                        logger.warning("chunks_count column missing, trying without it...")
                        # Try without chunks_count column
                        cursor.execute("""
                            INSERT INTO text_chunking_status (doc_id, status, message, updated_at)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (doc_id) DO UPDATE SET
                                status = EXCLUDED.status,
                                message = EXCLUDED.message,
                                updated_at = EXCLUDED.updated_at
                        """, (doc_id, status, message, datetime.utcnow()))
                    else:
                        raise schema_error
                
                conn.commit()
                logger.info(f"Updated chunking status: {doc_id} -> {status}")
                
        except Exception as e:
            logger.error(f"Error updating processing status: {e}")
            # Don't raise - allow processing to continue even if status update fails'''
        
        content = content.replace(old_method, new_method)
        
        # Write fixed content
        with open(text_chunker_file, 'w') as f:
            f.write(content)
        
        logger.info("✅ Database error handling fixes applied successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to fix database error handling: {e}")
        raise

if __name__ == "__main__":
    fix_database_error_handling()
