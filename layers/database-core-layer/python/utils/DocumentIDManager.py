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

# Import from the same layer
try:
    from .DatabaseManager import DatabaseManager
    from ..document_processing.DocumentMetadata import DocumentMetadata, MetadataField
except ImportError:
    # Fallback for development
    from DatabaseManager import DatabaseManager
    try:
        from document_processing.DocumentMetadata import DocumentMetadata, MetadataField
    except ImportError:
        # Create minimal classes for development
        class MetadataField:
            def __init__(self, value, confidence, source):
                self.value = value
                self.confidence = confidence
                self.source = source
        
        class DocumentMetadata:
            def __init__(self):
                self.title = None
                self.author = None
                self.url = None

class DocumentIDManager:
    """
    Enhanced DocumentIDManager with comprehensive metadata management.
    AWS-optimized with PostgreSQL support and S3 integration.
    """
    
    def __init__(self, s3_bucket: str = None):
        """
        Initialize DocumentIDManager with AWS infrastructure support.
        Uses gold standard DatabaseManager pattern with environment variables.
        
        Args:
            s3_bucket: S3 bucket for document storage (optional)
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize database manager using gold standard pattern (no parameters)
        self.db_manager = DatabaseManager()
        
        # S3 configuration (optional)
        self.s3_bucket = s3_bucket or os.environ.get('S3_BUCKET')
        if self.s3_bucket:
            try:
                import boto3
                self.s3_client = boto3.client('s3')
                self.logger.debug(f"S3 integration enabled with bucket: {self.s3_bucket}")
            except ImportError:
                self.logger.warning("boto3 not available, S3 integration disabled")
                self.s3_client = None
        else:
            self.s3_client = None
        
        self.logger.info("DocumentIDManager initialized successfully")

    def generate_id(self, url: str, content: bytes = None) -> str:
        """
        Generate a unique document ID from URL and optional content.
        
        Args:
            url: Document URL or identifier
            content: Document content bytes (optional)
            
        Returns:
            Generated document ID
        """
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
        
        if content:
            content_hash = hashlib.sha256(content).hexdigest()[:8]
            return f"{url_hash}_{content_hash}"
        else:
            # Use timestamp if no content provided
            timestamp_hash = hashlib.sha256(str(datetime.now().timestamp()).encode()).hexdigest()[:8]
            return f"{url_hash}_{timestamp_hash}"

    def generate_id_from_s3(self, bucket: str, key: str) -> str:
        """
        Generate document ID from S3 object information.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            Generated document ID
        """
        if self.s3_client:
            try:
                # Get object metadata for ETag (content hash)
                response = self.s3_client.head_object(Bucket=bucket, Key=key)
                etag = response['ETag'].strip('"')
                
                # Combine bucket, key, and etag for unique hash
                content = f"{bucket}/{key}/{etag}"
                doc_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
                
                self.logger.debug(f"Generated S3-based doc_id: {doc_hash} for s3://{bucket}/{key}")
                return doc_hash
                
            except Exception as e:
                self.logger.warning(f"Could not get S3 object metadata: {str(e)}")
                # Fallback to key-based hash
                content = f"{bucket}/{key}"
                return hashlib.sha256(content.encode()).hexdigest()[:16]
        else:
            # Fallback without S3 client
            content = f"{bucket}/{key}"
            return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get_or_create_id(self, url: str, content: bytes = None) -> str:
        """
        Get existing document ID or create new one.
        
        Args:
            url: Document URL or identifier
            content: Document content bytes (optional)
            
        Returns:
            Document ID (existing or new)
        """
        doc_id = self.generate_id(url, content)
        
        # Check if document exists
        existing_metadata = self.db_manager.get_document_metadata(doc_id)
        if not existing_metadata:
            # Initialize with basic metadata
            initial_metadata = {
                'url': url,
                'status': 'pending',
                'title': {
                    'value': os.path.basename(url) if url else 'Unknown',
                    'confidence': 0.1,
                    'source': 'url'
                },
                'processing_info': {
                    'creation_time': datetime.now().isoformat(),
                    'status': 'initialized'
                }
            }
            self.db_manager.add_or_update_document(doc_id, initial_metadata)
            self.logger.debug(f"Created new document ID: {doc_id}")
        
        return doc_id

    def get_or_create_id_from_s3(self, bucket: str, key: str) -> str:
        """
        Get or create document ID from S3 object.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            Document ID (existing or new)
        """
        doc_id = self.generate_id_from_s3(bucket, key)
        
        # Check if document exists
        existing_metadata = self.db_manager.get_document_metadata(doc_id)
        if not existing_metadata:
            # Initialize with S3-based metadata
            initial_metadata = {
                'url': f"s3://{bucket}/{key}",
                'original_filename': os.path.basename(key),
                'status': 'pending',
                'title': {
                    'value': os.path.splitext(os.path.basename(key))[0],
                    'confidence': 0.2,
                    'source': 's3_key'
                },
                'processing_info': {
                    'creation_time': datetime.now().isoformat(),
                    'status': 'initialized',
                    'source_bucket': bucket,
                    'source_key': key
                }
            }
            
            # Add S3 metadata if available
            if self.s3_client:
                try:
                    response = self.s3_client.head_object(Bucket=bucket, Key=key)
                    initial_metadata['processing_info'].update({
                        'content_length': response.get('ContentLength'),
                        'last_modified': response.get('LastModified').isoformat() if response.get('LastModified') else None,
                        'content_type': response.get('ContentType')
                    })
                except Exception as e:
                    self.logger.warning(f"Could not get S3 metadata: {str(e)}")
            
            self.db_manager.add_or_update_document(doc_id, initial_metadata)
            self.logger.debug(f"Created new S3-based document ID: {doc_id}")
        
        return doc_id

    def add_or_update_document(self, doc_id: str, metadata: Union[Dict[str, Any], DocumentMetadata]) -> None:
        """
        Add or update document with metadata, preserving existing values unless explicitly changed.
        
        Args:
            doc_id: Document ID
            metadata: Either a dictionary or DocumentMetadata object containing updates
        """
        try:
            # Get existing metadata
            existing_metadata = self.db_manager.get_document_metadata(doc_id)
            
            # Format and merge the new metadata
            formatted_updates = self._format_metadata(doc_id, metadata)
            merged_metadata = self._merge_metadata_dicts(existing_metadata, formatted_updates)
            
            # Store the merged metadata
            self.db_manager.add_or_update_document(doc_id, merged_metadata)
            
            self.logger.debug(f"Document {doc_id} metadata updated successfully")

        except Exception as e:
            error_msg = f"Error updating document {doc_id}: {str(e)}"
            self.logger.error(error_msg)
            raise

    def get_document_metadata(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document metadata by ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document metadata dictionary or None if not found
        """
        return self.db_manager.get_document_metadata(doc_id)

    def update_document_status(self, doc_id: str, status: str, error_message: str = None) -> bool:
        """
        Update document processing status.
        
        Args:
            doc_id: Document ID
            status: New status
            error_message: Optional error message
            
        Returns:
            True if successful, False otherwise
        """
        try:
            update_data = {
                'status': status,
                'processing_info': {
                    'last_updated': datetime.now().isoformat(),
                    'status': status
                }
            }
            
            if error_message:
                update_data['error_message'] = error_message
                update_data['processing_info']['error'] = error_message
            
            self.add_or_update_document(doc_id, update_data)
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating document status: {str(e)}")
            return False

    def update_system_id(self, doc_id: str, system_name: str, system_id: str, 
                        status: str = 'complete') -> bool:
        """
        Update system-specific ID for a document.
        
        Args:
            doc_id: Document ID
            system_name: Name of the system (e.g., 'opensearch', 'textract')
            system_id: System-specific identifier
            status: Processing status
            
        Returns:
            True if successful, False otherwise
        """
        return self.db_manager.update_system_id(doc_id, system_name, system_id, status)

    def get_documents_by_status(self, status: str) -> List[str]:
        """
        Get document IDs by processing status.
        
        Args:
            status: Status to filter by
            
        Returns:
            List of document IDs
        """
        return self.db_manager.get_documents_by_index_status('status', status)

    def _merge_metadata_dicts(self, existing: Optional[Dict[str, Any]], updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge existing metadata with updates, preserving existing values unless explicitly changed.
        
        Args:
            existing: Existing metadata dictionary (may be None)
            updates: New metadata dictionary with updates
            
        Returns:
            Merged metadata dictionary
        """
        if not existing:
            return updates

        merged = existing.copy()
        
        # Helper function to merge nested dictionaries
        def merge_dict(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
            result = base.copy()
            for key, value in overlay.items():
                if value is not None:  # Only update if new value is not None
                    if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                        # Recursively merge nested dictionaries
                        result[key] = merge_dict(base[key], value)
                    else:
                        # Replace value
                        result[key] = value
            return result

        # Merge top-level fields
        for key, value in updates.items():
            if value is not None:  # Only update if new value is not None
                if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                    # Handle nested dictionaries (like title, author, language)
                    merged[key] = merge_dict(merged[key], value)
                else:
                    merged[key] = value

        return merged

    def _format_metadata(self, doc_id: str, metadata: Union[Dict[str, Any], DocumentMetadata]) -> Dict[str, Any]:
        """Format metadata updates into a consistent structure for database storage."""
        if isinstance(metadata, DocumentMetadata):
            formatted = {
                "doc_id": doc_id
            }
            
            # Only include fields that are actually present in the metadata object
            if hasattr(metadata, 'url') and metadata.url:
                formatted["url"] = metadata.url
            if hasattr(metadata, 'pdf_path') and metadata.pdf_path:
                formatted["pdf_path"] = metadata.pdf_path
            if hasattr(metadata, 'text_path') and metadata.text_path:
                formatted["text_path"] = metadata.text_path
            if hasattr(metadata, 'original_filename') and metadata.original_filename:
                formatted["original_filename"] = metadata.original_filename
            if hasattr(metadata, 'download_date') and metadata.download_date:
                formatted["download_date"] = metadata.download_date
                
            # Handle complex fields only if present
            if metadata.title:
                formatted["title"] = {
                    "value": metadata.title.value,
                    "confidence": metadata.title.confidence,
                    "source": metadata.title.source
                }
            
            if metadata.author:
                formatted["author"] = {
                    "value": metadata.author.value,
                    "confidence": metadata.author.confidence,
                    "source": metadata.author.source
                }
            
            return formatted
        else:
            # Handle dictionary input
            formatted = metadata.copy()
            formatted["doc_id"] = doc_id
            return formatted

    def list_documents(self, limit: int = 100, offset: int = 0, status: str = None) -> List[Dict[str, Any]]:
        """
        List documents with optional filtering.
        
        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            status: Optional status filter
            
        Returns:
            List of document metadata dictionaries
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = """
                        SELECT d.doc_id, d.url, d.original_filename, d.status, 
                               d.created_at, d.updated_at,
                               m.title, m.author, m.metadata_quality
                        FROM documents d
                        LEFT JOIN document_metadata m ON d.doc_id = m.doc_id
                    """
                    params = []
                    
                    if status:
                        query += " WHERE d.status = %s"
                        params.append(status)
                    
                    query += " ORDER BY d.updated_at DESC LIMIT %s OFFSET %s"
                    params.extend([limit, offset])
                    
                    cursor.execute(query, params)
                    
                    columns = [desc[0] for desc in cursor.description]
                    results = []
                    
                    for row in cursor.fetchall():
                        doc_dict = dict(zip(columns, row))
                        results.append(doc_dict)
                    
                    return results
                
        except Exception as e:
            self.logger.error(f"Error listing documents: {str(e)}")
            return []

    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics for monitoring.
        
        Returns:
            Dictionary with processing statistics
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Get status counts
                    cursor.execute("""
                        SELECT status, COUNT(*) as count
                        FROM documents
                        GROUP BY status
                    """)
                    status_counts = dict(cursor.fetchall())
                    
                    # Get recent activity
                    cursor.execute("""
                        SELECT COUNT(*) as recent_updates
                        FROM documents
                        WHERE updated_at > NOW() - INTERVAL '1 hour'
                    """)
                    recent_updates = cursor.fetchone()[0]
                    
                    # Get total documents
                    cursor.execute("SELECT COUNT(*) FROM documents")
                    total_documents = cursor.fetchone()[0]
                    
                    return {
                        'total_documents': total_documents,
                        'status_counts': status_counts,
                        'recent_updates': recent_updates,
                        'timestamp': datetime.now().isoformat()
                    }
                
        except Exception as e:
            self.logger.error(f"Error getting processing statistics: {str(e)}")
            return {}

    def cleanup_old_documents(self, days_old: int = 30, status: str = 'failed') -> int:
        """
        Clean up old documents with specified status.
        
        Args:
            days_old: Age threshold in days
            status: Status of documents to clean up
            
        Returns:
            Number of documents cleaned up
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        DELETE FROM documents
                        WHERE status = %s 
                        AND updated_at < NOW() - INTERVAL '%s days'
                    """, (status, days_old))
                    
                    deleted_count = cursor.rowcount
                    conn.commit()
                    
                    self.logger.info(f"Cleaned up {deleted_count} old documents with status '{status}'")
                    return deleted_count
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old documents: {str(e)}")
            return 0
