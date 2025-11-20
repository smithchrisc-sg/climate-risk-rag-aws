#!/usr/bin/env python3
"""
Pre-Test Cleanup Service Invoker
Invokes the cleanup-service Lambda to clear system state before testing
Uses the same boto3 configuration pattern as invoke_pipeline_test.py
"""

import boto3
from botocore.config import Config
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PreTestCleanupInvoker:
    """Client for invoking the cleanup service Lambda function"""
    
    def __init__(self):
        # Use same boto3 configuration as working invoke_pipeline_test.py
        self.lambda_client = boto3.client('lambda', region_name='us-east-1', 
                                         config=Config(connect_timeout=5, read_timeout=65))
        self.lambda_function_name = 'cleanup-service'
    
    def create_cleanup_payload(self, scope: str = 'full', dry_run: bool = False) -> Dict[str, Any]:
        """
        Create cleanup payload based on scope
        
        Args:
            scope: 'full', 'databases', 's3', or 'minimal'
            dry_run: If True, only report what would be cleaned
            
        Returns:
            Dict containing cleanup configuration
        """
        base_payload = {
            "safety_checks": {
                "require_confirmation": False,
                "dry_run": dry_run,
                "max_documents_to_delete": 10000
            }
        }
        
        if scope == 'full':
            base_payload["cleanup_scope"] = {
                "databases": {
                    "postgresql": {
                        "enabled": True,
                        "tables": [
                            "document_processing_status",
                            "nlp_processing_status", 
                            "vector_processing_status",
                            "keyword_processing_status",
                            "kg_processing_status"
                        ],
                        "document_ids": []
                    },
                    "opensearch": {
                        "enabled": True,
                        "collections": [
                            "climate-risk-vectorsearch",
                            "climate-risk-keyword-index"
                        ],
                        "document_ids": []
                    },
                    "neptune": {
                        "enabled": True,
                        "clear_all_triples": True,
                        "document_ids": []
                    }
                },
                "s3_data_lake": {
                    "enabled": True,
                    "buckets": [
                        "solve-global-kr-dl-source-documents-*",
                        "solve-global-kr-dl-text-*",
                        "solve-global-kr-dl-chunks-*",
                        "solve-global-kr-dl-embeddings-*",
                        "solve-global-kr-dl-keywords-*",
                        "solve-global-kr-dl-nlp-*",
                        "solve-global-kr-dl-neptune-ttl-*"
                    ],
                    "document_ids": [],
                    "preserve_structure": True
                }
            }
        elif scope == 'databases':
            base_payload["cleanup_scope"] = {
                "databases": {
                    "postgresql": {
                        "enabled": True,
                        "tables": [
                            "document_processing_status",
                            "nlp_processing_status",
                            "vector_processing_status",
                            "keyword_processing_status",
                            "kg_processing_status"
                        ],
                        "document_ids": []
                    },
                    "opensearch": {
                        "enabled": True,
                        "collections": [
                            "climate-risk-vectorsearch",
                            "climate-risk-keyword-index"
                        ],
                        "document_ids": []
                    },
                    "neptune": {
                        "enabled": True,
                        "clear_all_triples": True,
                        "document_ids": []
                    }
                },
                "s3_data_lake": {
                    "enabled": False
                }
            }
        elif scope == 's3':
            base_payload["cleanup_scope"] = {
                "databases": {
                    "postgresql": {"enabled": False},
                    "opensearch": {"enabled": False},
                    "neptune": {"enabled": False}
                },
                "s3_data_lake": {
                    "enabled": True,
                    "buckets": [
                        "solve-global-kr-dl-source-documents-*",
                        "solve-global-kr-dl-text-*",
                        "solve-global-kr-dl-chunks-*",
                        "solve-global-kr-dl-embeddings-*",
                        "solve-global-kr-dl-keywords-*",
                        "solve-global-kr-dl-nlp-*",
                        "solve-global-kr-dl-neptune-ttl-*"
                    ],
                    "document_ids": [],
                    "preserve_structure": True
                }
            }
        elif scope == 'minimal':
            base_payload["cleanup_scope"] = {
                "databases": {
                    "postgresql": {
                        "enabled": True,
                        "tables": ["document_processing_status"],
                        "document_ids": []
                    },
                    "opensearch": {"enabled": False},
                    "neptune": {"enabled": False}
                },
                "s3_data_lake": {"enabled": False}
            }
        
        return base_payload
    
    def invoke_cleanup(self, scope: str = 'full', dry_run: bool = False) -> Dict[str, Any]:
        """
        Invoke cleanup service Lambda
        
        Args:
            scope: Cleanup scope ('full', 'databases', 's3', 'minimal')
            dry_run: If True, only report what would be cleaned
            
        Returns:
            Dict containing cleanup results
        """
        try:
            logger.info(f"🧹 Invoking cleanup service: {self.lambda_function_name}")
            logger.info(f"📋 Scope: {scope}")
            logger.info(f"🔍 Dry run: {dry_run}")
            
            # Create cleanup payload
            cleanup_payload = self.create_cleanup_payload(scope, dry_run)
            
            logger.info("📤 Sending cleanup request...")
            
            # Invoke the Lambda function (using same pattern as invoke_pipeline_test.py)
            response = self.lambda_client.invoke(
                FunctionName=self.lambda_function_name,
                InvocationType='RequestResponse',  # Synchronous
                Payload=json.dumps(cleanup_payload, default=str)  # Handle datetime serialization
            )
            
            # Parse the response (using same pattern as invoke_pipeline_test.py)
            status_code = response['StatusCode']
            payload = json.loads(response['Payload'].read())
            
            if status_code == 200:
                logger.info("✅ Lambda invocation successful")
                
                # Check cleanup results
                if payload.get('success', False):
                    logger.info("✅ Cleanup completed successfully")
                    
                    # Log summary
                    results = payload.get('results', {})
                    summary = results.get('summary', {})
                    
                    logger.info("📊 Cleanup Summary:")
                    logger.info(f"  Total operations: {summary.get('total_operations', 0)}")
                    logger.info(f"  Successful: {summary.get('successful_operations', 0)}")
                    logger.info(f"  Failed: {summary.get('failed_operations', 0)}")
                    
                    # Log database results
                    db_results = results.get('databases', {})
                    if db_results:
                        logger.info("🗄️ Database Results:")
                        for db_type, db_result in db_results.items():
                            if db_result.get('success'):
                                logger.info(f"  ✅ {db_type}: Success")
                            else:
                                logger.info(f"  ❌ {db_type}: Failed")
                                for error in db_result.get('errors', []):
                                    logger.warning(f"    - {error}")
                    
                    # Log S3 results
                    s3_results = results.get('s3_data_lake', {})
                    if s3_results and s3_results.get('enabled', False):
                        if s3_results.get('success'):
                            logger.info(f"✅ S3: {s3_results.get('total_objects_deleted', 0)} objects deleted")
                        else:
                            logger.info("❌ S3: Failed")
                            for error in s3_results.get('errors', []):
                                logger.warning(f"    - {error}")
                    
                    return payload
                else:
                    logger.error("❌ Cleanup failed")
                    error_msg = payload.get('error', 'Unknown error')
                    logger.error(f"Error: {error_msg}")
                    return payload
            else:
                logger.error(f"❌ Lambda invocation failed with status code: {status_code}")
                logger.error(f"Response: {payload}")
                return {'success': False, 'error': f'Lambda invocation failed: {status_code}'}
                
        except Exception as e:
            logger.error(f"❌ Failed to invoke cleanup service: {str(e)}")
            return {'success': False, 'error': str(e)}

def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(description='Invoke pre-test cleanup service')
    parser.add_argument('--scope', 
                       choices=['full', 'databases', 's3', 'minimal'], 
                       default='full',
                       help='Cleanup scope (default: full)')
    parser.add_argument('--dry-run', 
                       action='store_true',
                       help='Perform dry run (report what would be cleaned)')
    parser.add_argument('--force', 
                       action='store_true',
                       help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    # Show what will be cleaned
    logger.info("🧹 Pre-Test Cleanup Service")
    logger.info("=" * 50)
    logger.info(f"Scope: {args.scope}")
    logger.info(f"Dry run: {args.dry_run}")
    
    if not args.force and not args.dry_run:
        logger.warning("⚠️  This will clean system data!")
        logger.warning("Use --dry-run to see what would be cleaned first")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            logger.info("Cleanup cancelled")
            return 1
    
    # Create invoker and run cleanup
    invoker = PreTestCleanupInvoker()
    result = invoker.invoke_cleanup(scope=args.scope, dry_run=args.dry_run)
    
    if result.get('success', False):
        logger.info("🎉 Cleanup completed successfully!")
        return 0
    else:
        logger.error("💥 Cleanup failed!")
        return 1

if __name__ == "__main__":
    exit(main())
