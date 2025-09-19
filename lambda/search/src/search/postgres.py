import os
from typing import Dict, Any, List
import logging

class PostgresProcessor:
    """Handles PostgreSQL operations for document metadata via DatabaseManager"""
    
    def __init__(self):
        self.db_manager = None
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.info("PostgresProcessor initialized")
    
    def _get_db_manager(self):
        """Get DatabaseManager instance"""
        if not self.db_manager:
            from utils.DatabaseManager import DatabaseManager
            self.db_manager = DatabaseManager()
        return self.db_manager
    
    async def get_document_metadata(self, document_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get metadata for multiple documents"""
        if not document_ids:
            return {}
        
        try:
            db_manager = self._get_db_manager()
            
            # Use existing DatabaseManager method for each document
            metadata = {}
            for doc_id in document_ids:
                doc_data = db_manager.get_document(doc_id)
                if doc_data:
                    metadata[doc_id] = doc_data
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"PostgreSQL metadata query error: {e}")
            return {}
