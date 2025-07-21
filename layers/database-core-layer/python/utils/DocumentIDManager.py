"""
DocumentIDManager for Climate Risk RAG System
AWS-optimized with PostgreSQL support and S3 integration
"""

import os
import sys
import hashlib
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import json

from .DatabaseManager import DatabaseManager
from ..document_processing.DocumentMetadata import DocumentMetadata

class DocumentIDManager:
    """
    Enhanced DocumentIDManager with comprehensive metadata management.
    AWS-optimized with PostgreSQL support and S3 integration.
    """
    
    def __init__(self):
        """
        Initialize DocumentIDManager with AWS infrastructure support.
        Uses DatabaseManager pattern with environment variables.
        
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize database manager using gold standard pattern (no parameters)
        self.db_manager = DatabaseManager()
        
        self.logger.info("DocumentIDManager initialized successfully")

    def generate_id(self, source_url: str, content: bytes = None) -> str:
        """
        Generate a stable document ID from source URL only.
        Content is not used for ID generation to ensure stable identity across content updates.
        
        Args:
            source_url: Document URL or identifier
            content: Document content bytes (not used for ID generation)
            
        Returns:
            Generated document ID (20-character SHA256 hash of URL)
        """
        url_hash = hashlib.sha256(source_url.encode()).hexdigest()[:20]
        return url_hash

    def get_or_create_id(self, source_url: str, content: bytes) -> str:
        """
        Get existing document ID or create new one.
        Uses stable URL-based ID generation, allowing proper content update detection.
        
        Args:
            source_url: Document URL or identifier
            content: Document content bytes
            
        Returns:
            Document ID (existing or new)
        """
        doc_id = self.generate_id(source_url)  # Content not used for ID generation
        
        # Always call add_or_update_document - it handles new vs existing logic
        file_size_bytes = len(content)
        file_hash = hashlib.sha256(content).hexdigest()
        original_filename = os.path.basename(source_url)

        self.db_manager.add_or_update_document(doc_id, source_url, original_filename, file_size_bytes, file_hash)

        self.logger.debug(f"Processed document ID: {doc_id}")
        
        return doc_id
