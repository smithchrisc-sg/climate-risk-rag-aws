#!/usr/bin/env python3
"""
Simple cleanup service test to check functionality
"""

import boto3
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_cleanup():
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    payload = {
        "cleanup_scope": "test",
        "dry_run": True
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        logger.info("=== CLEANUP SERVICE RESPONSE ===")
        logger.info(json.dumps(result, indent=2))
        
        # Check what's working
        if 'results' in result and 'databases' in result['results']:
            databases = result['results']['databases']
            
            logger.info("\\n=== COMPONENT STATUS ===")
            for db_name, db_result in databases.items():
                status = "✅ WORKING" if db_result.get('success') else "❌ FAILED"
                logger.info(f"{db_name.upper()}: {status}")
                
                if not db_result.get('success') and 'errors' in db_result:
                    for error in db_result['errors']:
                        logger.info(f"  Error: {error}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error testing cleanup service: {e}")
        return None

if __name__ == "__main__":
    test_cleanup()
