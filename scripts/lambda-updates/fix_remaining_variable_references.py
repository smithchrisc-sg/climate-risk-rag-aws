#!/usr/bin/env python3
"""
Fix Remaining Variable References in Text Chunker
Fix any remaining chunks_count variable references
"""

import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_remaining_variable_references():
    """Fix any remaining chunks_count variable references"""
    
    text_chunker_file = "/Users/chris/climate-risk-rag-aws/lambda/text_chunker/text_chunker_processor_updated.py"
    
    try:
        # Read current file
        with open(text_chunker_file, 'r') as f:
            content = f.read()
        
        # Fix any remaining chunks_count variable references
        # Look for function calls that still use chunks_count
        content = content.replace(
            "len(chunks), 'Text chunking completed successfully')",
            "len(chunks), 'Text chunking completed successfully')"
        )
        
        # Fix any remaining variable references in the processing metadata
        content = content.replace(
            "'chunks_count': len(chunks),",
            "'chunks_created': len(chunks),"
        )
        
        # Fix any remaining references in coordination messages
        content = content.replace(
            "'chunks_count': len(chunks),",
            "'chunks_created': len(chunks),"
        )
        
        # Fix the specific error - look for chunks_count variable usage
        content = content.replace(
            "chunks_count,",
            "chunks_created,"
        )
        
        # Write fixed content
        with open(text_chunker_file, 'w') as f:
            f.write(content)
        
        logger.info("✅ Fixed remaining variable references")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to fix variable references: {e}")
        raise

if __name__ == "__main__":
    fix_remaining_variable_references()
