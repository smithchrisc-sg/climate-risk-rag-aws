#!/usr/bin/env python3
"""
Pipeline Test Lambda Invoker
Local client script that queries SQLite locally and sends document list to Lambda
"""

import boto3
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
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
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
    
    def invoke_pipeline_test(self, action: str = 'setup_and_test', **params) -> Dict[str, Any]:
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
            
            # Prepare the event payload with pre-selected documents
            event = {
                'action': action,
                'parameters': params,
                'selected_documents': selected_docs,  # Send documents to Lambda
                'invoked_at': datetime.utcnow().isoformat() + "Z",
                'invoked_by': 'local_client_with_sqlite'
            }
            
            logger.info(f"🚀 Invoking pipeline test Lambda: {self.lambda_function_name}")
            logger.info(f"📋 Action: {action}")
            logger.info(f"📄 Selected documents: {len(selected_docs)}")
            logger.info(f"📊 Total estimated pages: {sum(doc['estimated_pages'] for doc in selected_docs)}")
            
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
        """Print formatted results"""
        if not result['success']:
            logger.error("=" * 60)
            logger.error("❌ PIPELINE TEST FAILED")
            logger.error("=" * 60)
            logger.error(f"Error: {result.get('error', 'Unknown error')}")
            return
        
        response = result['response']
        status = response.get('status', 'unknown')
        
        if status == 'success':
            logger.info("=" * 60)
            logger.info("🎉 PIPELINE TEST SUCCESSFUL")
            logger.info("=" * 60)
            
            action = response.get('action', 'unknown')
            logger.info(f"📋 Action: {action}")
            
            if 'documents_prepared' in response:
                logger.info(f"📄 Documents Prepared: {response['documents_prepared']}")
                
                if 'statistics' in response:
                    stats = response['statistics']
                    logger.info(f"📊 Statistics:")
                    logger.info(f"  - Total Estimated Pages: {stats.get('total_estimated_pages', 0)}")
                    logger.info(f"  - Average Pages per Doc: {stats.get('average_pages', 0):.1f}")
                    logger.info(f"  - Total Size: {stats.get('total_size_mb', 0):.1f} MB")
                    logger.info(f"  - Average Size per Doc: {stats.get('average_size_mb', 0):.1f} MB")
            
            if 'documents_tested' in response:
                logger.info(f"🧪 Documents Tested: {response['documents_tested']}")
                logger.info(f"✅ Successful Triggers: {response.get('successful_triggers', 0)}")
                logger.info(f"❌ Failed Triggers: {response.get('failed_triggers', 0)}")
                logger.info(f"📈 Trigger Success Rate: {response.get('trigger_success_rate', 0):.1f}%")
                logger.info(f"📄 Total Estimated Pages: {response.get('total_estimated_pages', 0)}")
            
            # Show prepared documents
            if 'prepared_documents' in response:
                logger.info(f"\n📋 Prepared Documents:")
                for i, doc in enumerate(response['prepared_documents'], 1):
                    logger.info(f"  {i}. {doc['source_key']} ({doc['size_mb']} MB, ~{doc['estimated_pages']} pages)")
                    logger.info(f"     Source: {doc['source_url']}")
            
            # Show trigger results
            if 'trigger_results' in response:
                logger.info(f"\n🚀 Trigger Results:")
                for i, result in enumerate(response['trigger_results'], 1):
                    status_icon = "✅" if result['status'] == 'triggered' else "❌"
                    logger.info(f"  {i}. {status_icon} {result['doc_id']}: {result['status']}")
                    if result['status'] == 'failed':
                        logger.info(f"     Error: {result.get('error', 'Unknown error')}")
        
        elif status == 'failed':
            logger.error("=" * 60)
            logger.error("❌ PIPELINE TEST FAILED")
            logger.error("=" * 60)
            logger.error(f"Error: {response.get('error', 'Unknown error')}")
            
            if response.get('requires_force'):
                logger.warning("💡 Hint: Use --force to bypass safety limits")
        
        else:
            logger.warning(f"⚠️  Unknown status: {status}")
            logger.info(f"Response: {json.dumps(response, indent=2, default=str)}")

def main():
    """Main execution with argument parsing"""
    parser = argparse.ArgumentParser(description='Invoke Pipeline Test Lambda Function')
    
    # Action selection
    parser.add_argument('--action', choices=['setup_only', 'test_only', 'setup_and_test'], 
                       default='setup_and_test', help='Action to perform (default: setup_and_test)')
    
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
            'force': args.force
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
