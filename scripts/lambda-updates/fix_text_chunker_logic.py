#!/usr/bin/env python3
"""
Fix Text Chunker Logic - Handle None text_location values
"""

import os
import shutil
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_text_chunker_logic():
    """Fix the text reading logic to handle None values properly"""
    
    text_chunker_file = "/Users/chris/climate-risk-rag-aws/lambda/text_chunker/text_chunker_processor_updated.py"
    backup_file = text_chunker_file + ".backup"
    
    try:
        # Create backup
        logger.info("Creating backup of text chunker file...")
        shutil.copy2(text_chunker_file, backup_file)
        
        # Read current file
        with open(text_chunker_file, 'r') as f:
            content = f.read()
        
        # Fix 1: Add None check in read_text_from_s3
        old_text_reading = '''    def read_text_from_s3(self, text_location: str) -> str:
        """Read text content from S3 location"""
        try:
            # Parse S3 location
            if text_location.startswith('s3://'):'''
        
        new_text_reading = '''    def read_text_from_s3(self, text_location: str) -> str:
        """Read text content from S3 location"""
        try:
            # Validate text_location
            if not text_location:
                raise ValueError("text_location is None or empty")
            
            # Parse S3 location
            if text_location.startswith('s3://'):'''
        
        content = content.replace(old_text_reading, new_text_reading)
        
        # Fix 2: Add None check in read_document_structure
        old_structure_reading = '''    def read_document_structure(self, structure_location: str) -> Optional[Dict]:
        """Read document structure from S3 location"""
        try:
            # Parse S3 location
            if structure_location.startswith('s3://'):'''
        
        new_structure_reading = '''    def read_document_structure(self, structure_location: str) -> Optional[Dict]:
        """Read document structure from S3 location"""
        try:
            # Validate structure_location
            if not structure_location:
                logger.warning("structure_location is None or empty, skipping structure reading")
                return None
            
            # Parse S3 location
            if structure_location.startswith('s3://'):'''
        
        content = content.replace(old_structure_reading, new_structure_reading)
        
        # Fix 3: Add better error handling in process_text_chunking
        old_processing = '''        # Read full text from S3
        full_text = self.read_text_from_s3(text_location)
        if not full_text:
            raise ValueError("No text content found")'''
        
        new_processing = '''        # Validate text_location before reading
        if not text_location:
            raise ValueError("text_location is missing from message")
        
        # Read full text from S3
        full_text = self.read_text_from_s3(text_location)
        if not full_text:
            raise ValueError("No text content found")'''
        
        content = content.replace(old_processing, new_processing)
        
        # Write fixed content
        with open(text_chunker_file, 'w') as f:
            f.write(content)
        
        logger.info("✅ Text chunker logic fixes applied successfully")
        logger.info(f"✅ Backup saved to: {backup_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to fix text chunker logic: {e}")
        # Restore backup if it exists
        if os.path.exists(backup_file):
            shutil.copy2(backup_file, text_chunker_file)
            logger.info("Restored original file from backup")
        raise

if __name__ == "__main__":
    fix_text_chunker_logic()
