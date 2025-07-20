import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    try:
        logger.info("Starting simple DatabaseManager test")
        
        # Import DatabaseManager from layer
        from utils.DatabaseManager import DatabaseManager
        logger.info("✅ Successfully imported DatabaseManager from layer")
        
        # Create instance
        db_manager = DatabaseManager()
        logger.info("✅ Successfully created DatabaseManager instance")
        
        # Test keyword indexing method
        result = db_manager.update_keyword_indexing_status(
            doc_id="test_doc_123",
            status="PROCESSING",
            notes="Test from simple function"
        )
        logger.info(f"✅ Successfully called update_keyword_indexing_status: {result}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'DatabaseManager test successful',
                'test_doc_id': 'test_doc_123'
            })
        }
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
