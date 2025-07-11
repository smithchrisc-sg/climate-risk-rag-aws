#!/usr/bin/env python3
"""
Source Documents Bucket Setup
Creates the source documents bucket and prepares test documents with proper DocumentIDManager integration
"""

import boto3
import json
import sqlite3
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# Add layers to path for shared utilities
sys.path.append('layers/app-source')
sys.path.append('layers/app-source/utils')

try:
    from utils.DocumentIDManager import DocumentIDManager
except ImportError as e:
    print(f"Warning: Could not import DocumentIDManager: {e}")
    DocumentIDManager = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SourceDocumentsBucketSetup:
    """Sets up source documents bucket and prepares test documents"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        
        # Bucket configuration
        self.existing_bucket = "solve-global-kr-documents-861276078413-us-east-1"
        self.source_bucket = "solve-global-kr-dl-source-documents-861276078413-us-east-1"
        self.sqlite_db_path = "/Volumes/G-RAID Photo 24TB/climate_risk_rag/db/corpus_document_ids.db"
        
        # Initialize DocumentIDManager
        if DocumentIDManager:
            try:
                self.doc_id_manager = DocumentIDManager()
                logger.info("DocumentIDManager initialized successfully")
            except Exception as e:
                logger.warning(f"DocumentIDManager initialization failed: {e}")
                self.doc_id_manager = None
        else:
            self.doc_id_manager = None
    
    def create_source_bucket(self) -> bool:
        """Create the source documents bucket"""
        try:
            # Check if bucket already exists
            try:
                self.s3_client.head_bucket(Bucket=self.source_bucket)
                logger.info(f"Source bucket already exists: {self.source_bucket}")
                return True
            except:
                pass
            
            # Create bucket
            self.s3_client.create_bucket(Bucket=self.source_bucket)
            
            # Set bucket policy for Lambda access
            bucket_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "LambdaAccess",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                        },
                        "Action": [
                            "s3:GetObject",
                            "s3:PutObject",
                            "s3:DeleteObject"
                        ],
                        "Resource": f"arn:aws:s3:::{self.source_bucket}/*"
                    },
                    {
                        "Sid": "LambdaListAccess",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                        },
                        "Action": "s3:ListBucket",
                        "Resource": f"arn:aws:s3:::{self.source_bucket}"
                    }
                ]
            }
            
            self.s3_client.put_bucket_policy(
                Bucket=self.source_bucket,
                Policy=json.dumps(bucket_policy)
            )
            
            logger.info(f"Created source bucket: {self.source_bucket}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating source bucket: {e}")
            return False
    
    def get_available_documents(self, limit: int = 50) -> List[Dict]:
        """Get available documents from existing bucket with metadata"""
        try:
            logger.info(f"Fetching documents from existing bucket: {self.existing_bucket}")
            
            # List documents in existing bucket
            response = self.s3_client.list_objects_v2(
                Bucket=self.existing_bucket,
                Prefix="documents/",
                MaxKeys=limit * 2  # Get extra to allow for filtering
            )
            
            if 'Contents' not in response:
                logger.error("No documents found in existing bucket")
                return []
            
            documents = []
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('.pdf'):
                    filename = os.path.basename(key)
                    doc_id_from_filename = filename.replace('.pdf', '')
                    
                    # Get object metadata for size filtering
                    try:
                        head_response = self.s3_client.head_object(
                            Bucket=self.existing_bucket,
                            Key=key
                        )
                        content_length = head_response.get('ContentLength', 0)
                    except:
                        content_length = obj.get('Size', 0)
                    
                    documents.append({
                        'key': key,
                        'filename': filename,
                        'doc_id_from_filename': doc_id_from_filename,
                        'size': content_length,
                        'size_mb': round(content_length / (1024 * 1024), 2),
                        'last_modified': obj['LastModified']
                    })
            
            logger.info(f"Found {len(documents)} PDF documents in existing bucket")
            return documents
            
        except Exception as e:
            logger.error(f"Error getting available documents: {e}")
            return []
    
    def filter_documents_by_criteria(self, documents: List[Dict], 
                                   min_size_mb: float = 0.5, 
                                   max_size_mb: float = 50.0,
                                   limit: int = 10) -> List[Dict]:
        """Filter documents by size and other criteria"""
        try:
            # Filter by size
            filtered = [
                doc for doc in documents 
                if min_size_mb <= doc['size_mb'] <= max_size_mb
            ]
            
            # Sort by size (medium-sized documents first for testing)
            filtered.sort(key=lambda x: abs(x['size_mb'] - 5.0))  # Prefer ~5MB documents
            
            # Limit results
            filtered = filtered[:limit]
            
            logger.info(f"Filtered to {len(filtered)} documents (size: {min_size_mb}-{max_size_mb} MB)")
            for doc in filtered:
                logger.info(f"  - {doc['filename']}: {doc['size_mb']} MB")
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error filtering documents: {e}")
            return documents[:limit]  # Fallback to first N documents
    
    def get_source_url_from_sqlite(self, doc_id_from_filename: str) -> Optional[str]:
        """Get source URL from SQLite database"""
        try:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT url FROM documents WHERE doc_id = ?",
                (doc_id_from_filename,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
            else:
                logger.warning(f"No source URL found for doc_id: {doc_id_from_filename}")
                return None
                
        except Exception as e:
            logger.error(f"Error querying SQLite for {doc_id_from_filename}: {e}")
            return None
    
    def prepare_source_document(self, doc_info: Dict) -> Optional[Dict]:
        """Prepare a single document for the source bucket"""
        try:
            doc_id_from_filename = doc_info['doc_id_from_filename']
            
            # Get source URL from SQLite
            source_url = self.get_source_url_from_sqlite(doc_id_from_filename)
            if not source_url:
                logger.error(f"Cannot prepare document without source URL: {doc_id_from_filename}")
                return None
            
            # Get proper doc_id from DocumentIDManager
            if self.doc_id_manager:
                try:
                    proper_doc_id = self.doc_id_manager.get_or_create_id(source_url)
                    logger.info(f"Generated proper doc_id: {proper_doc_id} for URL: {source_url}")
                except Exception as e:
                    logger.error(f"DocumentIDManager failed for {source_url}: {e}")
                    return None
            else:
                logger.error("DocumentIDManager not available")
                return None
            
            # Copy document to source bucket with proper doc_id
            source_key = f"{proper_doc_id}.pdf"
            
            try:
                # Copy object
                copy_source = {
                    'Bucket': self.existing_bucket,
                    'Key': doc_info['key']
                }
                
                self.s3_client.copy_object(
                    CopySource=copy_source,
                    Bucket=self.source_bucket,
                    Key=source_key,
                    MetadataDirective='REPLACE',
                    Metadata={
                        'source-url': source_url,
                        'original-filename': doc_info['filename'],
                        'prepared-at': datetime.utcnow().isoformat(),
                        'doc-id': proper_doc_id
                    }
                )
                
                logger.info(f"Copied document to source bucket: {source_key}")
                
                return {
                    'original_doc_id': doc_id_from_filename,
                    'proper_doc_id': proper_doc_id,
                    'source_url': source_url,
                    'original_filename': doc_info['filename'],
                    'source_key': source_key,
                    'size_mb': doc_info['size_mb'],
                    'prepared_at': datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error copying document to source bucket: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error preparing document {doc_info.get('filename', 'unknown')}: {e}")
            return None
    
    def setup_test_documents(self, num_documents: int = 10, 
                           min_size_mb: float = 0.5, 
                           max_size_mb: float = 20.0,
                           language: str = "english",
                           document_types: List[str] = None,
                           target_avg_pages: int = 20,
                           max_total_pages: int = 100) -> List[Dict]:
        """Set up test documents in source bucket"""
        try:
            logger.info(f"Setting up {num_documents} test documents")
            
            # Get available documents
            available_docs = self.get_available_documents(limit=50)
            if not available_docs:
                logger.error("No documents available")
                return []
            
            # Filter by criteria
            filtered_docs = self.filter_documents_by_criteria(
                available_docs, 
                min_size_mb=min_size_mb, 
                max_size_mb=max_size_mb, 
                limit=num_documents
            )
            
            if not filtered_docs:
                logger.error("No documents match criteria")
                return []
            
            # Prepare each document
            prepared_docs = []
            for doc_info in filtered_docs:
                prepared = self.prepare_source_document(doc_info)
                if prepared:
                    prepared_docs.append(prepared)
                else:
                    logger.warning(f"Failed to prepare document: {doc_info['filename']}")
            
            logger.info(f"Successfully prepared {len(prepared_docs)} documents")
            
            # Save preparation summary
            summary = {
                'prepared_at': datetime.utcnow().isoformat(),
                'source_bucket': self.source_bucket,
                'documents_prepared': len(prepared_docs),
                'documents': prepared_docs
            }
            
            summary_file = f"source_documents_preparation_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            logger.info(f"Preparation summary saved to: {summary_file}")
            
            return prepared_docs
            
        except Exception as e:
            logger.error(f"Error setting up test documents: {e}")
            return []

def main():
    """Main setup execution"""
    try:
        setup = SourceDocumentsBucketSetup()
        
        # Create source bucket
        if not setup.create_source_bucket():
            logger.error("Failed to create source bucket")
            return False
        
        # Setup test documents
        prepared_docs = setup.setup_test_documents(
            num_documents=10,
            min_size_mb=1.0,    # At least 1MB
            max_size_mb=15.0    # At most 15MB
        )
        
        if not prepared_docs:
            logger.error("No documents were prepared")
            return False
        
        logger.info("=" * 60)
        logger.info("SOURCE DOCUMENTS BUCKET SETUP COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Bucket: {setup.source_bucket}")
        logger.info(f"Documents prepared: {len(prepared_docs)}")
        logger.info("\nPrepared documents:")
        for doc in prepared_docs:
            logger.info(f"  - {doc['source_key']} ({doc['size_mb']} MB)")
            logger.info(f"    Source: {doc['source_url']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
