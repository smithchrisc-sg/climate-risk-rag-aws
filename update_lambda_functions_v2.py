#!/usr/bin/env python3
"""
Update Lambda Functions with New Layer Version
Updates Lambda functions to use the new climate-risk-core-utilities layer version
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
    """Main function to update Lambda functions"""
    logger.info("🔧 Updating Lambda Functions with New Layer Version")
    logger.info("==================================================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # New layer version
    new_version = 10
    new_layer_arn = f"arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities:{new_version}"
    
    # Functions to update
    functions_to_update = ['text-chunker-pipeline', 'solve-global-kr-text-chunker-phase1']
    
    try:
        for function_name in functions_to_update:
            logger.info(f"Updating {function_name} to use the new layer version...")
            
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
                    new_layers.append(new_layer_arn)
                else:
                    # Keep the same layer
                    new_layers.append(layer['Arn'])
            
            # Update the function
            lambda_client.update_function_configuration(
                FunctionName=function_name,
                Layers=new_layers
            )
            
            logger.info(f"✅ Successfully updated {function_name} to use the new layer version")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error updating Lambda functions: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
