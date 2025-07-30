#!/usr/bin/env python3
"""
Deploy Source Document Events Stack
Deploys the SNS/SQS infrastructure for source document events
"""

import os
import sys
import subprocess
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main deployment function"""
    logger.info("🚀 Source Document Events Stack Deployment")
    logger.info("==================================================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("")
    
    # Change to CDK directory
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cdk"))
    
    # Deploy the stack
    logger.info("🚀 Deploying Source Document Events Stack")
    logger.info("==================================================")
    
    try:
        # Run CDK deploy
        result = subprocess.run(
            ["cdk", "deploy", "solve-global-kr-rag-source-document-events", "--require-approval", "never"],
            check=True,
            capture_output=True,
            text=True
        )
        
        logger.info(result.stdout)
        if result.stderr:
            logger.warning(result.stderr)
        
        logger.info("✅ Source Document Events Stack deployment complete!")
        
        return 0
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Deployment failed: {e}")
        logger.error(e.stdout)
        logger.error(e.stderr)
        return 1
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
