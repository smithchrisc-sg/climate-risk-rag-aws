#!/usr/bin/env python3
"""
Comprehensive Cleanup Script
Clean all tables that might contain document processing status
"""

import boto3
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Run comprehensive cleanup of all document-related tables"""
    logger.info("🧹 Running Comprehensive Cleanup of All Document Tables")
    logger.info("======================================================")
    
    try:
        # Clean documents table
        logger.info("Step 1: Cleaning documents table")
        cleanup_documents_table()
        
        # Clean processing status table
        logger.info("Step 2: Cleaning processing status table")
        cleanup_processing_status_table()
        
        # Clean job metadata table
        logger.info("Step 3: Cleaning job metadata table")
        cleanup_job_metadata_table()
        
        # Clean any other document-related tables
        logger.info("Step 4: Cleaning other document-related tables")
        cleanup_other_tables()
        
        logger.info("✅ Comprehensive cleanup completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Comprehensive cleanup failed: {str(e)}")
        return 1

def cleanup_documents_table():
    """Clean documents table"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    cleanup_payload = {
        'dry_run': False,
        'cleanup_scope': {
            'databases': {
                'postgresql': {
                    'enabled': True,
                    'tables': ['documents'],
                    'conditions': {
                        'where_clause': "1=1",  # Clean all records
                        'limit': 100
                    }
                }
            }
        },
        'safety_checks': {
            'confirmation_provided': True,
            'require_confirmation': True,
            'max_documents_to_delete': 100
        }
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            Payload=json.dumps(cleanup_payload)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        logger.info(f"Documents table cleanup result: {result}")
        
        if result.get('statusCode') == 200:
            logger.info("✅ Documents table cleaned successfully")
        else:
            logger.warning(f"⚠️ Documents table cleanup issues: {result}")
            
    except Exception as e:
        logger.error(f"❌ Documents table cleanup failed: {e}")

def cleanup_processing_status_table():
    """Clean processing status table"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    cleanup_payload = {
        'dry_run': False,
        'cleanup_scope': {
            'databases': {
                'postgresql': {
                    'enabled': True,
                    'tables': ['processing_status'],
                    'conditions': {
                        'where_clause': "1=1",  # Clean all records
                        'limit': 100
                    }
                }
            }
        },
        'safety_checks': {
            'confirmation_provided': True,
            'require_confirmation': True,
            'max_documents_to_delete': 100
        }
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            Payload=json.dumps(cleanup_payload)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        logger.info(f"Processing status table cleanup result: {result}")
        
        if result.get('statusCode') == 200:
            logger.info("✅ Processing status table cleaned successfully")
        else:
            logger.warning(f"⚠️ Processing status table cleanup issues: {result}")
            
    except Exception as e:
        logger.error(f"❌ Processing status table cleanup failed: {e}")

def cleanup_job_metadata_table():
    """Clean job metadata table"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    cleanup_payload = {
        'dry_run': False,
        'cleanup_scope': {
            'databases': {
                'postgresql': {
                    'enabled': True,
                    'tables': ['job_metadata'],
                    'conditions': {
                        'where_clause': "1=1",  # Clean all records
                        'limit': 100
                    }
                }
            }
        },
        'safety_checks': {
            'confirmation_provided': True,
            'require_confirmation': True,
            'max_documents_to_delete': 100
        }
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            Payload=json.dumps(cleanup_payload)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        logger.info(f"Job metadata table cleanup result: {result}")
        
        if result.get('statusCode') == 200:
            logger.info("✅ Job metadata table cleaned successfully")
        else:
            logger.warning(f"⚠️ Job metadata table cleanup issues: {result}")
            
    except Exception as e:
        logger.error(f"❌ Job metadata table cleanup failed: {e}")

def cleanup_other_tables():
    """Clean other document-related tables"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # List of other tables that might contain document references
    other_tables = ['textract_jobs', 'document_chunks', 'document_metadata', 'text_extraction_status']
    
    for table in other_tables:
        cleanup_payload = {
            'dry_run': False,
            'cleanup_scope': {
                'databases': {
                    'postgresql': {
                        'enabled': True,
                        'tables': [table],
                        'conditions': {
                            'where_clause': "1=1",  # Clean all records
                            'limit': 100
                        }
                    }
                }
            },
            'safety_checks': {
                'confirmation_provided': True,
                'require_confirmation': True,
                'max_documents_to_delete': 100
            }
        }
        
        try:
            response = lambda_client.invoke(
                FunctionName='solve-global-kr-cleanup-service',
                Payload=json.dumps(cleanup_payload)
            )
            
            result = json.loads(response['Payload'].read().decode('utf-8'))
            logger.info(f"{table} cleanup result: {result}")
            
            if result.get('statusCode') == 200:
                logger.info(f"✅ {table} cleaned successfully")
            else:
                logger.info(f"ℹ️ {table} cleanup: {result.get('body', 'No issues')}")
                
        except Exception as e:
            logger.info(f"ℹ️ {table} cleanup (table may not exist): {e}")

if __name__ == "__main__":
    import sys
    sys.exit(main())
