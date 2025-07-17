#!/usr/bin/env python3
"""
Update Text Extractor Initiator Code with Secrets Manager Integration
Add DATABASE_URL construction from standard environment variables
"""

import boto3
import json
import tempfile
import zipfile
import os

def main():
    """Update text extractor initiator code with Secrets Manager integration"""
    print("🔧 Updating Text Extractor Initiator Code")
    print("=========================================")
    
    # Read the current text extractor initiator code
    original_path = "/Users/chris/climate-risk-rag-aws/lambda/text_extractor_initiator/text_extractor_initiator.py"
    
    with open(original_path, 'r') as f:
        original_code = f.read()
    
    # Create updated code with Secrets Manager integration
    updated_code = add_secrets_manager_integration(original_code)
    
    # Deploy updated function
    deploy_updated_function(updated_code)
    
    # Test the updated function
    test_updated_function()

def add_secrets_manager_integration(original_code):
    """Add Secrets Manager integration to text extractor initiator code"""
    
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
    class_start = original_code.find('class TextExtractorInitiator:')
    if class_start == -1:
        raise ValueError("Could not find TextExtractorInitiator class")
    
    # Insert the secrets manager function before the class
    updated_code = (original_code[:class_start] + 
                   secrets_manager_function + 
                   original_code[class_start:])
    
    # Replace the DATABASE_URL initialization
    old_db_init = "        self.database_url = os.environ['DATABASE_URL']"
    new_db_init = '''        # Construct DATABASE_URL from Secrets Manager using standard environment variables
        try:
            self.database_url = get_database_url_from_secrets()
            logger.info("DATABASE_URL set from Secrets Manager using standard environment variables")
        except Exception as e:
            logger.error(f"Failed to construct DATABASE_URL: {str(e)}")
            raise RuntimeError(f"Database configuration failure: {str(e)}")'''
    
    # Replace the database initialization
    updated_code = updated_code.replace(old_db_init, new_db_init)
    
    return updated_code

def deploy_updated_function(updated_code):
    """Deploy the updated function"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write function code
        handler_path = os.path.join(temp_dir, 'text_extractor_initiator.py')
        with open(handler_path, 'w') as f:
            f.write(updated_code)
        
        # Create zip
        zip_path = os.path.join(temp_dir, 'function.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(handler_path, 'text_extractor_initiator.py')
        
        # Deploy
        with open(zip_path, 'rb') as f:
            response = lambda_client.update_function_code(
                FunctionName='solve-global-kr-textextractor-initiator',
                ZipFile=f.read()
            )
        
        print(f"✅ Deployed updated text extractor initiator: {response['CodeSha256']}")

def test_updated_function():
    """Test the updated function"""
    
    # Wait for deployment
    import time
    time.sleep(30)
    
    print("\n📋 Testing updated text extractor initiator...")
    print("The function will be tested when the next document is processed.")
    print("Let's run another pipeline test to trigger it...")

if __name__ == "__main__":
    main()
