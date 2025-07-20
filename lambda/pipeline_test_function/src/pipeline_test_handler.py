#!/usr/bin/env python3
"""
Pipeline Test Lambda Function - Modernized
Runs parameterized pipeline tests from within the VPC with database access
Uses gold standard DatabaseManager and DocumentIDManager patterns
"""

import json
import boto3
import sqlite3
import os
import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
import re

# Import from Lambda layers using gold standard pattern
try:
    from utils.DatabaseManager import DatabaseManager
    from utils.DocumentIDManager import DocumentIDManager
    logger = logging.getLogger()
    logger.info("✅ Successfully imported DatabaseManager and DocumentIDManager from gold standard layer")
except ImportError as e:
    logger = logging.getLogger()
    logger.error(f"❌ Failed to import from gold standard layer: {str(e)}")
    raise ImportError("Required modules not available in layer")

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class PipelineTestLambda:
    """
    Modernized Lambda-based pipeline test manager using gold standard patterns
    """
    
    def __init__(self):
        # AWS clients
        self.s3_client = boto3.client('s3')
        self.lambda_client = boto3.client('lambda')
        
        # Environment configuration
        self.source_bucket = os.environ.get('SOURCE_DOCUMENTS_BUCKET', 'solve-global-kr-dl-source-documents-861276078413-us-east-1')
        
        # Initialize DatabaseManager using gold standard pattern
        try:
            self.db_manager = DatabaseManager()
            logger.info("✅ DatabaseManager initialized successfully using gold standard pattern")
        except Exception as e:
            logger.error(f"❌ FATAL ERROR: DatabaseManager initialization failed: {str(e)}")
            logger.error("Database connectivity is required for pipeline operation")
            raise RuntimeError(f"Database connectivity failure: {str(e)}")
        
        # Initialize DocumentIDManager using gold standard pattern
        try:
            # DocumentIDManager will use the same environment variables as DatabaseManager
            self.doc_id_manager = DocumentIDManager()
            logger.info("✅ DocumentIDManager initialized successfully using gold standard pattern")
        except Exception as e:
            logger.error(f"❌ FATAL ERROR: DocumentIDManager initialization failed: {str(e)}")
            logger.error("DocumentIDManager is required for pipeline operation")
            raise RuntimeError(f"DocumentIDManager initialization failure: {str(e)}")
    
    def download_sqlite_db(self):
        """Download SQLite database from S3 to Lambda temp storage"""
        try:
            sqlite_s3_key = os.environ.get('SQLITE_S3_KEY', 'database/corpus_document_ids.db')
            sqlite_s3_bucket = os.environ.get('SQLITE_S3_BUCKET', 'solve-global-kr-cache-861276078413-us-east-1')
            
            logger.info(f"Downloading SQLite database from s3://{sqlite_s3_bucket}/{sqlite_s3_key}")
            
            self.s3_client.download_file(
                sqlite_s3_bucket,
                sqlite_s3_key,
                self.sqlite_db_path
            )
            
            logger.info(f"SQLite database downloaded to {self.sqlite_db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download SQLite database: {e}")
            return False
    
    def get_source_url_from_sqlite(self, doc_id_from_filename: str) -> Optional[str]:
        """Get source URL from SQLite database"""
        try:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            
            # Try exact match first
            cursor.execute("SELECT source_url FROM document_ids WHERE doc_id = ?", (doc_id_from_filename,))
            result = cursor.fetchone()
            
            if result:
                conn.close()
                return result[0]
            
            # Try partial match
            cursor.execute("SELECT source_url FROM document_ids WHERE doc_id LIKE ?", (f"%{doc_id_from_filename}%",))
            result = cursor.fetchone()
            
            conn.close()
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Error querying SQLite database: {e}")
            return None
    
    def create_test_document(self, source_url: str, doc_id_from_filename: str) -> Optional[str]:
        """
        Create a test document using gold standard DocumentIDManager
        
        Args:
            source_url: Source URL of the document
            doc_id_from_filename: Document ID extracted from filename
            
        Returns:
            Proper document ID from DocumentIDManager or None if failed
        """
        try:
            logger.info(f"Creating test document for URL: {source_url}")
            
            if not source_url:
                logger.error("No source URL provided")
                return None
            
            # Use DocumentIDManager to get or create proper document ID
            try:
                # Try to get existing document ID by URL
                existing_doc_id = self.doc_id_manager.get_document_id_by_url(source_url)
                
                if existing_doc_id:
                    logger.info(f"Found existing document ID: {existing_doc_id}")
                    return existing_doc_id
                
                # Create new document using DocumentIDManager
                logger.info(f"Creating new document for URL: {source_url}")
                
                # Use DocumentIDManager's create_document method
                proper_doc_id = self.doc_id_manager.create_document(
                    url=source_url,
                    original_filename=f"{doc_id_from_filename}.pdf",  # Assume PDF for test
                    status='pending'
                )
                
                if proper_doc_id:
                    logger.info(f"✅ Successfully created document {proper_doc_id} using DocumentIDManager")
                    return proper_doc_id
                else:
                    logger.error("❌ DocumentIDManager returned None for document creation")
                    return None
                    
            except Exception as e:
                import traceback
                logger.error(f"Error creating document with DocumentIDManager: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise
                
        except Exception as e:
            import traceback
            logger.error(f"Error creating test document: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def invoke_lambda_function(self, function_name: str, payload: Dict) -> Dict:
        """Invoke a Lambda function and return the response"""
        try:
            logger.info(f"Invoking Lambda function: {function_name}")
            
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            response_payload = json.loads(response['Payload'].read())
            
            if response.get('StatusCode') == 200:
                logger.info(f"✅ Successfully invoked {function_name}")
                return {
                    'success': True,
                    'response': response_payload,
                    'status_code': response['StatusCode']
                }
            else:
                logger.error(f"❌ Lambda function {function_name} returned status code: {response.get('StatusCode')}")
                return {
                    'success': False,
                    'response': response_payload,
                    'status_code': response.get('StatusCode')
                }
                
        except Exception as e:
            logger.error(f"Error invoking Lambda function {function_name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'status_code': None
            }
    
    def run_pipeline_test(self, test_config: Dict) -> Dict:
        """
        Run a complete pipeline test using gold standard patterns
        
        Args:
            test_config: Test configuration dictionary
            
        Returns:
            Test results dictionary
        """
        try:
            test_name = test_config.get('test_name', 'unnamed_test')
            doc_id_from_filename = test_config.get('doc_id_from_filename')
            target_functions = test_config.get('target_functions', [])
            
            logger.info(f"🧪 Starting pipeline test: {test_name}")
            logger.info(f"Document ID from filename: {doc_id_from_filename}")
            logger.info(f"Target functions: {target_functions}")
            
            results = {
                'test_name': test_name,
                'doc_id_from_filename': doc_id_from_filename,
                'timestamp': datetime.now().isoformat(),
                'steps': [],
                'success': False,
                'error': None
            }
            
            # Step 1: Get source URL from SQLite (if available)
            source_url = None
            if hasattr(self, 'sqlite_db_path') and os.path.exists(self.sqlite_db_path):
                source_url = self.get_source_url_from_sqlite(doc_id_from_filename)
                results['steps'].append({
                    'step': 'get_source_url',
                    'success': source_url is not None,
                    'source_url': source_url
                })
            
            # Step 2: Create test document using DocumentIDManager
            if source_url:
                proper_doc_id = self.create_test_document(source_url, doc_id_from_filename)
                results['steps'].append({
                    'step': 'create_document',
                    'success': proper_doc_id is not None,
                    'proper_doc_id': proper_doc_id
                })
                
                if not proper_doc_id:
                    results['error'] = "Failed to create test document"
                    return results
            else:
                results['error'] = "No source URL found for document"
                return results
            
            # Step 3: Invoke target Lambda functions
            function_results = []
            for function_name in target_functions:
                payload = {
                    'doc_id': proper_doc_id,
                    'test_mode': True,
                    'source_url': source_url
                }
                
                function_result = self.invoke_lambda_function(function_name, payload)
                function_results.append({
                    'function_name': function_name,
                    'result': function_result
                })
            
            results['steps'].append({
                'step': 'invoke_functions',
                'function_results': function_results
            })
            
            # Determine overall success
            all_functions_succeeded = all(
                result['result'].get('success', False) 
                for result in function_results
            )
            
            results['success'] = all_functions_succeeded
            
            if results['success']:
                logger.info(f"✅ Pipeline test {test_name} completed successfully")
            else:
                logger.warning(f"⚠️ Pipeline test {test_name} completed with some failures")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Pipeline test failed: {str(e)}")
            import traceback
            return {
                'test_name': test_name,
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc(),
                'timestamp': datetime.now().isoformat()
            }

def lambda_handler(event, context):
    """
    Main Lambda handler using gold standard patterns
    """
    try:
        logger.info("🚀 Pipeline Test Lambda starting with gold standard patterns")
        logger.info(f"Event: {json.dumps(event, default=str)}")
        
        # Initialize pipeline test manager
        pipeline_test = PipelineTestLambda()
        
        # Get action from event
        action = event.get('action', 'test')
        
        if action == 'test':
            # Run pipeline test
            test_config = event.get('test_config', {})
            
            # Download SQLite database if needed
            if event.get('download_sqlite', True):
                pipeline_test.sqlite_db_path = '/tmp/corpus_document_ids.db'
                sqlite_downloaded = pipeline_test.download_sqlite_db()
                if not sqlite_downloaded:
                    logger.warning("⚠️ SQLite database download failed, proceeding without it")
            
            # Run the test
            results = pipeline_test.run_pipeline_test(test_config)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'completed',
                    'results': results
                })
            }
            
        elif action == 'health_check':
            # Health check using gold standard components
            try:
                # Test DatabaseManager
                with pipeline_test.db_manager.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        db_healthy = cursor.fetchone()[0] == 1
                
                # Test DocumentIDManager
                stats = pipeline_test.doc_id_manager.get_processing_statistics()
                doc_manager_healthy = isinstance(stats, dict)
                
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'status': 'healthy',
                        'database_manager': db_healthy,
                        'document_id_manager': doc_manager_healthy,
                        'processing_stats': stats,
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
                    'error': f'Unknown action: {action}'
                })
            }
        
    except Exception as e:
        logger.error(f"Pipeline test Lambda failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            })
        }
