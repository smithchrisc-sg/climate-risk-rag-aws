"""
Fixed TextExtractor Lambda Function
Uses async Textract processing for better PDF compatibility
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

class FixedTextExtractor:
    """Fixed text extractor using async Textract for better compatibility"""
    
    def __init__(self, profile_name=None):
        # Use profile if provided (for local testing)
        session = boto3.Session(profile_name=profile_name) if profile_name else boto3.Session()
        
        self.textract = session.client('textract')
        self.s3 = session.client('s3')
        
        # Configuration from environment variables
        self.output_bucket = os.environ.get('OUTPUT_BUCKET', 'solve-global-kr-text-new-861276078413-us-east-1')
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        
        logger.info(f"FixedTextExtractor initialized - Output bucket: {self.output_bucket}")

    def extract_text_from_pdf(self, bucket: str, key: str) -> Dict[str, Any]:
        """
        Extract text from PDF using the most compatible Textract method
        
        Args:
            bucket: S3 bucket containing the PDF
            key: S3 key of the PDF file
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        try:
            logger.info(f"Starting text extraction for s3://{bucket}/{key}")
            
            # Get file size to determine processing method
            object_info = self.s3.head_object(Bucket=bucket, Key=key)
            file_size = object_info['ContentLength']
            
            # Try sync first for small files, then async for better compatibility
            if file_size < 1024 * 1024:  # 1MB threshold for sync attempt
                try:
                    return self._extract_sync(bucket, key)
                except Exception as sync_error:
                    logger.warning(f"Sync extraction failed: {str(sync_error)}")
                    logger.info("Falling back to async processing...")
                    return self._extract_async(bucket, key, sync_error)
            else:
                # Use async directly for larger files
                return self._extract_async(bucket, key)
                
        except Exception as e:
            logger.error(f"Error extracting text from {bucket}/{key}: {str(e)}")
            raise

    def _extract_sync(self, bucket: str, key: str) -> Dict[str, Any]:
        """Synchronous text extraction (for small, compatible PDFs)"""
        try:
            response = self.textract.detect_document_text(
                Document={
                    'S3Object': {
                        'Bucket': bucket,
                        'Name': key
                    }
                }
            )
            
            return self._process_textract_response(response, bucket, key, 'sync')
            
        except Exception as e:
            logger.error(f"Synchronous extraction failed for {bucket}/{key}: {str(e)}")
            raise

    def _extract_async(self, bucket: str, key: str, sync_error: Exception = None) -> Dict[str, Any]:
        """Asynchronous text extraction (for better compatibility)"""
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
                    return self._process_textract_response(result, bucket, key, 'async', sync_error)
                elif status == 'FAILED':
                    error_msg = result.get('StatusMessage', 'Unknown error')
                    raise Exception(f"Textract async job failed: {error_msg}")
                elif status in ['IN_PROGRESS']:
                    logger.info(f"Job {job_id} still in progress... ({elapsed_time}s elapsed)")
                    continue
                else:
                    raise Exception(f"Unexpected job status: {status}")
            
            raise Exception(f"Textract job timed out after {max_wait_time} seconds")
            
        except Exception as e:
            logger.error(f"Asynchronous extraction failed for {bucket}/{key}: {str(e)}")
            raise

    def _process_textract_response(self, response: Dict, bucket: str, key: str, method: str, sync_error: Exception = None) -> Dict[str, Any]:
        """Process Textract response and extract structured text"""
        try:
            blocks = response.get('Blocks', [])
            
            # Extract text content
            extracted_text = self._extract_text_content(blocks)
            
            # Extract document structure
            document_structure = self._analyze_document_structure(blocks)
            
            # Generate metadata
            metadata = self._generate_metadata(response, bucket, key, len(extracted_text), method, sync_error)
            
            return {
                'text_content': extracted_text,
                'document_structure': document_structure,
                'metadata': metadata
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
                'word_count': len([b for b in page_blocks if b['BlockType'] == 'WORD'])
            }
            structure['pages'].append(page_info)
        
        # Calculate statistics
        structure['statistics'] = {
            'total_pages': len(pages),
            'total_lines': len([b for b in blocks if b['BlockType'] == 'LINE']),
            'total_words': len([b for b in blocks if b['BlockType'] == 'WORD']),
            'average_confidence': sum(b.get('Confidence', 0) for b in blocks) / len(blocks) if blocks else 0
        }
        
        return structure

    def _generate_metadata(self, response: Dict, bucket: str, key: str, text_length: int, method: str, sync_error: Exception = None) -> Dict[str, Any]:
        """Generate comprehensive metadata for the extraction"""
        metadata = {
            'source_document': {
                'bucket': bucket,
                'key': key,
                'document_id': os.path.splitext(os.path.basename(key))[0]
            },
            'extraction_info': {
                'method': f'textract_{method}',
                'extraction_date': datetime.utcnow().isoformat(),
                'text_length': text_length,
                'word_count': len(response.get('Blocks', [])),
                'status': 'success'
            },
            'textract_metadata': {
                'job_status': response.get('JobStatus', 'COMPLETED'),
                'pages_processed': len(set(block.get('Page', 1) for block in response.get('Blocks', [])))
            }
        }
        
        # Add sync error info if async was used as fallback
        if sync_error:
            metadata['extraction_info']['sync_fallback_reason'] = str(sync_error)
            metadata['extraction_info']['method'] = 'textract_async_fallback'
        
        return metadata

    def save_extracted_text(self, extracted_data: Dict[str, Any], document_id: str) -> str:
        """Save extracted text and metadata to S3"""
        try:
            # Create output keys
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
            return f"s3://{self.output_bucket}/{output_key}"
            
        except Exception as e:
            logger.error(f"Error saving extracted text: {str(e)}")
            raise

