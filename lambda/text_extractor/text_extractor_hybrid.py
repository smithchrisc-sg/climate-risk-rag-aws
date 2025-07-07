"""
Hybrid TextExtractor Lambda Function
Uses AWS Textract as primary method, with fallback to PyPDF2 for unsupported documents
"""

import json
import boto3
import logging
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from urllib.parse import unquote_plus
import time
import io

# Import PyPDF2 for fallback text extraction
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logging.warning("PyPDF2 not available - fallback text extraction disabled")

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class HybridTextExtractor:
    """Hybrid text extractor using Textract with PyPDF2 fallback"""
    
    def __init__(self, profile_name=None):
        # Use profile if provided (for local testing)
        session = boto3.Session(profile_name=profile_name) if profile_name else boto3.Session()
        
        self.textract = session.client('textract')
        self.s3 = session.client('s3')
        
        # Configuration from environment variables
        self.output_bucket = os.environ.get('OUTPUT_BUCKET', 'solve-global-kr-text-new-861276078413-us-east-1')
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        
        logger.info(f"HybridTextExtractor initialized - Output bucket: {self.output_bucket}")

    def extract_text_from_pdf(self, bucket: str, key: str) -> Dict[str, Any]:
        """
        Extract text from PDF using Textract with PyPDF2 fallback
        
        Args:
            bucket: S3 bucket containing the PDF
            key: S3 key of the PDF file
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        try:
            logger.info(f"Starting hybrid text extraction for s3://{bucket}/{key}")
            
            # Try Textract first
            try:
                return self._extract_with_textract(bucket, key)
            except Exception as textract_error:
                logger.warning(f"Textract failed for {bucket}/{key}: {str(textract_error)}")
                
                # Fall back to PyPDF2
                if PYPDF2_AVAILABLE:
                    logger.info("Falling back to PyPDF2 extraction...")
                    return self._extract_with_pypdf2(bucket, key, textract_error)
                else:
                    raise Exception(f"Textract failed and PyPDF2 not available: {str(textract_error)}")
                
        except Exception as e:
            logger.error(f"All extraction methods failed for {bucket}/{key}: {str(e)}")
            raise

    def _extract_with_textract(self, bucket: str, key: str) -> Dict[str, Any]:
        """Extract text using AWS Textract"""
        
        # Get file size to determine sync vs async
        object_info = self.s3.head_object(Bucket=bucket, Key=key)
        file_size = object_info['ContentLength']
        
        if file_size > 5 * 1024 * 1024:  # 5MB threshold
            response = self._textract_async(bucket, key)
        else:
            response = self._textract_sync(bucket, key)
        
        return self._process_textract_response(response, bucket, key, 'textract')

    def _textract_sync(self, bucket: str, key: str) -> Dict[str, Any]:
        """Synchronous Textract extraction"""
        return self.textract.detect_document_text(
            Document={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            }
        )

    def _textract_async(self, bucket: str, key: str) -> Dict[str, Any]:
        """Asynchronous Textract extraction"""
        # Start job
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
        max_wait_time = 300  # 5 minutes
        poll_interval = 5
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            time.sleep(poll_interval)
            elapsed_time += poll_interval
            
            result = self.textract.get_document_text_detection(JobId=job_id)
            status = result['JobStatus']
            
            if status == 'SUCCEEDED':
                return result
            elif status == 'FAILED':
                raise Exception(f"Textract job failed: {result.get('StatusMessage', 'Unknown error')}")
            elif status in ['IN_PROGRESS']:
                continue
            else:
                raise Exception(f"Unexpected job status: {status}")
        
        raise Exception(f"Textract job timed out after {max_wait_time} seconds")

    def _extract_with_pypdf2(self, bucket: str, key: str, textract_error: Exception) -> Dict[str, Any]:
        """Extract text using PyPDF2 as fallback"""
        
        # Download PDF from S3
        response = self.s3.get_object(Bucket=bucket, Key=key)
        pdf_bytes = response['Body'].read()
        
        # Extract text with PyPDF2
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text_content = ""
        page_count = len(pdf_reader.pages)
        
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                if page_text.strip():
                    text_content += f"\n--- Page {page_num + 1} ---\n"
                    text_content += page_text
                    text_content += "\n"
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num + 1}: {str(e)}")
                continue
        
        # Create metadata
        metadata = {
            'source_document': {
                'bucket': bucket,
                'key': key,
                'document_id': os.path.splitext(os.path.basename(key))[0]
            },
            'extraction_info': {
                'method': 'pypdf2_fallback',
                'extraction_date': datetime.utcnow().isoformat(),
                'text_length': len(text_content),
                'word_count': len(text_content.split()) if text_content else 0,
                'status': 'success_fallback',
                'textract_error': str(textract_error)
            },
            'document_structure': {
                'pages': [{'page_number': i+1} for i in range(page_count)],
                'statistics': {
                    'total_pages': page_count,
                    'extraction_method': 'pypdf2'
                }
            }
        }
        
        return {
            'text_content': text_content.strip(),
            'document_structure': metadata['document_structure'],
            'metadata': metadata
        }

    def _process_textract_response(self, response: Dict, bucket: str, key: str, method: str) -> Dict[str, Any]:
        """Process Textract response"""
        blocks = response.get('Blocks', [])
        
        # Extract text content
        text_lines = []
        line_blocks = [block for block in blocks if block['BlockType'] == 'LINE']
        
        # Sort by page and position
        line_blocks.sort(key=lambda x: (
            x.get('Page', 1),
            x.get('Geometry', {}).get('BoundingBox', {}).get('Top', 0),
            x.get('Geometry', {}).get('BoundingBox', {}).get('Left', 0)
        ))
        
        for block in line_blocks:
            if 'Text' in block:
                text_lines.append(block['Text'])
        
        text_content = '\n'.join(text_lines)
        
        # Analyze structure
        pages = {}
        for block in blocks:
            page_num = block.get('Page', 1)
            if page_num not in pages:
                pages[page_num] = []
            pages[page_num].append(block)
        
        document_structure = {
            'pages': [{'page_number': p, 'line_count': len([b for b in blocks if b['BlockType'] == 'LINE' and b.get('Page') == p])} for p in sorted(pages.keys())],
            'statistics': {
                'total_pages': len(pages),
                'total_lines': len(line_blocks),
                'extraction_method': method
            }
        }
        
        metadata = {
            'source_document': {
                'bucket': bucket,
                'key': key,
                'document_id': os.path.splitext(os.path.basename(key))[0]
            },
            'extraction_info': {
                'method': method,
                'extraction_date': datetime.utcnow().isoformat(),
                'text_length': len(text_content),
                'word_count': len(text_content.split()) if text_content else 0,
                'status': 'success'
            }
        }
        
        return {
            'text_content': text_content,
            'document_structure': document_structure,
            'metadata': metadata
        }

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
    """Lambda function handler for hybrid text extraction"""
    try:
        logger.info(f"HybridTextExtractor Lambda triggered")
        
        extractor = HybridTextExtractor()
        
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
                        'word_count': extracted_data['metadata']['extraction_info']['word_count']
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
                    'word_count': extracted_data['metadata']['extraction_info']['word_count']
                })
            }
        
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid event format'})
            }
            
    except Exception as e:
        logger.error(f"HybridTextExtractor error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Text extraction failed: {str(e)}'})
        }
