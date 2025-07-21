"""
Text Extractor Processor Lambda Function
Processes completed Textract jobs with audit-first database design
"""

import json
import boto3
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import from locked database core layer - DO NOT CHANGE
from utils.DatabaseManager import DatabaseManager

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class TextExtractorProcessor:
    """Processes completed Textract jobs with audit-first status tracking"""
    
    def __init__(self):
        self.textract = boto3.client('textract')
        self.s3 = boto3.client('s3')
        self.sns = boto3.client('sns')
        
        # Environment configuration
        self.output_bucket = os.environ['OUTPUT_BUCKET']
        self.text_extraction_complete_topic_arn = os.environ.get(
            'TEXT_EXTRACTION_COMPLETE_TOPIC_ARN',
            'arn:aws:sns:us-east-1:861276078413:text-extraction-complete'
        )
        
        # Initialize DatabaseManager - LOCKED LAYER
        self.db_manager = DatabaseManager()
        
        logger.info("✅ Text Extractor Processor initialized")
        logger.info(f"Output bucket: {self.output_bucket}")
        logger.info(f"Completion topic: {self.text_extraction_complete_topic_arn}")
    
    def extract_doc_id_from_textract_event(self, textract_message: Dict) -> str:
        """
        Extract doc_id from Textract completion message
        Uses DocumentLocation.S3ObjectName to get the correct doc_id
        """
        try:
            # Get S3 object name from Textract message
            doc_location = textract_message.get('DocumentLocation', {})
            s3_object_name = doc_location.get('S3ObjectName', '')
            
            if s3_object_name:
                # Extract doc_id from S3 path: data-lake/064762102bead7b04a39.pdf
                filename = s3_object_name.split('/')[-1]  # Get filename
                doc_id = filename.replace('.pdf', '')     # Remove extension
                
                logger.info(f"Extracted doc_id: {doc_id} from S3 object: {s3_object_name}")
                return doc_id
            
            # Fallback: extract from job_id (not ideal but better than failure)
            job_id = textract_message.get('JobId', '')
            logger.warning(f"Could not extract doc_id from S3 path, using truncated job_id")
            return job_id[:20]  # Truncate to fit database constraint
            
        except Exception as e:
            logger.error(f"Failed to extract doc_id: {str(e)}")
            job_id = textract_message.get('JobId', 'unknown')
            return job_id[:20]  # Truncate to fit database constraint
    
    def get_textract_results(self, job_id: str) -> Dict[str, Any]:
        """Get Textract job results"""
        try:
            response = self.textract.get_document_analysis(JobId=job_id)
            
            # Handle pagination
            blocks = response.get('Blocks', [])
            next_token = response.get('NextToken')
            
            while next_token:
                response = self.textract.get_document_analysis(
                    JobId=job_id,
                    NextToken=next_token
                )
                blocks.extend(response.get('Blocks', []))
                next_token = response.get('NextToken')
            
            return {
                'job_status': response.get('JobStatus'),
                'blocks': blocks,
                'document_metadata': response.get('DocumentMetadata', {}),
                'job_id': job_id
            }
            
        except Exception as e:
            logger.error(f"Failed to get Textract results for job {job_id}: {str(e)}")
            raise
    
    def extract_text_content(self, blocks: List[Dict]) -> Dict[str, Any]:
        """Extract structured text content from Textract blocks"""
        try:
            text_lines = []
            tables = []
            forms = []
            
            # Group blocks by type
            line_blocks = [b for b in blocks if b.get('BlockType') == 'LINE']
            table_blocks = [b for b in blocks if b.get('BlockType') == 'TABLE']
            key_value_blocks = [b for b in blocks if b.get('BlockType') == 'KEY_VALUE_SET']
            
            # Extract line text
            for block in line_blocks:
                if 'Text' in block:
                    text_lines.append({
                        'text': block['Text'],
                        'confidence': block.get('Confidence', 0),
                        'geometry': block.get('Geometry', {})
                    })
            
            # Extract table information (simplified)
            for table in table_blocks:
                tables.append({
                    'id': table.get('Id'),
                    'confidence': table.get('Confidence', 0),
                    'row_count': len([r for r in table.get('Relationships', []) if r.get('Type') == 'CHILD']),
                    'geometry': table.get('Geometry', {})
                })
            
            # Extract form information (simplified)
            for kv in key_value_blocks:
                if kv.get('EntityTypes') and 'KEY' in kv.get('EntityTypes', []):
                    forms.append({
                        'id': kv.get('Id'),
                        'confidence': kv.get('Confidence', 0),
                        'geometry': kv.get('Geometry', {})
                    })
            
            # Combine all text
            full_text = '\n'.join([line['text'] for line in text_lines])
            
            return {
                'full_text': full_text,
                'line_count': len(text_lines),
                'table_count': len(tables),
                'form_count': len(forms),
                'character_count': len(full_text),
                'lines': text_lines,
                'tables': tables,
                'forms': forms
            }
            
        except Exception as e:
            logger.error(f"Failed to extract text content: {str(e)}")
            raise
    
    def save_results_to_s3(self, doc_id: str, text_content: Dict[str, Any], 
                          textract_response: Dict[str, Any]) -> Dict[str, str]:
        """Save extracted text and structure to S3"""
        try:
            base_path = f"dl-text/{doc_id}"
            
            # Save raw text
            text_key = f"{base_path}/raw_text.txt"
            self.s3.put_object(
                Bucket=self.output_bucket,
                Key=text_key,
                Body=text_content['full_text'],
                ContentType='text/plain'
            )
            
            # Save structured data (JSON)
            structure_key = f"{base_path}/textract_response.json"
            self.s3.put_object(
                Bucket=self.output_bucket,
                Key=structure_key,
                Body=json.dumps(textract_response, default=str, indent=2),
                ContentType='application/json'
            )
            
            # Save text analysis summary
            summary_key = f"{base_path}/text_analysis.json"
            summary = {
                'doc_id': doc_id,
                'processing_timestamp': datetime.utcnow().isoformat() + 'Z',
                'statistics': {
                    'character_count': text_content['character_count'],
                    'line_count': text_content['line_count'],
                    'table_count': text_content['table_count'],
                    'form_count': text_content['form_count']
                }
            }
            
            self.s3.put_object(
                Bucket=self.output_bucket,
                Key=summary_key,
                Body=json.dumps(summary, indent=2),
                ContentType='application/json'
            )
            
            logger.info(f"Saved text extraction results for {doc_id}")
            
            return {
                'text_location': f"s3://{self.output_bucket}/{text_key}",
                'structure_location': f"s3://{self.output_bucket}/{structure_key}",
                'summary_location': f"s3://{self.output_bucket}/{summary_key}"
            }
            
        except Exception as e:
            logger.error(f"Failed to save results to S3: {str(e)}")
            raise
    
    def publish_completion_message(self, doc_id: str, locations: Dict[str, str], 
                                 text_content: Dict[str, Any]) -> None:
        """Publish standardized text extraction completion message"""
        try:
            # Create standardized message format (includes doc_id as confirmed)
            message = {
                "version": "1.0",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "climate-risk-rag-system",
                "stage": "text_ready",
                "doc_id": doc_id,  # ✅ doc_id included as confirmed
                "document_metadata": {
                    "processing_completed": datetime.utcnow().isoformat() + "Z"
                },
                "data_locations": {
                    "text_location": locations['text_location'],
                    "structure_location": locations['structure_location'],
                    "base_path": locations['text_location'].rsplit('/', 1)[0] + "/"
                },
                "processing_metadata": {
                    "total_characters": text_content['character_count'],
                    "line_count": text_content['line_count'],
                    "table_count": text_content['table_count'],
                    "form_count": text_content['form_count']
                },
                "integration_flags": {
                    "database_tracking_enabled": True,
                    "audit_first_design": True
                }
            }
            
            # Publish message
            response = self.sns.publish(
                TopicArn=self.text_extraction_complete_topic_arn,
                Message=json.dumps(message, default=str),
                Subject=f"Text extraction complete: {doc_id}",
                MessageAttributes={
                    'stage': {
                        'DataType': 'String',
                        'StringValue': 'text_ready'
                    },
                    'doc_id': {
                        'DataType': 'String',
                        'StringValue': doc_id
                    },
                    'version': {
                        'DataType': 'String',
                        'StringValue': '1.0'
                    }
                }
            )
            
            logger.info(f"Published text extraction complete message for {doc_id}: {response['MessageId']}")
            
        except Exception as e:
            logger.error(f"Failed to publish completion message: {str(e)}")
            raise
    
    def process_textract_completion(self, textract_message: Dict) -> Dict[str, Any]:
        """Process Textract job completion using the full message"""
        
        # Extract doc_id from Textract message
        doc_id = self.extract_doc_id_from_textract_event(textract_message)
        job_id = textract_message.get('JobId')
        job_status = textract_message.get('Status')
        
        try:
            # Update status to in_progress
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='textract_complete',
                status='in_progress',
                system_id=job_id
            )
            
            if job_status == 'SUCCEEDED':
                # Get Textract results
                textract_response = self.get_textract_results(job_id)
                
                # Extract text content
                text_content = self.extract_text_content(textract_response['blocks'])
                
                # Save results to S3
                locations = self.save_results_to_s3(doc_id, text_content, textract_response)
                
                # Publish completion message
                self.publish_completion_message(doc_id, locations, text_content)
                
                # Update status to completed
                self.db_manager.set_processing_status(
                    doc_id=doc_id,
                    stage='textract_complete',
                    status='completed',
                    system_id=job_id
                )
                
                return {
                    'status': 'success',
                    'doc_id': doc_id,
                    'job_id': job_id,
                    'locations': locations,
                    'statistics': {
                        'character_count': text_content['character_count'],
                        'line_count': text_content['line_count'],
                        'table_count': text_content['table_count'],
                        'form_count': text_content['form_count']
                    }
                }
                
            else:
                # Job failed
                error_msg = f"Textract job failed with status: {job_status}"
                
                # Update status to failed
                self.db_manager.set_processing_status(
                    doc_id=doc_id,
                    stage='textract_complete',
                    status='failed',
                    error_message=error_msg,
                    system_id=job_id
                )
                
                return {
                    'status': 'failed',
                    'doc_id': doc_id,
                    'job_id': job_id,
                    'error': error_msg
                }
                
        except Exception as e:
            logger.error(f"Error processing Textract completion: {str(e)}")
            
            # Update status to failed
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='textract_complete',
                status='failed',
                error_message=str(e),
                system_id=job_id
            )
            
            raise

