#!/usr/bin/env python3
"""
Debug cleanup service actual cleanup vs dry-run
"""

import boto3
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_cleanup_actual():
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Test actual cleanup (not dry-run)
    cleanup_payload = {
        "cleanup_scope": {
            "databases": {
                "postgresql": {
                    "enabled": True,
                    "tables": ["document_processing_status"],
                    "document_ids": []
                }
            }
        },
        "safety_checks": {
            "require_confirmation": False,
            "dry_run": False,  # ACTUAL CLEANUP
            "max_documents_to_delete": 100
        }
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            InvocationType='RequestResponse',
            Payload=json.dumps(cleanup_payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        logger.info("=== ACTUAL CLEANUP RESULT ===")
        logger.info(json.dumps(result, indent=2))
        
        return result.get('success', False)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_cleanup_actual()
