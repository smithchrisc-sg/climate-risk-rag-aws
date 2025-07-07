#!/usr/bin/env python3
"""
Post-Migration Processing Trigger
Triggers AWS Lambda processing for migrated documents
"""

import boto3
import json
import logging
import argparse
from typing import List, Dict
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProcessingTrigger:
    """Triggers processing for migrated documents"""
    
    def __init__(self, aws_region: str = 'us-east-1'):
        self.s3 = boto3.client('s3', region_name=aws_region)
        self.lambda_client = boto3.client('lambda', region_name=aws_region)
        self.stepfunctions = boto3.client('stepfunctions', region_name=aws_region)
    
    def trigger_bulk_processing(self, documents_bucket: str, 
                               max_concurrent: int = 10,
                               batch_size: int = 100) -> Dict:
        """Trigger processing for all documents in bucket"""
        
        logger.info(f"Starting bulk processing trigger for bucket: {documents_bucket}")
        
        # Get list of documents
        documents = self._get_document_list(documents_bucket)
        logger.info(f"Found {len(documents)} documents to process")
        
        if not documents:
            return {'processed': 0, 'errors': 0, 'message': 'No documents found'}
        
        # Process in batches
        results = {'processed': 0, 'errors': 0, 'details': []}
        
        for i in tqdm(range(0, len(documents), batch_size), desc="Processing batches"):
            batch = documents[i:i+batch_size]
            batch_results = self._process_document_batch(
                batch, documents_bucket, max_concurrent
            )
            
            results['processed'] += batch_results['processed']
            results['errors'] += batch_results['errors']
            results['details'].extend(batch_results['details'])
            
            # Rate limiting - avoid overwhelming Lambda
            if i + batch_size < len(documents):
                time.sleep(2)
        
        logger.info(f"Bulk processing completed: {results['processed']} processed, {results['errors']} errors")
        return results
    
    def _get_document_list(self, bucket: str) -> List[Dict]:
        """Get list of documents from S3 bucket"""
        documents = []
        
        try:
            paginator = self.s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket, Prefix='documents/'):
                for obj in page.get('Contents', []):
                    if obj['Key'].endswith('.pdf'):
                        documents.append({
                            'bucket': bucket,
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified']
                        })
        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
        
        return documents
    
    def _process_document_batch(self, documents: List[Dict], bucket: str, 
                               max_concurrent: int) -> Dict:
        """Process a batch of documents concurrently"""
        
        results = {'processed': 0, 'errors': 0, 'details': []}
        
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # Submit all documents in batch
            future_to_doc = {
                executor.submit(self._trigger_document_processing, doc): doc
                for doc in documents
            }
            
            # Collect results
            for future in as_completed(future_to_doc):
                doc = future_to_doc[future]
                try:
                    result = future.result()
                    if result['success']:
                        results['processed'] += 1
                    else:
                        results['errors'] += 1
                    results['details'].append(result)
                    
                except Exception as e:
                    logger.error(f"Error processing {doc['key']}: {str(e)}")
                    results['errors'] += 1
                    results['details'].append({
                        'document': doc['key'],
                        'success': False,
                        'error': str(e)
                    })
        
        return results
    
    def _trigger_document_processing(self, document: Dict) -> Dict:
        """Trigger processing for a single document"""
        try:
            # Option 1: Trigger Step Functions workflow (preferred)
            # This would require the Step Functions ARN from CDK output
            
            # Option 2: Trigger Lambda function directly
            # For now, we'll use the bulk processor Lambda
            
            payload = {
                'action': 'process_document',
                'bucket': document['bucket'],
                'key': document['key'],
                'trigger_source': 'bulk_migration'
            }
            
            # Invoke bulk processor Lambda (async)
            response = self.lambda_client.invoke(
                FunctionName='climate-risk-rag-BulkProcessor',  # CDK generated name
                InvocationType='Event',  # Async invocation
                Payload=json.dumps(payload)
            )
            
            return {
                'document': document['key'],
                'success': True,
                'status_code': response['StatusCode'],
                'request_id': response['ResponseMetadata']['RequestId']
            }
            
        except Exception as e:
            logger.error(f"Error triggering processing for {document['key']}: {str(e)}")
            return {
                'document': document['key'],
                'success': False,
                'error': str(e)
            }
    
    def check_processing_status(self, artifacts_bucket: str) -> Dict:
        """Check status of document processing"""
        
        status = {
            'total_documents': 0,
            'processed_documents': 0,
            'processing_rate': 0.0,
            'recent_activity': []
        }
        
        try:
            # Count processing status files
            paginator = self.s3.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=artifacts_bucket, Prefix='processing_status/'):
                for obj in page.get('Contents', []):
                    status['processed_documents'] += 1
                    
                    # Get recent activity (last 10 files)
                    if len(status['recent_activity']) < 10:
                        status['recent_activity'].append({
                            'file': obj['Key'],
                            'processed_at': obj['LastModified'].isoformat()
                        })
            
            # Get total document count from migration manifest
            try:
                manifest_obj = self.s3.get_object(
                    Bucket=artifacts_bucket,
                    Key='migration_manifest.json'
                )
                manifest = json.loads(manifest_obj['Body'].read())
                status['total_documents'] = len(manifest.get('documents', []))
                
            except Exception as e:
                logger.warning(f"Could not load migration manifest: {str(e)}")
            
            # Calculate processing rate
            if status['total_documents'] > 0:
                status['processing_rate'] = (
                    status['processed_documents'] / status['total_documents'] * 100
                )
            
            logger.info(f"Processing status: {status['processed_documents']}/{status['total_documents']} "
                       f"({status['processing_rate']:.1f}%)")
            
        except Exception as e:
            logger.error(f"Error checking processing status: {str(e)}")
            status['error'] = str(e)
        
        return status


