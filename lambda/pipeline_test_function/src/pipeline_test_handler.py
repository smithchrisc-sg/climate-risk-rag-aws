#!/usr/bin/env python3
"""
Pipeline Test Lambda Function - Restored to July 16th Requirements
Simple document copying workflow that simulates document discovery subsystem
NO SQLite operations - everything supplied by invoke_pipeline_test.py
"""

import json
import boto3
import logging
from datetime import datetime
from typing import Dict, List, Any

# Import DocumentIDManager from gold standard layer
try:
    from utils.DocumentIDManager import DocumentIDManager
    logger = logging.getLogger()
    logger.info("✅ Successfully imported DocumentIDManager from gold standard layer")
except ImportError as e:
    logger = logging.getLogger()
    logger.error(f"❌ Failed to import DocumentIDManager from layer: {str(e)}")
    raise ImportError("DocumentIDManager not available in layer")

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class PipelineTestLambda:
    """
    Simple pipeline test manager - restored to original July 16th requirements
    Receives legacy-doc-id/source-url pairs and copies documents to trigger pipeline
    """
    
    def __init__(self):
        # AWS clients
        self.s3_client = boto3.client('s3')
        
        # S3 bucket configuration
        self.source_documents_bucket = 'solve-global-kr-documents-861276078413-us-east-1'
        self.target_documents_bucket = 'solve-global-kr-dl-source-documents-861276078413-us-east-1'
        
        # Initialize DocumentIDManager from gold standard layer
        try:
            self.doc_id_manager = DocumentIDManager()
            logger.info("✅ DocumentIDManager initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize DocumentIDManager: {str(e)}")
            raise
        
        logger.info("✅ Pipeline Test Lambda initialized with simplified logic")
        logger.info(f"Source bucket: {self.source_documents_bucket}")
        logger.info(f"Target bucket: {self.target_documents_bucket}")
    
    def copy_document(self, legacy_doc_id: str, new_doc_id: str) -> Dict[str, Any]:
        """
        Copy document from source bucket to target bucket with new ID
        
        Args:
            legacy_doc_id: Original document ID (filename without .pdf)
            new_doc_id: New document ID from DocumentIDManager
            
        Returns:
            Dict with copy operation results
        """
        try:
            source_key = f"documents/{legacy_doc_id}.pdf"
            target_key = f"data-lake/{new_doc_id}.pdf"
            
            logger.info(f"Copying {source_key} → {target_key}")
            
            # Copy document
            copy_source = {
                'Bucket': self.source_documents_bucket,
                'Key': source_key
            }
            
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.target_documents_bucket,
                Key=target_key
            )
            
            logger.info(f"✅ Successfully copied document: {legacy_doc_id} → {new_doc_id}")
            
            return {
                'success': True,
                'legacy_doc_id': legacy_doc_id,
                'new_doc_id': new_doc_id,
                'source_key': source_key,
                'target_key': target_key,
                'copied_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to copy document {legacy_doc_id}: {str(e)}")
            return {
                'success': False,
                'legacy_doc_id': legacy_doc_id,
                'new_doc_id': new_doc_id,
                'error': str(e)
            }
    
    def process_document_pairs(self, document_pairs: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Process list of legacy-doc-id/source-url pairs
        
        Args:
            document_pairs: List of {'legacy_doc_id': str, 'source_url': str}
            
        Returns:
            Dict with processing results
        """
        try:
            logger.info(f"Processing {len(document_pairs)} document pairs")
            
            results = []
            successful_copies = 0
            failed_copies = 0
            
            for pair in document_pairs:
                legacy_doc_id = pair.get('legacy_doc_id')
                source_url = pair.get('source_url')
                
                if not legacy_doc_id or not source_url:
                    logger.error(f"Invalid document pair: {pair}")
                    results.append({
                        'success': False,
                        'legacy_doc_id': legacy_doc_id,
                        'error': 'Missing legacy_doc_id or source_url'
                    })
                    failed_copies += 1
                    continue
                
                try:
                    # Download document content first to pass to DocumentIDManager
                    logger.info(f"Downloading document content for URL: {source_url}")
                    source_key = f"documents/{legacy_doc_id}.pdf"
                    
                    # Get document content from S3
                    response = self.s3_client.get_object(
                        Bucket=self.source_documents_bucket,
                        Key=source_key
                    )
                    content_bytes = response['Body'].read()
                    logger.info(f"Downloaded {len(content_bytes)} bytes for {legacy_doc_id}")
                    
                    # Get new document ID from DocumentIDManager with content
                    logger.info(f"Getting new doc ID for URL: {source_url}")
                    new_doc_id = self.doc_id_manager.get_or_create_id(source_url, content_bytes)
                    logger.info(f"Got new doc ID: {new_doc_id}")
                    
                    # Copy document using existing method
                    copy_result = self.copy_document(legacy_doc_id, new_doc_id)
                    copy_result['source_url'] = source_url
                    
                    results.append(copy_result)
                    
                    if copy_result['success']:
                        successful_copies += 1
                    else:
                        failed_copies += 1
                        
                except Exception as e:
                    logger.error(f"❌ Error processing document pair {legacy_doc_id}: {str(e)}")
                    results.append({
                        'success': False,
                        'legacy_doc_id': legacy_doc_id,
                        'source_url': source_url,
                        'error': str(e)
                    })
                    failed_copies += 1
            
            return {
                'success': failed_copies == 0,
                'total_documents': len(document_pairs),
                'successful_copies': successful_copies,
                'failed_copies': failed_copies,
                'results': results,
                'processed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing document pairs: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'processed_at': datetime.now().isoformat()
            }

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main Lambda handler - restored to simple July 16th requirements
    
    Expected event format:
    {
        "action": "test",
        "document_pairs": [
            {"legacy_doc_id": "abc123", "source_url": "https://example.com/doc1.pdf"},
            {"legacy_doc_id": "def456", "source_url": "https://example.com/doc2.pdf"}
        ]
    }
    """
    try:
        logger.info("🚀 Pipeline Test Lambda starting - simplified version")
        logger.info(f"Event: {json.dumps(event, default=str)}")
        
        # Initialize pipeline test manager
        pipeline_test = PipelineTestLambda()
        
        # Get action from event
        action = event.get('action', 'test')
        
        if action == 'test':
            # Get document pairs from event
            document_pairs = event.get('document_pairs', [])
            
            if not document_pairs:
                logger.warning("No document pairs provided in event")
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'success': False,
                        'error': 'No document_pairs provided in event'
                    })
                }
            
            # Process the document pairs
            results = pipeline_test.process_document_pairs(document_pairs)
            
            # Return results
            status_code = 200 if results['success'] else 500
            
            return {
                'statusCode': status_code,
                'body': json.dumps({
                    'status': 'completed' if results['success'] else 'failed',
                    'action': action,
                    'results': results
                })
            }
            
        elif action == 'health_check':
            # Simple health check
            try:
                # Test DocumentIDManager with dummy content
                test_url = "https://example.com/test.pdf"
                test_content = b"dummy content for health check"
                test_doc_id = pipeline_test.doc_id_manager.get_or_create_id(test_url, test_content)
                doc_manager_healthy = isinstance(test_doc_id, str) and len(test_doc_id) > 0
                
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'status': 'healthy',
                        'document_id_manager': doc_manager_healthy,
                        'timestamp': datetime.now().isoformat()
                    })
                }
                
            except Exception as e:
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'status': 'unhealthy',
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
                }
        
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'status': 'failed',
                    'error': f'Unknown action: {action}. Supported actions: test, health_check'
                })
            }
        
    except Exception as e:
        logger.error(f"❌ Pipeline test Lambda failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
        }
# Updated Sun Jul 20 16:28:07 PDT 2025
# Force cold start Sun Jul 20 16:34:42 PDT 2025
