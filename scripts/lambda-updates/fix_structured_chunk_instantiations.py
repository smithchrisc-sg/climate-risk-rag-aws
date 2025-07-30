#!/usr/bin/env python3
"""
Fix StructuredChunk Instantiations
Add missing required fields to all StructuredChunk instantiations
"""

import os
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_structured_chunk_instantiations():
    """Fix all StructuredChunk instantiations to include required fields"""
    
    chunking_file = "/Users/chris/climate-risk-rag-aws/lambda/shared_layer/python/structured_chunking_smart_complete.py"
    
    try:
        # Read current file
        with open(chunking_file, 'r') as f:
            content = f.read()
        
        # Pattern to find StructuredChunk instantiations
        pattern = r'StructuredChunk\(\s*([^)]+)\s*\)'
        
        def fix_instantiation(match):
            args_str = match.group(1)
            
            # Check if required fields are missing and add them
            required_fields = {
                'page_number': '1',
                'section_context': '""',
                'word_count': 'len(chunk_text.strip().split()) if "chunk_text" in locals() else len(text.split())',
                'sentence_count': 'chunk_text.count(".") + chunk_text.count("!") + chunk_text.count("?") if "chunk_text" in locals() else text.count(".") + text.count("!") + text.count("?")'
            }
            
            # Add missing fields
            for field, default_value in required_fields.items():
                if field not in args_str:
                    args_str += f',\n                    {field}={default_value}'
            
            return f'StructuredChunk(\n                    {args_str}\n                )'
        
        # Apply the fix to all StructuredChunk instantiations
        fixed_content = re.sub(pattern, fix_instantiation, content, flags=re.DOTALL)
        
        # Also fix specific known problematic instantiations more directly
        # Fix the fallback chunking instantiation
        old_instantiation = """StructuredChunk(
                    text=chunk_text.strip(),
                    chunk_type="text",
                    hierarchy_level=3,
                    start_char=i,
                    end_char=min(i + chunk_size, len(text)),
                    bounding_box={},
                    metadata={
                        'chunking_method': 'fallback_text',
                        'chunk_size': len(chunk_text),
                        'overlap_used': overlap if i > 0 else 0
                    }
                )"""
        
        new_instantiation = """StructuredChunk(
                    text=chunk_text.strip(),
                    chunk_type="text",
                    hierarchy_level=3,
                    page_number=1,
                    section_context="",
                    word_count=len(chunk_text.strip().split()),
                    sentence_count=chunk_text.count('.') + chunk_text.count('!') + chunk_text.count('?'),
                    bounding_box={},
                    metadata={
                        'chunking_method': 'fallback_text',
                        'chunk_size': len(chunk_text),
                        'overlap_used': overlap if i > 0 else 0
                    },
                    start_char=i,
                    end_char=min(i + chunk_size, len(text))
                )"""
        
        if old_instantiation in fixed_content:
            fixed_content = fixed_content.replace(old_instantiation, new_instantiation)
            logger.info("✅ Fixed fallback chunking instantiation")
        
        # Write fixed content
        with open(chunking_file, 'w') as f:
            f.write(fixed_content)
        
        logger.info("✅ StructuredChunk instantiation fixes applied successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to fix StructuredChunk instantiations: {e}")
        raise

if __name__ == "__main__":
    fix_structured_chunk_instantiations()
