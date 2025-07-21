#!/usr/bin/env python3
"""
TextExtractor Processor Lambda Function - Gold Standard
Processes completed Textract jobs with sophisticated structure extraction
Uses gold standard DatabaseManager and DocumentIDManager patterns
"""

import json
import boto3
import logging
import os
import csv
import io
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import from gold standard layers
from utils.DatabaseManager import DatabaseManager
from utils.DocumentIDManager import DocumentIDManager

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class TextExtractorProcessor:
    """Processes completed Textract jobs using gold standard patterns"""
    
    def __init__(self):
        self.textract = boto3.client('textract')
        self.s3 = boto3.client('s3')
        self.sns = boto3.client('sns')
        
        # Initialize gold standard database components
        self.db_manager = DatabaseManager()
        self.doc_id_manager = DocumentIDManager()
        
        # Environment configuration
        self.output_bucket = os.environ['OUTPUT_BUCKET']
        self.text_bucket = os.environ.get('TEXT_BUCKET', self.output_bucket)
        self.chunks_bucket = os.environ.get('CHUNKS_BUCKET')
        self.chunks_ready_topic_arn = os.environ.get('CHUNKS_READY_TOPIC_ARN')
        
        logger.info("✅ TextExtractor Processor initialized with gold standard patterns")
        logger.info(f"Output bucket: {self.output_bucket}")
        logger.info(f"Text bucket: {self.text_bucket}")
    
    def extract_doc_id_from_job_tag(self, job_tag: str) -> str:
        """Extract document ID from Textract job tag or output prefix"""
        # Job tag format: textract-output/{doc_id}/
        if 'textract-output/' in job_tag:
            doc_id = job_tag.split('textract-output/')[1].rstrip('/')
        else:
            doc_id = job_tag
        
        logger.info(f"Extracted doc_id: {doc_id} from job tag: {job_tag}")
        return doc_id
    
    def get_textract_results(self, job_id: str) -> Dict[str, Any]:
        """Get complete Textract results for a job"""
        try:
            logger.info(f"Retrieving Textract results for job: {job_id}")
            
            # Get document analysis results
            response = self.textract.get_document_analysis(JobId=job_id)
            
            # Collect all blocks
            blocks = response.get('Blocks', [])
            
            # Handle pagination
            while 'NextToken' in response:
                response = self.textract.get_document_analysis(
                    JobId=job_id,
                    NextToken=response['NextToken']
                )
                blocks.extend(response.get('Blocks', []))
            
            logger.info(f"✅ Retrieved {len(blocks)} blocks from Textract")
            
            return {
                'JobStatus': response.get('JobStatus'),
                'Blocks': blocks,
                'DocumentMetadata': response.get('DocumentMetadata', {}),
                'JobId': job_id
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get Textract results: {str(e)}")
            raise
    
    def extract_text_content(self, blocks: List[Dict]) -> Dict[str, Any]:
        """Extract structured text content from Textract blocks"""
        try:
            # Organize blocks by type
            lines = []
            tables = []
            forms = []
            
            # Extract text lines
            for block in blocks:
                if block['BlockType'] == 'LINE':
                    lines.append({
                        'text': block.get('Text', ''),
                        'confidence': block.get('Confidence', 0),
                        'geometry': block.get('Geometry', {}),
                        'id': block.get('Id')
                    })
                elif block['BlockType'] == 'TABLE':
                    # Process table structure
                    table_data = self.extract_table_data(block, blocks)
                    if table_data:
                        tables.append(table_data)
                elif block['BlockType'] == 'KEY_VALUE_SET':
                    # Process form fields
                    form_data = self.extract_form_data(block, blocks)
                    if form_data:
                        forms.append(form_data)
            
            # Combine all text
            full_text = '\\n'.join([line['text'] for line in lines])
            
            return {
                'full_text': full_text,
                'lines': lines,
                'tables': tables,
                'forms': forms,
                'total_lines': len(lines),
                'total_tables': len(tables),
                'total_forms': len(forms)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to extract text content: {str(e)}")
            raise
    
    def extract_table_data(self, table_block: Dict, all_blocks: List[Dict]) -> Optional[Dict]:
        """Extract structured data from a table block"""
        try:
            # This is a simplified table extraction
            # In production, you'd want more sophisticated table processing
            return {
                'id': table_block.get('Id'),
                'confidence': table_block.get('Confidence', 0),
                'geometry': table_block.get('Geometry', {}),
                'row_count': len(table_block.get('Relationships', [])),
                'type': 'table'
            }
        except Exception as e:
            logger.error(f"Error extracting table data: {str(e)}")
            return None
    
    def extract_form_data(self, form_block: Dict, all_blocks: List[Dict]) -> Optional[Dict]:
        """Extract structured data from a form block"""
        try:
            # This is a simplified form extraction
            # In production, you'd want more sophisticated form processing
            return {
                'id': form_block.get('Id'),
                'confidence': form_block.get('Confidence', 0),
                'geometry': form_block.get('Geometry', {}),
                'entity_type': form_block.get('EntityTypes', []),
                'type': 'form'
            }
        except Exception as e:
            logger.error(f"Error extracting form data: {str(e)}")
            return None
    
    def save_extracted_text(self, doc_id: str, text_content: Dict[str, Any]) -> str:
        """Save extracted text to S3"""
        try:
            # Create text file content
            text_data = {
                'doc_id': doc_id,
                'extracted_at': datetime.now().isoformat(),
                'content': text_content,
                'metadata': {
                    'total_characters': len(text_content['full_text']),
                    'total_lines': text_content['total_lines'],
                    'total_tables': text_content['total_tables'],
                    'total_forms': text_content['total_forms']
                }
            }
            
            # Save to S3
            key = f'extracted-text/{doc_id}.json'
            
            self.s3.put_object(
                Bucket=self.text_bucket,
                Key=key,
                Body=json.dumps(text_data, indent=2),
                ContentType='application/json'
            )
            
            logger.info(f"✅ Saved extracted text to s3://{self.text_bucket}/{key}")
            return key
            
        except Exception as e:
            logger.error(f"❌ Failed to save extracted text: {str(e)}")
            raise
    
    def update_processing_status(self, doc_id: str, status: str, job_id: str = None, 
                               text_s3_key: str = None, error: str = None):
        """Update document processing status using gold standard pattern"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Update processing status using correct column names
                    cursor.execute("""
                        UPDATE document_processing_status 
                        SET text_extraction_status = %s, 
                            text_extraction_completed_at = %s,
                            text_s3_key = %s,
                            error_message = %s,
                            updated_at = %s
                        WHERE doc_id = %s AND textract_job_id = %s
                    """, (
                        status, 
                        datetime.now() if status == 'text_extracted' else None,
                        text_s3_key,
                        error,
                        datetime.now(),
                        doc_id,
                        job_id
                    ))
                    
                    if cursor.rowcount == 0:
                        # Insert if not exists
                        cursor.execute("""
                            INSERT INTO document_processing_status 
                            (doc_id, textract_job_id, text_extraction_status, text_s3_key, error_message, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (doc_id, job_id, status, text_s3_key, error, datetime.now()))
                    
                    conn.commit()
                    logger.info(f"✅ Updated processing status for {doc_id}: {status}")
                    
        except Exception as e:
            logger.error(f"❌ Failed to update processing status: {str(e)}")
            raise
    
    def publish_text_extraction_complete(self, doc_id: str, text_s3_key: str):
        """Publish message that text extraction is complete"""
        try:
            if not self.chunks_ready_topic_arn:
                logger.warning("No chunks ready topic ARN configured")
                return
            
            message = {
                'event_type': 'text_extraction_complete',
                'doc_id': doc_id,
                'text_s3_key': text_s3_key,
                'text_bucket': self.text_bucket,
                'timestamp': datetime.now().isoformat(),
                'next_step': 'text_chunking'
            }
            
            self.sns.publish(
                TopicArn=self.chunks_ready_topic_arn,
                Message=json.dumps(message),
                Subject=f'Text extraction complete for {doc_id}'
            )
            
            logger.info(f"✅ Published text extraction complete message for {doc_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to publish completion message: {str(e)}")
            # Don't raise - this is not critical
    
    def process_textract_completion(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process Textract job completion notification"""
        try:
            logger.info(f"Processing Textract completion event")
            
            # Parse SNS message
            if 'Records' in event:
                # SNS event format
                sns_message = json.loads(event['Records'][0]['Sns']['Message'])
            else:
                # Direct invocation format
                sns_message = event
            
            job_id = sns_message.get('JobId')
            job_status = sns_message.get('Status')
            
            if not job_id:
                raise ValueError("No JobId found in event")
            
            logger.info(f"Processing Textract job {job_id} with status {job_status}")
            
            if job_status != 'SUCCEEDED':
                error_msg = f"Textract job failed with status: {job_status}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'job_id': job_id
                }
            
            # Get Textract results
            textract_results = self.get_textract_results(job_id)
            
            # Extract document ID from job tag or output config
            doc_id = self.extract_doc_id_from_job_tag(
                sns_message.get('OutputConfig', {}).get('S3Prefix', job_id)
            )
            
            # Extract text content
            text_content = self.extract_text_content(textract_results['Blocks'])
            
            # Save extracted text
            text_s3_key = self.save_extracted_text(doc_id, text_content)
            
            # Update processing status
            self.update_processing_status(
                doc_id=doc_id,
                status='text_extracted',
                job_id=job_id,
                text_s3_key=text_s3_key
            )
            
            # Publish completion message
            self.publish_text_extraction_complete(doc_id, text_s3_key)
            
            return {
                'success': True,
                'doc_id': doc_id,
                'job_id': job_id,
                'text_s3_key': text_s3_key,
                'text_stats': text_content['metadata'] if 'metadata' in text_content else {}
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing Textract completion: {str(e)}")
            
            # Try to update status with error
            try:
                if 'job_id' in locals():
                    doc_id = self.extract_doc_id_from_job_tag(job_id)
                    self.update_processing_status(
                        doc_id=doc_id,
                        status='text_extraction_failed',
                        job_id=job_id,
                        error=str(e)
                    )
            except:
                pass  # Don't fail on error logging
            
            return {
                'success': False,
                'error': str(e),
                'job_id': locals().get('job_id')
            }

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for text extraction processing
    
    Args:
        event: SNS notification about completed Textract job
        context: Lambda context object
        
    Returns:
        Dict containing processing status and results
    """
    try:
        logger.info(f"🚀 Text extraction processor invoked with event: {json.dumps(event, default=str)}")
        
        # Initialize processor
        processor = TextExtractorProcessor()
        
        # Process the Textract completion
        result = processor.process_textract_completion(event)
        
        if result['success']:
            logger.info(f"✅ Text extraction processing completed successfully")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'message': f"Successfully processed text extraction for document {result.get('doc_id')}",
                    'result': result
                })
            }
        else:
            logger.error(f"❌ Text extraction processing failed: {result.get('error')}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'success': False,
                    'error': result.get('error'),
                    'result': result
                })
            }
        
    except Exception as e:
        logger.error(f"❌ Error in text extraction processor: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
