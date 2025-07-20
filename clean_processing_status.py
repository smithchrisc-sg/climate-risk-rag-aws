#!/usr/bin/env python3
"""
Clean Document Processing Status Table
Clean the table that tracks text extraction processing status
"""

import boto3
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Clean document processing status table"""
    logger.info("🧹 Cleaning Document Processing Status Table")
    logger.info("============================================")
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    cleanup_payload = {
        'dry_run': False,
        'cleanup_scope': {
            'databases': {
                'postgresql': {
                    'enabled': True,
                    'tables': ['document_processing_status'],
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
        logger.info(f"Document processing status cleanup result: {result}")
        
        if result.get('statusCode') == 200:
            body = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
            if body.get('success'):
                logger.info("✅ Document processing status table cleaned successfully")
                
                # Check what was cleaned
                if 'databases' in body and 'postgresql' in body['databases']:
                    pg_result = body['databases']['postgresql']
                    records_deleted = pg_result.get('records_affected', {}).get('document_processing_status', 0)
                    logger.info(f"🗑️ Records deleted: {records_deleted}")
                    
            else:
                logger.info(f"⚠️ Cleanup result: {body.get('error', 'Unknown issue')}")
        else:
            logger.warning(f"❌ Cleanup failed: {result}")
            
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")

if __name__ == "__main__":
    main()
