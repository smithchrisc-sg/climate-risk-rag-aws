#!/usr/bin/env python3
"""
Test Actual Cleanup with dry_run: false
Check what happens when we actually try to run cleanup
"""

import boto3
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Test actual cleanup with dry_run: false"""
    logger.info("🧹 Testing Actual Cleanup (dry_run: false)")
    logger.info("==========================================")
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Test 1: Simple cleanup with dry_run: false
    logger.info("Test 1: Simple cleanup with dry_run: false")
    test_simple_cleanup(lambda_client)
    
    # Test 2: Cleanup with minimal scope and dry_run: false
    logger.info("\nTest 2: Cleanup with minimal scope and dry_run: false")
    test_minimal_scope_cleanup(lambda_client)
    
    # Test 3: Check what the cleanup service expects
    logger.info("\nTest 3: Check cleanup service requirements")
    test_cleanup_requirements(lambda_client)

def test_simple_cleanup(lambda_client):
    """Test simple cleanup with dry_run: false"""
    
    payload = {
        'dry_run': False
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        logger.info(f"Simple cleanup result: {json.dumps(result, indent=2)}")
        
        if result.get('statusCode') == 200:
            body = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
            if body.get('success'):
                logger.info("✅ Cleanup executed successfully")
            else:
                logger.info(f"⚠️ Cleanup blocked: {body.get('error', 'Unknown reason')}")
        else:
            logger.warning(f"❌ Cleanup failed: {result}")
            
    except Exception as e:
        logger.error(f"❌ Simple cleanup test failed: {e}")

def test_minimal_scope_cleanup(lambda_client):
    """Test cleanup with minimal scope"""
    
    payload = {
        'dry_run': False,
        'cleanup_scope': {
            'databases': {
                'postgresql': {
                    'enabled': True,
                    'tables': ['documents'],
                    'conditions': {
                        'where_clause': "filename LIKE '%test%' AND created_at < NOW() - INTERVAL '1 hour'",
                        'limit': 5
                    }
                }
            }
        }
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        logger.info(f"Minimal scope cleanup result: {json.dumps(result, indent=2)}")
        
        if result.get('statusCode') == 200:
            body = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
            if body.get('success'):
                logger.info("✅ Minimal scope cleanup executed")
            else:
                logger.info(f"⚠️ Cleanup blocked: {body.get('error', 'Unknown reason')}")
        else:
            logger.warning(f"❌ Minimal scope cleanup failed: {result}")
            
    except Exception as e:
        logger.error(f"❌ Minimal scope cleanup test failed: {e}")

def test_cleanup_requirements(lambda_client):
    """Test what the cleanup service actually requires"""
    
    # Try with explicit confirmation
    payload = {
        'dry_run': False,
        'cleanup_scope': {
            'databases': {
                'postgresql': {
                    'enabled': True,
                    'tables': ['documents'],
                    'conditions': {
                        'where_clause': "filename LIKE '%test%'",
                        'limit': 1
                    }
                }
            }
        },
        'confirmation': 'I confirm this cleanup operation',
        'safety_override': True
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        logger.info(f"Cleanup with confirmation result: {json.dumps(result, indent=2)}")
        
        if result.get('statusCode') == 200:
            body = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
            if body.get('success'):
                logger.info("✅ Cleanup with confirmation executed")
                
                # Check what was actually cleaned
                if 'databases' in body and 'postgresql' in body['databases']:
                    pg_result = body['databases']['postgresql']
                    records_deleted = pg_result.get('records_deleted', 0)
                    logger.info(f"🗑️ Records deleted: {records_deleted}")
                    
            else:
                logger.info(f"⚠️ Cleanup still blocked: {body.get('error', 'Unknown reason')}")
                
                # Show what validations are failing
                if 'validation' in str(body).lower():
                    logger.info("ℹ️ This appears to be a validation issue")
                if 'confirmation' in str(body).lower():
                    logger.info("ℹ️ This appears to be a confirmation issue")
                    
        else:
            logger.warning(f"❌ Cleanup with confirmation failed: {result}")
            
    except Exception as e:
        logger.error(f"❌ Cleanup requirements test failed: {e}")

if __name__ == "__main__":
    main()
