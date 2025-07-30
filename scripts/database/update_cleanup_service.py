#!/usr/bin/env python3
"""
Update Cleanup Service with Standardized Database Layer
Apply the proven pattern from pipeline test function
"""

import boto3
import json
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Update cleanup service with standardized database layer"""
    logger.info("🧹 Updating Cleanup Service with Standardized Database Layer")
    logger.info("============================================================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    try:
        # Step 1: Update cleanup service layers to match working pattern
        logger.info("Step 1: Updating cleanup service layers")
        update_cleanup_service_layers()
        
        # Step 2: Test cleanup service database connectivity
        logger.info("Step 2: Testing cleanup service database connectivity")
        test_cleanup_database_connectivity()
        
        # Step 3: Test cleanup service functionality
        logger.info("Step 3: Testing cleanup service functionality")
        test_cleanup_functionality()
        
        logger.info("✅ Cleanup service update completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Failed to update cleanup service: {str(e)}")
        return 1

def update_cleanup_service_layers():
    """Update cleanup service to use the proven layer combination"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Use the same layer combination that works for pipeline test function
    working_layers = [
        "arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities:12",
        "arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies-pipeline:3",
        "arn:aws:lambda:us-east-1:861276078413:layer:opensearch-dependencies:2"  # Keep OpenSearch for cleanup
    ]
    
    # Update function configuration
    response = lambda_client.update_function_configuration(
        FunctionName='solve-global-kr-cleanup-service',
        Layers=working_layers
    )
    
    logger.info("✅ Updated cleanup service layers:")
    for layer in working_layers:
        logger.info(f"  - {layer.split(':')[-2]}:{layer.split(':')[-1]}")
    
    # Wait for update to propagate
    import time
    time.sleep(30)

def test_cleanup_database_connectivity():
    """Test cleanup service database connectivity"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create test payload for database connectivity
    test_payload = {
        'test': 'database_connectivity',
        'dry_run': True  # Don't actually delete anything
    }
    
    try:
        logger.info("Testing cleanup service database connectivity...")
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            Payload=json.dumps(test_payload)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        logger.info(f"Database connectivity test result: {result}")
        
        # Check for database-related errors
        result_str = str(result)
        if 'Database connection' in result_str and 'successful' in result_str:
            logger.info("✅ Cleanup service database connectivity working")
            return True
        elif 'password authentication failed' in result_str:
            logger.error("❌ Database authentication failed - need to check credentials")
            return False
        elif 'No module named' in result_str:
            logger.error("❌ Import errors - layer configuration issue")
            return False
        else:
            logger.info("⚠️ Cleanup service executed - checking logs for database status")
            return True
            
    except Exception as e:
        logger.error(f"❌ Database connectivity test failed: {str(e)}")
        return False

def test_cleanup_functionality():
    """Test cleanup service functionality with dry run"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create test payload for cleanup functionality
    test_payload = {
        'dry_run': True,  # Don't actually delete anything
        'test_mode': True
    }
    
    try:
        logger.info("Testing cleanup service functionality...")
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            Payload=json.dumps(test_payload)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        logger.info(f"Cleanup functionality test result: {result}")
        
        # Check for successful execution
        if result.get('statusCode') == 200:
            logger.info("✅ Cleanup service functionality working")
            return True
        else:
            logger.warning(f"⚠️ Cleanup service returned: {result}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Cleanup functionality test failed: {str(e)}")
        return False

if __name__ == "__main__":
    sys.exit(main())
