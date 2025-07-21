"""
Output Formatter - Handles formatting and saving of Textract output
Extracted from main processor for better modularity
"""

import json
import csv
import io
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class OutputFormatter:
    """Formats and saves Textract output in various structured formats"""
    
    def __init__(self, config):
        """Initialize formatter with configuration"""
        self.config = config
        import boto3
        self.s3 = boto3.client('s3')
    
    def save_structured_output(self, doc_id: str, textract_response: Dict, job_metadata: Dict) -> List[str]:
        """
        Save structured output from Textract analysis
        
        Args:
            doc_id: Document identifier
            textract_response: Complete Textract response
            job_metadata: Job metadata from database
            
        Returns:
            List of created file paths
        """
        files_created = []
        
        try:
            blocks = textract_response.get('Blocks', [])
            
            # Extract different types of content
            text_content = self._extract_text_content(blocks)
            tables = self._extract_tables(blocks)
            forms = self._extract_forms(blocks)
            layout_info = self._extract_layout_info(blocks)
            
            # Save raw text
            if text_content:
                text_file = self._save_text_content(doc_id, text_content)
                files_created.append(text_file)
            
            # Save tables as CSV
            if tables:
                table_files = self._save_tables_as_csv(doc_id, tables)
                files_created.extend(table_files)
            
            # Save forms as JSON
            if forms:
                forms_file = self._save_forms_as_json(doc_id, forms)
                files_created.append(forms_file)
            
            # Save layout information
            layout_file = self._save_layout_info(doc_id, layout_info)
            files_created.append(layout_file)
            
            # Save complete structured output
            structured_file = self._save_complete_structured_output(
                doc_id, text_content, tables, forms, layout_info, job_metadata
            )
            files_created.append(structured_file)
            
            logger.info(f"Created {len(files_created)} output files for document {doc_id}")
            return files_created
            
        except Exception as e:
            logger.error(f"Error saving structured output for {doc_id}: {str(e)}")
            raise
    
    def _extract_text_content(self, blocks: List[Dict]) -> str:
        """Extract plain text content from Textract blocks"""
        try:
            text_blocks = [block for block in blocks if block.get('BlockType') == 'LINE']
            text_lines = []
            
            for block in text_blocks:
                if 'Text' in block:
                    text_lines.append(block['Text'])
            
            return '\n'.join(text_lines)
            
        except Exception as e:
            logger.error(f"Error extracting text content: {str(e)}")
            return ""
    
    def _extract_tables(self, blocks: List[Dict]) -> List[Dict]:
        """Extract table data from Textract blocks"""
        try:
            tables = []
            table_blocks = [block for block in blocks if block.get('BlockType') == 'TABLE']
            
            for table_block in table_blocks:
                table_data = self._process_table_block(table_block, blocks)
                if table_data:
                    tables.append(table_data)
            
            return tables
            
        except Exception as e:
            logger.error(f"Error extracting tables: {str(e)}")
            return []
    
    def _extract_forms(self, blocks: List[Dict]) -> List[Dict]:
        """Extract form data from Textract blocks"""
        try:
            forms = []
            key_value_blocks = [block for block in blocks if block.get('BlockType') == 'KEY_VALUE_SET']
            
            # Process key-value pairs
            for block in key_value_blocks:
                if block.get('EntityTypes') and 'KEY' in block['EntityTypes']:
                    form_field = self._process_key_value_pair(block, blocks)
                    if form_field:
                        forms.append(form_field)
            
            return forms
            
        except Exception as e:
            logger.error(f"Error extracting forms: {str(e)}")
            return []
    
    def _extract_layout_info(self, blocks: List[Dict]) -> Dict:
        """Extract layout and structure information"""
        try:
            layout_info = {
                'page_count': 0,
                'block_counts': {},
                'confidence_stats': {},
                'geometry_info': []
            }
            
            # Count different block types
            for block in blocks:
                block_type = block.get('BlockType', 'UNKNOWN')
                layout_info['block_counts'][block_type] = layout_info['block_counts'].get(block_type, 0) + 1
                
                # Track page count
                if block_type == 'PAGE':
                    layout_info['page_count'] += 1
                
                # Collect confidence statistics
                confidence = block.get('Confidence', 0)
                if block_type not in layout_info['confidence_stats']:
                    layout_info['confidence_stats'][block_type] = []
                layout_info['confidence_stats'][block_type].append(confidence)
                
                # Collect geometry information for key blocks
                if block_type in ['LINE', 'WORD', 'TABLE', 'KEY_VALUE_SET']:
                    geometry = block.get('Geometry', {})
                    if geometry:
                        layout_info['geometry_info'].append({
                            'block_type': block_type,
                            'block_id': block.get('Id'),
                            'bounding_box': geometry.get('BoundingBox', {}),
                            'confidence': confidence
                        })
            
            # Calculate average confidence per block type
            for block_type, confidences in layout_info['confidence_stats'].items():
                if confidences:
                    layout_info['confidence_stats'][block_type] = {
                        'average': sum(confidences) / len(confidences),
                        'min': min(confidences),
                        'max': max(confidences),
                        'count': len(confidences)
                    }
            
            return layout_info
            
        except Exception as e:
            logger.error(f"Error extracting layout info: {str(e)}")
            return {}
    
    def _save_text_content(self, doc_id: str, text_content: str) -> str:
        """Save plain text content to S3"""
        try:
            key = f"extracted_text/{doc_id}/full_text.txt"
            
            self.s3.put_object(
                Bucket=self.config.output_bucket,
                Key=key,
                Body=text_content.encode('utf-8'),
                ContentType='text/plain'
            )
            
            return f"s3://{self.config.output_bucket}/{key}"
            
        except Exception as e:
            logger.error(f"Error saving text content for {doc_id}: {str(e)}")
            raise
    
    def _save_tables_as_csv(self, doc_id: str, tables: List[Dict]) -> List[str]:
        """Save tables as CSV files"""
        files_created = []
        
        try:
            for i, table in enumerate(tables):
                csv_content = self._table_to_csv(table)
                key = f"extracted_text/{doc_id}/table_{i+1}.csv"
                
                self.s3.put_object(
                    Bucket=self.config.output_bucket,
                    Key=key,
                    Body=csv_content.encode('utf-8'),
                    ContentType='text/csv'
                )
                
                files_created.append(f"s3://{self.config.output_bucket}/{key}")
            
            return files_created
            
        except Exception as e:
            logger.error(f"Error saving tables for {doc_id}: {str(e)}")
            return []
    
    def _save_forms_as_json(self, doc_id: str, forms: List[Dict]) -> str:
        """Save form data as JSON"""
        try:
            key = f"extracted_text/{doc_id}/forms.json"
            
            self.s3.put_object(
                Bucket=self.config.output_bucket,
                Key=key,
                Body=json.dumps(forms, indent=2).encode('utf-8'),
                ContentType='application/json'
            )
            
            return f"s3://{self.config.output_bucket}/{key}"
            
        except Exception as e:
            logger.error(f"Error saving forms for {doc_id}: {str(e)}")
            raise
    
    def _save_layout_info(self, doc_id: str, layout_info: Dict) -> str:
        """Save layout information as JSON"""
        try:
            key = f"extracted_text/{doc_id}/layout_info.json"
            
            self.s3.put_object(
                Bucket=self.config.output_bucket,
                Key=key,
                Body=json.dumps(layout_info, indent=2).encode('utf-8'),
                ContentType='application/json'
            )
            
            return f"s3://{self.config.output_bucket}/{key}"
            
        except Exception as e:
            logger.error(f"Error saving layout info for {doc_id}: {str(e)}")
            raise
    
    def _save_complete_structured_output(self, doc_id: str, text_content: str, tables: List[Dict], 
                                       forms: List[Dict], layout_info: Dict, job_metadata: Dict) -> str:
        """Save complete structured output as JSON"""
        try:
            structured_output = {
                'document_id': doc_id,
                'extraction_timestamp': datetime.now().isoformat(),
                'source_metadata': job_metadata,
                'content': {
                    'text': text_content,
                    'tables': tables,
                    'forms': forms,
                    'layout': layout_info
                },
                'processing_info': {
                    'extractor_version': '2.0',
                    'text_length': len(text_content) if text_content else 0,
                    'table_count': len(tables),
                    'form_field_count': len(forms),
                    'page_count': layout_info.get('page_count', 0)
                }
            }
            
            key = f"extracted_text/{doc_id}/structured_output.json"
            
            self.s3.put_object(
                Bucket=self.config.output_bucket,
                Key=key,
                Body=json.dumps(structured_output, indent=2).encode('utf-8'),
                ContentType='application/json'
            )
            
            return f"s3://{self.config.output_bucket}/{key}"
            
        except Exception as e:
            logger.error(f"Error saving structured output for {doc_id}: {str(e)}")
            raise
    
    def _process_table_block(self, table_block: Dict, all_blocks: List[Dict]) -> Dict:
        """Process a table block to extract structured table data"""
        # Simplified table processing - would need full implementation
        return {
            'table_id': table_block.get('Id'),
            'confidence': table_block.get('Confidence', 0),
            'rows': [],  # Would extract actual table data here
            'geometry': table_block.get('Geometry', {})
        }
    
    def _process_key_value_pair(self, key_block: Dict, all_blocks: List[Dict]) -> Dict:
        """Process key-value pair from form data"""
        # Simplified form processing - would need full implementation
        return {
            'key_id': key_block.get('Id'),
            'key_text': '',  # Would extract actual key text here
            'value_text': '',  # Would extract actual value text here
            'confidence': key_block.get('Confidence', 0)
        }
    
    def _table_to_csv(self, table: Dict) -> str:
        """Convert table data to CSV format"""
        # Simplified CSV conversion - would need full implementation
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Would write actual table rows here
        writer.writerow(['Table data would be processed here'])
        
        return output.getvalue()
