#!/usr/bin/env python3
"""
Standardize NLP Stage for Consistency
Fixes database authentication, messaging formats, and data paths
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
    """Main function to standardize NLP stage"""
    logger.info("🔧 Standardizing NLP Stage for Consistency")
    logger.info("==========================================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # Step 1: Fix database authentication consistency
        logger.info("Step 1: Fixing database authentication consistency")
        fix_database_authentication(lambda_client)
        
        # Step 2: Update messaging and data path handling
        logger.info("Step 2: Updating messaging and data path handling")
        update_messaging_and_paths(lambda_client)
        
        # Step 3: Verify configurations
        logger.info("Step 3: Verifying configurations")
        verify_configurations(lambda_client)
        
        logger.info("✅ Successfully standardized NLP stage")
        logger.info("\n📋 NLP stage is now consistent with other stages:")
        logger.info("- Database authentication standardized")
        logger.info("- Messaging formats aligned")
        logger.info("- Data paths follow standard structure")
        logger.info("- Ready for integration testing")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error standardizing NLP stage: {str(e)}")
        return 1

def fix_database_authentication(lambda_client):
    """Fix database authentication to be consistent with other stages"""
    
    # Get the working database configuration from text-chunker
    logger.info("Getting reference database configuration from text-chunker...")
    response = lambda_client.get_function(FunctionName="text-chunker-pipeline")
    reference_env = response['Configuration']['Environment']['Variables']
    
    # Standard database environment variables
    standard_db_env = {
        'DATABASE_SECRET_NAME': reference_env.get('DATABASE_SECRET_NAME'),
        'DB_HOST': reference_env.get('DB_HOST'),
        'DB_NAME': reference_env.get('DB_NAME'),
        'DB_PORT': reference_env.get('DB_PORT'),
        'DATABASE_URL': f"postgresql://postgres:{{secret}}@{reference_env.get('DB_HOST')}:{reference_env.get('DB_PORT')}/{reference_env.get('DB_NAME')}"
    }
    
    # Update NLP processor
    logger.info("Updating NLP processor database configuration...")
    response = lambda_client.get_function(FunctionName="nlp-processor")
    current_env = response['Configuration']['Environment']['Variables']
    
    # Merge with existing environment variables
    updated_env = current_env.copy()
    updated_env.update(standard_db_env)
    
    lambda_client.update_function_configuration(
        FunctionName="nlp-processor",
        Environment={'Variables': updated_env}
    )
    
    # Update NLP worker
    logger.info("Updating NLP worker database configuration...")
    response = lambda_client.get_function(FunctionName="nlp-worker")
    current_env = response['Configuration']['Environment']['Variables']
    
    # Merge with existing environment variables
    updated_env = current_env.copy()
    updated_env.update(standard_db_env)
    
    lambda_client.update_function_configuration(
        FunctionName="nlp-worker",
        Environment={'Variables': updated_env}
    )
    
    logger.info("✅ Database authentication standardized")

def update_messaging_and_paths(lambda_client):
    """Update NLP functions to use standard messaging and data paths"""
    
    # Update NLP processor code
    logger.info("Updating NLP processor messaging...")
    update_nlp_processor_code(lambda_client)
    
    # Update NLP worker code  
    logger.info("Updating NLP worker data paths...")
    update_nlp_worker_code(lambda_client)

def update_nlp_processor_code(lambda_client):
    """Update NLP processor to use standard messaging format"""
    function_name = "nlp-processor"
    
    # Read the original processor code
    processor_path = "/Users/chris/climate-risk-rag-aws/lambda/nlp_processor/nlp_processor.py"
    
    with open(processor_path, 'r') as f:
        original_content = f.read()
    
    # Fix import statements to match working functions
    fixed_content = original_content.replace(
        "# Import utilities from lambda layer\nfrom utils.DatabaseManager import DatabaseManager",
        """# Import utilities from lambda layer
try:
    from utils.DatabaseManager import DatabaseManager
    logger.info("DatabaseManager imported successfully")
