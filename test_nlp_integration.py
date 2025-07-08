#!/usr/bin/env python
"""
NLP Integration Testing Script
Tests the NLP worker Lambda function with real documents from S3
"""
import json
import boto3
import time
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NLPIntegrationTester:
    """Test NLP processing with real documents"""
    
    def __init__(self, profile_name='solve-global', region='us-east-1'):
        """Initialize AWS clients"""
        self.session = boto3.Session(profile_name=profile_name)
        self.lambda_client = self.session.client('lambda', region_name=region)
        self.s3_client = self.session.client('s3', region_name=region)
        self.region = region
        
        # S3 buckets
        self.text_bucket = 'solve-global-kr-text-861276078413-us-east-1'
        self.chunks_bucket = 'solve-global-kr-chunks-861276078413-us-east-1'
        self.ner_results_bucket = 'solve-global-kr-ner-results-861276078413-us-east-1'
        
        # Lambda functions
        self.nlp_worker_function = 'nlp-worker'
        
        logger.info("Initialized NLP Integration Tester for region {}".format(region))
    
    def get_test_documents(self, limit=5):
        """Get list of test documents from S3"""
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.text_bucket,
                Prefix='extracted_text/',
                MaxKeys=limit
            )
            
            documents = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Extract doc_id from filename
                    filename = obj['Key'].split('/')[-1]
                    doc_id = filename.replace('.txt', '')
                    
                    documents.append({
                        'doc_id': doc_id,
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified']
                    })
            
            logger.info("Found {} test documents".format(len(documents)))
            return documents
            
        except Exception as e:
            logger.error("Error getting test documents: {}".format(str(e)))
            return []
    
    def load_document_text(self, doc_key):
        """Load document text from S3"""
        
        try:
            response = self.s3_client.get_object(Bucket=self.text_bucket, Key=doc_key)
            text = response['Body'].read().decode('utf-8')
            logger.info("Loaded {} characters from {}".format(len(text), doc_key))
            return text
            
        except Exception as e:
            logger.error("Error loading document {}: {}".format(doc_key, str(e)))
            return ""
    
    def create_mock_chunks(self, doc_id, full_text):
        """Create mock chunks for testing (simulating text chunker output)"""
        
        # Simple chunking for testing - split by paragraphs
        paragraphs = [p.strip() for p in full_text.split('\n\n') if p.strip()]
        
        chunks = []
        current_offset = 0
        
        for i, paragraph in enumerate(paragraphs[:10]):  # Limit to 10 chunks for testing
            chunk = {
                'chunk_id': "{}_chunk_{:04d}".format(doc_id, i+1),
                'chunk_index': i,
                'text': paragraph,
                'start_offset': current_offset,
                'end_offset': current_offset + len(paragraph),
                'metadata': {
                    'doc_id': doc_id,
                    'chunk_type': 'paragraph',
                    'word_count': len(paragraph.split()),
                    'char_count': len(paragraph)
                }
            }
            chunks.append(chunk)
            current_offset += len(paragraph) + 2  # Account for paragraph breaks
        
        logger.info("Created {} mock chunks for {}".format(len(chunks), doc_id))
        return chunks
    
    def create_nlp_worker_event(self, doc_id, full_text, chunks):
        """Create event payload for NLP worker Lambda"""
        
        # Store full text temporarily in S3 for testing
        full_text_key = "test_full_text/{}_full_text.txt".format(doc_id)
        self.s3_client.put_object(
            Bucket=self.text_bucket,
            Key=full_text_key,
            Body=full_text.encode('utf-8'),
            ContentType='text/plain'
        )
        
        # Store chunks temporarily in S3 for testing
        chunks_prefix = "test_chunks/{}/".format(doc_id)
        for chunk in chunks:
            chunk_key = "{}{}".format(chunks_prefix, chunk['chunk_id'] + '.json')
            self.s3_client.put_object(
                Bucket=self.chunks_bucket,
                Key=chunk_key,
                Body=json.dumps(chunk, indent=2).encode('utf-8'),
                ContentType='application/json'
            )
        
        # Create SNS message format that NLP worker expects
        sns_message = {
            'doc_id': doc_id,
            'chunks_location': {
                'bucket': self.chunks_bucket,
                'prefix': chunks_prefix,
                'pattern': "{}_chunk_NNNN.json".format(doc_id),
                'sequence_range': "0001-{:04d}".format(len(chunks))
            },
            'full_text_location': {
                'bucket': self.text_bucket,
                'key': full_text_key
            },
            'nlp_provider': 'comprehend',
            'processing_type': 'entity_and_phrases'
        }
        
        # Wrap in SQS message format
        sqs_message = {
            'Message': json.dumps(sns_message),
            'MessageId': 'test-message-{}'.format(int(time.time())),
            'Timestamp': datetime.now().isoformat()
        }
        
        # Create Lambda event
        event = {
            'Records': [
                {
                    'body': json.dumps(sqs_message),
                    'messageId': sqs_message['MessageId'],
                    'receiptHandle': 'test-receipt-handle',
                    'attributes': {
                        'ApproximateReceiveCount': '1',
                        'SentTimestamp': str(int(time.time() * 1000))
                    }
                }
            ]
        }
        
        return event
    
    def invoke_nlp_worker(self, event):
        """Invoke NLP worker Lambda function"""
        
        try:
            logger.info("Invoking NLP worker Lambda function...")
            
            response = self.lambda_client.invoke(
                FunctionName=self.nlp_worker_function,
                InvocationType='RequestResponse',  # Synchronous for testing
                Payload=json.dumps(event)
            )
            
            # Parse response
            payload = json.loads(response['Payload'].read())
            
            logger.info("NLP worker response status: {}".format(response['StatusCode']))
            
            if response['StatusCode'] == 200:
                logger.info("✅ NLP worker invocation successful")
                if 'body' in payload:
                    body = json.loads(payload['body']) if isinstance(payload['body'], str) else payload['body']
                    logger.info("Processing result: {}".format(body))
                return payload
            else:
                logger.error("❌ NLP worker invocation failed: {}".format(payload))
                return payload
                
        except Exception as e:
            logger.error("Error invoking NLP worker: {}".format(str(e)))
            return {'error': str(e)}
    
    def check_nlp_results(self, doc_id):
        """Check if NLP results were stored in S3"""
        
        try:
            # Check for NLP results in S3
            results_prefix = "{}/".format(doc_id)
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.ner_results_bucket,
                Prefix=results_prefix
            )
            
            if 'Contents' in response:
                logger.info("✅ Found {} NLP result files for {}".format(len(response['Contents']), doc_id))
                
                # Load the main results file
                for obj in response['Contents']:
                    if obj['Key'].endswith('_nlp_results.json'):
                        result_response = self.s3_client.get_object(
                            Bucket=self.ner_results_bucket,
                            Key=obj['Key']
                        )
                        results = json.loads(result_response['Body'].read().decode('utf-8'))
                        
                        logger.info("NLP Results Summary:")
                        logger.info("  - Entities found: {}".format(len(results.get('entities', []))))
                        logger.info("  - Key phrases found: {}".format(len(results.get('key_phrases', []))))
                        logger.info("  - Processing cost: ${:.6f}".format(results.get('processing_cost', 0)))
                        logger.info("  - Processing duration: {:.2f}s".format(results.get('processing_duration', 0)))
                        
                        return results
            else:
                logger.warning("❌ No NLP results found for {}".format(doc_id))
                return {}
                
        except Exception as e:
            logger.error("Error checking NLP results: {}".format(str(e)))
            return {}
    
    def cleanup_test_files(self, doc_id):
        """Clean up temporary test files"""
        
        try:
            # Clean up full text file
            full_text_key = "test_full_text/{}_full_text.txt".format(doc_id)
            self.s3_client.delete_object(Bucket=self.text_bucket, Key=full_text_key)
            
            # Clean up chunk files
            chunks_prefix = "test_chunks/{}/".format(doc_id)
            response = self.s3_client.list_objects_v2(
                Bucket=self.chunks_bucket,
                Prefix=chunks_prefix
            )
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    self.s3_client.delete_object(Bucket=self.chunks_bucket, Key=obj['Key'])
            
            logger.info("Cleaned up test files for {}".format(doc_id))
            
        except Exception as e:
            logger.warning("Error cleaning up test files: {}".format(str(e)))
    
    def run_single_document_test(self, doc_info):
        """Run NLP test on a single document"""
        
        doc_id = doc_info['doc_id']
        logger.info("\n" + "="*60)
        logger.info("🧪 TESTING DOCUMENT: {}".format(doc_id))
        logger.info("   Size: {} bytes".format(doc_info['size']))
        logger.info("   Key: {}".format(doc_info['key']))
        logger.info("="*60)
        
        try:
            # Load document text
            full_text = self.load_document_text(doc_info['key'])
            if not full_text:
                return {'error': 'Failed to load document text'}
            
            # Create mock chunks
            chunks = self.create_mock_chunks(doc_id, full_text)
            if not chunks:
                return {'error': 'Failed to create chunks'}
            
            # Create NLP worker event
            event = self.create_nlp_worker_event(doc_id, full_text, chunks)
            
            # Invoke NLP worker
            start_time = time.time()
            result = self.invoke_nlp_worker(event)
            processing_time = time.time() - start_time
            
            # Wait a moment for S3 consistency
            time.sleep(2)
            
            # Check results
            nlp_results = self.check_nlp_results(doc_id)
            
            # Clean up test files
            self.cleanup_test_files(doc_id)
            
            test_result = {
                'doc_id': doc_id,
                'success': 'error' not in result,
                'processing_time': processing_time,
                'lambda_result': result,
                'nlp_results': nlp_results,
                'text_length': len(full_text),
                'chunks_created': len(chunks)
            }
            
            if test_result['success']:
                logger.info("✅ Test PASSED for {}".format(doc_id))
            else:
                logger.error("❌ Test FAILED for {}".format(doc_id))
            
            return test_result
            
        except Exception as e:
            logger.error("Error in single document test: {}".format(str(e)))
            return {'error': str(e), 'doc_id': doc_id}
    
    def run_integration_tests(self, num_documents=3):
        """Run NLP integration tests on multiple documents"""
        
        logger.info("\n🚀 STARTING NLP INTEGRATION TESTS")
        logger.info("Testing {} documents".format(num_documents))
        logger.info("Target Lambda: {}".format(self.nlp_worker_function))
        logger.info("Region: {}".format(self.region))
        
        # Get test documents
        test_docs = self.get_test_documents(limit=num_documents)
        if not test_docs:
            logger.error("No test documents found!")
            return {'error': 'No test documents available'}
        
        # Run tests
        results = []
        total_cost = 0
        successful_tests = 0
        
        for doc_info in test_docs:
            result = self.run_single_document_test(doc_info)
            results.append(result)
            
            if result.get('success'):
                successful_tests += 1
                if 'nlp_results' in result and 'processing_cost' in result['nlp_results']:
                    total_cost += result['nlp_results']['processing_cost']
        
        # Summary
        logger.info("\n📊 TEST SUMMARY")
        logger.info("="*60)
        logger.info("Total documents tested: {}".format(len(results)))
        logger.info("Successful tests: {}".format(successful_tests))
        logger.info("Failed tests: {}".format(len(results) - successful_tests))
        logger.info("Success rate: {:.1f}%".format(successful_tests/len(results)*100))
        logger.info("Total processing cost: ${:.6f}".format(total_cost))
        logger.info("Average cost per document: ${:.6f}".format(total_cost/len(results) if results else 0))
        logger.info("="*60)
        
        return {
            'summary': {
                'total_tests': len(results),
                'successful_tests': successful_tests,
                'failed_tests': len(results) - successful_tests,
                'success_rate': successful_tests/len(results)*100 if results else 0,
                'total_cost': total_cost,
                'average_cost_per_doc': total_cost/len(results) if results else 0
            },
            'detailed_results': results
        }

def main():
    """Main test execution"""
    
    # Initialize tester
    tester = NLPIntegrationTester()
    
    # Run integration tests
    results = tester.run_integration_tests(num_documents=3)
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = 'nlp_integration_test_results_{}.json'.format(timestamp)
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info("\n💾 Results saved to: {}".format(results_file))
    
    return results

if __name__ == '__main__':
    main()
