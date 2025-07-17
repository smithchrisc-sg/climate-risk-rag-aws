#!/usr/bin/env python3
"""
Update Text Chunker Pipeline Lambda Layers
Fixes the Lambda layer configuration for the text-chunker-pipeline function
"""

import boto3
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to update Lambda layers"""
    logger.info("🔧 Updating Text Chunker Pipeline Lambda Layers")
    logger.info("==================================================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Function name
    function_name = 'text-chunker-pipeline'
    
    try:
        # Get current function configuration
        logger.info(f"Getting current configuration for {function_name}...")
        response = lambda_client.get_function(FunctionName=function_name)
        current_config = response['Configuration']
        
        # Get current layers
        current_layers = current_config.get('Layers', [])
        logger.info(f"Current layers: {current_layers}")
        
        # Define the layers we want to use
        # Use the same layers as the pipeline test function
        desired_layers = [
            'arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities:2',
            'arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies:2'
        ]
        
        logger.info(f"Updating layers for {function_name}...")
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Layers=desired_layers
        )
        
        logger.info(f"✅ Successfully updated layers for {function_name}")
        logger.info(f"New layers: {desired_layers}")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error updating Lambda layers: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
