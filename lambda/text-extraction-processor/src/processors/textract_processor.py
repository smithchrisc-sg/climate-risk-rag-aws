"""
Textract Processor - Core business logic for text extraction processing
Extracted from monolithic handler for better modularity and testability
"""

import json
import boto3
import logging
import csv
import io
from datetime import datetime
from typing import Dict, List, Any, Optional

from utils.DatabaseManager import DatabaseManager
from DocumentIDManager import DocumentIDManager
from messaging.standardized_messaging import StandardizedMessagePublisher, StandardizedMessageParser
from models.extraction_models import TextractJob, ExtractionResult

logger = logging.getLogger(__name__)

class TextractProcessor:
    """Processes completed Textract jobs with sophisticated structure extraction"""
    
    def __init__(self, config):
        """Initialize processor with configuration"""
        self.config = config
        self.textract = boto3.client('textract')
        self.s3 = boto3.client('s3')
        
        # Initialize database manager
        self.db_manager = DatabaseManager()
        
        # Initialize DocumentIDManager
        self.doc_id_manager = DocumentIDManager()
        
        # Initialize messaging
        self.message_publisher = StandardizedMessagePublisher()
        self.message_parser = StandardizedMessageParser()
        
    def process_textract_completion(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Textract job completion event
        
        Args:
            event: Lambda event containing SNS notification
            
        Returns:
            Dict containing processing results
        """
        try:
            # Parse the SNS message
            job_info = self._parse_textract_completion_event(event)
            if not job_info:
                logger.warning("No valid Textract job information found in event")
                return {'status': 'skipped', 'reason': 'No valid job information'}
            
            job_id = job_info['JobId']
            job_status = job_info['JobStatus']
            
            logger.info(f"Processing Textract job completion: {job_id}, status: {job_status}")
            
            if job_status != 'SUCCEEDED':
                logger.warning(f"Textract job {job_id} did not succeed: {job_status}")
                self._handle_failed_job(job_id, job_status)
                return {'status': 'failed', 'job_id': job_id, 'job_status': job_status}
            
            # Process successful job
            result = self._process_successful_job(job_id)
            
            return {
                'status': 'success',
                'job_id': job_id,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Error processing Textract completion: {str(e)}", exc_info=True)
            raise
    
    def _parse_textract_completion_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse Textract completion event from SNS"""
        try:
            # Handle SNS event structure
            if 'Records' in event:
                for record in event['Records']:
                    if record.get('eventSource') == 'aws:sns':
                        message = json.loads(record['Sns']['Message'])
                        if 'JobId' in message and 'JobStatus' in message:
                            return message
            
            # Direct invocation for testing
            if 'JobId' in event and 'JobStatus' in event:
                return event
                
            return None
            
        except Exception as e:
            logger.error(f"Error parsing Textract completion event: {str(e)}")
            return None
    
    def _process_successful_job(self, job_id: str) -> Dict[str, Any]:
        """Process a successful Textract job"""
        try:
            # Get job metadata from database
            job_metadata = self._get_job_metadata(job_id)
            if not job_metadata:
                raise ValueError(f"Job metadata not found for job_id: {job_id}")
            
            doc_id = job_metadata['doc_id']
            logger.info(f"Processing successful Textract job {job_id} for document {doc_id}")
            
            # Get Textract results
            textract_response = self._get_textract_results(job_id)
            
            # Save structured output (text, tables, forms, layout)
            files_created = self._save_structured_output(doc_id, textract_response, job_metadata)
            
            # Update job status in database
            self._update_job_status(job_id, 'COMPLETED', files_created)
            
            # Publish completion message
            self._publish_completion_message(doc_id, files_created, job_metadata)
            
            return {
                'doc_id': doc_id,
                'files_created': files_created,
                'job_metadata': job_metadata
            }
            
        except Exception as e:
            logger.error(f"Error processing successful job {job_id}: {str(e)}")
            # Update job status to failed
            try:
                self._update_job_status(job_id, 'FAILED', error_message=str(e))
            except Exception as update_error:
                logger.error(f"Failed to update job status: {str(update_error)}")
            raise
    
    def _get_job_metadata(self, job_id: str) -> Optional[Dict]:
        """Get job metadata from database"""
        try:
            metadata = self.db_manager.get_textract_job_metadata(job_id)
            
            if not metadata:
                logger.error(f"No metadata found for job_id: {job_id}")
                return None
            
            logger.info(f"Retrieved metadata for job {job_id}: doc_id={metadata.get('doc_id')}")
            return metadata
            
        except Exception as e:
            logger.error(f"Error retrieving job metadata for {job_id}: {str(e)}")
            return None
    
    def _get_textract_results(self, job_id: str) -> Dict[str, Any]:
        """Get complete Textract results for a job"""
        try:
            logger.info(f"Retrieving Textract results for job {job_id}")
            
            # Get document analysis results
            response = self.textract.get_document_analysis(JobId=job_id)
            
            # Handle multi-page results
            blocks = response.get('Blocks', [])
            
            # Get additional pages if they exist
            while 'NextToken' in response:
                response = self.textract.get_document_analysis(
                    JobId=job_id,
                    NextToken=response['NextToken']
                )
                blocks.extend(response.get('Blocks', []))
            
            logger.info(f"Retrieved {len(blocks)} blocks from Textract job {job_id}")
            
            return {
                'JobId': job_id,
                'JobStatus': response.get('JobStatus'),
                'Blocks': blocks,
                'DocumentMetadata': response.get('DocumentMetadata', {}),
                'AnalyzeDocumentModelVersion': response.get('AnalyzeDocumentModelVersion')
            }
            
        except Exception as e:
            logger.error(f"Error retrieving Textract results for job {job_id}: {str(e)}")
            raise
    
    def _save_structured_output(self, doc_id: str, textract_response: Dict, job_metadata: Dict) -> List[str]:
        """Save structured output from Textract analysis"""
        try:
            from processors.output_formatter import OutputFormatter
            
            formatter = OutputFormatter(self.config)
            files_created = formatter.save_structured_output(doc_id, textract_response, job_metadata)
            
            logger.info(f"Created {len(files_created)} output files for document {doc_id}")
            return files_created
            
        except Exception as e:
            logger.error(f"Error saving structured output for {doc_id}: {str(e)}")
            raise
    
    def _update_job_status(self, job_id: str, status: str, files_created: List[str] = None, error_message: str = None):
        """Update job status in database"""
        try:
            if status == 'COMPLETED':
                # For completed jobs, store file information
                self.db_manager.update_textract_job_status(
                    job_id=job_id,
                    status=status,
                    completed_at=datetime.now(),
                    output_files=files_created or []
                )
            else:
                # For failed jobs, store error information
                self.db_manager.update_textract_job_status(
                    job_id=job_id,
                    status=status,
                    error_message=error_message,
                    completed_at=datetime.now()
                )
            
            logger.info(f"Updated job {job_id} status to {status}")
            
        except Exception as e:
            logger.error(f"Error updating job status for {job_id}: {str(e)}")
            raise
    
    def _publish_completion_message(self, doc_id: str, files_created: List[str], job_metadata: Dict):
        """Publish text extraction completion message"""
        try:
            message_data = {
                'event_type': 'text_extraction_complete',
                'doc_id': doc_id,
                'files_created': files_created,
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'source_url': job_metadata.get('source_url'),
                    'original_filename': job_metadata.get('original_filename'),
                    'processing_stage': 'text_extraction'
                }
            }
            
            self.message_publisher.publish_message(
                topic_arn=self.config.text_extraction_complete_topic_arn,
                message_data=message_data,
                message_type='text_extraction_complete'
            )
            
            logger.info(f"Published text extraction completion message for document {doc_id}")
            
        except Exception as e:
            logger.error(f"Error publishing completion message for {doc_id}: {str(e)}")
            # Don't raise - this is not critical for the main processing
    
    def _handle_failed_job(self, job_id: str, job_status: str):
        """Handle failed Textract job"""
        try:
            error_message = f"Textract job failed with status: {job_status}"
            self._update_job_status(job_id, 'FAILED', error_message=error_message)
            logger.warning(f"Handled failed Textract job {job_id}: {error_message}")
            
        except Exception as e:
            logger.error(f"Error handling failed job {job_id}: {str(e)}")