def lambda_handler(event, context):
    """Lambda handler for Text Extractor Processor"""
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        processor = TextExtractorProcessor()
        results = []
        
        # Handle SQS messages (Textract notifications come through SQS)
        if 'Records' in event:
            for record in event['Records']:
                if record.get('eventSource') == 'aws:sqs':
                    # Parse SQS message body (contains Textract notification)
                    try:
                        textract_message = json.loads(record['body'])
                        
                        job_id = textract_message.get('JobId')
                        job_status = textract_message.get('Status')
                        s3_output_config = textract_message.get('OutputConfig', {})
                        s3_output_path = s3_output_config.get('S3Prefix', '')
                        
                        if job_id and job_status:
                            logger.info(f"Processing Textract completion: {job_id} -> {job_status}")
                            result = processor.process_textract_completion(textract_message)
                            results.append(result)
                        else:
                            logger.warning(f"Missing job_id or status in message: {textract_message}")
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse SQS message body: {e}")
                        results.append({'status': 'error', 'error': f'JSON parse error: {e}'})
                        
                elif record.get('EventSource') == 'aws:sns':
                    # Handle direct SNS notifications (legacy support)
                    sns_message = json.loads(record['Sns']['Message'])
                    
                    job_id = sns_message.get('JobId')
                    job_status = sns_message.get('Status')
                    s3_output_path = sns_message.get('OutputConfig', {}).get('S3Prefix')
                    
                    if job_id and job_status:
                        result = processor.process_textract_completion(
                            job_id, job_status, s3_output_path
                        )
                        results.append(result)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Text extraction processing completed',
                'processed_records': len(results),
                'results': results
            }, default=str)
        }
        
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
