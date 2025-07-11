#!/usr/bin/env python3
"""
Pipeline Test Lambda Invoker
Local client script to invoke the pipeline test Lambda function with parameters
"""

import boto3
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PipelineTestInvoker:
    """Client for invoking the pipeline test Lambda function"""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        self.lambda_function_name = 'solve-global-kr-pipeline-test-function'
    
    def invoke_pipeline_test(self, action: str = 'setup_and_test', **params) -> Dict[str, Any]:
        """Invoke the pipeline test Lambda function"""
        try:
            # Prepare the event payload
            event = {
                'action': action,
                'parameters': params,
                'invoked_at': datetime.utcnow().isoformat() + "Z",
                'invoked_by': 'local_client'
            }
            
            logger.info(f"🚀 Invoking pipeline test Lambda: {self.lambda_function_name}")
            logger.info(f"📋 Action: {action}")
            logger.info(f"🎛️  Parameters: {json.dumps(params, indent=2)}")
            
            # Invoke the Lambda function
            response = self.lambda_client.invoke(
                FunctionName=self.lambda_function_name,
                InvocationType='RequestResponse',  # Synchronous
                Payload=json.dumps(event)
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
