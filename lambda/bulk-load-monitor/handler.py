#!/usr/bin/env python3
"""
Bulk Load Monitor Lambda Handler
Monitors active Neptune bulk loads and updates processing status when complete
"""

import json
import logging
from src.bulk_load_monitor import BulkLoadMonitor

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Lambda handler for bulk load monitoring
    Triggered by EventBridge on a schedule
    """
    try:
        logger.info("Starting bulk load monitoring")
        
        monitor = BulkLoadMonitor()
        results = monitor.monitor_active_loads()
        
        logger.info(f"Monitoring completed. Results: {results}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Bulk load monitoring completed',
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"Error in bulk load monitoring: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
