#!/usr/bin/env python3
"""
Properly Fix Text Extractor Processor Code
Fix the syntax error by properly placing the Secrets Manager function
"""

import os

def main():
    """Fix the processor code syntax error"""
    print("🔧 Fixing Text Extractor Processor Syntax Error")
    print("===============================================")
    
    # Read the current broken code
    processor_path = "/Users/chris/climate-risk-rag-aws/lambda/text_extractor_processor/text_extractor_processor.py"
    
    with open(processor_path, 'r') as f:
        broken_code = f.read()
    
    # Fix the code by properly placing the Secrets Manager function
    fixed_code = fix_code_structure(broken_code)
    
    # Write the fixed code
    with open(processor_path, 'w') as f:
        f.write(fixed_code)
    
    print("✅ Fixed processor code syntax")
    
    # Redeploy the function
    redeploy_function()

def fix_code_structure(broken_code):
    """Fix the code structure by properly placing the Secrets Manager function"""
    
    # Remove the incorrectly placed function
    lines = broken_code.split('\n')
    fixed_lines = []
    skip_until_class = False
    
    for line in lines:
        if 'def get_database_url_from_secrets():' in line:
            skip_until_class = True
            continue
        elif skip_until_class and (line.strip().startswith('class ') or line.strip().startswith('def ') and 'get_database_url_from_secrets' not in line):
            skip_until_class = False
        
        if not skip_until_class:
            fixed_lines.append(line)
    
    # Reconstruct the code
    fixed_code = '\n'.join(fixed_lines)
    
    # Find the proper place to insert the Secrets Manager function (after all imports)
    import_section_end = 0
    lines = fixed_code.split('\n')
    
    for i, line in enumerate(lines):
        if (line.strip().startswith('import ') or 
            line.strip().startswith('from ') or
            line.strip().startswith('try:') or
            line.strip().startswith('except') or
            line.strip() == '' and i < 50):  # Allow empty lines in import section
            import_section_end = i
        elif line.strip() and not line.strip().startswith('#'):
            break
    
    # Insert the Secrets Manager function after imports
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
    
    # Insert the function at the proper location
    lines.insert(import_section_end + 1, secrets_manager_function)
    
    # Reconstruct the code
    final_code = '\n'.join(lines)
    
    # Replace DATABASE_URL references
    if "os.environ['DATABASE_URL']" in final_code:
        final_code = final_code.replace("os.environ['DATABASE_URL']", "get_database_url_from_secrets()")
    elif "os.environ.get('DATABASE_URL')" in final_code:
        final_code = final_code.replace("os.environ.get('DATABASE_URL')", "get_database_url_from_secrets()")
    
    return final_code

def redeploy_function():
    """Redeploy the function with fixed code"""
    import boto3
    import tempfile
    import zipfile
    import shutil
    
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
        
        print(f"✅ Redeployed fixed processor: {response['CodeSha256']}")

if __name__ == "__main__":
    main()
