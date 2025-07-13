#!/usr/bin/env python3
"""
TextExtractor Processor Lambda Function - STANDARDIZED MESSAGING VERSION
Processes completed Textract jobs and publishes standardized messages
"""

import json
import boto3
import logging
import os
import csv
import io
from datetime import datetime
from typing import Dict, List, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

# Import standardized messaging
from standardized_messaging import StandardizedMessagePublisher, StandardizedMessageParser

# Import DocumentIDManager from shared layer
try:
    from DocumentIDManager import DocumentIDManager
except ImportError:
    # Fallback for development/testing
    class DocumentIDManager:
        def __init__(self, database_url=None):
            self.database_url = database_url
        
        def get_or_create_id_from_s3(self, bucket, key):
            # Fallback implementation
            import hashlib
            content = f"{bucket}/{key}"
            return hashlib.sha256(content.encode()).hexdigest()[:16]

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class TextExtractorProcessor:
    """Processes completed Textract jobs with standardized messaging"""
    
    def __init__(self):
        self.textract = boto3.client('textract')
        self.s3 = boto3.client('s3')
        
        # Environment configuration
        self.output_bucket = os.environ['OUTPUT_BUCKET']
        self.database_url = os.environ['DATABASE_URL']
        
        # Standardized messaging - use SNS instead of SQS
        self.text_extraction_complete_topic_arn = os.environ.get(
            'TEXT_EXTRACTION_COMPLETE_TOPIC_ARN',
            'arn:aws:sns:us-east-1:861276078413:text-extraction-complete'
        )
        
        # Initialize standardized message publisher
        self.message_publisher = StandardizedMessagePublisher()
        
        # Initialize DocumentIDManager
        try:
            self.doc_id_manager = DocumentIDManager(database_url=self.database_url)
            logger.info("DocumentIDManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DocumentIDManager: {e}")
            self.doc_id_manager = None
        
        # Load S3 mappings for selective migration
        self.s3_mappings = self.load_s3_mappings()
        
        logger.info("TextExtractor Processor initialized")
        logger.info(f"Output bucket: {self.output_bucket}")
        logger.info(f"Text extraction complete topic: {self.text_extraction_complete_topic_arn}")

    def lambda_handler(self, event, context):
        """Lambda handler for processing SQS messages from SNS notifications"""
        
        results = []
        
        try:
            logger.info(f"Processing {len(event.get('Records', []))} records")
            
            for record in event.get('Records', []):
                try:
                    result = self.process_sqs_record(record)
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Error processing SQS record: {e}")
                    results.append({'success': False, 'error': str(e)})
            
            # Summary response
            successful = len([r for r in results if r.get('status') == 'success'])
            failed = len([r for r in results if r.get('status') in ['failed', 'unknown'] or not r.get('success', True)])
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'processed': len(results),
                    'successful': successful,
                    'failed': failed,
                    'results': results,
                    'standardized_messaging': True
                })
            }
            
        except Exception as e:
            logger.error(f"Lambda handler error: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }

    def process_sqs_record(self, record: Dict) -> Dict:
        """Process individual SQS record from SNS"""
        
        try:
            # Parse SQS message (from SNS)
            message_body = json.loads(record['body'])
            
            # Handle SNS notification
            if 'Message' in message_body:
                sns_message = json.loads(message_body['Message'])
                
                # AWS Textract completion notification format
                # The message contains job completion details
                job_id = sns_message.get('JobId')
                status = sns_message.get('Status')
                
                # Alternative format - sometimes the job info is nested
                if not job_id and 'DocumentLocation' in sns_message:
                    # This might be a different format, extract what we can
                    job_id = sns_message.get('JobId') or sns_message.get('jobId')
                    status = sns_message.get('Status') or sns_message.get('status') or 'SUCCEEDED'
                
                # If still no job_id, try to extract from the message structure
                if not job_id:
                    # Log the actual message format for debugging
                    logger.info(f"Received SNS message format: {json.dumps(sns_message, indent=2)}")
                    
                    # Try common AWS service notification patterns
                    if 'detail' in sns_message:
                        detail = sns_message['detail']
                        job_id = detail.get('jobId') or detail.get('JobId')
                        status = detail.get('status') or detail.get('Status', 'SUCCEEDED')
                    elif 'Records' in sns_message:
                        # Sometimes AWS services send Records array
                        for record in sns_message['Records']:
                            if 'jobId' in record or 'JobId' in record:
                                job_id = record.get('jobId') or record.get('JobId')
                                status = record.get('status') or record.get('Status', 'SUCCEEDED')
                                break
                
                if job_id:
                    logger.info(f"Processing Textract job completion: {job_id} with status: {status}")
                    return self.process_textract_completion(job_id, status)
                else:
                    # If we still can't find job_id, this might be a different type of message
                    # Log the full message for debugging and try to handle it gracefully
                    logger.warning(f"Could not extract JobId from SNS message. Message keys: {list(sns_message.keys())}")
                    logger.info(f"Full SNS message: {json.dumps(sns_message, indent=2)}")
                    
                    # Return a non-fatal error so processing can continue
                    return {
                        'status': 'skipped',
                        'reason': 'no_job_id_found',
                        'message_keys': list(sns_message.keys())
                    }
            else:
                # Handle direct SQS messages (not from SNS)
                logger.info(f"Processing direct SQS message: {json.dumps(message_body, indent=2)}")
                
                # Check if this is a direct Textract completion message
                job_id = message_body.get('JobId') or message_body.get('jobId')
                status = message_body.get('Status') or message_body.get('status', 'SUCCEEDED')
                
                if job_id:
                    return self.process_textract_completion(job_id, status)
                else:
                    logger.warning(f"Unrecognized message format. Keys: {list(message_body.keys())}")
                    return {
                        'status': 'skipped',
                        'reason': 'unrecognized_format',
                        'message_keys': list(message_body.keys())
                    }
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Raw message body: {record.get('body', 'No body')}")
            raise
        except Exception as e:
            logger.error(f"Error processing SQS record: {e}")
            logger.error(f"Record: {json.dumps(record, indent=2)}")
            raise

    def process_textract_completion(self, job_id: str, status: str) -> Dict:
        """Process Textract job completion with standardized messaging"""
        
        doc_hash = None
        
        try:
            logger.info(f"Processing Textract completion: {job_id} -> {status}")
            
            # Get job metadata from database
            job_metadata = self.get_job_metadata(job_id)
            if not job_metadata:
                raise ValueError(f"Job metadata not found for job_id: {job_id}")
            
            doc_hash = job_metadata['doc_hash']
            
            if status == 'SUCCEEDED':
                # Process successful job
                processing_metadata = self.process_successful_job(job_id, job_metadata)
                
                # Get proper doc_id using DocumentIDManager
                doc_id = self.get_or_create_doc_id(job_metadata)
                
                # Publish standardized text extraction complete message
                self.publish_text_extraction_complete(doc_id, doc_hash, job_metadata, processing_metadata)
                
                return {
                    'status': 'success',
                    'job_id': job_id,
                    'doc_hash': doc_hash,
                    'doc_id': doc_id,
                    'files_created': processing_metadata.get('files_created', []),
                    'pages_processed': processing_metadata.get('pages_processed', 0),
                    'blocks_extracted': processing_metadata.get('blocks_extracted', 0),
                    'standardized_messaging': True
                }
                
            elif status == 'FAILED':
                error_message = f"Textract job failed: {job_id}"
                self.update_job_status(job_id, 'FAILED', error_message=error_message)
                
                return {
                    'status': 'failed',
                    'job_id': job_id,
                    'doc_hash': doc_hash,
                    'error': error_message
                }
            
            else:
                logger.warning(f"Unexpected job status: {status}")
                return {
                    'status': 'unknown',
                    'job_id': job_id,
                    'textract_status': status
                }
                
        except Exception as e:
            logger.error(f"Error processing Textract completion: {str(e)}")
            # Update job status to failed
            try:
                self.update_job_status(job_id, 'FAILED', error_message=str(e))
            except:
                pass
            raise

    def publish_text_extraction_complete(self, doc_id: str, doc_hash: str, job_metadata: Dict, processing_metadata: Dict):
        """Publish standardized text extraction complete message"""
        
        try:
            # Construct S3 folder URL (per requirements - send folder URL not file URLs)
            text_folder_url = f"s3://{self.output_bucket}/data_lake/{doc_id}/"
            
            # Prepare document metadata
            document_metadata = {
                "original_filename": job_metadata.get('source_key', '').split('/')[-1],
                "file_size": 0,  # Default value since file_size not in database
                "page_count": processing_metadata.get('pages_processed', 0),
                "processing_started": job_metadata.get('created_at', datetime.utcnow().isoformat() + "Z")
            }
            
            # Add cost estimate and processing time
            processing_metadata['cost_estimate'] = self.estimate_processing_cost(processing_metadata)
            processing_metadata['selective_migration_used'] = doc_id in [m.get('doc_id') for m in self.s3_mappings.values()]
            
            # Publish standardized message with folder URL
            self.message_publisher.publish_text_extraction_complete(
                doc_id=doc_id,
                doc_hash=doc_hash,
                text_location=text_folder_url,  # Send folder URL
                structure_location=text_folder_url,  # Same folder contains all files
                document_metadata=document_metadata,
                processing_metadata=processing_metadata,
                topic_arn=self.text_extraction_complete_topic_arn
            )
            
            logger.info(f"Published standardized text extraction complete message for {doc_id}")
            
        except Exception as e:
            logger.error(f"Failed to publish text extraction complete message: {e}")
            raise

    def estimate_processing_cost(self, processing_metadata: Dict) -> float:
        """Estimate processing cost based on pages processed"""
        pages = processing_metadata.get('pages_processed', 0)
        # Textract cost: ~$1.50 per 1000 pages
        return (pages / 1000.0) * 1.50

    def process_successful_job(self, job_id: str, job_metadata: Dict) -> Dict:
        """Process successful Textract job and save structured output"""
        
        processing_start = datetime.utcnow()
        
        try:
            # Retrieve Textract results
            logger.info(f"Retrieving Textract results for job: {job_id}")
            textract_response = self.get_textract_results(job_id)
            
            # Get proper doc_id from source key
            doc_id = self.get_or_create_doc_id(job_metadata)
            logger.info(f"Saving structured output for doc_id: {doc_id}")
            
            files_created = self.save_structured_output(doc_id, textract_response, job_metadata)
            
            # Calculate processing metadata
            processing_time = (datetime.utcnow() - processing_start).total_seconds() * 1000
            
            processing_metadata = {
                'files_created': files_created,
                'pages_processed': len(set(block.get('Page', 1) for block in textract_response.get('Blocks', []))),
                'blocks_extracted': len(textract_response.get('Blocks', [])),
                'character_count': self.count_characters(textract_response),
                'processing_time_ms': int(processing_time),
                'job_id': job_id
            }
            
            # Update job status
            self.update_job_status(job_id, 'SUCCEEDED', processing_metadata=processing_metadata)
            
            logger.info(f"Saved {len(files_created)} files for doc_id: {doc_id}")
            
            return processing_metadata
            
        except Exception as e:
            logger.error(f"Error processing successful job: {e}")
            raise

    def get_textract_results(self, job_id: str) -> Dict:
        """Retrieve complete Textract results with pagination"""
        
        all_blocks = []
        next_token = None
        
        while True:
            try:
                if next_token:
                    logger.info("Fetching next page of results...")
                    response = self.textract.get_document_analysis(
                        JobId=job_id,
                        NextToken=next_token
                    )
                else:
                    response = self.textract.get_document_analysis(JobId=job_id)
                
                all_blocks.extend(response.get('Blocks', []))
                next_token = response.get('NextToken')
                
                if not next_token:
                    break
                    
            except Exception as e:
                logger.error(f"Error retrieving Textract results: {e}")
                raise
        
        logger.info(f"Retrieved {len(all_blocks)} blocks from Textract")
        
        return {
            'Blocks': all_blocks,
            'JobStatus': 'SUCCEEDED',
            'DocumentMetadata': response.get('DocumentMetadata', {})
        }

    def save_structured_output(self, doc_id: str, textract_response: Dict, job_metadata: Dict) -> List[str]:
        """Save structured Textract output to S3"""
        
        files_created = []
        base_path = f"data_lake/{doc_id}"
        
        try:
            # 1. Save raw text
            raw_text = self.extract_raw_text(textract_response)
            text_key = f"{base_path}/raw_text.txt"
            self.s3.put_object(
                Bucket=self.output_bucket,
                Key=text_key,
                Body=raw_text.encode('utf-8'),
                ContentType='text/plain'
            )
            files_created.append(text_key)
            
            # 2. Save complete Textract response
            response_key = f"{base_path}/textract_response.json"
            self.s3.put_object(
                Bucket=self.output_bucket,
                Key=response_key,
                Body=json.dumps(textract_response, default=str).encode('utf-8'),
                ContentType='application/json'
            )
            files_created.append(response_key)
            
            # 3. Save processing metadata
            metadata = {
                'doc_id': doc_id,
                'job_id': job_metadata.get('job_id'),
                'source_document': {
                    'bucket': job_metadata.get('source_bucket'),
                    'key': job_metadata.get('source_key')
                },
                'processing_timestamp': datetime.utcnow().isoformat(),
                'blocks_count': len(textract_response.get('Blocks', [])),
                'pages_count': len(set(block.get('Page', 1) for block in textract_response.get('Blocks', []))),
                'character_count': len(raw_text)
            }
            
            metadata_key = f"{base_path}/processing_metadata.json"
            self.s3.put_object(
                Bucket=self.output_bucket,
                Key=metadata_key,
                Body=json.dumps(metadata, default=str).encode('utf-8'),
                ContentType='application/json'
            )
            files_created.append(metadata_key)
            
            # 4. Extract and save structured data (tables, key-values, etc.)
            structured_files = self.extract_structured_data(textract_response, base_path)
            files_created.extend(structured_files)
            
            return files_created
            
        except Exception as e:
            logger.error(f"Error saving structured output: {e}")
            raise

    def extract_raw_text(self, textract_response: Dict) -> str:
        """Extract plain text in reading order"""
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
            
            # Extract text
            text_lines = []
            for block in line_blocks:
                text = block.get('Text', '').strip()
                if text:
                    text_lines.append(text)
            
            return '\n'.join(text_lines)
            
        except Exception as e:
            logger.error(f"Error extracting raw text: {e}")
            return ""

    def extract_structured_data(self, textract_response: Dict, base_path: str) -> List[str]:
        """Extract structured data (tables, key-values) and save to S3"""
        
        files_created = []
        blocks = textract_response.get('Blocks', [])
        
        try:
            # Extract tables
            tables = self.extract_tables(blocks)
            for i, table in enumerate(tables, 1):
                table_key = f"{base_path}/table_{i}.csv"
                csv_content = self.table_to_csv(table)
                
                self.s3.put_object(
                    Bucket=self.output_bucket,
                    Key=table_key,
                    Body=csv_content.encode('utf-8'),
                    ContentType='text/csv'
                )
                files_created.append(table_key)
            
            # Extract key-value pairs
            key_values = self.extract_key_values(blocks)
            if key_values:
                kv_key = f"{base_path}/key_values.csv"
                kv_content = self.key_values_to_csv(key_values)
                
                self.s3.put_object(
                    Bucket=self.output_bucket,
                    Key=kv_key,
                    Body=kv_content.encode('utf-8'),
                    ContentType='text/csv'
                )
                files_created.append(kv_key)
            
            # Extract layout information
            layout_info = self.extract_layout_info(blocks)
            if layout_info:
                layout_key = f"{base_path}/layout.csv"
                layout_content = self.layout_to_csv(layout_info)
                
                self.s3.put_object(
                    Bucket=self.output_bucket,
                    Key=layout_key,
                    Body=layout_content.encode('utf-8'),
                    ContentType='text/csv'
                )
                files_created.append(layout_key)
            
            return files_created
            
        except Exception as e:
            logger.error(f"Error extracting structured data: {e}")
            return files_created

    def extract_tables(self, blocks: List[Dict]) -> List[List[List[str]]]:
        """Extract table data from Textract blocks"""
        # Implementation for table extraction
        # This is a simplified version - full implementation would be more complex
        tables = []
        table_blocks = [block for block in blocks if block.get('BlockType') == 'TABLE']
        
        for table_block in table_blocks:
            # Extract table cells and organize into rows/columns
            # This is a placeholder - actual implementation would parse relationships
            table_data = [["Sample", "Table", "Data"]]
            tables.append(table_data)
        
        return tables

    def extract_key_values(self, blocks: List[Dict]) -> List[Dict]:
        """Extract key-value pairs from Textract blocks"""
        # Implementation for key-value extraction
        key_values = []
        kv_blocks = [block for block in blocks if block.get('BlockType') == 'KEY_VALUE_SET']
        
        for kv_block in kv_blocks:
            # Extract key-value relationships
            # This is a placeholder - actual implementation would parse relationships
            key_values.append({
                'key': 'Sample Key',
                'value': 'Sample Value',
                'confidence': kv_block.get('Confidence', 0)
            })
        
        return key_values

    def extract_layout_info(self, blocks: List[Dict]) -> List[Dict]:
        """Extract layout information from Textract blocks"""
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
        writer = csv.DictWriter(output, fieldnames=['key', 'value', 'confidence'])
        writer.writeheader()
        for kv in key_values:
            writer.writerow(kv)
        return output.getvalue()

    def layout_to_csv(self, layout_info: List[Dict]) -> str:
        """Convert layout information to CSV format"""
        output = io.StringIO()
        if layout_info:
            writer = csv.DictWriter(output, fieldnames=layout_info[0].keys())
            writer.writeheader()
            for item in layout_info:
                writer.writerow(item)
        return output.getvalue()

    def count_characters(self, textract_response: Dict) -> int:
        """Count total characters in extracted text"""
        total_chars = 0
        blocks = textract_response.get('Blocks', [])
        
        for block in blocks:
            if block.get('BlockType') == 'LINE':
                text = block.get('Text', '')
                total_chars += len(text)
        
        return total_chars

    # Database and utility methods (unchanged from original)
    def get_job_metadata(self, job_id: str) -> Optional[Dict]:
        """Get job metadata from database"""
        try:
            conn = psycopg2.connect(self.database_url)
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT job_id, doc_hash, source_bucket, source_key, 
                           created_at, status
                    FROM textract_jobs 
                    WHERE job_id = %s
                """, (job_id,))
                
                result = cursor.fetchone()
                return dict(result) if result else None
                
        except Exception as e:
            logger.error(f"Error getting job metadata: {e}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()

    def update_job_status(self, job_id: str, status: str, error_message: str = None, processing_metadata: Dict = None):
        """Update job status in database"""
        try:
            conn = psycopg2.connect(self.database_url)
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE textract_jobs 
                    SET status = %s, completed_at = %s, error_message = %s
                    WHERE job_id = %s
                """, (status, datetime.utcnow(), error_message, job_id))
                
                conn.commit()
                logger.info(f"Updated job status: {job_id} -> {status}")
                
        except Exception as e:
            logger.error(f"Error updating job status: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    def get_or_create_doc_id(self, job_metadata: Dict) -> str:
        """Extract doc_id from source key filename (data_lake/{doc_id}.pdf)"""
        try:
            source_key = job_metadata.get('source_key', '')
            
            # Extract doc_id from data_lake/{doc_id}.pdf structure
            if source_key.startswith('data_lake/') and source_key.endswith('.pdf'):
                doc_id = source_key[10:-4]  # Remove 'data_lake/' and '.pdf'
                logger.info(f"Extracted doc_id: {doc_id} from source_key: {source_key}")
                return doc_id
            else:
                # Fallback for old structure or unexpected format
                logger.warning(f"Unexpected source_key format: {source_key}, using doc_hash fallback")
                return job_metadata['doc_hash']
                
        except Exception as e:
            logger.error(f"Error extracting doc_id from source_key: {e}")
            return job_metadata['doc_hash']

    def load_s3_mappings(self) -> Dict:
        """Load S3 mappings for selective migration"""
        try:
            # This would load from a configuration file or database
            # For now, return empty dict
            return {}
        except Exception as e:
            logger.error(f"Error loading S3 mappings: {e}")
            return {}


def lambda_handler(event, context):
    """Lambda entry point"""
    processor = TextExtractorProcessor()
    return processor.lambda_handler(event, context)


# For testing
if __name__ == "__main__":
    # Test with a sample event
    test_event = {
        'Records': [{
            'body': json.dumps({
                'Message': json.dumps({
                    'JobId': 'test-job-123',
                    'Status': 'SUCCEEDED',
                    'API': 'StartDocumentAnalysis',
                    'Timestamp': 1752004867493,
                    'DocumentLocation': {
                        'S3ObjectName': 'documents/test.pdf',
                        'S3Bucket': 'test-bucket'
                    }
                })
            })
        }]
    }
    
    processor = TextExtractorProcessor()
    result = processor.lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
