#!/usr/bin/env python3
"""
Pipeline Test Lambda Invoker
Local client script that queries SQLite locally and sends document list to Lambda
"""

import boto3
from botocore.config import Config
import json
import argparse
import logging
import sqlite3
import os
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PipelineTestInvoker:
    """Client for invoking the pipeline test Lambda function with local SQLite queries"""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda', region_name='us-east-1', 
                                         config=Config(connect_timeout=5, read_timeout=65))
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.lambda_function_name = 'solve-global-kr-pipeline-test-function'
        self.sqlite_db_path = "/Volumes/G-RAID Photo 24TB/climate_risk_rag/db/corpus_document_ids.db"
        self.existing_bucket = "solve-global-kr-documents-861276078413-us-east-1"
    
    def get_available_documents_with_urls(self, limit: int = 100) -> List[Dict]:
        """Get available documents from S3 and match with SQLite URLs locally"""
        try:
            logger.info(f"Fetching documents from S3 and matching with SQLite database...")
            
            # Get documents from S3
            response = self.s3_client.list_objects_v2(
                Bucket=self.existing_bucket,
                Prefix="documents/",
                MaxKeys=limit * 2
            )
            
            if 'Contents' not in response:
                logger.error("No documents found in S3 bucket")
                return []
            
            # Extract S3 document info
            s3_documents = {}
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('.pdf'):
                    filename = os.path.basename(key)
                    doc_id_from_filename = filename.replace('.pdf', '')
                    size_mb = round(obj['Size'] / (1024 * 1024), 2)
                    estimated_pages = max(1, int((size_mb * 1024) / 75))  # ~75KB per page
                    
                    s3_documents[doc_id_from_filename] = {
                        'key': key,
                        'filename': filename,
                        'doc_id_from_filename': doc_id_from_filename,
                        'size': obj['Size'],
                        'size_mb': size_mb,
                        'estimated_pages': estimated_pages,
                        'last_modified': obj['LastModified']
                    }
            
            logger.info(f"Found {len(s3_documents)} PDF documents in S3")
            
            # Query SQLite for source URLs
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT doc_id, url, original_filename FROM documents")
            sqlite_results = cursor.fetchall()
            conn.close()
            
            logger.info(f"Found {len(sqlite_results)} documents in SQLite database")
            
            # Match S3 documents with SQLite URLs
            matched_documents = []
            for doc_id, url, original_filename in sqlite_results:
                if doc_id in s3_documents:
                    doc_info = s3_documents[doc_id].copy()
                    doc_info['source_url'] = url
                    doc_info['original_filename_from_db'] = original_filename
                    matched_documents.append(doc_info)
            
            logger.info(f"Successfully matched {len(matched_documents)} documents with source URLs")
            return matched_documents
            
        except Exception as e:
            logger.error(f"Error getting documents with URLs: {e}")
            return []
    
    def filter_documents_by_criteria(self, documents: List[Dict], **criteria) -> List[Dict]:
        """Filter documents by criteria locally"""
        try:
            num_documents = criteria.get('num_documents', 5)
            min_size_mb = criteria.get('min_size_mb', 1.0)
            max_size_mb = criteria.get('max_size_mb', 10.0)
            document_types = criteria.get('document_types')
            target_avg_pages = criteria.get('target_avg_pages', 20)
            
            logger.info(f"Filtering {len(documents)} documents with criteria:")
            logger.info(f"  - Count: {num_documents}")
            logger.info(f"  - Size: {min_size_mb}-{max_size_mb} MB")
            logger.info(f"  - Document types: {document_types or 'any'}")
            logger.info(f"  - Target avg pages: {target_avg_pages}")
            
            # Filter by size
            filtered = [
                doc for doc in documents 
                if min_size_mb <= doc['size_mb'] <= max_size_mb
            ]
            logger.info(f"After size filtering: {len(filtered)} documents")
            
            # Filter by document type if specified
            if document_types:
                document_type_patterns = {
                    "report": ["report", "assessment", "evaluation", "study"],
                    "policy": ["policy", "strategy", "framework", "guideline"],
                    "research": ["research", "analysis", "working", "paper"],
                    "project": ["project", "implementation", "completion", "icr"],
                    "financial": ["financial", "economic", "budget", "cost"],
                    "technical": ["technical", "manual", "specification", "guide"]
                }
                
                type_filtered = []
                for doc in filtered:
                    filename_lower = doc['filename'].lower()
                    for doc_type in document_types:
                        if doc_type in document_type_patterns:
                            patterns = document_type_patterns[doc_type]
                            if any(pattern in filename_lower for pattern in patterns):
                                type_filtered.append(doc)
                                break
                filtered = type_filtered
                logger.info(f"After document type filtering: {len(filtered)} documents")
            
            # Sort by how close they are to target page count
            filtered.sort(key=lambda x: abs(x['estimated_pages'] - target_avg_pages))
            
            # Limit results
            filtered = filtered[:num_documents]
            
            if filtered:
                total_pages = sum(doc['estimated_pages'] for doc in filtered)
                avg_pages = total_pages / len(filtered)
                avg_size = sum(doc['size_mb'] for doc in filtered) / len(filtered)
                
                logger.info(f"Selected {len(filtered)} documents:")
                logger.info(f"  - Total estimated pages: {total_pages}")
                logger.info(f"  - Average pages per doc: {avg_pages:.1f}")
                logger.info(f"  - Average size: {avg_size:.1f} MB")
                
                for i, doc in enumerate(filtered, 1):
                    logger.info(f"  {i}. {doc['filename']}: {doc['size_mb']} MB (~{doc['estimated_pages']} pages)")
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error filtering documents: {e}")
            return documents[:criteria.get('num_documents', 5)]
    
    def check_safety_limits(self, documents: List[Dict], force: bool = False) -> bool:
        """Check safety limits locally before sending to Lambda"""
        total_pages = sum(doc['estimated_pages'] for doc in documents)
        
        if len(documents) > 10:
            logger.error(f"Too many documents ({len(documents)}). Maximum is 10 for Textract parallel processing.")
            return False
        
        if total_pages > 100 and not force:
            logger.warning(f"⚠️  WARNING: Total estimated pages ({total_pages}) exceeds 100.")
            logger.warning("This could be expensive and slow.")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                logger.info("Operation cancelled by user")
                return False
        
        large_docs = [doc for doc in documents if doc['size_mb'] > 400]
        if large_docs:
            logger.error(f"Found {len(large_docs)} documents larger than 400MB (Textract limit)")
            return False
        
        logger.info(f"✅ Safety check passed: {len(documents)} documents (~{total_pages} pages)")
        return True
    
    def invoke_pipeline_test(self, action: str = 'test', **params) -> Dict[str, Any]:
        """Invoke the pipeline test Lambda function with pre-selected documents"""
        try:
            # Get and filter documents locally
            logger.info("📋 Selecting documents locally...")
            available_docs = self.get_available_documents_with_urls(limit=100)
            
            if not available_docs:
                return {
                    'success': False,
                    'error': 'No documents available with source URLs'
                }
            
            # Filter documents by criteria
            selected_docs = self.filter_documents_by_criteria(available_docs, **params)
            
            if not selected_docs:
                return {
                    'success': False,
                    'error': 'No documents match the specified criteria'
                }
            
            # Check safety limits
            if not self.check_safety_limits(selected_docs, params.get('force', False)):
                return {
                    'success': False,
                    'error': 'Safety limits exceeded or user cancelled'
                }
            
            # Convert selected documents to the format expected by Lambda
            # Lambda expects: [{"legacy_doc_id": str, "source_url": str}, ...]
            document_pairs = []
            for doc in selected_docs:
                # Extract legacy doc ID from filename (remove .pdf extension)
                legacy_doc_id = doc['filename'].replace('.pdf', '')
                source_url = doc['source_url']
                
                document_pairs.append({
                    'legacy_doc_id': legacy_doc_id,
                    'source_url': source_url
                })
            
            # Prepare the event payload in the format expected by restored Lambda
            event = {
                'action': 'test',  # Always use 'test' - Lambda only supports this action
                'document_pairs': document_pairs
            }
            
            logger.info(f"🚀 Invoking pipeline test Lambda: {self.lambda_function_name}")
            logger.info(f"📋 Action: test")
            logger.info(f"📄 Selected documents: {len(document_pairs)}")
            logger.info(f"📊 Total estimated pages: {sum(doc['estimated_pages'] for doc in selected_docs)}")
            
            # Show document pairs being sent
            for i, pair in enumerate(document_pairs, 1):
                logger.info(f"  {i}. {pair['legacy_doc_id']} → {pair['source_url'][:50]}...")
            
            # Invoke the Lambda function
            response = self.lambda_client.invoke(
                FunctionName=self.lambda_function_name,
                InvocationType='RequestResponse',  # Synchronous
                Payload=json.dumps(event, default=str)
            )
            
            # Parse the response
            status_code = response['StatusCode']
            payload = json.loads(response['Payload'].read())
            
            if status_code == 200:
                logger.info("✅ Lambda invocation successful")
                
                # Parse the response body
                if 'body' in payload:
                    body = json.loads(payload['body']) if isinstance(payload['body'], str) else payload['body']
                    return {
                        'success': True,
                        'lambda_status_code': status_code,
                        'response': body
                    }
                else:
                    return {
                        'success': True,
                        'lambda_status_code': status_code,
                        'response': payload
                    }
            else:
                logger.error(f"❌ Lambda invocation failed with status code: {status_code}")
                return {
                    'success': False,
                    'lambda_status_code': status_code,
                    'error': payload
                }
                
        except Exception as e:
            logger.error(f"❌ Error invoking Lambda function: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def print_results(self, result: Dict[str, Any]):
        """Print formatted results for simplified pipeline test"""
        if not result['success']:
            logger.error("=" * 60)
            logger.error("❌ PIPELINE TEST FAILED")
            logger.error("=" * 60)
            logger.error(f"Error: {result.get('error', 'Unknown error')}")
            return
        
        response = result['response']
        status = response.get('status', 'unknown')
        
        if status == 'completed':
            logger.info("=" * 60)
            logger.info("🎉 PIPELINE TEST SUCCESSFUL")
            logger.info("=" * 60)
            
            action = response.get('action', 'test')
            results = response.get('results', {})
            
            logger.info(f"📋 Action: {action}")
            logger.info(f"📄 Total Documents: {results.get('total_documents', 0)}")
            logger.info(f"✅ Successful Copies: {results.get('successful_copies', 0)}")
            logger.info(f"❌ Failed Copies: {results.get('failed_copies', 0)}")
            
            # Show individual document results
            if 'results' in results and results['results']:
                logger.info(f"\n📋 Document Processing Results:")
                for i, doc_result in enumerate(results['results'], 1):
                    if doc_result.get('success'):
                        legacy_id = doc_result.get('legacy_doc_id', 'unknown')
                        new_id = doc_result.get('new_doc_id', 'unknown')
                        target_key = doc_result.get('target_key', 'unknown')
                        logger.info(f"  {i}. ✅ {legacy_id} → {new_id}")
                        logger.info(f"     Copied to: {target_key}")
                        logger.info(f"     Source URL: {doc_result.get('source_url', 'unknown')[:60]}...")
                    else:
                        legacy_id = doc_result.get('legacy_doc_id', 'unknown')
                        error = doc_result.get('error', 'Unknown error')
                        logger.info(f"  {i}. ❌ {legacy_id}: {error}")
            
            # Success summary
            total = results.get('total_documents', 0)
            successful = results.get('successful_copies', 0)
            if successful == total:
                logger.info(f"\n🎉 ALL {total} DOCUMENTS PROCESSED SUCCESSFULLY!")
                logger.info("Documents copied to source bucket will trigger text extraction pipeline.")
            else:
                logger.warning(f"\n⚠️ {successful}/{total} documents processed successfully")
                
        elif status == 'failed':
            logger.error("=" * 60)
            logger.error("❌ PIPELINE TEST FAILED")
            logger.error("=" * 60)
            
            results = response.get('results', {})
            error = results.get('error', response.get('error', 'Unknown error'))
            logger.error(f"Error: {error}")
            
            # Show partial results if available
            if 'total_documents' in results:
                logger.info(f"📄 Total Documents: {results.get('total_documents', 0)}")
                logger.info(f"✅ Successful Copies: {results.get('successful_copies', 0)}")
                logger.info(f"❌ Failed Copies: {results.get('failed_copies', 0)}")
        
        else:
            logger.warning(f"⚠️  Unknown status: {status}")
            logger.info(f"Response: {json.dumps(response, indent=2, default=str)}")

def main():
    """Main execution with argument parsing"""
    parser = argparse.ArgumentParser(description='Invoke Pipeline Test Lambda Function')
    
    # Action selection - simplified to match restored Lambda
    parser.add_argument('--action', choices=['test'], 
                       default='test', help='Action to perform (only "test" supported)')
    
    # Document selection parameters
    parser.add_argument('--num-documents', type=int, default=5,
                       help='Number of documents to process (default: 5)')
    parser.add_argument('--min-size-mb', type=float, default=1.0,
                       help='Minimum document size in MB (default: 1.0)')
    parser.add_argument('--max-size-mb', type=float, default=10.0,
                       help='Maximum document size in MB (default: 10.0)')
    parser.add_argument('--language', type=str, default='english',
                       help='Document language (default: english)')
    parser.add_argument('--document-types', nargs='+', 
                       choices=['report', 'policy', 'research', 'project', 'financial', 'technical'],
                       help='Document types to include')
    parser.add_argument('--target-avg-pages', type=int, default=20,
                       help='Target average pages per document (default: 20)')
    
    # Control parameters
    parser.add_argument('--force', action='store_true',
                       help='Skip safety confirmations')
    parser.add_argument('--save-results', action='store_true',
                       help='Save results to JSON file')
    parser.add_argument('--skip-lambda-invocation', action='store_true',
                       help='Skip Lambda invocation for text extraction (for testing only)')
    
    args = parser.parse_args()
    
    try:
        # Initialize invoker
        invoker = PipelineTestInvoker()
        
        # Prepare parameters
        params = {
            'num_documents': args.num_documents,
            'min_size_mb': args.min_size_mb,
            'max_size_mb': args.max_size_mb,
            'language': args.language,
            'target_avg_pages': args.target_avg_pages,
            'force': args.force,
            'skip_lambda_invocation': args.skip_lambda_invocation
        }
        
        if args.document_types:
            params['document_types'] = args.document_types
        
        # Invoke the Lambda function
        result = invoker.invoke_pipeline_test(action=args.action, **params)
        
        # Print results
        invoker.print_results(result)
        
        # Save results if requested
        if args.save_results and result['success']:
            results_filename = f"pipeline_test_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            with open(results_filename, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            logger.info(f"📄 Results saved to: {results_filename}")
        
        # Return appropriate exit code
        return 0 if result['success'] else 1
        
    except Exception as e:
        logger.error(f"Client execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