def handler(event, context):
    """Lambda function handler for fixed text extraction"""
    try:
        logger.info(f"FixedTextExtractor Lambda triggered")
        
        extractor = FixedTextExtractor()
        
        # Handle S3 event
        if 'Records' in event:
            results = []
            
            for record in event['Records']:
                bucket = record['s3']['bucket']['name']
                key = unquote_plus(record['s3']['object']['key'])
                
                if not key.lower().endswith('.pdf'):
                    continue
                
                document_id = os.path.splitext(os.path.basename(key))[0]
                
                try:
                    extracted_data = extractor.extract_text_from_pdf(bucket, key)
                    output_location = extractor.save_extracted_text(extracted_data, document_id)
                    
                    results.append({
                        'document_id': document_id,
                        'source_location': f"s3://{bucket}/{key}",
                        'output_location': output_location,
                        'status': 'success',
                        'extraction_method': extracted_data['metadata']['extraction_info']['method'],
                        'text_length': len(extracted_data['text_content']),
                        'pages_processed': extracted_data['metadata']['textract_metadata']['pages_processed']
                    })
                    
                except Exception as e:
                    results.append({
                        'document_id': document_id,
                        'source_location': f"s3://{bucket}/{key}",
                        'status': 'error',
                        'error': str(e)
                    })
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'Processed {len(results)} documents',
                    'results': results
                })
            }
        
        # Handle direct invocation
        elif 'bucket' in event and 'key' in event:
            bucket = event['bucket']
            key = event['key']
            document_id = os.path.splitext(os.path.basename(key))[0]
            
            extracted_data = extractor.extract_text_from_pdf(bucket, key)
            output_location = extractor.save_extracted_text(extracted_data, document_id)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Text extraction completed',
                    'document_id': document_id,
                    'output_location': output_location,
                    'extraction_method': extracted_data['metadata']['extraction_info']['method'],
                    'text_length': len(extracted_data['text_content']),
                    'pages_processed': extracted_data['metadata']['textract_metadata']['pages_processed']
                })
            }
        
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid event format'})
            }
            
    except Exception as e:
        logger.error(f"FixedTextExtractor error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Text extraction failed: {str(e)}'})
        }
