#!/usr/bin/env python3
"""
DocumentIDManager - Core Database Layer
Clean, focused document ID management
Works with DatabaseManager for database operations
"""

import logging
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime
from .DatabaseManager import DatabaseManager

logger = logging.getLogger(__name__)

class DocumentIDManager:
    """
    Document ID management for pipeline processing
    Handles document registration, status tracking, and metadata
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize DocumentIDManager with database connection"""
        self.db_manager = db_manager or DatabaseManager.get_instance()
        logger.info("DocumentIDManager initialized")
    
    def generate_doc_id(self, filename: str, content_hash: str = None) -> str:
        """Generate unique document ID from filename and optional content hash"""
        if content_hash:
            # Use provided content hash
            base_string = f"{filename}_{content_hash}"
        else:
            # Generate hash from filename
            base_string = filename
        
        # Create short hash for doc_id
        doc_hash = hashlib.md5(base_string.encode()).hexdigest()[:16]
        doc_id = f"{filename.split('.')[0]}_{doc_hash}"
        
        logger.info(f"Generated doc_id: {doc_id} for filename: {filename}")
        return doc_id
    
    def register_document(self, doc_id: str, filename: str, metadata: Dict[str, Any] = None) -> bool:
        """Register new document in database"""
        try:
            # Check if document already exists
            if self.document_exists(doc_id):
                logger.info(f"Document {doc_id} already registered")
                return True
            
            # Insert new document record
            query = """
                INSERT INTO documents (doc_id, filename, status, metadata, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            now = datetime.utcnow()
            metadata_json = metadata or {}
            
            params = (
                doc_id,
                filename,
                'registered',
                str(metadata_json),  # Convert to string for storage
                now,
                now
            )
            
            rows_affected = self.db_manager.execute_update(query, params)
            
            if rows_affected > 0:
                logger.info(f"Successfully registered document: {doc_id}")
                return True
            else:
                logger.error(f"Failed to register document: {doc_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error registering document {doc_id}: {e}")
            return False
    
    def document_exists(self, doc_id: str) -> bool:
        """Check if document exists in database"""
        try:
            query = "SELECT COUNT(*) FROM documents WHERE doc_id = %s"
            result = self.db_manager.execute_query(query, (doc_id,))
            return result[0][0] > 0
        except Exception as e:
            logger.error(f"Error checking document existence {doc_id}: {e}")
            return False
    
    def update_document_status(self, doc_id: str, status: str, metadata: Dict[str, Any] = None) -> bool:
        """Update document processing status"""
        try:
            if metadata:
                query = """
                    UPDATE documents 
                    SET status = %s, metadata = %s, updated_at = %s 
                    WHERE doc_id = %s
                """
                params = (status, str(metadata), datetime.utcnow(), doc_id)
            else:
                query = """
                    UPDATE documents 
                    SET status = %s, updated_at = %s 
                    WHERE doc_id = %s
                """
                params = (status, datetime.utcnow(), doc_id)
            
            rows_affected = self.db_manager.execute_update(query, params)
            
            if rows_affected > 0:
                logger.info(f"Updated document {doc_id} status to: {status}")
                return True
            else:
                logger.warning(f"No document found to update: {doc_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating document status {doc_id}: {e}")
            return False
    
    def get_document_info(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document information from database"""
        try:
            query = """
                SELECT doc_id, filename, status, metadata, created_at, updated_at
                FROM documents 
                WHERE doc_id = %s
            """
            
            result = self.db_manager.execute_query(query, (doc_id,))
            
            if result:
                row = result[0]
                return {
                    'doc_id': row[0],
                    'filename': row[1],
                    'status': row[2],
                    'metadata': row[3],
                    'created_at': row[4],
                    'updated_at': row[5]
                }
            else:
                logger.info(f"Document not found: {doc_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting document info {doc_id}: {e}")
            return None
    
    def get_documents_by_status(self, status: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get documents by processing status"""
        try:
            query = """
                SELECT doc_id, filename, status, metadata, created_at, updated_at
                FROM documents 
                WHERE status = %s
                ORDER BY created_at DESC
                LIMIT %s
            """
            
            results = self.db_manager.execute_query(query, (status, limit))
            
            documents = []
            for row in results:
                documents.append({
                    'doc_id': row[0],
                    'filename': row[1],
                    'status': row[2],
                    'metadata': row[3],
                    'created_at': row[4],
                    'updated_at': row[5]
                })
            
            logger.info(f"Found {len(documents)} documents with status: {status}")
            return documents
            
        except Exception as e:
            logger.error(f"Error getting documents by status {status}: {e}")
            return []
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete document record from database"""
        try:
            query = "DELETE FROM documents WHERE doc_id = %s"
            rows_affected = self.db_manager.execute_update(query, (doc_id,))
            
            if rows_affected > 0:
                logger.info(f"Deleted document: {doc_id}")
                return True
            else:
                logger.warning(f"No document found to delete: {doc_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            return False
    
    def cleanup_documents(self, status_filter: str = None, older_than_days: int = None) -> int:
        """Cleanup documents based on criteria"""
        try:
            conditions = []
            params = []
            
            if status_filter:
                conditions.append("status = %s")
                params.append(status_filter)
            
            if older_than_days:
                conditions.append("created_at < NOW() - INTERVAL '%s days'")
                params.append(older_than_days)
            
            if not conditions:
                logger.warning("No cleanup criteria specified")
                return 0
            
            query = f"DELETE FROM documents WHERE {' AND '.join(conditions)}"
            rows_affected = self.db_manager.execute_update(query, tuple(params))
            
            logger.info(f"Cleaned up {rows_affected} documents")
            return rows_affected
            
        except Exception as e:
            logger.error(f"Error during document cleanup: {e}")
            return 0
