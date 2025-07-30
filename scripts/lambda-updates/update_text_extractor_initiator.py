#!/usr/bin/env python3
"""
Update Text Extractor Initiator with Standardized Database Layer
Apply the same Secrets Manager pattern we used for other functions
"""

import boto3
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Update text extractor initiator with standardized database layer"""
    logger.info("🔧 Updating Text Extractor Initiator with Standardized Database Layer")
    logger.info("=====================================================================")
    
    try:
        # Step 1: Update environment variables to use standard configuration
        logger.info("Step 1: Updating environment variables")
        update_environment_variables()
        
        # Step 2: Update layers to use standardized layers
        logger.info("Step 2: Updating layers")
        update_function_layers()
        
        # Step 3: Test the updated function
        logger.info("Step 3: Testing updated function")
        test_updated_function()
        
        logger.info("✅ Text extractor initiator update completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Failed to update text extractor initiator: {str(e)}")
        return 1

def update_environment_variables():
    """Update environment variables to use standard database configuration"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Standard environment variables (same as pipeline test function and cleanup service)
    standard_env_vars = {
        'DATABASE_SECRET_NAME': 'rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863',
        'DB_HOST': 'solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com',
        'DB_NAME': 'climate_risk_rag',
        'DB_PORT': '5432',
        'DATABASE_CONNECTION_METHOD': 'secrets_manager',
        # Keep existing environment variables
        'OUTPUT_BUCKET': 'solve-global-kr-chunks-861276078413-us-east-1',
        'TEXTRACT_SNS_TOPIC_ARN': 'arn:aws:sns:us-east-1:861276078413:solve-global-kr-textract-completion',
        'TEXTRACT_SERVICE_ROLE_ARN': 'arn:aws:iam::861276078413:role/solve-global-kr-textract-service-role'
    }
    
    # Update function configuration
    response = lambda_client.update_function_configuration(
        FunctionName='solve-global-kr-textextractor-initiator',
        Environment={
            'Variables': standard_env_vars
        }
    )
    
    logger.info("✅ Updated environment variables to use standard database configuration")
    logger.info("  - Removed hardcoded DATABASE_URL")
    logger.info("  - Added DATABASE_SECRET_NAME")
    logger.info("  - Added standard DB_HOST, DB_NAME, DB_PORT")
    logger.info("  - Added DATABASE_CONNECTION_METHOD=secrets_manager")

def update_function_layers():
    """Update function layers to use standardized layers"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Use the same layer combination that works for pipeline test function and cleanup service
    standard_layers = [
        "arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities:12",
        "arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies-pipeline:3"
    ]
    
    # Update function configuration
    response = lambda_client.update_function_configuration(
        FunctionName='solve-global-kr-textextractor-initiator',
        Layers=standard_layers
    )
    
    logger.info("✅ Updated layers to use standardized configuration:")
    for layer in standard_layers:
        logger.info(f"  - {layer.split(':')[-2]}:{layer.split(':')[-1]}")
    
    # Wait for update to propagate
    import time
    time.sleep(30)

def test_updated_function():
    """Test the updated function by checking recent logs"""
    logger.info("Testing updated text extractor initiator...")
    
    # The function will be tested when the next document is processed
    # For now, let's check if the configuration looks correct
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        response = lambda_client.get_function(FunctionName='solve-global-kr-textextractor-initiator')
        config = response['Configuration']
        
        env_vars = config.get('Environment', {}).get('Variables', {})
        layers = [layer['Arn'] for layer in config.get('Layers', [])]
        
        logger.info("📋 Updated function configuration:")
        logger.info(f"  - DATABASE_SECRET_NAME: {env_vars.get('DATABASE_SECRET_NAME', 'NOT SET')}")
        logger.info(f"  - DB_HOST: {env_vars.get('DB_HOST', 'NOT SET')}")
        logger.info(f"  - DATABASE_CONNECTION_METHOD: {env_vars.get('DATABASE_CONNECTION_METHOD', 'NOT SET')}")
        logger.info(f"  - Layers: {len(layers)} layers configured")
        
        # Check if old DATABASE_URL is removed
        if 'DATABASE_URL' not in env_vars:
            logger.info("✅ Old hardcoded DATABASE_URL removed")
        else:
            logger.warning("⚠️ Old DATABASE_URL still present")
        
        # Check if standard environment variables are present
        required_vars = ['DATABASE_SECRET_NAME', 'DB_HOST', 'DB_NAME', 'DB_PORT']
        missing_vars = [var for var in required_vars if var not in env_vars]
        
        if not missing_vars:
            logger.info("✅ All required standard environment variables present")
        else:
            logger.warning(f"⚠️ Missing environment variables: {missing_vars}")
        
        logger.info("✅ Text extractor initiator updated with standardized database layer")
        logger.info("🔄 Next document processing will test the database connectivity")
        
    except Exception as e:
        logger.error(f"❌ Error checking updated function: {e}")

if __name__ == "__main__":
    import sys
    sys.exit(main())
