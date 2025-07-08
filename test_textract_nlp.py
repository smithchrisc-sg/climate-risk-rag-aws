#!/usr/bin/env python3
"""
Textract Document NLP Testing Script
Tests NLP processing on clean Textract-extracted English documents
"""
import json
import boto3
import time
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TextractNLPTester:
    """Test NLP processing with clean Textract-extracted documents"""
    
    def __init__(self, profile_name='solve-global', region='us-east-1'):
        """Initialize AWS clients"""
        self.session = boto3.Session(profile_name=profile_name)
        self.lambda_client = self.session.client('lambda', region_name=region)
        self.s3_client = self.session.client('s3', region_name=region)
        self.region = region
        
        # S3 buckets - CORRECTED to use Textract bucket
        self.text_bucket = 'solve-global-kr-text-new-861276078413-us-east-1'  # Textract output
        self.chunks_bucket = 'solve-global-kr-chunks-861276078413-us-east-1'
        self.ner_results_bucket = 'solve-global-kr-ner-results-861276078413-us-east-1'
        
        # Lambda functions
        self.nlp_worker_function = 'nlp-worker'
        
        logger.info("Initialized Textract NLP Tester for region {}".format(region))
        logger.info("Using Textract text bucket: {}".format(self.text_bucket))
    
    def get_textract_documents(self):
        """Get available Textract-extracted documents"""
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.text_bucket,
                Prefix='extracted_text/'
            )
            
            documents = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'].endswith('.txt'):
                        # Extract doc_id from filename
                        filename = obj['Key'].split('/')[-1]
                        doc_id = filename.replace('.txt', '')
                        
                        documents.append({
                            'doc_id': doc_id,
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified']
                        })
            
            logger.info("Found {} Textract documents".format(len(documents)))
            return documents
            
        except Exception as e:
            logger.error("Error getting Textract documents: {}".format(str(e)))
            return []
    
    def load_document_text(self, doc_key):
        """Load document text from Textract S3 bucket"""
        
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
        
        # Simple chunking for testing - split by paragraphs or sections
        sections = []
        current_section = ""
        
        for line in full_text.split('\n'):
            if line.strip().startswith('---') or line.strip().startswith('Page'):
                # New page/section marker
                if current_section.strip():
                    sections.append(current_section.strip())
                current_section = line + '\n'
            else:
                current_section += line + '\n'
        
        # Add final section
        if current_section.strip():
            sections.append(current_section.strip())
        
        # If no sections found, split by double newlines
        if len(sections) <= 1:
            sections = [s.strip() for s in full_text.split('\n\n') if s.strip()]
        
        chunks = []
        current_offset = 0
        
        for i, section in enumerate(sections[:20]):  # Limit to 20 chunks for testing
            chunk = {
                'chunk_id': "{}_chunk_{:04d}".format(doc_id, i+1),
                'chunk_index': i,
                'text': section,
                'start_offset': current_offset,
                'end_offset': current_offset + len(section),
                'metadata': {
                    'doc_id': doc_id,
                    'chunk_type': 'section',
                    'word_count': len(section.split()),
                    'char_count': len(section)
                }
            }
            chunks.append(chunk)
            current_offset += len(section) + 2  # Account for section breaks
        
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
    
    def download_and_analyze_results(self, doc_id):
        """Download and analyze NLP results"""
        
        try:
            # Check for NLP results in S3
            results_prefix = "{}/".format(doc_id)
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.ner_results_bucket,
                Prefix=results_prefix
            )
            
            if 'Contents' not in response:
                logger.warning("❌ No NLP results found for {}".format(doc_id))
                return None
            
            logger.info("✅ Found {} NLP result files for {}".format(len(response['Contents']), doc_id))
            
            # Download all result files
            results = {}
            for obj in response['Contents']:
                file_key = obj['Key']
                file_name = file_key.split('/')[-1]
                
                result_response = self.s3_client.get_object(
                    Bucket=self.ner_results_bucket,
                    Key=file_key
                )
                file_content = json.loads(result_response['Body'].read().decode('utf-8'))
                results[file_name] = file_content
                
                # Save locally for analysis
                local_filename = "textract_{}".format(file_name)
                with open(local_filename, 'w') as f:
                    json.dump(file_content, f, indent=2)
                logger.info("Saved {} locally as {}".format(file_name, local_filename))
            
            return results
                
        except Exception as e:
            logger.error("Error downloading NLP results: {}".format(str(e)))
            return None
    
    def analyze_entity_categories(self, results):
        """Analyze entity categories for manual review"""
        
        if not results:
            logger.error("No results provided for analysis")
            return
        
        # Find entities file
        entities_file = None
        for filename, content in results.items():
            if 'entities_' in filename:
                entities_file = content
                break
        
        if not entities_file:
            logger.error("Could not find entities in results")
            return
        
        # Analyze entity categories
        entity_categories = {}
        for entity in entities_file.get('entities', []):
            entity_type = entity.get('entity_type', 'UNKNOWN')
            if entity_type not in entity_categories:
                entity_categories[entity_type] = []
            entity_categories[entity_type].append({
                'text': entity.get('text', ''),
                'confidence': entity.get('confidence', 0)
            })
        
        # Print analysis
        logger.info("\n" + "="*60)
        logger.info("ENTITY CATEGORY ANALYSIS - TEXTRACT DOCUMENT")
        logger.info("="*60)
        
        for category, entities in sorted(entity_categories.items()):
            logger.info("\n{} ({} entities):".format(category, len(entities)))
            logger.info("-" * 40)
            for entity in sorted(entities, key=lambda x: x['confidence'], reverse=True)[:15]:
                logger.info("  • \"{}\" (confidence: {:.3f})".format(entity['text'], entity['confidence']))
            if len(entities) > 15:
                logger.info("  ... and {} more".format(len(entities) - 15))
        
        return entity_categories
    
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
    
    def test_textract_document(self, doc_info):
        """Test NLP processing on a single Textract document"""
        
        doc_id = doc_info['doc_id']
        doc_key = doc_info['key']
        
        logger.info("\n" + "="*60)
        logger.info("🧪 TESTING TEXTRACT DOCUMENT: {}".format(doc_id))
        logger.info("   Key: {}".format(doc_key))
        logger.info("   Size: {} bytes".format(doc_info['size']))
        logger.info("="*60)
        
        try:
            # Load document text
            full_text = self.load_document_text(doc_key)
            if not full_text:
                return {'error': 'Failed to load document text'}
            
            # Show sample of clean text
            logger.info("Sample text (first 200 chars): \"{}...\"".format(full_text[:200]))
            
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
            time.sleep(3)
            
            # Download and analyze results
            nlp_results = self.download_and_analyze_results(doc_id)
            
            if nlp_results:
                # Analyze entity categories
                entity_categories = self.analyze_entity_categories(nlp_results)
                
                # Print summary
                logger.info("\n" + "="*60)
                logger.info("PROCESSING SUMMARY - TEXTRACT DOCUMENT")
                logger.info("="*60)
                logger.info("Document: {}".format(doc_id))
                logger.info("Text length: {} characters".format(len(full_text)))
                logger.info("Chunks created: {}".format(len(chunks)))
                logger.info("Processing time: {:.2f} seconds".format(processing_time))
                
                # Extract cost info if available
                for filename, content in nlp_results.items():
                    if 'metadata' in filename:
                        cost = content.get('processing_cost', 0)
                        entities_count = content.get('results_summary', {}).get('entities_count', 0)
                        phrases_count = content.get('results_summary', {}).get('key_phrases_count', 0)
                        logger.info("Processing cost: ${:.5f}".format(cost))
                        logger.info("Entities found: {}".format(entities_count))
                        logger.info("Key phrases found: {}".format(phrases_count))
                        break
            
            # Clean up test files
            self.cleanup_test_files(doc_id)
            
            return {
                'doc_id': doc_id,
                'success': True,
                'processing_time': processing_time,
                'text_length': len(full_text),
                'chunks_created': len(chunks),
                'nlp_results': nlp_results
            }
            
        except Exception as e:
            logger.error("Error in Textract document test: {}".format(str(e)))
            return {'error': str(e), 'doc_id': doc_id}

def main():
    """Main test execution"""
    
    # Initialize tester
    tester = TextractNLPTester()
    
    logger.info("🚀 STARTING TEXTRACT NLP TESTING")
    
    # Get available Textract documents
    textract_docs = tester.get_textract_documents()
    
    if not textract_docs:
        logger.error("No Textract documents found!")
        return
    
    # Test the first available document
    doc_to_test = textract_docs[0]
    logger.info("Testing document: {}".format(doc_to_test['doc_id']))
    
    # Run test
    result = tester.test_textract_document(doc_to_test)
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = 'textract_nlp_test_results_{}.json'.format(timestamp)
    
    with open(results_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    logger.info("\n💾 Results saved to: {}".format(results_file))
    
    return result

if __name__ == '__main__':
    main()
