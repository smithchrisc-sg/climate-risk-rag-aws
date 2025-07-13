#!/usr/bin/env python3
"""
Fix DocumentSection Dataclass Fields
Add missing start_char and end_char fields to DocumentSection
"""

import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_document_section_fields():
    """Fix the DocumentSection dataclass to include missing fields"""
    
    chunking_file = "/Users/chris/climate-risk-rag-aws/lambda/shared_layer/python/structured_chunking_smart_complete.py"
    
    try:
        # Read current file
        with open(chunking_file, 'r') as f:
            content = f.read()
        
        # Find and replace the DocumentSection dataclass definition
        old_definition = """@dataclass
class DocumentSection:
    \"\"\"Represents a logical section of a document\"\"\"
    text: str
    section_type: SectionType
    hierarchy_level: int
    page_number: int
    bounding_box: Dict
    confidence: float
    children: List['DocumentSection'] = None
    metadata: Dict = None"""
        
        new_definition = """@dataclass
class DocumentSection:
    \"\"\"Represents a logical section of a document\"\"\"
    text: str
    section_type: SectionType
    hierarchy_level: int
    page_number: int
    bounding_box: Dict
    confidence: float
    start_char: int = 0
    end_char: int = 0
    children: List['DocumentSection'] = None
    metadata: Dict = None"""
        
        # Replace the definition
        if old_definition in content:
            content = content.replace(old_definition, new_definition)
            logger.info("✅ Fixed DocumentSection dataclass definition")
        else:
            logger.warning("⚠️ Could not find exact DocumentSection definition to replace")
            # Try a more targeted approach
            content = content.replace(
                "confidence: float\n    children: List['DocumentSection'] = None",
                "confidence: float\n    start_char: int = 0\n    end_char: int = 0\n    children: List['DocumentSection'] = None"
            )
            logger.info("✅ Applied targeted fix for DocumentSection fields")
        
        # Write fixed content
        with open(chunking_file, 'w') as f:
            f.write(content)
        
        logger.info("✅ DocumentSection fields fix applied successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to fix DocumentSection fields: {e}")
        raise

if __name__ == "__main__":
    fix_document_section_fields()
