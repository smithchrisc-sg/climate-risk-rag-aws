#!/usr/bin/env python3
"""
Process NatCat manifest through document pipeline
Converts JSONL manifest to format expected by pipeline-test-function
"""

import json
import boto3
import logging
from datetime import datetime
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ManifestPipelineProcessor:
    """Process manifest documents through the pipeline"""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        self.lambda_function_name = 'pipeline-test-function'
    
    def load_manifest(self, manifest_path: str) -> List[Dict]:
        """Load documents from JSONL manifest, filtering out skipped entries"""
        documents = []
        skipped_count = 0
        with open(manifest_path, 'r') as f:
            for line in f:
                doc = json.loads(line.strip())
                # Skip documents marked with "skip": true
                if doc.get('skip', False):
                    skipped_count += 1
                    logger.info(f"Skipping document {doc.get('doc_id', 'unknown')} (skip flag set)")
                    continue
                documents.append(doc)
        
        if skipped_count > 0:
            logger.info(f"Skipped {skipped_count} documents marked with skip flag")
        
        return documents
    
    def convert_to_pipeline_format(self, manifest_docs: List[Dict]) -> List[Dict]:
        """Convert manifest format to pipeline Lambda format"""
        document_pairs = []
        
        for doc in manifest_docs:
            # Pipeline expects: {"legacy_doc_id": str, "source_url": str}
            document_pairs.append({
                "legacy_doc_id": doc["doc_id"],
                "source_url": doc["url"]
            })
        
        return document_pairs
    
    def process_batch(self, document_pairs: List[Dict], batch_size: int = 5, delay_seconds: int = 180) -> List[Dict]:
        """Process documents in batches through pipeline with delays"""
        import time
        
        results = []
        
        for i in range(0, len(document_pairs), batch_size):
            batch = document_pairs[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(document_pairs) + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} documents)")
            
            # Prepare event for Lambda
            event = {
                "action": "test",
                "document_pairs": batch
            }
            
            try:
                # Invoke Lambda
                response = self.lambda_client.invoke(
                    FunctionName=self.lambda_function_name,
                    InvocationType='RequestResponse',
                    Payload=json.dumps(event, default=str)
                )
                
                # Parse response
                status_code = response['StatusCode']
                payload = json.loads(response['Payload'].read())
                
                if status_code == 200:
                    if 'body' in payload:
                        body = json.loads(payload['body']) if isinstance(payload['body'], str) else payload['body']
                        results.append({
                            'batch_num': batch_num,
                            'success': True,
                            'response': body
                        })
                        
                        # Log batch results
                        batch_results = body.get('results', {})
                        successful = batch_results.get('successful_copies', 0)
                        failed = batch_results.get('failed_copies', 0)
                        logger.info(f"Batch {batch_num}: {successful} successful, {failed} failed")
                    else:
                        results.append({
                            'batch_num': batch_num,
                            'success': True,
                            'response': payload
                        })
                else:
                    logger.error(f"Batch {batch_num} failed with status {status_code}")
                    results.append({
                        'batch_num': batch_num,
                        'success': False,
                        'error': payload
                    })
                    
            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {e}")
                results.append({
                    'batch_num': batch_num,
                    'success': False,
                    'error': str(e)
                })
            
            # Add delay between batches (except for the last batch)
            if batch_num < total_batches:
                logger.info(f"Waiting {delay_seconds} seconds before next batch...")
                time.sleep(delay_seconds)
        
        return results
    
    def process_manifest(self, manifest_path: str, batch_size: int = 5, delay_seconds: int = 180, dry_run: bool = False, limit: int = None) -> Dict:
        """Process entire manifest through pipeline"""
        try:
            # Load manifest
            logger.info(f"Loading manifest: {manifest_path}")
            manifest_docs = self.load_manifest(manifest_path)
            logger.info(f"Loaded {len(manifest_docs)} documents from manifest")
            
            # Apply limit if specified
            if limit is not None and limit > 0:
                manifest_docs = manifest_docs[:limit]
                logger.info(f"Limited to first {len(manifest_docs)} documents")
            
            # Convert to pipeline format
            document_pairs = self.convert_to_pipeline_format(manifest_docs)
            
            if dry_run:
                logger.info("=== DRY RUN ===")
                logger.info(f"Would process {len(document_pairs)} documents in batches of {batch_size}")
                logger.info("Sample document pairs:")
                for i, pair in enumerate(document_pairs[:3]):
                    logger.info(f"  {i+1}. {pair['legacy_doc_id']} -> {pair['source_url'][:60]}...")
                return {"success": True, "dry_run": True, "total_documents": len(document_pairs)}
            
            # Process in batches
            logger.info(f"Processing {len(document_pairs)} documents in batches of {batch_size} with {delay_seconds}s delays")
            batch_results = self.process_batch(document_pairs, batch_size, delay_seconds)
            
            # Summarize results
            total_successful = 0
            total_failed = 0
            successful_batches = 0
            
            for batch_result in batch_results:
                if batch_result['success']:
                    successful_batches += 1
                    response = batch_result['response']
                    if 'results' in response:
                        results = response['results']
                        total_successful += results.get('successful_copies', 0)
                        total_failed += results.get('failed_copies', 0)
            
            return {
                'success': True,
                'total_documents': len(document_pairs),
                'total_successful': total_successful,
                'total_failed': total_failed,
                'successful_batches': successful_batches,
                'total_batches': len(batch_results),
                'batch_results': batch_results,
                'processed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing manifest: {e}")
            return {
                'success': False,
                'error': str(e),
                'processed_at': datetime.now().isoformat()
            }

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Process NatCat manifest through document pipeline')
    parser.add_argument('--manifest', required=True, help='Path to JSONL manifest file')
    parser.add_argument('--batch-size', type=int, default=5, help='Batch size for processing (default: 5)')
    parser.add_argument('--delay-seconds', type=int, default=180, help='Delay between batches in seconds (default: 180)')
    parser.add_argument('--limit', type=int, default=None, help='Limit to first N documents from manifest (default: process all)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be processed without executing')
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = ManifestPipelineProcessor()
    
    # Process manifest
    result = processor.process_manifest(args.manifest, args.batch_size, args.delay_seconds, args.dry_run, args.limit)
    
    # Print results
    if result['success']:
        if result.get('dry_run'):
            logger.info("✅ Dry run completed successfully")
        else:
            logger.info("=" * 60)
            logger.info("🎉 MANIFEST PROCESSING COMPLETE")
            logger.info("=" * 60)
            logger.info(f"📄 Total Documents: {result['total_documents']}")
            logger.info(f"✅ Successfully Processed: {result['total_successful']}")
            logger.info(f"❌ Failed: {result['total_failed']}")
            logger.info(f"📦 Successful Batches: {result['successful_batches']}/{result['total_batches']}")
            
            if result['total_successful'] > 0:
                logger.info(f"\n🚀 {result['total_successful']} documents copied to processing bucket")
                logger.info("These will trigger the text extraction pipeline automatically")
    else:
        logger.error("❌ Manifest processing failed")
        logger.error(f"Error: {result.get('error', 'Unknown error')}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