def main():
    parser = argparse.ArgumentParser(description='Trigger processing for migrated documents')
    parser.add_argument('--documents-bucket', required=True,
                       help='S3 bucket containing documents')
    parser.add_argument('--artifacts-bucket', required=True,
                       help='S3 bucket for artifacts')
    parser.add_argument('--region', default='us-east-1',
                       help='AWS region')
    parser.add_argument('--max-concurrent', type=int, default=10,
                       help='Maximum concurrent processing')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Batch size for processing')
    parser.add_argument('--check-status', action='store_true',
                       help='Check processing status only')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be processed without triggering')
    
    args = parser.parse_args()
    
    trigger = ProcessingTrigger(args.region)
    
    if args.check_status:
        # Check processing status
        status = trigger.check_processing_status(args.artifacts_bucket)
        
        print(f"\n📊 Processing Status:")
        print(f"  Total Documents: {status['total_documents']}")
        print(f"  Processed: {status['processed_documents']}")
        print(f"  Progress: {status['processing_rate']:.1f}%")
        
        if status['recent_activity']:
            print(f"\n🕒 Recent Activity:")
            for activity in status['recent_activity'][:5]:
                print(f"  {activity['file']} - {activity['processed_at']}")
    
    elif args.dry_run:
        # Show what would be processed
        documents = trigger._get_document_list(args.documents_bucket)
        print(f"\n📋 Dry Run Results:")
        print(f"  Documents found: {len(documents)}")
        print(f"  Batch size: {args.batch_size}")
        print(f"  Max concurrent: {args.max_concurrent}")
        print(f"  Estimated batches: {(len(documents) + args.batch_size - 1) // args.batch_size}")
        
        if documents:
            print(f"\n📄 Sample documents:")
            for doc in documents[:5]:
                print(f"    {doc['key']} ({doc['size']} bytes)")
    
    else:
        # Trigger bulk processing
        print(f"\n🚀 Starting bulk processing trigger...")
        print(f"  Documents bucket: {args.documents_bucket}")
        print(f"  Max concurrent: {args.max_concurrent}")
        print(f"  Batch size: {args.batch_size}")
        
        results = trigger.trigger_bulk_processing(
            args.documents_bucket,
            args.max_concurrent,
            args.batch_size
        )
        
        print(f"\n✅ Processing trigger completed:")
        print(f"  Processed: {results['processed']}")
        print(f"  Errors: {results['errors']}")
        
        if results['errors'] > 0:
            print(f"\n❌ Error details:")
            error_details = [d for d in results['details'] if not d['success']]
            for error in error_details[:5]:  # Show first 5 errors
                print(f"    {error['document']}: {error.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
