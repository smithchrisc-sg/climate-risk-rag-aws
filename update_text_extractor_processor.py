#!/usr/bin/env python3
"""
Update Text Extractor Processor with Standardized Database Layer
Apply the same proven pattern that worked for the initiator
"""

import boto3
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Update text extractor processor with standardized database layer"""
    logger.info("🔧 Updating Text Extractor Processor with Standardized Database Layer")
    logger.info("====================================================================")
    
    try:
        # Step 1: Update environment variables to use standard configuration
        logger.info("Step 1: Updating environment variables")
        update_environment_variables()
        
        # Step 2: Update VPC configuration to use working subnets
        logger.info("Step 2: Updating VPC configuration")
        update_vpc_configuration()
        
        # Step 3: Update layers to use standardized layers
        logger.info("Step 3: Updating layers")
        update_function_layers()
        
        # Step 4: Update function code with Secrets Manager integration
        logger.info("Step 4: Updating function code")
        update_function_code()
        
        logger.info("✅ Text extractor processor update completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Failed to update text extractor processor: {str(e)}")
        return 1

def update_environment_variables():
    """Update environment variables to use standard database configuration"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Get current environment variables
    response = lambda_client.get_function(FunctionName='solve-global-kr-textextractor-processor')
    current_env = response['Configuration']['Environment']['Variables']
    
    # Standard environment variables (same as working functions)
    standard_env_vars = {
        'DATABASE_SECRET_NAME': 'rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863',
        'DB_HOST': 'solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com',
        'DB_NAME': 'climate_risk_rag',
        'DB_PORT': '5432',
        'DATABASE_CONNECTION_METHOD': 'secrets_manager',
        # Keep existing environment variables
        'CHUNKS_BUCKET': current_env.get('CHUNKS_BUCKET', ''),
        'CHUNKS_READY_TOPIC_ARN': current_env.get('CHUNKS_READY_TOPIC_ARN', ''),
        'OUTPUT_BUCKET': current_env.get('OUTPUT_BUCKET', ''),
        'TEXT_BUCKET': current_env.get('TEXT_BUCKET', '')
    }
    
    # Update function configuration
    response = lambda_client.update_function_configuration(
        FunctionName='solve-global-kr-textextractor-processor',
        Environment={
            'Variables': standard_env_vars
        }
    )
    
    logger.info("✅ Updated environment variables to use standard database configuration")
    logger.info("  - Removed hardcoded DATABASE_URL")
    logger.info("  - Added DATABASE_SECRET_NAME")
    logger.info("  - Added standard DB_HOST, DB_NAME, DB_PORT")
    logger.info("  - Added DATABASE_CONNECTION_METHOD=secrets_manager")
    
    # Wait for update to propagate
    import time
    time.sleep(30)

def update_vpc_configuration():
    """Update VPC configuration to use working subnets"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Use the same VPC configuration that works for pipeline test function and text extractor initiator
    working_vpc_config = {
        'SubnetIds': ['subnet-03d8bd6cf3491f38c', 'subnet-0c0be1dd59f70f70e'],
        'SecurityGroupIds': ['sg-099296a5c809e8d9d']
    }
    
    # Update function configuration
    response = lambda_client.update_function_configuration(
        FunctionName='solve-global-kr-textextractor-processor',
        VpcConfig=working_vpc_config
    )
    
    logger.info("✅ Updated VPC configuration to use working subnets:")
    logger.info("  - Subnets: Private subnets with NAT Gateway routing")
    logger.info("  - Security Group: Same as working functions")
    
    # Wait for update to propagate
    import time
    time.sleep(30)

def update_function_layers():
    """Update function layers to use standardized layers"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Use the same layer combination that works for other functions
    standard_layers = [
        "arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities:12",
        "arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies-pipeline:3"
    ]
    
    # Update function configuration
    response = lambda_client.update_function_configuration(
        FunctionName='solve-global-kr-textextractor-processor',
        Layers=standard_layers
    )
    
    logger.info("✅ Updated layers to use standardized configuration:")
    for layer in standard_layers:
        logger.info(f"  - {layer.split(':')[-2]}:{layer.split(':')[-1]}")
    
    # Wait for update to propagate
    import time
    time.sleep(30)

