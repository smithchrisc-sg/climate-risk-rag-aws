"""
TextExtractor Processor Lambda Function
Processes completed Textract jobs and saves structured output
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

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class TextExtractorProcessor:
    """Processes completed Textract jobs and saves structured output"""
    
    def __init__(self):
        self.textract = boto3.client('textract')
        self.s3 = boto3.client('s3')
        self.sqs = boto3.client('sqs')
        
        # Environment configuration
        self.output_bucket = os.environ['OUTPUT_BUCKET']
        self.database_url = os.environ['DATABASE_URL']
        self.next_stage_queue_url = os.environ.get('NEXT_STAGE_QUEUE_URL')
        
        logger.info(f"TextExtractor Processor initialized")
        logger.info(f"Output bucket: {self.output_bucket}")

    def get_db_connection(self):
        """Get PostgreSQL database connection"""
        try:
            conn = psycopg2.connect(self.database_url)
            return conn
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            raise

    def generate_doc_id(self, source_key: str) -> str:
        """Generate doc_id from source key"""
        try:
            # Extract filename without extension
            filename = os.path.basename(source_key)
            doc_id = os.path.splitext(filename)[0]
            
            # Clean up doc_id (remove special characters, spaces)
            import re
            doc_id = re.sub(r'[^a-zA-Z0-9_-]', '_', doc_id)
            doc_id = re.sub(r'_+', '_', doc_id)  # Replace multiple underscores with single
            doc_id = doc_id.strip('_')  # Remove leading/trailing underscores
            
            logger.info(f"Generated doc_id: {doc_id} from source_key: {source_key}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error generating doc_id from {source_key}: {str(e)}")
            # Fallback to timestamp-based ID
            return f"doc_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    def get_complete_textract_response(self, job_id: str) -> Dict[str, Any]:
        """Get complete Textract response handling pagination"""
        try:
            logger.info(f"Retrieving Textract results for job: {job_id}")
            
            # Get first page of results
            response = self.textract.get_document_analysis(JobId=job_id)
            
            # Collect all blocks
            all_blocks = response.get('Blocks', [])
            
            # Handle pagination
            next_token = response.get('NextToken')
            while next_token:
                logger.info(f"Fetching next page of results...")
                next_response = self.textract.get_document_analysis(
                    JobId=job_id,
                    NextToken=next_token
                )
                all_blocks.extend(next_response.get('Blocks', []))
                next_token = next_response.get('NextToken')
            
            # Update response with all blocks
            response['Blocks'] = all_blocks
            
            logger.info(f"Retrieved {len(all_blocks)} blocks from Textract")
            return response
            
        except Exception as e:
            logger.error(f"Error retrieving Textract results: {str(e)}")
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
                if 'Text' in block:
                    text_lines.append(block['Text'])
            
            return '\n'.join(text_lines)
            
        except Exception as e:
            logger.error(f"Error extracting raw text: {str(e)}")
            return ""

    def extract_layout_csv(self, textract_response: Dict) -> str:
        """Extract layout information as CSV"""
        try:
            blocks = textract_response.get('Blocks', [])
            
            # Get layout blocks
            layout_blocks = [block for block in blocks if block['BlockType'].startswith('LAYOUT_')]
            
            # Sort by reading order
            layout_blocks.sort(key=lambda x: (
                x.get('Page', 1),
                x.get('Geometry', {}).get('BoundingBox', {}).get('Top', 0),
                x.get('Geometry', {}).get('BoundingBox', {}).get('Left', 0)
            ))
            
            # Create CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                'Page', 'Layout_Type', 'Text', 'Reading_Order', 'Confidence', 
                'Top', 'Left', 'Width', 'Height'
            ])
            
            # Data rows
            for i, block in enumerate(layout_blocks):
                bbox = block.get('Geometry', {}).get('BoundingBox', {})
                writer.writerow([
                    block.get('Page', 1),
                    block['BlockType'],
                    block.get('Text', '').replace('\n', ' '),
                    i + 1,
                    round(block.get('Confidence', 0), 2),
                    round(bbox.get('Top', 0), 6),
                    round(bbox.get('Left', 0), 6),
                    round(bbox.get('Width', 0), 6),
                    round(bbox.get('Height', 0), 6)
                ])
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error extracting layout CSV: {str(e)}")
            return ""

    def extract_key_value_csv(self, textract_response: Dict) -> str:
        """Extract key-value pairs as CSV"""
        try:
            blocks = textract_response.get('Blocks', [])
            
            # Get key-value blocks
            kv_blocks = [block for block in blocks if block['BlockType'] == 'KEY_VALUE_SET']
            
            # Separate keys and values
            key_blocks = [block for block in kv_blocks if block.get('EntityTypes', []) == ['KEY']]
            value_blocks = [block for block in kv_blocks if block.get('EntityTypes', []) == ['VALUE']]
            
            # Create mapping of relationships
            key_value_pairs = []
            
            for key_block in key_blocks:
                key_text = self._get_block_text(key_block, blocks)
                value_text = ""
                
                # Find associated value
                relationships = key_block.get('Relationships', [])
                for relationship in relationships:
                    if relationship['Type'] == 'VALUE':
                        value_ids = relationship.get('Ids', [])
                        for value_id in value_ids:
                            value_block = next((b for b in value_blocks if b['Id'] == value_id), None)
                            if value_block:
                                value_text = self._get_block_text(value_block, blocks)
                                break
                
                key_value_pairs.append({
                    'page': key_block.get('Page', 1),
                    'key': key_text,
                    'value': value_text,
                    'key_confidence': round(key_block.get('Confidence', 0), 2),
                    'value_confidence': round(value_block.get('Confidence', 0) if 'value_block' in locals() else 0, 2)
                })
            
            # Create CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow(['Page', 'Key', 'Value', 'Key_Confidence', 'Value_Confidence'])
            
            # Data rows
            for pair in key_value_pairs:
                writer.writerow([
                    pair['page'],
                    pair['key'],
                    pair['value'],
                    pair['key_confidence'],
                    pair['value_confidence']
                ])
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error extracting key-value CSV: {str(e)}")
            return ""

    def extract_tables_csv(self, textract_response: Dict) -> List[str]:
        """Extract tables as separate CSV strings"""
        try:
            blocks = textract_response.get('Blocks', [])
            
            # Get table blocks
            table_blocks = [block for block in blocks if block['BlockType'] == 'TABLE']
            
            tables_csv = []
            
            for table_block in table_blocks:
                # Get table cells
                cell_blocks = []
                relationships = table_block.get('Relationships', [])
                
                for relationship in relationships:
                    if relationship['Type'] == 'CHILD':
                        cell_ids = relationship.get('Ids', [])
                        for cell_id in cell_ids:
                            cell_block = next((b for b in blocks if b['Id'] == cell_id and b['BlockType'] == 'CELL'), None)
                            if cell_block:
                                cell_blocks.append(cell_block)
                
                if not cell_blocks:
                    continue
                
                # Organize cells by row and column
                table_data = {}
                max_row = 0
                max_col = 0
                
                for cell in cell_blocks:
                    row_index = cell.get('RowIndex', 1)
                    col_index = cell.get('ColumnIndex', 1)
                    cell_text = self._get_block_text(cell, blocks)
                    
                    if row_index not in table_data:
                        table_data[row_index] = {}
                    
                    table_data[row_index][col_index] = {
                        'text': cell_text,
                        'confidence': round(cell.get('Confidence', 0), 2)
                    }
                    
                    max_row = max(max_row, row_index)
                    max_col = max(max_col, col_index)
                
                # Create CSV for this table
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Data rows
                for row in range(1, max_row + 1):
                    row_data = []
                    for col in range(1, max_col + 1):
                        cell_data = table_data.get(row, {}).get(col, {'text': '', 'confidence': 0})
                        row_data.append(cell_data['text'])
                    writer.writerow(row_data)
                
                # Add confidence scores as separate section
                writer.writerow([])  # Empty row
                writer.writerow(['Confidence Scores'])
                for row in range(1, max_row + 1):
                    conf_data = []
                    for col in range(1, max_col + 1):
                        cell_data = table_data.get(row, {}).get(col, {'text': '', 'confidence': 0})
                        conf_data.append(str(cell_data['confidence']))
                    writer.writerow(conf_data)
                
                tables_csv.append(output.getvalue())
            
            return tables_csv
            
        except Exception as e:
            logger.error(f"Error extracting tables CSV: {str(e)}")
            return []

    def create_document_structure(self, textract_response: Dict) -> Dict:
        """Create optimized document structure for smart chunker"""
        try:
            blocks = textract_response.get('Blocks', [])
            
            # Pre-process structure information for chunker efficiency
            structure = {
                'version': '2025-07-04',
                'created_at': datetime.utcnow().isoformat(),
                'document_metadata': textract_response.get('DocumentMetadata', {}),
                'sections': [],
                'tables': [],
                'forms': [],
                'layout_analysis': {
                    'total_blocks': len(blocks),
                    'block_types': {}
                }
            }
            
            # Count block types
            for block in blocks:
                block_type = block['BlockType']
                structure['layout_analysis']['block_types'][block_type] = \
                    structure['layout_analysis']['block_types'].get(block_type, 0) + 1
            
            # Extract layout sections (headers, paragraphs, etc.)
            layout_blocks = [b for b in blocks if b['BlockType'].startswith('LAYOUT_')]
            layout_blocks.sort(key=lambda x: (
                x.get('Page', 1),
                x.get('Geometry', {}).get('BoundingBox', {}).get('Top', 0),
                x.get('Geometry', {}).get('BoundingBox', {}).get('Left', 0)
            ))
            
            for i, block in enumerate(layout_blocks):
                section = {
                    'section_id': f"section_{i:03d}",
                    'block_type': block['BlockType'],
                    'page': block.get('Page', 1),
                    'text': block.get('Text', ''),
                    'confidence': block.get('Confidence', 0),
                    'geometry': block.get('Geometry', {}),
                    'reading_order': i + 1
                }
                structure['sections'].append(section)
            
            # Extract table information
            table_blocks = [b for b in blocks if b['BlockType'] == 'TABLE']
            for i, table_block in enumerate(table_blocks):
                table_info = {
                    'table_id': f"table_{i:03d}",
                    'page': table_block.get('Page', 1),
                    'confidence': table_block.get('Confidence', 0),
                    'geometry': table_block.get('Geometry', {}),
                    'row_count': 0,
                    'column_count': 0
                }
                
                # Count rows and columns if relationships exist
                relationships = table_block.get('Relationships', [])
                for rel in relationships:
                    if rel['Type'] == 'CHILD':
                        child_ids = rel.get('Ids', [])
                        cells = [b for b in blocks if b['Id'] in child_ids and b['BlockType'] == 'CELL']
                        if cells:
                            max_row = max(cell.get('RowIndex', 0) for cell in cells)
                            max_col = max(cell.get('ColumnIndex', 0) for cell in cells)
                            table_info['row_count'] = max_row
                            table_info['column_count'] = max_col
                
                structure['tables'].append(table_info)
            
            # Extract form information
            kv_blocks = [b for b in blocks if b['BlockType'] == 'KEY_VALUE_SET']
            key_blocks = [b for b in kv_blocks if b.get('EntityTypes', []) == ['KEY']]
            
            for i, key_block in enumerate(key_blocks):
                form_field = {
                    'field_id': f"field_{i:03d}",
                    'page': key_block.get('Page', 1),
                    'key_text': self._get_block_text(key_block, blocks),
                    'key_confidence': key_block.get('Confidence', 0),
                    'geometry': key_block.get('Geometry', {})
                }
                structure['forms'].append(form_field)
            
            logger.info(f"Created document structure with {len(structure['sections'])} sections, "
                       f"{len(structure['tables'])} tables, {len(structure['forms'])} form fields")
            
            return structure
            
        except Exception as e:
            logger.error(f"Error creating document structure: {str(e)}")
            return {
                'version': '2025-07-04',
                'created_at': datetime.utcnow().isoformat(),
                'error': str(e),
                'fallback': True
            }

    def _get_block_text(self, block: Dict, all_blocks: List[Dict]) -> str:
        """Get text content from a block by following relationships"""
        try:
            # If block has direct text, return it
            if 'Text' in block:
                return block['Text']
            
            # Otherwise, get text from child blocks
            text_parts = []
            relationships = block.get('Relationships', [])
            
            for relationship in relationships:
                if relationship['Type'] == 'CHILD':
                    child_ids = relationship.get('Ids', [])
                    for child_id in child_ids:
                        child_block = next((b for b in all_blocks if b['Id'] == child_id), None)
                        if child_block and child_block['BlockType'] == 'WORD':
                            text_parts.append(child_block.get('Text', ''))
            
            return ' '.join(text_parts)
            
        except Exception as e:
            logger.error(f"Error getting block text: {str(e)}")
            return ""

    def save_structured_output(self, textract_response: Dict, doc_hash: str, job_metadata: Dict) -> Dict[str, Any]:
        """Save structured Textract output to S3 using new directory structure"""
        try:
            # Generate doc_id from source key
            doc_id = self.generate_doc_id(job_metadata['source_key'])
            logger.info(f"Saving structured output for doc_id: {doc_id} (doc_hash: {doc_hash})")
            
            # New directory structure: {doc_id}/
            base_key = doc_id
            files_created = []
            
            # Extract raw text first (needed for multiple files)
            raw_text = self.extract_raw_text(textract_response)
            
            # 1. Save full text file: {doc_id}_full_text.txt
            if raw_text:
                text_key = f"{base_key}/{doc_id}_full_text.txt"
                self.s3.put_object(
                    Bucket=self.output_bucket,
                    Key=text_key,
                    Body=raw_text.encode('utf-8'),
                    ContentType='text/plain'
                )
                files_created.append(f'{doc_id}_full_text.txt')
                logger.info(f"Saved full text: {text_key}")
            
            # 2. Create metadata directory structure
            metadata_base = f"{base_key}/metadata"
            
            # 2a. Save complete JSON response (for smart chunker)
            json_key = f"{metadata_base}/textract_response.json"
            self.s3.put_object(
                Bucket=self.output_bucket,
                Key=json_key,
                Body=json.dumps(textract_response, indent=2, default=str),
                ContentType='application/json'
            )
            files_created.append('metadata/textract_response.json')
            
            # 2b. Save layout structure CSV
            layout_csv = self.extract_layout_csv(textract_response)
            if layout_csv:
                layout_key = f"{metadata_base}/layout_structure.csv"
                self.s3.put_object(
                    Bucket=self.output_bucket,
                    Key=layout_key,
                    Body=layout_csv.encode('utf-8'),
                    ContentType='text/csv'
                )
                files_created.append('metadata/layout_structure.csv')
            
            # 2c. Create and save document_structure.json (NEW - optimized for chunker)
            document_structure = self.create_document_structure(textract_response)
            if document_structure:
                doc_structure_key = f"{metadata_base}/document_structure.json"
                self.s3.put_object(
                    Bucket=self.output_bucket,
                    Key=doc_structure_key,
                    Body=json.dumps(document_structure, indent=2, default=str),
                    ContentType='application/json'
                )
                files_created.append('metadata/document_structure.json')
            
            # 3. Save tables in tables/ subdirectory
            tables_csv = self.extract_tables_csv(textract_response)
            if tables_csv:
                tables_summary = {
                    'total_tables': len(tables_csv),
                    'table_files': [],
                    'created_at': datetime.utcnow().isoformat()
                }
                
                for i, table_csv in enumerate(tables_csv):
                    table_key = f"{metadata_base}/tables/table_{i+1:03d}.csv"
                    self.s3.put_object(
                        Bucket=self.output_bucket,
                        Key=table_key,
                        Body=table_csv.encode('utf-8'),
                        ContentType='text/csv'
                    )
                    table_filename = f'table_{i+1:03d}.csv'
                    files_created.append(f'metadata/tables/{table_filename}')
                    tables_summary['table_files'].append(table_filename)
                
                # Save tables summary
                tables_summary_key = f"{metadata_base}/tables/tables_summary.json"
                self.s3.put_object(
                    Bucket=self.output_bucket,
                    Key=tables_summary_key,
                    Body=json.dumps(tables_summary, indent=2, default=str),
                    ContentType='application/json'
                )
                files_created.append('metadata/tables/tables_summary.json')
            
            # 4. Save forms in forms/ subdirectory
            kv_csv = self.extract_key_value_csv(textract_response)
            if kv_csv:
                forms_key = f"{metadata_base}/forms/key_values.csv"
                self.s3.put_object(
                    Bucket=self.output_bucket,
                    Key=forms_key,
                    Body=kv_csv.encode('utf-8'),
                    ContentType='text/csv'
                )
                files_created.append('metadata/forms/key_values.csv')
                
                # Save forms summary
                forms_summary = {
                    'key_value_pairs_found': len(kv_csv.split('\n')) - 1 if kv_csv else 0,
                    'created_at': datetime.utcnow().isoformat()
                }
                forms_summary_key = f"{metadata_base}/forms/forms_summary.json"
                self.s3.put_object(
                    Bucket=self.output_bucket,
                    Key=forms_summary_key,
                    Body=json.dumps(forms_summary, indent=2, default=str),
                    ContentType='application/json'
                )
                files_created.append('metadata/forms/forms_summary.json')
            
            # 5. Save processing info
            processing_info = {
                'doc_id': doc_id,
                'doc_hash': doc_hash,
                'processing_date': datetime.utcnow().isoformat(),
                'textract_model_version': textract_response.get('AnalyzeDocumentModelVersion'),
                'pages_processed': textract_response.get('DocumentMetadata', {}).get('Pages', 0),
                'blocks_extracted': len(textract_response.get('Blocks', [])),
                'files_created': files_created,
                'source_document': {
                    'bucket': job_metadata['source_bucket'],
                    'key': job_metadata['source_key']
                },
                'extraction_statistics': {
                    'total_blocks': len(textract_response.get('Blocks', [])),
                    'layout_blocks': len([b for b in textract_response.get('Blocks', []) if b['BlockType'].startswith('LAYOUT_')]),
                    'table_blocks': len([b for b in textract_response.get('Blocks', []) if b['BlockType'] == 'TABLE']),
                    'key_value_blocks': len([b for b in textract_response.get('Blocks', []) if b['BlockType'] == 'KEY_VALUE_SET']),
                    'text_length': len(raw_text) if raw_text else 0
                },
                'directory_structure': 'v2_new_format',
                'structure_version': '2025-07-04'
            }
            
            processing_info_key = f"{metadata_base}/processing_info.json"
            self.s3.put_object(
                Bucket=self.output_bucket,
                Key=processing_info_key,
                Body=json.dumps(processing_info, indent=2, default=str),
                ContentType='application/json'
            )
            files_created.append('metadata/processing_info.json')
            
            logger.info(f"Saved {len(files_created)} files for doc_id: {doc_id} in new structure")
            return processing_info
            
        except Exception as e:
            logger.error(f"Error saving structured output: {str(e)}")
            raise

    def update_job_status(self, job_id: str, status: str, metadata: Optional[Dict] = None, error_message: Optional[str] = None):
        """Update job status in PostgreSQL"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Update textract_jobs table
            update_query = """
                UPDATE textract_jobs 
                SET status = %s, completed_at = %s, error_message = %s,
                    pages_processed = %s, blocks_extracted = %s, files_created = %s,
                    textract_model_version = %s, updated_at = NOW()
                WHERE job_id = %s
            """
            
            cursor.execute(update_query, (
                status,
                datetime.utcnow() if status in ['SUCCEEDED', 'FAILED'] else None,
                error_message,
                metadata.get('pages_processed') if metadata else None,
                metadata.get('blocks_extracted') if metadata else None,
                json.dumps(metadata.get('files_created', [])) if metadata else None,
                metadata.get('textract_model_version') if metadata else None,
                job_id
            ))
            
            # Update document processing status
            if status == 'SUCCEEDED':
                doc_status_query = """
                    UPDATE document_processing_status 
                    SET text_extraction_status = 'COMPLETED',
                        text_extraction_completed_at = NOW(),
                        updated_at = NOW()
                    WHERE text_extraction_job_id = %s
                """
                cursor.execute(doc_status_query, (job_id,))
            elif status == 'FAILED':
                doc_status_query = """
                    UPDATE document_processing_status 
                    SET text_extraction_status = 'FAILED',
                        updated_at = NOW()
                    WHERE text_extraction_job_id = %s
                """
                cursor.execute(doc_status_query, (job_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Updated job status: {job_id} -> {status}")
            
        except Exception as e:
            logger.error(f"Error updating job status: {str(e)}")
            raise

    def get_job_metadata(self, job_id: str) -> Optional[Dict]:
        """Get job metadata from PostgreSQL"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT * FROM textract_jobs WHERE job_id = %s
            """
            
            cursor.execute(query, (job_id,))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Error getting job metadata: {str(e)}")
            return None

    def send_to_next_stage(self, doc_hash: str, job_metadata: Dict, processing_metadata: Dict):
        """Send message to next stage queue for chunking with new format"""
        try:
            if not self.next_stage_queue_url:
                logger.info("No next stage queue configured, skipping")
                return
            
            # Generate doc_id from source key
            doc_id = self.generate_doc_id(job_metadata['source_key'])
            
            # New message format for updated text chunker
            message = {
                'doc_id': doc_id,
                'doc_hash': doc_hash,
                'stage': 'text_ready',
                'full_text_location': {
                    'bucket': self.output_bucket,
                    'key': f"{doc_id}/{doc_id}_full_text.txt"
                },
                'document_structure_location': {
                    'bucket': self.output_bucket,
                    'key': f"{doc_id}/metadata/textract_response.json"
                },
                'metadata_base_path': f"{doc_id}/metadata/",
                'source_document': {
                    'bucket': job_metadata['source_bucket'],
                    'key': job_metadata['source_key']
                },
                'processing_metadata': processing_metadata,
                'timestamp': datetime.utcnow().isoformat(),
                'structure_version': '2025-07-04'
            }
            
            self.sqs.send_message(
                QueueUrl=self.next_stage_queue_url,
                MessageBody=json.dumps(message, default=str)
            )
            
            logger.info(f"Sent new format message to next stage queue for doc_id: {doc_id} (doc_hash: {doc_hash})")
            
        except Exception as e:
            logger.error(f"Error sending to next stage: {str(e)}")
            # Don't raise - this shouldn't fail the main processing

    def process_textract_completion(self, job_id: str, status: str) -> Dict[str, Any]:
        """Process Textract job completion"""
        try:
            logger.info(f"Processing Textract completion: {job_id} -> {status}")
            
            # Get job metadata
            job_metadata = self.get_job_metadata(job_id)
            if not job_metadata:
                raise Exception(f"Job metadata not found for job_id: {job_id}")
            
            doc_hash = job_metadata['doc_hash']
            
            if status == 'SUCCEEDED':
                # Get Textract results
                textract_response = self.get_complete_textract_response(job_id)
                
                # Save structured output
                processing_metadata = self.save_structured_output(textract_response, doc_hash, job_metadata)
                
                # Update job status
                self.update_job_status(job_id, 'SUCCEEDED', processing_metadata)
                
                # Send to next stage
                self.send_to_next_stage(doc_hash, job_metadata, processing_metadata)
                
                return {
                    'status': 'success',
                    'job_id': job_id,
                    'doc_hash': doc_hash,
                    'files_created': processing_metadata.get('files_created', []),
                    'pages_processed': processing_metadata.get('pages_processed', 0),
                    'blocks_extracted': processing_metadata.get('blocks_extracted', 0)
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

def lambda_handler(event, context):
    """Lambda function handler for TextExtractor Processor"""
    try:
        logger.info(f"TextExtractor Processor triggered with event: {json.dumps(event, default=str)}")
        
        processor = TextExtractorProcessor()
        results = []
        
        # Process SQS messages (from SNS notifications)
        if 'Records' in event:
            for record in event['Records']:
                event_source = record.get('eventSource') or record.get('EventSource')
                
                if event_source == 'aws:sqs':
                    # Parse SQS message body (contains SNS notification)
                    try:
                        message_body = json.loads(record['body'])
                        job_id = message_body.get('JobId')
                        status = message_body.get('Status')
                        
                        if job_id and status:
                            logger.info(f"Processing Textract completion: {job_id} - {status}")
                            result = processor.process_textract_completion(job_id, status)
                            results.append(result)
                        else:
                            logger.warning(f"Invalid message format: {message_body}")
                            results.append({
                                'status': 'error',
                                'error': 'Invalid message format'
                            })
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse SQS message body: {e}")
                        results.append({
                            'status': 'error',
                            'error': f'JSON decode error: {str(e)}'
                        })
                        
                elif event_source == 'aws:sns':
                    # Direct SNS message (legacy support)
                    sns_message = json.loads(record['Sns']['Message'])
                    job_id = sns_message.get('JobId')
                    status = sns_message.get('Status')
                    
                    if job_id and status:
                        result = processor.process_textract_completion(job_id, status)
                        results.append(result)
                    else:
                        logger.warning(f"Invalid SNS message format: {sns_message}")
                        results.append({
                            'status': 'error',
                            'error': 'Invalid SNS message format'
                        })
                else:
                    logger.warning(f"Unsupported event source: {event_source}")
        
        # Handle direct invocation for testing
        elif 'job_id' in event and 'status' in event:
            result = processor.process_textract_completion(event['job_id'], event['status'])
            results.append(result)
        
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid event format. Expected SNS notification or direct invocation.'
                })
            }
        
        # Summary statistics
        success_count = len([r for r in results if r['status'] == 'success'])
        failed_count = len([r for r in results if r['status'] == 'failed'])
        error_count = len([r for r in results if r['status'] == 'error'])
        
        response_body = {
            'message': f'Processed {len(results)} Textract completions',
            'summary': {
                'success': success_count,
                'failed': failed_count,
                'errors': error_count
            },
            'results': results
        }
        
        logger.info(f"Processing complete: {success_count} success, {failed_count} failed, {error_count} errors")
        
        return {
            'statusCode': 200,
            'body': json.dumps(response_body, default=str)
        }
        
    except Exception as e:
        logger.error(f"TextExtractor Processor error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'TextExtractor Processor failed: {str(e)}'
            })
        }