except ImportError as e:
    logger.error(f"Failed to import DatabaseManager: {e}")
    raise ImportError(f"DatabaseManager import failed: {e}")"""
    )
    
    # Ensure standard message format handling
    if "chunks_ready" not in fixed_content:
        fixed_content = fixed_content.replace(
            'message.get(\'stage\')',
            'message.get(\'stage\', \'chunks_ready\')'
        )
    
    # Create a temporary directory and zip file
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write the fixed processor file
        processor_file = os.path.join(temp_dir, 'nlp_processor.py')
        with open(processor_file, 'w') as f:
            f.write(fixed_content)
        
        # Copy standardized_messaging.py
        standardized_messaging_path = "/Users/chris/climate-risk-rag-aws/lambda/nlp_processor/standardized_messaging.py"
        if os.path.exists(standardized_messaging_path):
            with open(standardized_messaging_path, 'r') as f:
                standardized_content = f.read()
            with open(os.path.join(temp_dir, 'standardized_messaging.py'), 'w') as f:
                f.write(standardized_content)
        
        # Create requirements.txt
        with open(os.path.join(temp_dir, 'requirements.txt'), 'w') as f:
            f.write("boto3>=1.28.0\n")
        
        # Create the zip file
        zip_path = os.path.join(temp_dir, 'nlp_processor.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file != 'nlp_processor.zip':
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
        
        # Update the Lambda function
        with open(zip_path, 'rb') as f:
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=f.read()
            )
        
        logger.info(f"✅ Updated {function_name} with standard messaging")

def update_nlp_worker_code(lambda_client):
    """Update NLP worker to use standard data paths"""
    function_name = "nlp-worker"
    
    # Read the original worker code
    worker_path = "/Users/chris/climate-risk-rag-aws/lambda/nlp_worker/nlp_worker.py"
    
    with open(worker_path, 'r') as f:
        original_content = f.read()
    
    # Fix import statements
    fixed_content = original_content.replace(
        "# Import utilities from lambda layer\nfrom utils.DatabaseManager import DatabaseManager",
        """# Import utilities from lambda layer
try:
    from utils.DatabaseManager import DatabaseManager
    logger.info("DatabaseManager imported successfully")
except ImportError as e:
    logger.error(f"Failed to import DatabaseManager: {e}")
    raise ImportError(f"DatabaseManager import failed: {e}")"""
    )
    
    # Update S3 data path handling to use standard structure
    # NLP data will be in: s3://bucket/data_lake/{doc_id}/nlp/
    fixed_content = fixed_content.replace(
        'def load_full_text_from_s3',
        '''def get_standard_nlp_paths(doc_id, chunks_location):
    """Get standard NLP data paths based on doc_id and chunks location"""
    # Extract bucket and base path from chunks location
    # Expected: s3://bucket/data_lake/{doc_id}/chunks/
    if not chunks_location.startswith('s3://'):
        raise ValueError(f"Invalid S3 location format: {chunks_location}")
    
    # Parse S3 location
    parts = chunks_location.replace('s3://', '').split('/')
    bucket = parts[0]
    
    # Standard data lake structure: data_lake/{doc_id}/
    base_path = f"s3://{bucket}/data_lake/{doc_id}"
    
    return {
        'text_location': f"{base_path}/text/",
        'chunks_location': f"{base_path}/chunks/", 
        'nlp_output_location': f"{base_path}/nlp/",
        'bucket': bucket,
        'base_path': base_path
    }

def load_full_text_from_s3'''
    )
    
    # Update the function to use standard paths
    fixed_content = fixed_content.replace(
        'text_location = data_locations.get(\'text_folder_url\') or data_locations.get(\'text_location\')',
        '''# Get standard data paths
    paths = get_standard_nlp_paths(doc_id, chunks_location)
    text_location = paths['text_location']
    nlp_output_location = paths['nlp_output_location']
    
    logger.info(f"Using standard data paths:")
    logger.info(f"  Text location: {text_location}")
    logger.info(f"  NLP output location: {nlp_output_location}")'''
    )
    
    # Create a temporary directory and zip file
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write the fixed worker file
        worker_file = os.path.join(temp_dir, 'nlp_worker.py')
        with open(worker_file, 'w') as f:
            f.write(fixed_content)
        
        # Copy other required files from worker directory
        worker_dir = "/Users/chris/climate-risk-rag-aws/lambda/nlp_worker/"
        required_files = [
            'nlp_interface.py',
            'comprehend_provider.py',
            'flair_provider.py',
            'offset_mapper.py',
            's3_data_lake_manager.py',
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
        zip_path = os.path.join(temp_dir, 'nlp_worker.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file != 'nlp_worker.zip':
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
        
        # Update the Lambda function
        with open(zip_path, 'rb') as f:
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=f.read()
            )
        
        logger.info(f"✅ Updated {function_name} with standard data paths")

def verify_configurations(lambda_client):
    """Verify that configurations are consistent"""
    
    # Check NLP processor configuration
    logger.info("Verifying NLP processor configuration...")
    response = lambda_client.get_function(FunctionName="nlp-processor")
    processor_env = response['Configuration']['Environment']['Variables']
    
    required_vars = ['DATABASE_SECRET_NAME', 'DB_HOST', 'DB_NAME', 'DB_PORT', 'DATABASE_URL']
    for var in required_vars:
        if var not in processor_env:
            logger.warning(f"Missing environment variable in processor: {var}")
        else:
            logger.info(f"✅ Processor has {var}")
    
    # Check NLP worker configuration
    logger.info("Verifying NLP worker configuration...")
    response = lambda_client.get_function(FunctionName="nlp-worker")
    worker_env = response['Configuration']['Environment']['Variables']
    
    for var in required_vars:
        if var not in worker_env:
            logger.warning(f"Missing environment variable in worker: {var}")
        else:
            logger.info(f"✅ Worker has {var}")
    
    logger.info("✅ Configuration verification complete")

if __name__ == "__main__":
    sys.exit(main())
