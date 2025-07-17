#!/usr/bin/env python3
"""
Update Lambda Function Configuration
Updates the text-chunker-pipeline function to use the new layer version
"""

import boto3
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to update Lambda function configuration"""
    logger.info("🔧 Updating Lambda Function Configuration")
    logger.info("==================================================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Function name
    function_name = 'text-chunker-pipeline'
    
    try:
        # Get current layer version
        logger.info("Getting current layer version...")
        response = lambda_client.list_layer_versions(
            LayerName='climate-risk-core-utilities',
            MaxItems=1
        )
        
        layer_version = response['LayerVersions'][0]['Version']
        logger.info(f"Current layer version: {layer_version}")
        
        # Update the function configuration to use the new layer version
        logger.info(f"Updating Lambda function configuration...")
        
        # Get current function configuration
        function_response = lambda_client.get_function(
            FunctionName=function_name
        )
        
        current_layers = function_response['Configuration'].get('Layers', [])
        
        # Replace the climate-risk-core-utilities layer with the new version
        new_layers = []
        for layer in current_layers:
            if 'climate-risk-core-utilities:' in layer['Arn'] and 'climate-risk-core-utilities-db:' not in layer['Arn']:
                # Replace with new version
                new_layer_arn = f"arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities:{layer_version}"
                new_layers.append(new_layer_arn)
            else:
                # Keep the same layer
                new_layers.append(layer['Arn'])
        
        # Update the function configuration
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Layers=new_layers
        )
        
        logger.info(f"✅ Successfully updated configuration for {function_name}")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error updating Lambda function configuration: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
