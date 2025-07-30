#!/usr/bin/env python3
"""
Fix Text Extractor Processor Deployment
Properly deploy the function with all necessary files and Secrets Manager integration
"""

import boto3
import json
import tempfile
import zipfile
import os
import shutil

def main():
    """Fix text extractor processor deployment"""
    print("🔧 Fixing Text Extractor Processor Deployment")
    print("==============================================")
    
    # Create updated function code with Secrets Manager integration
    create_updated_processor_code()
    
    # Deploy the fixed function
    deploy_fixed_processor()
    
    print("✅ Text extractor processor deployment fixed")

def create_updated_processor_code():
    """Create updated processor code with Secrets Manager integration"""
    
    # Read the original processor code
    processor_path = "/Users/chris/climate-risk-rag-aws/lambda/text_extractor_processor/text_extractor_processor.py"
    
    with open(processor_path, 'r') as f:
        original_code = f.read()
    
    # Add Secrets Manager integration
    updated_code = add_secrets_manager_integration(original_code)
    
    # Write the updated code back
    with open(processor_path, 'w') as f:
        f.write(updated_code)
    
    print("✅ Updated processor code with Secrets Manager integration")

def add_secrets_manager_integration(original_code):
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
            # Find the end of imports
            lines = original_code.split('\n')
            import_end_line = 0
            for i, line in enumerate(lines):
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    import_end_line = i
            import_end = len('\n'.join(lines[:import_end_line + 1])) + 1
        class_start = import_end
    
    # Insert the secrets manager function
    updated_code = (original_code[:class_start] + 
                   secrets_manager_function + 
                   original_code[class_start:])
    
    # Replace DATABASE_URL initialization - look for the specific pattern
    if "os.environ['DATABASE_URL']" in updated_code:
        updated_code = updated_code.replace("os.environ['DATABASE_URL']", "get_database_url_from_secrets()")
    elif "os.environ.get('DATABASE_URL')" in updated_code:
        updated_code = updated_code.replace("os.environ.get('DATABASE_URL')", "get_database_url_from_secrets()")
    
    return updated_code

def deploy_fixed_processor():
    """Deploy the fixed processor function"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy all processor files
        processor_dir = "/Users/chris/climate-risk-rag-aws/lambda/text_extractor_processor"
        
        # Copy all Python files
        for file in os.listdir(processor_dir):
            if file.endswith('.py') and not file.startswith('DEPRECATED'):
                shutil.copy(os.path.join(processor_dir, file), temp_dir)
        
        # Create deployment zip
        zip_path = os.path.join(temp_dir, 'processor.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in os.listdir(temp_dir):
                if file.endswith('.py'):
                    zipf.write(os.path.join(temp_dir, file), file)
        
        # Deploy function code
        with open(zip_path, 'rb') as f:
            response = lambda_client.update_function_code(
                FunctionName='solve-global-kr-textextractor-processor',
                ZipFile=f.read()
            )
        
        print(f"✅ Deployed fixed processor: {response['CodeSha256']}")

if __name__ == "__main__":
    main()
