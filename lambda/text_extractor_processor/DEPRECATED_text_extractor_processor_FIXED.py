"""
TextExtractor Processor Lambda Function - FIXED VERSION
Processes completed Textract jobs and saves structured output
Now properly integrated with DocumentIDManager system
"""

import json
import boto3
import logging
import os
import csv
import io
from datetime import datetime
from typing import Dict, List, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

# Import DocumentIDManager from shared layer
try:
    from DocumentIDManager import DocumentIDManager
except ImportError:
    # Fallback for development/testing
    class DocumentIDManager:
        def __init__(self, database_url=None):
            self.database_url = database_url
        
        def get_or_create_id_from_s3(self, bucket, key):
            # Fallback implementation
            import hashlib
            content = f"{bucket}/{key}"
            return hashlib.sha256(content.encode()).hexdigest()[:16]

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class TextExtractorProcessor:
    """Processes completed Textract jobs and saves structured output"""
    
    def __init__(self):
        self.textract = boto3.client('textract')
        self.s3 = boto3.client('s3')
        self.sqs = boto3.client('sqs')
        
        # Environment configuration
        self.output_bucket = os.environ['OUTPUT_BUCKET']
        self.database_url = os.environ['DATABASE_URL']
        self.next_stage_queue_url = os.environ.get('NEXT_STAGE_QUEUE_URL')
        
        # Initialize DocumentIDManager
        self.doc_id_manager = DocumentIDManager(database_url=self.database_url)
        
        logger.info(f"TextExtractor Processor initialized")
        logger.info(f"Output bucket: {self.output_bucket}")

    def get_db_connection(self):
        """Get PostgreSQL database connection"""
        try:
            conn = psycopg2.connect(self.database_url)
            return conn
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            raise

    def get_or_create_doc_id(self, job_metadata: Dict) -> str:
        """Get or create proper doc_id using DocumentIDManager"""
        try:
            source_bucket = job_metadata['source_bucket']
            source_key = job_metadata['source_key']
            
            # Use DocumentIDManager to get or create proper GUID-based doc_id
            doc_id = self.doc_id_manager.get_or_create_id_from_s3(source_bucket, source_key)
            
            logger.info(f"Using doc_id: {doc_id} for s3://{source_bucket}/{source_key}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error getting doc_id: {str(e)}")
            # Fallback to doc_hash if DocumentIDManager fails
            return job_metadata.get('doc_hash', 'unknown')

    def save_structured_output(self, textract_response: Dict, doc_hash: str, job_metadata: Dict) -> Dict[str, Any]:
        """Save structured Textract output to S3 using proper doc_id"""
        try:
            # Get proper doc_id using DocumentIDManager
            doc_id = self.get_or_create_doc_id(job_metadata)
            logger.info(f"Saving structured output for doc_id: {doc_id} (doc_hash: {doc_hash})")
            
            # New directory structure: {doc_id}/
            base_key = doc_id
            files_created = []
            
            # Extract raw text first (needed for multiple files)
            raw_text = self.extract_raw_text(textract_response)
            
            # 1. Save full text file: {doc_id}_full_text.txt
            if raw_text:
                text_key = f"{base_key}/{doc_id}_full_text.txt"
                self.s3.put_object(
                    Bucket=self.output_bucket,
                    Key=text_key,
                    Body=raw_text.encode('utf-8'),
                    ContentType='text/plain'
                )
                files_created.append(f'{doc_id}_full_text.txt')
                logger.info(f"Saved full text: {text_key}")
            
            # 2. Create metadata directory structure
            metadata_base = f"{base_key}/metadata"
            
            # 2a. Save complete JSON response (for smart chunker)
            json_key = f"{metadata_base}/textract_response.json"
            self.s3.put_object(
                Bucket=self.output_bucket,
                Key=json_key,
                Body=json.dumps(textract_response, indent=2, default=str),
                ContentType='application/json'
            )
            files_created.append('metadata/textract_response.json')
            
            # 2b. Save layout structure CSV
            layout_csv = self.extract_layout_csv(textract_response)
            if layout_csv:
                layout_key = f"{metadata_base}/layout_structure.csv"
                self.s3.put_object(
                    Bucket=self.output_bucket,
                    Key=layout_key,
                    Body=layout_csv.encode('utf-8'),
                    ContentType='text/csv'
                )
                files_created.append('metadata/layout_structure.csv')
            
            # 2c. Create and save document_structure.json (NEW - optimized for chunker)
            document_structure = self.create_document_structure(textract_response)
            if document_structure:
                doc_structure_key = f"{metadata_base}/document_structure.json"
                self.s3.put_object(
                    Bucket=self.output_bucket,
                    Key=doc_structure_key,
                    Body=json.dumps(document_structure, indent=2, default=str),
                    ContentType='application/json'
                )
                files_created.append('metadata/document_structure.json')
            
            # 3. Save tables in tables/ subdirectory
            tables_csv = self.extract_tables_csv(textract_response)
            if tables_csv:
                tables_summary = {
                    'total_tables': len(tables_csv),
                    'table_files': [],
                    'created_at': datetime.utcnow().isoformat()
                }
                
                for i, table_csv in enumerate(tables_csv):
                    table_key = f"{metadata_base}/tables/table_{i+1:03d}.csv"
                    self.s3.put_object(
                        Bucket=self.output_bucket,
                        Key=table_key,
                        Body=table_csv.encode('utf-8'),
                        ContentType='text/csv'
                    )
                    table_filename = f'table_{i+1:03d}.csv'
                    files_created.append(f'metadata/tables/{table_filename}')
                    tables_summary['table_files'].append(table_filename)
                
                # Save tables summary
                tables_summary_key = f"{metadata_base}/tables/tables_summary.json"
                self.s3.put_object(
                    Bucket=self.output_bucket,
                    Key=tables_summary_key,
                    Body=json.dumps(tables_summary, indent=2, default=str),
                    ContentType='application/json'
                )
                files_created.append('metadata/tables/tables_summary.json')
            
            # 4. Save forms in forms/ subdirectory
            kv_csv = self.extract_key_value_csv(textract_response)
            if kv_csv:
                forms_key = f"{metadata_base}/forms/key_values.csv"
                self.s3.put_object(
                    Bucket=self.output_bucket,
                    Key=forms_key,
                    Body=kv_csv.encode('utf-8'),
                    ContentType='text/csv'
                )
                files_created.append('metadata/forms/key_values.csv')
                
                # Save forms summary
                forms_summary = {
                    'key_value_pairs_found': len(kv_csv.split('\n')) - 1 if kv_csv else 0,
                    'created_at': datetime.utcnow().isoformat()
                }
                forms_summary_key = f"{metadata_base}/forms/forms_summary.json"
                self.s3.put_object(
                    Bucket=self.output_bucket,
                    Key=forms_summary_key,
                    Body=json.dumps(forms_summary, indent=2, default=str),
                    ContentType='application/json'
                )
                files_created.append('metadata/forms/forms_summary.json')
            
            # 5. Save processing info
            processing_info = {
                'doc_id': doc_id,
                'doc_hash': doc_hash,  # Keep doc_hash for TextExtractor system compatibility
                'processing_date': datetime.utcnow().isoformat(),
                'textract_model_version': textract_response.get('AnalyzeDocumentModelVersion'),
                'pages_processed': textract_response.get('DocumentMetadata', {}).get('Pages', 0),
                'blocks_extracted': len(textract_response.get('Blocks', [])),
                'files_created': files_created,
                'source_document': {
                    'bucket': job_metadata['source_bucket'],
                    'key': job_metadata['source_key']
                },
                'extraction_statistics': {
                    'total_blocks': len(textract_response.get('Blocks', [])),
                    'layout_blocks': len([b for b in textract_response.get('Blocks', []) if b['BlockType'].startswith('LAYOUT_')]),
                    'table_blocks': len([b for b in textract_response.get('Blocks', []) if b['BlockType'] == 'TABLE']),
                    'key_value_blocks': len([b for b in textract_response.get('Blocks', []) if b['BlockType'] == 'KEY_VALUE_SET']),
                    'text_length': len(raw_text) if raw_text else 0
                },
                'directory_structure': 'v2_documentid_integrated',
                'structure_version': '2025-07-04-fixed',
                'documentid_manager_integration': True
            }
            
            processing_info_key = f"{metadata_base}/processing_info.json"
            self.s3.put_object(
                Bucket=self.output_bucket,
                Key=processing_info_key,
                Body=json.dumps(processing_info, indent=2, default=str),
                ContentType='application/json'
            )
            files_created.append('metadata/processing_info.json')
            
            # 6. Update DocumentIDManager with processing status
            try:
                self.doc_id_manager.update_document_status(doc_id, 'text_extraction_complete')
                self.doc_id_manager.update_system_id(doc_id, 'textract', doc_hash, 'complete')
                logger.info(f"Updated DocumentIDManager for doc_id: {doc_id}")
            except Exception as e:
                logger.warning(f"Could not update DocumentIDManager: {str(e)}")
            
            logger.info(f"Saved {len(files_created)} files for doc_id: {doc_id} in new structure")
            return processing_info
            
        except Exception as e:
            logger.error(f"Error saving structured output: {str(e)}")
            raise

    def send_to_next_stage(self, doc_hash: str, job_metadata: Dict, processing_metadata: Dict):
        """Send message to next stage queue for chunking with proper doc_id"""
        try:
            if not self.next_stage_queue_url:
                logger.info("No next stage queue configured, skipping")
                return
            
            # Get proper doc_id using DocumentIDManager
            doc_id = self.get_or_create_doc_id(job_metadata)
            
            # New message format for updated text chunker
            message = {
                'doc_id': doc_id,
                'doc_hash': doc_hash,  # Keep for compatibility
                'stage': 'text_ready',
                'full_text_location': {
                    'bucket': self.output_bucket,
                    'key': f"{doc_id}/{doc_id}_full_text.txt"
                },
                'document_structure_location': {
                    'bucket': self.output_bucket,
                    'key': f"{doc_id}/metadata/textract_response.json"
                },
                'metadata_base_path': f"{doc_id}/metadata/",
                'source_document': {
                    'bucket': job_metadata['source_bucket'],
                    'key': job_metadata['source_key']
                },
                'processing_metadata': processing_metadata,
                'timestamp': datetime.utcnow().isoformat(),
                'structure_version': '2025-07-04-fixed',
                'documentid_manager_integration': True
            }
            
            self.sqs.send_message(
                QueueUrl=self.next_stage_queue_url,
                MessageBody=json.dumps(message, default=str)
            )
            
            logger.info(f"Sent new format message to next stage queue for doc_id: {doc_id} (doc_hash: {doc_hash})")
            
        except Exception as e:
            logger.error(f"Error sending to next stage: {str(e)}")
            # Don't raise - this shouldn't fail the main processing

    # ... (rest of the methods remain the same as before)
    # Including: extract_raw_text, extract_layout_csv, extract_key_value_csv, 
    # extract_tables_csv, create_document_structure, etc.
