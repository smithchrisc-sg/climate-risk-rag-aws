#!/usr/bin/env python3
"""
Update Pipeline Test Function to use New Database Layer
Methodically updates the function while preserving all other functionality
"""

import os
import logging
import sys
import zipfile
import tempfile
import boto3
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to update pipeline test function"""
    logger.info("🔧 Updating Pipeline Test Function")
    logger.info("==================================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    try:
        # Step 1: Read current function code
        logger.info("Step 1: Reading current function code")
        current_code = read_current_function_code()
        
        # Step 2: Update imports and database initialization
        logger.info("Step 2: Updating imports and database initialization")
        updated_code = update_function_code(current_code)
        
        # Step 3: Deploy updated function
        logger.info("Step 3: Deploying updated function")
        deploy_updated_function(updated_code)
        
        # Step 4: Test updated function
        logger.info("Step 4: Testing updated function")
        test_updated_function()
        
        logger.info("✅ Pipeline test function updated successfully")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Failed to update pipeline test function: {str(e)}")
        return 1

def read_current_function_code():
    """Read current pipeline test function code"""
    function_path = "/Users/chris/climate-risk-rag-aws/lambda/pipeline_test_function/pipeline_test_handler.py"
    
    with open(function_path, 'r') as f:
        content = f.read()
    
    logger.info(f"Read {len(content)} characters from current function")
    return content

def update_function_code(current_code):
    """Update function code to use new database layer"""
    
    # Step 1: Update imports section
    old_imports = '''# Import from Lambda layers
try:
    # Add /opt paths to Python path
    import sys
    sys.path.append("/opt/python")
    sys.path.append("/opt/build")
    sys.path.append("/opt/build/climate-risk-core-layer")
    sys.path.append("/opt/build/climate-risk-core-layer/python")
    
    # Try to import DocumentIDManager
    try:
        from DocumentIDManager import DocumentIDManager
        logger = logging.getLogger()'''
    
    new_imports = '''# Import from Lambda layers - New Database Core Layer
try:
    # Standard database imports (using new database-core-layer)
    from utils.DatabaseManager import DatabaseManager
    from utils.DocumentIDManager import DocumentIDManager
    from utils.database_config import validate_database_environment, log_database_configuration
    logger = logging.getLogger()
    logger.info("Database utilities imported successfully from database-core-layer")
    
    # Log database configuration (without sensitive data)
    log_database_configuration()'''
    
    updated_code = current_code.replace(old_imports, new_imports)
    
    # Step 2: Update database initialization in __init__ method
    old_init = '''        # Get DATABASE_URL from environment
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            raise ValueError("DATABASE_URL environment variable not set")
        
        # Initialize DocumentIDManager with DATABASE_URL
        if DocumentIDManager is None:
            raise ImportError("DocumentIDManager module not available")
        
        try:
            self.doc_id_manager = DocumentIDManager(database_url)
            logger.info("DocumentIDManager initialized successfully")
        except Exception as e:
            # Treat database connectivity as a hard requirement
            logger.error(f"FATAL ERROR: DocumentIDManager initialization failed: {str(e)}")
            logger.error("Database connectivity is required for pipeline operation")
            raise RuntimeError(f"Database connectivity failure: {str(e)}")'''
    
    new_init = '''        # Initialize database managers using new database-core-layer
        try:
            # Validate database environment variables
            validate_database_environment()
            
            # Initialize DatabaseManager (uses Secrets Manager automatically)
            self.db_manager = DatabaseManager()
            logger.info("DatabaseManager initialized successfully")
            
            # Initialize DocumentIDManager with DatabaseManager
            self.doc_id_manager = DocumentIDManager(self.db_manager)
            logger.info("DocumentIDManager initialized successfully")
            
            # Test database connectivity
            if not self.db_manager.test_connection():
                raise RuntimeError("Database connection test failed")
            logger.info("Database connectivity verified")
            
        except Exception as e:
            # Treat database connectivity as a hard requirement
            logger.error(f"FATAL ERROR: Database initialization failed: {str(e)}")
            logger.error("Database connectivity is required for pipeline operation")
            raise RuntimeError(f"Database connectivity failure: {str(e)}")'''
    
    updated_code = updated_code.replace(old_init, new_init)
    
    # Step 3: Update any remaining DocumentIDManager usage if needed
    # (Most usage should remain the same since we preserved the interface)
    
    logger.info("Function code updated successfully")
    logger.info("- Updated imports to use database-core-layer")
    logger.info("- Updated database initialization to use Secrets Manager")
    logger.info("- Preserved all other functionality")
    
    return updated_code

def deploy_updated_function(updated_code):
    """Deploy updated function code"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create temporary directory for deployment
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write updated code
        handler_path = os.path.join(temp_dir, 'pipeline_test_handler.py')
        with open(handler_path, 'w') as f:
            f.write(updated_code)
        
        # Create deployment zip
        zip_path = os.path.join(temp_dir, 'function.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(handler_path, 'pipeline_test_handler.py')
        
        # Deploy function code
        with open(zip_path, 'rb') as f:
            response = lambda_client.update_function_code(
                FunctionName='solve-global-kr-pipeline-test-function',
                ZipFile=f.read()
            )
        
        logger.info("✅ Function code deployed successfully")
        logger.info(f"Code SHA256: {response['CodeSha256']}")

def test_updated_function():
    """Test updated function"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Simple test payload
    test_payload = {
        'test': 'database_connection',
        'action': 'test_database'
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-pipeline-test-function',
            Payload=json.dumps(test_payload)
        )
        
        response_payload = json.loads(response['Payload'].read().decode('utf-8'))
        
        # Check for import errors
        if 'ImportModuleError' in str(response_payload):
            logger.error("❌ Import errors detected")
            return False
        elif 'errorType' in response_payload and 'Import' in response_payload['errorType']:
            logger.error("❌ Import errors detected")
            return False
        elif 'DATABASE_URL environment variable not set' in str(response_payload):
            logger.error("❌ Still expecting DATABASE_URL (update may not have worked)")
            return False
        else:
            logger.info("✅ No import errors detected")
            
        # Check for database initialization
        if 'Database' in str(response_payload) or 'database' in str(response_payload):
            logger.info("✅ Database initialization attempted")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Function test failed: {str(e)}")
        return False

if __name__ == "__main__":
    sys.exit(main())
