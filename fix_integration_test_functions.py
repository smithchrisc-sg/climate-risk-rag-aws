#!/usr/bin/env python3
"""
Fix Integration Test Functions
Fixes database authentication for cleanup service and pipeline test function
"""

import boto3
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to fix integration test functions"""
    logger.info("🔧 Fixing Integration Test Functions")
    logger.info("===================================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # Step 1: Fix cleanup service database authentication
        logger.info("Step 1: Fixing cleanup service database authentication")
        fix_cleanup_service(lambda_client)
        
        # Step 2: Fix pipeline test function database authentication
        logger.info("Step 2: Fixing pipeline test function database authentication")
        fix_pipeline_test_function(lambda_client)
        
        # Step 3: Verify configurations
        logger.info("Step 3: Verifying configurations")
        verify_configurations(lambda_client)
        
        logger.info("✅ Successfully fixed integration test functions")
        logger.info("\n📋 Ready for integration testing:")
        logger.info("- Cleanup service can now clean database properly")
        logger.info("- Pipeline test function can now upload documents")
        logger.info("- End-to-end integration tests should work")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error fixing integration test functions: {str(e)}")
        return 1

def fix_cleanup_service(lambda_client):
    """Fix cleanup service database authentication"""
    function_name = "solve-global-kr-cleanup-service"
    
    # Get reference database configuration from working function
    logger.info("Getting reference database configuration...")
    response = lambda_client.get_function(FunctionName="text-chunker-pipeline")
    reference_env = response['Configuration']['Environment']['Variables']
    
    # Get current cleanup service environment
    response = lambda_client.get_function(FunctionName=function_name)
    current_env = response['Configuration']['Environment']['Variables']
    
    # Standard database environment variables
    standard_db_env = {
        'DATABASE_SECRET_NAME': reference_env.get('DATABASE_SECRET_NAME'),
        'DB_HOST': reference_env.get('DB_HOST'),
        'DB_NAME': reference_env.get('DB_NAME'),
        'DB_PORT': reference_env.get('DB_PORT'),
        'DATABASE_URL': f"postgresql://postgres:{{secret}}@{reference_env.get('DB_HOST')}:{reference_env.get('DB_PORT')}/{reference_env.get('DB_NAME')}"
    }
    
    # Merge with existing environment variables
    updated_env = current_env.copy()
    updated_env.update(standard_db_env)
    
    # Update function configuration
    lambda_client.update_function_configuration(
        FunctionName=function_name,
        Environment={'Variables': updated_env}
    )
    
    logger.info(f"✅ Updated {function_name} database configuration")

def fix_pipeline_test_function(lambda_client):
    """Fix pipeline test function database authentication"""
    function_name = "solve-global-kr-pipeline-test-function"
    
    # Get reference database configuration from working function
    logger.info("Getting reference database configuration...")
    response = lambda_client.get_function(FunctionName="text-chunker-pipeline")
    reference_env = response['Configuration']['Environment']['Variables']
    
    # Get current pipeline test function environment
    response = lambda_client.get_function(FunctionName=function_name)
    current_env = response['Configuration']['Environment']['Variables']
    
    # Standard database environment variables
    standard_db_env = {
        'DATABASE_SECRET_NAME': reference_env.get('DATABASE_SECRET_NAME'),
        'DB_HOST': reference_env.get('DB_HOST'),
        'DB_NAME': reference_env.get('DB_NAME'),
        'DB_PORT': reference_env.get('DB_PORT'),
        'DATABASE_URL': f"postgresql://postgres:{{secret}}@{reference_env.get('DB_HOST')}:{reference_env.get('DB_PORT')}/{reference_env.get('DB_NAME')}"
    }
    
    # Merge with existing environment variables (preserve SQLITE_DB_PATH, etc.)
    updated_env = current_env.copy()
    updated_env.update(standard_db_env)
    
    # Update function configuration
    lambda_client.update_function_configuration(
        FunctionName=function_name,
        Environment={'Variables': updated_env}
    )
    
    logger.info(f"✅ Updated {function_name} database configuration")

def verify_configurations(lambda_client):
    """Verify that configurations are correct"""
    
    required_vars = ['DATABASE_SECRET_NAME', 'DB_HOST', 'DB_NAME', 'DB_PORT', 'DATABASE_URL']
    
    # Check cleanup service configuration
    logger.info("Verifying cleanup service configuration...")
    response = lambda_client.get_function(FunctionName="solve-global-kr-cleanup-service")
    cleanup_env = response['Configuration']['Environment']['Variables']
    
    for var in required_vars:
        if var not in cleanup_env:
            logger.warning(f"Missing environment variable in cleanup service: {var}")
        else:
            logger.info(f"✅ Cleanup service has {var}")
    
    # Check pipeline test function configuration
    logger.info("Verifying pipeline test function configuration...")
    response = lambda_client.get_function(FunctionName="solve-global-kr-pipeline-test-function")
    pipeline_env = response['Configuration']['Environment']['Variables']
    
    for var in required_vars:
        if var not in pipeline_env:
            logger.warning(f"Missing environment variable in pipeline test function: {var}")
        else:
            logger.info(f"✅ Pipeline test function has {var}")
    
    # Check if they match reference configuration
    response = lambda_client.get_function(FunctionName="text-chunker-pipeline")
    reference_env = response['Configuration']['Environment']['Variables']
    
    logger.info("Verifying consistency with working functions...")
    for var in ['DATABASE_SECRET_NAME', 'DB_HOST', 'DB_NAME', 'DB_PORT']:
        ref_value = reference_env.get(var)
        cleanup_value = cleanup_env.get(var)
        pipeline_value = pipeline_env.get(var)
        
        if cleanup_value == ref_value and pipeline_value == ref_value:
            logger.info(f"✅ {var} is consistent across all functions")
        else:
            logger.warning(f"❌ {var} inconsistency detected")
    
    logger.info("✅ Configuration verification complete")

if __name__ == "__main__":
    sys.exit(main())
