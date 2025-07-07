"""
TextExtractor Lambda Function
Extracts text from PDF documents using AWS Textract with structured document analysis
Replaces the original Tika-based text extraction with AWS-native solution
"""

import json
import boto3
import logging
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from urllib.parse import unquote_plus
import time

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class TextExtractor:
    """AWS Textract-based text extractor with structured document analysis"""
    
    def __init__(self, profile_name=None):
        # Use profile if provided (for local testing)
        session = boto3.Session(profile_name=profile_name) if profile_name else boto3.Session()
        
        self.textract = session.client('textract')
        self.s3 = session.client('s3')
        
        # Configuration from environment variables
        self.output_bucket = os.environ.get('OUTPUT_BUCKET', 'solve-global-kr-text-new-861276078413-us-east-1')
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        
        logger.info(f"TextExtractor initialized - Output bucket: {self.output_bucket}")

    def extract_text_from_pdf(self, bucket: str, key: str) -> Dict[str, Any]:
        """
        Extract text from PDF using AWS Textract
        
        Args:
            bucket: S3 bucket containing the PDF
            key: S3 key of the PDF file
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        try:
            logger.info(f"Starting text extraction for s3://{bucket}/{key}")
            
            # For large documents, use asynchronous processing
            # For smaller documents (< 5MB), use synchronous processing
            object_info = self.s3.head_object(Bucket=bucket, Key=key)
            file_size = object_info['ContentLength']
            
            if file_size > 5 * 1024 * 1024:  # 5MB threshold
                return self._extract_async(bucket, key)
            else:
                return self._extract_sync(bucket, key)
                
        except Exception as e:
            logger.error(f"Error extracting text from {bucket}/{key}: {str(e)}")
            raise

    def _extract_sync(self, bucket: str, key: str) -> Dict[str, Any]:
        """Synchronous text extraction for smaller documents"""
        try:
            # Call Textract synchronously
            response = self.textract.detect_document_text(
                Document={
                    'S3Object': {
                        'Bucket': bucket,
                        'Name': key
                    }
                }
            )
            
            return self._process_textract_response(response, bucket, key)
            
        except Exception as e:
            logger.error(f"Synchronous extraction failed for {bucket}/{key}: {str(e)}")
            raise

    def _extract_async(self, bucket: str, key: str) -> Dict[str, Any]:
        """Asynchronous text extraction for larger documents"""
        try:
            # Start asynchronous job
            response = self.textract.start_document_text_detection(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': bucket,
                        'Name': key
                    }
                }
            )
            
            job_id = response['JobId']
            logger.info(f"Started async Textract job: {job_id}")
            
            # Poll for completion
            max_wait_time = 300  # 5 minutes max wait
            poll_interval = 5    # 5 seconds between polls
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                time.sleep(poll_interval)
                elapsed_time += poll_interval
                
                result = self.textract.get_document_text_detection(JobId=job_id)
                status = result['JobStatus']
                
                if status == 'SUCCEEDED':
                    logger.info(f"Async job {job_id} completed successfully")
                    return self._process_textract_response(result, bucket, key, is_async=True)
                elif status == 'FAILED':
                    raise Exception(f"Textract job failed: {result.get('StatusMessage', 'Unknown error')}")
                elif status in ['IN_PROGRESS']:
                    logger.info(f"Job {job_id} still in progress... ({elapsed_time}s elapsed)")
                    continue
                else:
                    raise Exception(f"Unexpected job status: {status}")
            
            raise Exception(f"Textract job timed out after {max_wait_time} seconds")
            
        except Exception as e:
            logger.error(f"Asynchronous extraction failed for {bucket}/{key}: {str(e)}")
            raise

    def _process_textract_response(self, response: Dict, bucket: str, key: str, is_async: bool = False) -> Dict[str, Any]:
        """Process Textract response and extract structured text"""
        try:
            blocks = response.get('Blocks', [])
            
            # Extract text content
            extracted_text = self._extract_text_content(blocks)
            
            # Extract document structure
            document_structure = self._analyze_document_structure(blocks)
            
            # Generate metadata
            metadata = self._generate_metadata(response, bucket, key, len(extracted_text), is_async)
            
            return {
                'text_content': extracted_text,
                'document_structure': document_structure,
                'metadata': metadata,
                'textract_response': response  # Keep full response for debugging
            }
            
        except Exception as e:
            logger.error(f"Error processing Textract response: {str(e)}")
            raise

    def _extract_text_content(self, blocks: List[Dict]) -> str:
        """Extract plain text content from Textract blocks"""
        text_lines = []
        
        # Sort blocks by page and position
        line_blocks = [block for block in blocks if block['BlockType'] == 'LINE']
        
        # Sort by page number, then by top position, then by left position
        line_blocks.sort(key=lambda x: (
            x.get('Page', 1),
            x.get('Geometry', {}).get('BoundingBox', {}).get('Top', 0),
            x.get('Geometry', {}).get('BoundingBox', {}).get('Left', 0)
        ))
        
        for block in line_blocks:
            if 'Text' in block:
                text_lines.append(block['Text'])
        
        return '\n'.join(text_lines)

    def _analyze_document_structure(self, blocks: List[Dict]) -> Dict[str, Any]:
        """Analyze document structure from Textract blocks"""
        structure = {
            'pages': [],
            'tables': [],
            'key_value_pairs': [],
            'statistics': {}
        }
        
        # Group blocks by page
        pages = {}
        for block in blocks:
            page_num = block.get('Page', 1)
            if page_num not in pages:
                pages[page_num] = []
            pages[page_num].append(block)
        
        # Analyze each page
        for page_num, page_blocks in pages.items():
            page_info = {
                'page_number': page_num,
                'line_count': len([b for b in page_blocks if b['BlockType'] == 'LINE']),
                'word_count': len([b for b in page_blocks if b['BlockType'] == 'WORD']),
                'table_count': len([b for b in page_blocks if b['BlockType'] == 'TABLE'])
            }
            structure['pages'].append(page_info)
        
        # Extract tables if present
        table_blocks = [block for block in blocks if block['BlockType'] == 'TABLE']
        for table in table_blocks:
            structure['tables'].append({
                'page': table.get('Page', 1),
                'confidence': table.get('Confidence', 0),
                'row_count': table.get('RowCount', 0),
                'column_count': table.get('ColumnCount', 0)
            })
        
        # Calculate statistics
        structure['statistics'] = {
            'total_pages': len(pages),
            'total_lines': len([b for b in blocks if b['BlockType'] == 'LINE']),
            'total_words': len([b for b in blocks if b['BlockType'] == 'WORD']),
            'total_tables': len(table_blocks),
            'average_confidence': sum(b.get('Confidence', 0) for b in blocks) / len(blocks) if blocks else 0
        }
        
        return structure

    def _generate_metadata(self, response: Dict, bucket: str, key: str, text_length: int, is_async: bool) -> Dict[str, Any]:
        """Generate comprehensive metadata for the extraction"""
        return {
            'source_document': {
                'bucket': bucket,
                'key': key,
                'document_id': os.path.splitext(os.path.basename(key))[0]
            },
            'extraction_info': {
                'method': 'aws_textract_async' if is_async else 'aws_textract_sync',
                'extraction_date': datetime.utcnow().isoformat(),
                'text_length': text_length,
                'word_count': len(str(response).split()) if response else 0,
                'status': 'success'
            },
            'textract_metadata': {
                'detect_document_text_model_version': response.get('DetectDocumentTextModelVersion'),
                'job_status': response.get('JobStatus'),
                'pages_processed': len(set(block.get('Page', 1) for block in response.get('Blocks', [])))
            }
        }

    def save_extracted_text(self, extracted_data: Dict[str, Any], document_id: str) -> str:
        """Save extracted text and metadata to S3"""
        try:
            # Create output key
            output_key = f"extracted_text/{document_id}.txt"
            metadata_key = f"extraction_metadata/{document_id}.json"
            
            # Save plain text
            self.s3.put_object(
                Bucket=self.output_bucket,
                Key=output_key,
                Body=extracted_data['text_content'].encode('utf-8'),
                ContentType='text/plain',
                Metadata={
                    'source-document': extracted_data['metadata']['source_document']['key'],
                    'extraction-method': extracted_data['metadata']['extraction_info']['method'],
                    'extraction-date': extracted_data['metadata']['extraction_info']['extraction_date']
                }
            )
            
            # Save metadata
            self.s3.put_object(
                Bucket=self.output_bucket,
                Key=metadata_key,
                Body=json.dumps(extracted_data['metadata'], indent=2).encode('utf-8'),
                ContentType='application/json'
            )
            
            logger.info(f"Saved extracted text to s3://{self.output_bucket}/{output_key}")
            logger.info(f"Saved metadata to s3://{self.output_bucket}/{metadata_key}")
            
            return f"s3://{self.output_bucket}/{output_key}"
            
        except Exception as e:
            logger.error(f"Error saving extracted text: {str(e)}")
            raise

def handler(event, context):
    """
    Lambda function handler for text extraction
    Triggered by S3 events when PDFs are uploaded to the documents bucket
    """
    try:
        logger.info(f"TextExtractor Lambda triggered with event: {json.dumps(event)}")
        
        extractor = TextExtractor()
        
        # Handle S3 event
        if 'Records' in event:
            results = []
            
            for record in event['Records']:
                # Parse S3 event
                bucket = record['s3']['bucket']['name']
                key = unquote_plus(record['s3']['object']['key'])
                
                logger.info(f"Processing document: s3://{bucket}/{key}")
                
                # Skip non-PDF files
                if not key.lower().endswith('.pdf'):
                    logger.info(f"Skipping non-PDF file: {key}")
                    continue
                
                # Extract document ID from filename
                document_id = os.path.splitext(os.path.basename(key))[0]
                
                try:
                    # Extract text using Textract
                    extracted_data = extractor.extract_text_from_pdf(bucket, key)
                    
                    # Save extracted text
                    output_location = extractor.save_extracted_text(extracted_data, document_id)
                    
                    result = {
                        'document_id': document_id,
                        'source_location': f"s3://{bucket}/{key}",
                        'output_location': output_location,
                        'status': 'success',
                        'text_length': len(extracted_data['text_content']),
                        'word_count': extracted_data['metadata']['extraction_info']['word_count'],
                        'pages_processed': extracted_data['metadata']['textract_metadata']['pages_processed']
                    }
                    
                    results.append(result)
                    logger.info(f"Successfully processed {document_id}")
                    
                except Exception as e:
                    error_result = {
                        'document_id': document_id,
                        'source_location': f"s3://{bucket}/{key}",
                        'status': 'error',
                        'error': str(e)
                    }
                    results.append(error_result)
                    logger.error(f"Failed to process {document_id}: {str(e)}")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'Processed {len(results)} documents',
                    'results': results
                })
            }
        
        # Handle direct invocation for testing
        elif 'bucket' in event and 'key' in event:
            bucket = event['bucket']
            key = event['key']
            document_id = os.path.splitext(os.path.basename(key))[0]
            
            logger.info(f"Direct invocation - processing: s3://{bucket}/{key}")
            
            # Extract text
            extracted_data = extractor.extract_text_from_pdf(bucket, key)
            
            # Save extracted text
            output_location = extractor.save_extracted_text(extracted_data, document_id)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Text extraction completed',
                    'document_id': document_id,
                    'output_location': output_location,
                    'text_length': len(extracted_data['text_content']),
                    'word_count': extracted_data['metadata']['extraction_info']['word_count']
                })
            }
        
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid event format. Expected S3 event or direct invocation with bucket/key.'
                })
            }
            
    except Exception as e:
        logger.error(f"TextExtractor Lambda error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Text extraction failed: {str(e)}'
            })
        }
