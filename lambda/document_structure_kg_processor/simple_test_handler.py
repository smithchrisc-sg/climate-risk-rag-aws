#!/usr/bin/env python3
"""
Simple test handler for document structure KG processor
Tests basic functionality without shared layer dependencies
"""

import json
import boto3
import os
from datetime import datetime

def lambda_handler(event, context):
    """Simple test handler for KG processing"""
    
    try:
        print(f"Received event: {json.dumps(event, default=str)}")
        
        # Parse SNS message
        records = event.get('Records', [])
        results = []
        
        for record in records:
            if record.get('EventSource') == 'aws:sns':
                message = json.loads(record['Sns']['Message'])
                document_id = message.get('document_id')
                status = message.get('status')
                
                print(f"Processing document: {document_id}, status: {status}")
                
                # Test S3 access
                s3_client = boto3.client('s3')
                chunks_bucket = os.environ.get('CHUNKS_BUCKET', 'solve-global-kr-chunks-861276078413-us-east-1')
                
                try:
                    # List objects in chunks bucket for this document
                    response = s3_client.list_objects_v2(
                        Bucket=chunks_bucket,
                        Prefix=f"{document_id}/"
                    )
                    
                    chunk_count = len(response.get('Contents', []))
                    print(f"Found {chunk_count} objects for document {document_id}")
                    
                    results.append({
                        'document_id': document_id,
                        'status': 'success',
                        'chunks_found': chunk_count,
                        'message': f'Successfully processed document {document_id}'
                    })
                    
                except Exception as e:
                    print(f"Error accessing S3: {str(e)}")
                    results.append({
                        'document_id': document_id,
                        'status': 'error',
                        'error': str(e)
                    })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Test processing completed',
                'results': results,
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        print(f"Error in lambda handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Test processing failed'
            })
        }
