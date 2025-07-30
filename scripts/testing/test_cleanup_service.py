#!/usr/bin/env python3
"""
Test script for the migrated cleanup service
"""

import boto3
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_cleanup_service():
    """Test the cleanup service with a dry run"""
    
    # Create Lambda client
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Test payload - dry run to avoid actually cleaning anything
    test_payload = {
        "cleanup_scope": {
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
                    "solve-global-kr-dl-text-*",
                    "solve-global-kr-dl-chunks-*"
                ],
                "document_ids": [],
                "preserve_structure": True
            }
        },
        "safety_checks": {
            "require_confirmation": False,
            "dry_run": True,
            "max_documents_to_delete": 10
        }
    }
    
    try:
        logger.info("Testing cleanup service with dry run...")
        
        # Invoke the cleanup service
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        # Parse response
        result = json.loads(response['Payload'].read())
        
        logger.info(f"Cleanup service response: {json.dumps(result, indent=2)}")
        
        if result.get('success'):
            logger.info("✅ Cleanup service test PASSED")
            return True
        else:
            logger.error(f"❌ Cleanup service test FAILED: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_cleanup_service()
    exit(0 if success else 1)
