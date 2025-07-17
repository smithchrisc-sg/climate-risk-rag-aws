#!/usr/bin/env python3
"""
Update Text Chunker Pipeline Environment Variables
Adds the DATABASE_URL environment variable to the text-chunker-pipeline function
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
    """Main function to update Lambda environment variables"""
    logger.info("🔧 Updating Text Chunker Pipeline Environment Variables")
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
        
        # Get current environment variables
        current_env = current_config.get('Environment', {}).get('Variables', {})
        logger.info(f"Current environment variables: {current_env}")
        
        # Add DATABASE_URL environment variable
        new_env = current_env.copy()
        new_env['DATABASE_URL'] = "postgresql://postgres:c0xfd_t#PBUqV(pLM-9IqM59G:>c@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require"
        
        logger.info(f"Updating environment variables for {function_name}...")
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={
                'Variables': new_env
            }
        )
        
        logger.info(f"✅ Successfully updated environment variables for {function_name}")
        logger.info(f"Added DATABASE_URL environment variable")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error updating Lambda environment variables: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
