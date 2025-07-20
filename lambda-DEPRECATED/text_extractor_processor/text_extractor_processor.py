#!/usr/bin/env python3
"""
TextExtractor Processor Lambda Function - ENHANCED VERSION
Processes completed Textract jobs with sophisticated structure extraction
Uses DatabaseManager pattern and preserves all structural information
"""

import json
import boto3
import logging
import os
import csv
import io
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import standardized messaging
from standardized_messaging import StandardizedMessagePublisher, StandardizedMessageParser

# Import DatabaseManager from shared layer
from utils.DatabaseManager import DatabaseManager

# Import DocumentIDManager from shared layer
from DocumentIDManager import DocumentIDManager

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class TextExtractorProcessor:
    """Processes completed Textract jobs with sophisticated structure extraction"""
    
    def __init__(self):
        self.textract = boto3.client('textract')
        self.s3 = boto3.client('s3')
        
        # Initialize database manager
        self.db_manager = DatabaseManager()
        # Database URL is handled internally by DatabaseManager
        
        # Environment configuration
        self.output_bucket = os.environ['OUTPUT_BUCKET']
        
        # Initialize DocumentIDManager with database connection
        self.doc_id_manager = DocumentIDManager()
        
        # Standardized messaging
        self.text_extraction_complete_topic_arn = os.environ.get(
            'TEXT_EXTRACTION_COMPLETE_TOPIC_ARN',
            'arn:aws:sns:us-east-1:861276078413:text-extraction-complete'
        )
        
        # Initialize standardized message publisher
        self.message_publisher = StandardizedMessagePublisher()
        
        logger.info("TextExtractor Processor initialized with structure extraction")
        logger.info(f"Output bucket: {self.output_bucket}")
        logger.info(f"Text extraction complete topic: {self.text_extraction_complete_topic_arn}")
    
    def lambda_handler(self, event, context):
        """Main Lambda handler"""
        logger.info(f"Processing {len(event.get('Records', []))} records")
        
        results = {
            'processed': 0,
            'errors': 0,
            'skipped': 0
        }
        
        for record in event.get('Records', []):
            try:
                if record.get('eventSource') == 'aws:sqs':
                    # Process SQS message (Textract completion notification)
                    self.process_sqs_record(record)
                    results['processed'] += 1
                else:
                    logger.warning(f"Unsupported event source: {record.get('eventSource')}")
                    results['skipped'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing record: {str(e)}")
                logger.error(f"Record: {json.dumps(record, indent=2)}")
                results['errors'] += 1
        
        logger.info(f"Processing complete: {results['processed']} success, {results['errors']} errors, {results['skipped']} skipped")
        
        return {
            'statusCode': 200,
            'body': json.dumps(results)
        }
    
    def process_sqs_record(self, record):
        """Process SQS record containing Textract completion notification"""
        try:
            # Parse the SQS message body
            message_body = json.loads(record['body'])
            
            # Handle both direct SQS messages and SNS-wrapped messages
            if message_body.get('Type') == 'Notification':
                # SNS notification wrapped in SQS
                sns_message = json.loads(message_body['Message'])
                logger.info(f"Processing SNS message: {sns_message}")
                self.process_textract_completion(sns_message)
            else:
                # Direct SQS message
                logger.info(f"Processing direct SQS message: {message_body}")
                self.process_textract_completion(message_body)
                
        except Exception as e:
            logger.error(f"Error processing SQS record: {str(e)}")
            raise
    
    def process_textract_completion(self, completion_data):
        """Process Textract job completion with structure extraction"""
        job_id = completion_data.get('JobId')
        status = completion_data.get('Status')
        
        logger.info(f"Processing Textract completion: {job_id} -> {status}")
        
        if status != 'SUCCEEDED':
            logger.error(f"Textract job failed: {job_id} with status {status}")
            return
        
        try:
            # Get job metadata from database using DatabaseManager
            job_metadata = self.get_job_metadata(job_id)
            if not job_metadata:
                logger.error(f"Job metadata not found for job_id: {job_id}")
                raise Exception(f"Job metadata not found for job_id: {job_id}")
            
            # Get complete Textract response with all blocks
            textract_response = self.get_complete_textract_response(job_id)
            
            # Save structured output (text, tables, forms, layout)
            files_created = self.save_structured_output(job_metadata['doc_id'], textract_response, job_metadata)
            
            # Update job status in database using DatabaseManager
            self.update_job_status(job_id, 'COMPLETED', files_created)
            
            # Publish completion message
            self.publish_text_extraction_complete(job_metadata, files_created, textract_response)
            
            logger.info(f"Successfully processed Textract job: {job_id} with {len(files_created)} files created")
            
        except Exception as e:
            logger.error(f"Error processing Textract completion: {str(e)}")
            # Update job status to failed using DatabaseManager
            try:
                self.update_job_status(job_id, 'FAILED', error_message=str(e))
            except Exception as update_error:
                logger.error(f"Error updating job status: {str(update_error)}")
            raise
    
    def get_job_metadata(self, job_id: str) -> Optional[Dict]:
        """Get job metadata from database using DatabaseManager"""
        try:
            metadata = self.db_manager.get_textract_job_metadata(job_id)
            
            if metadata:
                # Convert to format expected by rest of the code
                return {
                    'job_id': metadata['job_id'],
                    'doc_id': metadata['doc_id'],
                    's3_bucket': metadata['source_bucket'],  # Map source_bucket to s3_bucket for compatibility
                    's3_key': metadata['source_key'],        # Map source_key to s3_key for compatibility
                    'created_at': metadata['started_at'],
                    'status': metadata['status']
                }
            return None
                    
        except Exception as e:
            logger.error(f"Error getting job metadata: {str(e)}")
            raise
    
    def get_complete_textract_response(self, job_id: str) -> Dict:
        """Get complete Textract response with all blocks across all pages"""
        try:
            logger.info(f"Retrieving complete Textract response for job: {job_id}")
            
            # Get first page
            response = self.textract.get_document_analysis(JobId=job_id)
            all_blocks = response.get('Blocks', [])
            
            # Get remaining pages if they exist
            while response.get('NextToken'):
                try:
                    response = self.textract.get_document_analysis(
                        JobId=job_id,
                        NextToken=response['NextToken']
                    )
                    all_blocks.extend(response.get('Blocks', []))
                    
                except Exception as e:
                    logger.error(f"Error retrieving Textract results: {e}")
                    raise
            
            logger.info(f"Retrieved {len(all_blocks)} blocks from Textract")
            
            return {
                'Blocks': all_blocks,
                'JobStatus': 'SUCCEEDED',
                'DocumentMetadata': response.get('DocumentMetadata', {})
            }
            
        except Exception as e:
            logger.error(f"Error getting complete Textract response: {str(e)}")
            raise
    
    def save_structured_output(self, doc_id: str, textract_response: Dict, job_metadata: Dict) -> List[str]:
        """Save structured Textract output to S3"""
        
        files_created = []
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        base_path = f"extracted_text/{doc_id}"
        
        try:
            # 1. Save readable text (reconstructed from LINE blocks in reading order)
            readable_text = self.extract_readable_text(textract_response)
            text_key = f"{base_path}/{timestamp}_full_text.txt"
            self.s3.put_object(
                Bucket=self.output_bucket,
                Key=text_key,
                Body=readable_text.encode('utf-8'),
                ContentType='text/plain',
                Metadata={
                    'doc_id': doc_id,
                    'extraction_timestamp': timestamp,
                    'textract_job_id': job_metadata['job_id'],
                    'character_count': str(len(readable_text))
                }
            )
            files_created.append(text_key)
            logger.info(f"Saved readable text: {len(readable_text)} characters")
            
            # 2. Save complete Textract response for debugging/analysis
            response_key = f"{base_path}/{timestamp}_textract_response.json"
            self.s3.put_object(
                Bucket=self.output_bucket,
                Key=response_key,
                Body=json.dumps(textract_response, default=str).encode('utf-8'),
                ContentType='application/json'
            )
            files_created.append(response_key)
            
            # 3. Extract and save structured data (tables, key-values, layout)
            structured_files = self.extract_structured_data(textract_response, base_path, timestamp)
            files_created.extend(structured_files)
            
            # 4. Save processing metadata
            metadata = {
                'doc_id': doc_id,
                'job_id': job_metadata['job_id'],
                'source_document': {
                    'bucket': job_metadata['s3_bucket'],
                    'key': job_metadata['s3_key']
                },
                'processing_timestamp': timestamp,
                'blocks_count': len(textract_response.get('Blocks', [])),
                'pages_count': len(set(block.get('Page', 1) for block in textract_response.get('Blocks', []))),
                'character_count': len(readable_text),
                'files_created': files_created
            }
            
            metadata_key = f"{base_path}/{timestamp}_processing_metadata.json"
            self.s3.put_object(
                Bucket=self.output_bucket,
                Key=metadata_key,
                Body=json.dumps(metadata, default=str).encode('utf-8'),
                ContentType='application/json'
            )
            files_created.append(metadata_key)
            
            return files_created
            
        except Exception as e:
            logger.error(f"Error saving structured output: {e}")
            raise
    
    def extract_readable_text(self, textract_response: Dict) -> str:
        """Extract readable text in proper reading order from LINE blocks"""
        try:
            blocks = textract_response.get('Blocks', [])
            
            # Get LINE blocks and sort by reading order
            line_blocks = [block for block in blocks if block['BlockType'] == 'LINE']
            
            # Sort by page, then by top position, then by left position
            line_blocks.sort(key=lambda x: (
                x.get('Page', 1),
                x.get('Geometry', {}).get('BoundingBox', {}).get('Top', 0),
                x.get('Geometry', {}).get('BoundingBox', {}).get('Left', 0)
            ))
            
            # Extract text and reconstruct paragraphs
            text_lines = []
            current_page = 1
            
            for block in line_blocks:
                page = block.get('Page', 1)
                text = block.get('Text', '').strip()
                
                if text:
                    # Add page break marker if we've moved to a new page
                    if page > current_page:
                        text_lines.append(f"\n--- Page {page} ---\n")
                        current_page = page
                    
                    text_lines.append(text)
            
            return '\n'.join(text_lines)
            
        except Exception as e:
            logger.error(f"Error extracting readable text: {e}")
            return ""
    
    def extract_structured_data(self, textract_response: Dict, base_path: str, timestamp: str) -> List[str]:
        """Extract structured data (tables, key-values, layout) and save to S3"""
        
        files_created = []
        blocks = textract_response.get('Blocks', [])
        
        try:
            # Extract tables
            tables = self.extract_tables(blocks)
            for i, table in enumerate(tables, 1):
                table_key = f"{base_path}/{timestamp}_table_{i}.csv"
                csv_content = self.table_to_csv(table)
                
                self.s3.put_object(
                    Bucket=self.output_bucket,
                    Key=table_key,
                    Body=csv_content.encode('utf-8'),
                    ContentType='text/csv'
                )
                files_created.append(table_key)
                logger.info(f"Saved table {i}: {len(table)} rows")
            
            # Extract key-value pairs
            key_values = self.extract_key_values(blocks)
            if key_values:
                kv_key = f"{base_path}/{timestamp}_key_values.csv"
                kv_content = self.key_values_to_csv(key_values)
                
                self.s3.put_object(
                    Bucket=self.output_bucket,
                    Key=kv_key,
                    Body=kv_content.encode('utf-8'),
                    ContentType='text/csv'
                )
                files_created.append(kv_key)
                logger.info(f"Saved key-values: {len(key_values)} pairs")
            
            # Extract layout information
            layout_info = self.extract_layout_info(blocks)
            if layout_info:
                layout_key = f"{base_path}/{timestamp}_layout.csv"
                layout_content = self.layout_to_csv(layout_info)
                
                self.s3.put_object(
                    Bucket=self.output_bucket,
                    Key=layout_key,
                    Body=layout_content.encode('utf-8'),
                    ContentType='text/csv'
                )
                files_created.append(layout_key)
                logger.info(f"Saved layout info: {len(layout_info)} elements")
            
            return files_created
            
        except Exception as e:
            logger.error(f"Error extracting structured data: {e}")
            return files_created
    
    def extract_tables(self, blocks: List[Dict]) -> List[List[List[str]]]:
        """Extract table data from Textract TABLE blocks"""
        tables = []
        table_blocks = [block for block in blocks if block.get('BlockType') == 'TABLE']
        
        for table_block in table_blocks:
            # For now, create a simple representation
            # Full implementation would parse CELL relationships
            table_data = []
            
            # Get table dimensions from relationships
            relationships = table_block.get('Relationships', [])
            cell_ids = []
            
            for relationship in relationships:
                if relationship.get('Type') == 'CHILD':
                    cell_ids.extend(relationship.get('Ids', []))
            
            # Find CELL blocks
            cell_blocks = [block for block in blocks if block.get('Id') in cell_ids and block.get('BlockType') == 'CELL']
            
            if cell_blocks:
                # Group cells by row
                rows = {}
                for cell in cell_blocks:
                    row_index = cell.get('RowIndex', 1)
                    col_index = cell.get('ColumnIndex', 1)
                    
                    if row_index not in rows:
                        rows[row_index] = {}
                    
                    # Get cell text from child WORD blocks
                    cell_text = self.get_cell_text(cell, blocks)
                    rows[row_index][col_index] = cell_text
                
                # Convert to table format
                for row_idx in sorted(rows.keys()):
                    row_data = []
                    row = rows[row_idx]
                    for col_idx in sorted(row.keys()):
                        row_data.append(row[col_idx])
                    table_data.append(row_data)
            
            if table_data:
                tables.append(table_data)
        
        return tables
    
    def get_cell_text(self, cell_block: Dict, all_blocks: List[Dict]) -> str:
        """Get text content of a table cell"""
        cell_text = []
        
        relationships = cell_block.get('Relationships', [])
        for relationship in relationships:
            if relationship.get('Type') == 'CHILD':
                child_ids = relationship.get('Ids', [])
                for child_id in child_ids:
                    child_block = next((block for block in all_blocks if block.get('Id') == child_id), None)
                    if child_block and child_block.get('BlockType') == 'WORD':
                        cell_text.append(child_block.get('Text', ''))
        
        return ' '.join(cell_text)
    
    def extract_key_values(self, blocks: List[Dict]) -> List[Dict]:
        """Extract key-value pairs from KEY_VALUE_SET blocks"""
        key_values = []
        kv_blocks = [block for block in blocks if block.get('BlockType') == 'KEY_VALUE_SET']
        
        # Group by key-value pairs
        keys = [block for block in kv_blocks if block.get('EntityTypes', [{}])[0].get('Type') == 'KEY']
        values = [block for block in kv_blocks if block.get('EntityTypes', [{}])[0].get('Type') == 'VALUE']
        
        # Match keys with their values
        for key_block in keys:
            key_text = self.get_kv_text(key_block, blocks)
            
            # Find corresponding value
            value_text = ""
            relationships = key_block.get('Relationships', [])
            for relationship in relationships:
                if relationship.get('Type') == 'VALUE':
                    value_ids = relationship.get('Ids', [])
                    for value_id in value_ids:
                        value_block = next((block for block in values if block.get('Id') == value_id), None)
                        if value_block:
                            value_text = self.get_kv_text(value_block, blocks)
                            break
            
            if key_text:
                key_values.append({
                    'key': key_text,
                    'value': value_text,
                    'confidence': key_block.get('Confidence', 0)
                })
        
        return key_values
    
    def get_kv_text(self, kv_block: Dict, all_blocks: List[Dict]) -> str:
        """Get text content of a key-value block"""
        kv_text = []
        
        relationships = kv_block.get('Relationships', [])
        for relationship in relationships:
            if relationship.get('Type') == 'CHILD':
                child_ids = relationship.get('Ids', [])
                for child_id in child_ids:
                    child_block = next((block for block in all_blocks if block.get('Id') == child_id), None)
                    if child_block and child_block.get('BlockType') == 'WORD':
                        kv_text.append(child_block.get('Text', ''))
        
        return ' '.join(kv_text)
    
    def extract_layout_info(self, blocks: List[Dict]) -> List[Dict]:
        """Extract layout information from blocks"""
        layout_info = []
        
        for block in blocks:
            if block.get('BlockType') in ['LINE', 'WORD']:
                geometry = block.get('Geometry', {}).get('BoundingBox', {})
                layout_info.append({
                    'block_type': block.get('BlockType'),
                    'text': block.get('Text', ''),
                    'page': block.get('Page', 1),
                    'left': geometry.get('Left', 0),
                    'top': geometry.get('Top', 0),
                    'width': geometry.get('Width', 0),
                    'height': geometry.get('Height', 0),
                    'confidence': block.get('Confidence', 0)
                })
        
        return layout_info
    
    def table_to_csv(self, table: List[List[str]]) -> str:
        """Convert table data to CSV format"""
        output = io.StringIO()
        writer = csv.writer(output)
        for row in table:
            writer.writerow(row)
        return output.getvalue()
    
    def key_values_to_csv(self, key_values: List[Dict]) -> str:
        """Convert key-value pairs to CSV format"""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Key', 'Value', 'Confidence'])
        for kv in key_values:
            writer.writerow([kv['key'], kv['value'], kv['confidence']])
        return output.getvalue()
    
    def layout_to_csv(self, layout_info: List[Dict]) -> str:
        """Convert layout information to CSV format"""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['BlockType', 'Text', 'Page', 'Left', 'Top', 'Width', 'Height', 'Confidence'])
        for item in layout_info:
            writer.writerow([
                item['block_type'], item['text'], item['page'],
                item['left'], item['top'], item['width'], item['height'],
                item['confidence']
            ])
        return output.getvalue()
    
    def update_job_status(self, job_id: str, status: str, files_created: List[str] = None, error_message: str = None):
        """Update job status in database using DatabaseManager"""
        try:
            if status == 'COMPLETED':
                # For completed jobs, store file information
                files_dict = {'files_created': files_created} if files_created else None
                self.db_manager.update_textract_job_completion(
                    job_id=job_id,
                    status=status,
                    files_created=files_dict
                )
            else:
                # For failed jobs
                self.db_manager.update_textract_job_completion(
                    job_id=job_id,
                    status=status,
                    error_message=error_message
                )
            
            logger.info(f"Updated job status: {job_id} -> {status}")
                    
        except Exception as e:
            logger.error(f"Error updating job status: {str(e)}")
            raise
    
    def publish_text_extraction_complete(self, job_metadata: Dict, files_created: List[str], textract_response: Dict):
        """Publish text extraction completion message"""
        try:
            # Find the main text file
            text_file = next((f for f in files_created if 'full_text.txt' in f), '')
            
            # Prepare document metadata
            document_metadata = {
                "original_filename": job_metadata['s3_key'].split('/')[-1],
                "file_size": 0,  # We don't have this readily available
                "page_count": len(set(block.get('Page', 1) for block in textract_response.get('Blocks', []))),
                "processing_started": job_metadata.get('created_at', datetime.utcnow()).isoformat() + "Z" if isinstance(job_metadata.get('created_at'), datetime) else str(job_metadata.get('created_at', datetime.utcnow().isoformat() + "Z"))
            }
            
            # Prepare processing metadata
            processing_metadata = {
                "character_count": 0,  # We'd need to calculate this
                "extraction_method": "aws_textract_structured",
                "textract_job_id": job_metadata['job_id'],
                "files_created_count": len(files_created),
                "structure_extracted": True
            }
            
            # Use the correct method from StandardizedMessagePublisher
            self.message_publisher.publish_text_extraction_complete(
                doc_id=job_metadata['doc_id'],
                doc_hash=job_metadata['doc_id'],  # Using doc_id as doc_hash for now
                text_location=f"s3://{self.output_bucket}/{text_file}" if text_file else "",
                structure_location=f"s3://{self.output_bucket}/extracted_text/{job_metadata['doc_id']}/",
                document_metadata=document_metadata,
                processing_metadata=processing_metadata,
                topic_arn=self.text_extraction_complete_topic_arn
            )
            
            logger.info(f"Published text extraction completion: {job_metadata['doc_id']} with {len(files_created)} files")
            
        except Exception as e:
            logger.error(f"Error publishing completion message: {str(e)}")
            # Don't raise - this is not critical for the core text extraction functionality
            logger.warning("Continuing despite messaging error - text extraction completed successfully")


# Lambda handler function
def lambda_handler(event, context):
    """Lambda entry point"""
    try:
        processor = TextExtractorProcessor()
        return processor.lambda_handler(event, context)
    except Exception as e:
        logger.error(f"TextExtractor Processor error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
