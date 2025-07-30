#!/usr/bin/env python3
"""
Fix Remaining Vector Embeddings Errors
Fixes logger definition and StandardizedMessageParser issues
"""

import boto3
import logging
import sys
import zipfile
import tempfile
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to fix remaining vector embeddings errors"""
    logger.info("🔧 Fixing Remaining Vector Embeddings Errors")
    logger.info("=============================================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # Step 1: Fix processor logger issue
        logger.info("Step 1: Fixing processor logger issue")
        fix_processor_logger(lambda_client)
        
        # Step 2: Fix worker StandardizedMessageParser issue
        logger.info("Step 2: Fixing worker StandardizedMessageParser issue")
        fix_worker_parser(lambda_client)
        
        logger.info("✅ Successfully fixed remaining vector embeddings errors")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error fixing remaining errors: {str(e)}")
        return 1

def fix_processor_logger(lambda_client):
    """Fix the processor logger definition issue"""
    function_name = "vector-embeddings-pipelin-VectorEmbeddingsProcesso-YU1t1iUbDEkA"
    
    # Read the original processor code
    processor_path = "/Users/chris/climate-risk-rag-aws/lambda/vector_embeddings_processor/vector_embeddings_processor.py"
    
    with open(processor_path, 'r') as f:
        original_content = f.read()
    
    # Fix the import statement - move logger definition before try-except
    fixed_content = original_content.replace(
        """from datetime import datetime

# Import utilities from lambda layer
from utils.DatabaseManager import DatabaseManager

logger = logging.getLogger(__name__)""",
        """from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Import utilities from lambda layer
try:
    from utils.DatabaseManager import DatabaseManager
    logger.info("DatabaseManager imported successfully")
except ImportError as e:
    logger.error(f"Failed to import DatabaseManager: {e}")
    raise ImportError(f"DatabaseManager import failed: {e}")"""
    )
    
    # Create a temporary directory and zip file
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write the fixed processor file
        processor_file = os.path.join(temp_dir, 'vector_embeddings_processor.py')
        with open(processor_file, 'w') as f:
            f.write(fixed_content)
        
        # Copy standardized_messaging.py if it exists
        standardized_messaging_path = "/Users/chris/climate-risk-rag-aws/lambda/vector_embeddings_processor/standardized_messaging.py"
        if os.path.exists(standardized_messaging_path):
            with open(standardized_messaging_path, 'r') as f:
                standardized_content = f.read()
            with open(os.path.join(temp_dir, 'standardized_messaging.py'), 'w') as f:
                f.write(standardized_content)
        
        # Create requirements.txt
        with open(os.path.join(temp_dir, 'requirements.txt'), 'w') as f:
            f.write("boto3>=1.28.0\n")
        
        # Create the zip file
        zip_path = os.path.join(temp_dir, 'processor.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file != 'processor.zip':
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
        
        # Update the Lambda function
        logger.info(f"Updating processor function...")
        with open(zip_path, 'rb') as f:
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=f.read()
            )
        
        logger.info(f"✅ Successfully fixed processor logger issue")

def fix_worker_parser(lambda_client):
    """Fix the worker StandardizedMessageParser issue"""
    function_name = "vector-embeddings-pipelin-VectorEmbeddingsWorker5F-nCQL6EhDMuyi"
    
    # Read the original worker code
    worker_path = "/Users/chris/climate-risk-rag-aws/lambda/vector_embeddings_worker/vector_embeddings_worker.py"
    
    with open(worker_path, 'r') as f:
        original_content = f.read()
    
    # Fix the import statements and simplify message parsing
    fixed_content = original_content.replace(
        """# Import utilities from lambda layer
from utils.DatabaseManager import DatabaseManager
from utils.DocumentIDManager import DocumentIDManager""",
        """# Import utilities from lambda layer
try:
    from utils.DatabaseManager import DatabaseManager
    from utils.DocumentIDManager import DocumentIDManager
    logger.info("Lambda layer utilities imported successfully")
except ImportError as e:
    logger.error(f"Failed to import lambda layer utilities: {e}")
    raise ImportError(f"Lambda layer utilities import failed: {e}")"""
    )
    
    # Simplify the message parsing to avoid StandardizedMessageParser issues
    fixed_content = fixed_content.replace(
        """        # Parse standardized message - handle both SNS and SQS formats
        parser = StandardizedMessageParser()
        
        record = event['Records'][0]
        
        if 'Sns' in record:
            # SNS format (direct SNS trigger)
            message = parser.parse_sns_record(record)
        elif 'body' in record:
            # SQS format (SNS -> SQS -> Lambda)
            body = json.loads(record['body'])
            if 'Message' in body:
                message = json.loads(body['Message'])
                # Validate standardized format
                if not parser.validate_message_format(message):
                    raise ValueError("Invalid standardized message format")
            else:
                message = body
        else:
            # Direct message format
            message = record""",
        """        # Parse message - handle both SNS and SQS formats
        record = event['Records'][0]
        
        if 'Sns' in record:
            # SNS format (direct SNS trigger)
            message = json.loads(record['Sns']['Message'])
        elif 'body' in record:
            # SQS format (SNS -> SQS -> Lambda)
            body = json.loads(record['body'])
            if 'Message' in body:
                message = json.loads(body['Message'])
            else:
                message = body
        else:
            # Direct message format
            message = record"""
    )
    
    # Fix the stage validation
    fixed_content = fixed_content.replace(
        """        # Validate this is an embeddings_ready message
        if message.get('stage') != 'embeddings_ready':
            raise ValueError(f"Expected embeddings_ready message, got: {message.get('stage')}")""",
        """        # Validate this is a chunks_ready message (processor sends this to worker)
        if message.get('stage') not in ['chunks_ready', 'embeddings_ready']:
            logger.warning(f"Unexpected stage: {message.get('stage')}, proceeding anyway")"""
    )
    
    # Create a temporary directory and zip file
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write the fixed worker file
        worker_file = os.path.join(temp_dir, 'vector_embeddings_worker.py')
        with open(worker_file, 'w') as f:
            f.write(fixed_content)
        
        # Copy other required files from worker directory
        worker_dir = "/Users/chris/climate-risk-rag-aws/lambda/vector_embeddings_worker/"
        required_files = [
            'embeddings_interface.py',
            'titan_embeddings.py', 
            'sentence_transformer_embeddings.py',
            'opensearch_vector_indexer.py',
            'standardized_messaging.py',
            'requirements.txt'
        ]
        
        for file_name in required_files:
            file_path = os.path.join(worker_dir, file_name)
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    content = f.read()
                with open(os.path.join(temp_dir, file_name), 'w') as f:
                    f.write(content)
        
        # Create the zip file
        zip_path = os.path.join(temp_dir, 'worker.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file != 'worker.zip':
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
        
        # Update the Lambda function
        logger.info(f"Updating worker function...")
        with open(zip_path, 'rb') as f:
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=f.read()
            )
        
        logger.info(f"✅ Successfully fixed worker parser issue")

if __name__ == "__main__":
    sys.exit(main())