def update_function_code():
    """Update function code with Secrets Manager integration"""
    import tempfile
    import zipfile
    import os
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Read the current text extractor processor code
    processor_path = "/Users/chris/climate-risk-rag-aws/lambda/text_extractor_processor"
    
    # Find the main handler file
    handler_files = []
    for file in os.listdir(processor_path):
        if file.endswith('.py') and ('processor' in file or 'handler' in file):
            handler_files.append(file)
    
    if not handler_files:
        logger.error("Could not find processor handler file")
        return
    
    main_file = handler_files[0]  # Use the first processor file found
    original_file_path = os.path.join(processor_path, main_file)
    
    with open(original_file_path, 'r') as f:
        original_code = f.read()
    
    # Add Secrets Manager integration
    updated_code = add_secrets_manager_to_processor(original_code)
    
    # Deploy updated function
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write updated code
        handler_path = os.path.join(temp_dir, main_file)
        with open(handler_path, 'w') as f:
            f.write(updated_code)
        
        # Create zip
        zip_path = os.path.join(temp_dir, 'function.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(handler_path, main_file)
        
        # Deploy
        with open(zip_path, 'rb') as f:
            response = lambda_client.update_function_code(
                FunctionName='solve-global-kr-textextractor-processor',
                ZipFile=f.read()
            )
        
        logger.info(f"✅ Updated function code with Secrets Manager integration")

def add_secrets_manager_to_processor(original_code):
    """Add Secrets Manager integration to processor code"""
    
    # Add the Secrets Manager function at the top after imports
    secrets_manager_function = '''
def get_database_url_from_secrets():
    """Construct DATABASE_URL from standard environment variables and Secrets Manager"""
    import boto3
    import json
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get standard environment variables
        secret_name = os.environ.get('DATABASE_SECRET_NAME')
        db_host = os.environ.get('DB_HOST')
        db_name = os.environ.get('DB_NAME')
        db_port = os.environ.get('DB_PORT', '5432')
        
        logger.info(f"Constructing DATABASE_URL from standard environment variables")
        
        if not all([secret_name, db_host, db_name]):
            raise ValueError("Missing required database environment variables")
        
        # Get credentials from Secrets Manager
        secrets_client = boto3.client('secretsmanager')
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret_data = json.loads(response['SecretString'])
        
        username = secret_data.get('username', 'postgres')
        password = secret_data['password']
        
        # Construct DATABASE_URL
        database_url = f"postgresql://{username}:{password}@{db_host}:{db_port}/{db_name}?sslmode=require"
        
        logger.info("✅ DATABASE_URL constructed from Secrets Manager")
        return database_url
        
    except Exception as e:
        logger.error(f"❌ Failed to construct DATABASE_URL: {str(e)}")
        raise

'''
    
    # Find where to insert the function (after imports, before class)
    class_start = original_code.find('class ')
    if class_start == -1:
        # Try to find a good insertion point after imports
        import_end = original_code.find('logger = logging.getLogger')
        if import_end != -1:
            import_end = original_code.find('\n', import_end) + 1
        else:
            import_end = original_code.find('\n\n') + 2
        class_start = import_end
    
    # Insert the secrets manager function
    updated_code = (original_code[:class_start] + 
                   secrets_manager_function + 
                   original_code[class_start:])
    
    # Replace DATABASE_URL initialization
    old_db_init = "os.environ['DATABASE_URL']"
    new_db_init = "get_database_url_from_secrets()"
    
    # Replace all occurrences
    updated_code = updated_code.replace(old_db_init, new_db_init)
    
    return updated_code

if __name__ == "__main__":
    import sys
    sys.exit(main())
