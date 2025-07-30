#!/usr/bin/env python3
"""
Test Cleanup with Proper Confirmation Format
Use the correct safety_checks format that the validator expects
"""

import boto3
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Test cleanup with proper confirmation format"""
    logger.info("🧹 Testing Cleanup with Proper Confirmation")
    logger.info("===========================================")
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Test 1: Dry run with proper format
    logger.info("Test 1: Dry run with proper format")
    test_dry_run_proper_format(lambda_client)
    
    # Test 2: Actual cleanup with proper confirmation
    logger.info("\nTest 2: Actual cleanup with proper confirmation")
    test_actual_cleanup_proper_format(lambda_client)

def test_dry_run_proper_format(lambda_client):
    """Test dry run with proper format"""
    
    payload = {
        'dry_run': True,
        'cleanup_scope': {
            'databases': {
                'postgresql': {
                    'enabled': True,
                    'tables': ['documents'],
                    'conditions': {
                        'where_clause': "filename LIKE '%test%'",
                        'limit': 5
                    }
                }
            }
        },
        'safety_checks': {
            'confirmation_provided': True,
            'require_confirmation': False  # For dry run
        }
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        logger.info(f"Dry run result: {json.dumps(result, indent=2)}")
        
        if result.get('statusCode') == 200:
            body = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
            if body.get('success'):
                logger.info("✅ Dry run executed successfully")
                
                # Show what would be cleaned
                if 'databases' in body and 'postgresql' in body['databases']:
                    pg_result = body['databases']['postgresql']
                    logger.info(f"📊 Would clean: {pg_result}")
                    
            else:
                logger.info(f"⚠️ Dry run blocked: {body.get('error', 'Unknown reason')}")
        else:
            logger.warning(f"❌ Dry run failed: {result}")
            
    except Exception as e:
        logger.error(f"❌ Dry run test failed: {e}")

def test_actual_cleanup_proper_format(lambda_client):
    """Test actual cleanup with proper confirmation format"""
    
    payload = {
        'dry_run': False,
        'cleanup_scope': {
            'databases': {
                'postgresql': {
                    'enabled': True,
                    'tables': ['documents'],
                    'conditions': {
                        'where_clause': "filename LIKE '%test%' AND created_at < NOW() - INTERVAL '1 hour'",
                        'limit': 3  # Small limit for safety
                    }
                }
            }
        },
        'safety_checks': {
            'confirmation_provided': True,
            'require_confirmation': True,
            'max_documents_to_delete': 10
        }
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        logger.info(f"Actual cleanup result: {json.dumps(result, indent=2)}")
        
        if result.get('statusCode') == 200:
            body = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
            if body.get('success'):
                logger.info("🎉 ACTUAL CLEANUP EXECUTED SUCCESSFULLY!")
                
                # Show what was actually cleaned
                if 'databases' in body and 'postgresql' in body['databases']:
                    pg_result = body['databases']['postgresql']
                    records_deleted = pg_result.get('records_deleted', 0)
                    logger.info(f"🗑️ PostgreSQL records deleted: {records_deleted}")
                    
                if 'summary' in body:
                    summary = body['summary']
                    logger.info(f"📈 Total operations: {summary.get('total_operations', 0)}")
                    logger.info(f"📈 Successful operations: {summary.get('successful_operations', 0)}")
                    
            else:
                logger.info(f"⚠️ Cleanup blocked: {body.get('error', 'Unknown reason')}")
        else:
            logger.warning(f"❌ Cleanup failed: {result}")
            
    except Exception as e:
        logger.error(f"❌ Actual cleanup test failed: {e}")

if __name__ == "__main__":
    main()
