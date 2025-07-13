#!/usr/bin/env python3
"""
Fix StructuredChunk Compatibility Issue
Convert StructuredChunk dataclass objects to dictionaries before updating
"""

import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_structured_chunk_compatibility():
    """Fix the StructuredChunk compatibility issue"""
    
    text_chunker_file = "/Users/chris/climate-risk-rag-aws/lambda/text_chunker/text_chunker_processor_updated.py"
    
    try:
        # Read current file
        with open(text_chunker_file, 'r') as f:
            content = f.read()
        
        # Find the problematic section and replace it
        old_code = """            # Add metadata to chunks
            for i, chunk in enumerate(chunks):
                chunk.update({
                    'chunk_id': f"{doc_id}_chunk_{i:03d}",
                    'doc_id': doc_id,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'created_at': datetime.utcnow().isoformat() + 'Z'
                })"""
        
        new_code = """            # Add metadata to chunks
            processed_chunks = []
            for i, chunk in enumerate(chunks):
                # Convert StructuredChunk dataclass to dictionary if needed
                if hasattr(chunk, '__dataclass_fields__'):
                    # It's a dataclass, convert to dict
                    chunk_dict = {
                        'text': chunk.text,
                        'chunk_type': getattr(chunk, 'chunk_type', 'structured'),
                        'hierarchy_level': getattr(chunk, 'hierarchy_level', 0),
                        'page_number': getattr(chunk, 'page_number', 1),
                        'section_context': getattr(chunk, 'section_context', ''),
                        'word_count': getattr(chunk, 'word_count', len(chunk.text.split())),
                        'sentence_count': getattr(chunk, 'sentence_count', chunk.text.count('.') + chunk.text.count('!') + chunk.text.count('?')),
                        'bounding_box': getattr(chunk, 'bounding_box', {}),
                        'metadata': getattr(chunk, 'metadata', {})
                    }
                elif isinstance(chunk, dict):
                    # Already a dictionary
                    chunk_dict = chunk.copy()
                else:
                    # Fallback - create basic dictionary
                    chunk_dict = {
                        'text': str(chunk),
                        'chunk_type': 'basic'
                    }
                
                # Add standard metadata
                chunk_dict.update({
                    'chunk_id': f"{doc_id}_chunk_{i:03d}",
                    'doc_id': doc_id,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'created_at': datetime.utcnow().isoformat() + 'Z'
                })
                
                processed_chunks.append(chunk_dict)
            
            # Replace chunks with processed chunks
            chunks = processed_chunks"""
        
        # Replace the problematic code
        if old_code in content:
            content = content.replace(old_code, new_code)
            logger.info("✅ Fixed StructuredChunk compatibility issue")
        else:
            logger.warning("⚠️ Could not find exact code pattern to replace")
            # Try a more targeted approach
            content = content.replace(
                "chunk.update({",
                "# Convert StructuredChunk to dict if needed\n                if hasattr(chunk, '__dataclass_fields__'):\n                    chunk_dict = {\n                        'text': chunk.text,\n                        'chunk_type': getattr(chunk, 'chunk_type', 'structured'),\n                        'hierarchy_level': getattr(chunk, 'hierarchy_level', 0),\n                        'page_number': getattr(chunk, 'page_number', 1),\n                        'section_context': getattr(chunk, 'section_context', ''),\n                        'word_count': getattr(chunk, 'word_count', len(chunk.text.split())),\n                        'sentence_count': getattr(chunk, 'sentence_count', chunk.text.count('.') + chunk.text.count('!') + chunk.text.count('?')),\n                        'bounding_box': getattr(chunk, 'bounding_box', {}),\n                        'metadata': getattr(chunk, 'metadata', {})\n                    }\n                elif isinstance(chunk, dict):\n                    chunk_dict = chunk.copy()\n                else:\n                    chunk_dict = {'text': str(chunk), 'chunk_type': 'basic'}\n                \n                chunk_dict.update({"
            )
            logger.info("✅ Applied targeted fix for StructuredChunk compatibility")
        
        # Write fixed content
        with open(text_chunker_file, 'w') as f:
            f.write(content)
        
        logger.info("✅ StructuredChunk compatibility fix applied successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to fix StructuredChunk compatibility: {e}")
        raise

if __name__ == "__main__":
    fix_structured_chunk_compatibility()
