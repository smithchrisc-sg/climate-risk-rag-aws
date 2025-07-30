#!/usr/bin/env python3
"""
Test Hierarchical Layout-Based Chunker
Tests the new hierarchical chunking on a document with LAYOUT analysis
"""

import boto3
import json
import logging
import time
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_hierarchical_chunker():
    """Test the hierarchical chunker with a document that has LAYOUT blocks"""
    
    # Use the test document that we know has LAYOUT blocks
    test_doc_id = "00eb3286786882b6163b"
    
    logger.info(f"🧪 Testing hierarchical chunker with document: {test_doc_id}")
    
    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    try:
        # Create test message for the chunker
        test_message = {
            "doc_id": test_doc_id,
            "stage": "text_ready",
            "data_locations": {
                "text_location": f"s3://solve-global-kr-dl-text-861276078413-us-east-1/data-lake/{test_doc_id}/raw_text.txt",
                "structure_location": f"s3://solve-global-kr-dl-text-861276078413-us-east-1/data-lake/{test_doc_id}/textract_response.json"
            },
            "processing_metadata": {
                "text_extraction_complete": True,
                "layout_analysis_enabled": True
            },
            "document_metadata": {
                "filename": f"{test_doc_id}.pdf",
                "upload_timestamp": "2025-07-28T19:00:00Z"
            }
        }
        
        # Invoke the Lambda function
        logger.info("Invoking text-chunker-processor Lambda function...")
        
        response = lambda_client.invoke(
            FunctionName='text-chunker-processor',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'Records': [{
                    'body': json.dumps(test_message)
                }]
            })
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        if response.get('StatusCode') == 200:
            logger.info("✅ Lambda function executed successfully")
            
            # Check for errors in the response
            if 'errorMessage' in response_payload:
                logger.error(f"❌ Lambda function error: {response_payload['errorMessage']}")
                return False
            
            logger.info("📊 Processing completed successfully")
            
            # Wait a moment for S3 consistency
            time.sleep(2)
            
            # Download and analyze the new chunks
            analyze_hierarchical_chunks(test_doc_id, s3_client)
            
            return True
            
        else:
            logger.error(f"❌ Lambda invocation failed with status: {response.get('StatusCode')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        return False

def analyze_hierarchical_chunks(doc_id: str, s3_client):
    """Analyze the hierarchical structure of the generated chunks"""
    
    logger.info(f"🔍 Analyzing hierarchical chunks for {doc_id}")
    
    chunks_bucket = "solve-global-kr-dl-chunks-861276078413-us-east-1"
    chunks_prefix = f"data-lake/{doc_id}/"
    
    try:
        # List all chunk files
        response = s3_client.list_objects_v2(
            Bucket=chunks_bucket,
            Prefix=chunks_prefix
        )
        
        chunk_files = [obj['Key'] for obj in response.get('Contents', []) 
                      if obj['Key'].endswith('_chunk_') and obj['Key'].endswith('.json')]
        
        chunk_files.sort()
        
        logger.info(f"Found {len(chunk_files)} chunk files")
        
        # Download and analyze chunks
        chunks = []
        for chunk_file in chunk_files[:10]:  # Analyze first 10 chunks
            obj = s3_client.get_object(Bucket=chunks_bucket, Key=chunk_file)
            chunk_data = json.loads(obj['Body'].read())
            chunks.append(chunk_data)
        
        # Analyze hierarchical structure
        logger.info("\n📋 Hierarchical Structure Analysis:")
        logger.info("=" * 60)
        
        hierarchy_levels = {}
        section_types = {}
        parent_child_relationships = 0
        split_paragraphs = 0
        
        for i, chunk in enumerate(chunks):
            chunk_id = chunk.get('chunk_id', f'chunk_{i}')
            section_type = chunk.get('section_type', 'unknown')
            hierarchy_level = chunk.get('hierarchy_level', 0)
            parent_id = chunk.get('parent_chunk_id')
            child_ids = chunk.get('child_chunk_ids', [])
            is_split = chunk.get('is_split_paragraph', False)
            
            # Count statistics
            if hierarchy_level not in hierarchy_levels:
                hierarchy_levels[hierarchy_level] = 0
            hierarchy_levels[hierarchy_level] += 1
            
            if section_type not in section_types:
                section_types[section_type] = 0
            section_types[section_type] += 1
            
            if parent_id:
                parent_child_relationships += 1
            
            if is_split:
                split_paragraphs += 1
            
            # Display chunk info
            text_preview = chunk.get('text', '')[:100].replace('\n', ' ')
            logger.info(f"Chunk {i:2d}: {chunk_id}")
            logger.info(f"         Type: {section_type:12} Level: {hierarchy_level}")
            logger.info(f"         Parent: {parent_id or 'None'}")
            logger.info(f"         Children: {len(child_ids)} {'(split)' if is_split else ''}")
            logger.info(f"         Text: {text_preview}...")
            logger.info("")
        
        # Summary statistics
        logger.info("📊 Summary Statistics:")
        logger.info(f"  Total chunks analyzed: {len(chunks)}")
        logger.info(f"  Hierarchy levels: {dict(sorted(hierarchy_levels.items()))}")
        logger.info(f"  Section types: {dict(sorted(section_types.items()))}")
        logger.info(f"  Parent-child relationships: {parent_child_relationships}")
        logger.info(f"  Split paragraphs: {split_paragraphs}")
        
        # Check for improvements
        logger.info("\n✨ Hierarchical Chunker Benefits:")
        
        # Check if we have clean section types (no mixed types per chunk)
        mixed_sections = sum(1 for chunk in chunks 
                           if isinstance(chunk.get('section_types'), list) and 
                           len(chunk.get('section_types', [])) > 1)
        
        if mixed_sections == 0:
            logger.info("  ✅ Clean section boundaries - no mixed section types")
        else:
            logger.info(f"  ⚠️  {mixed_sections} chunks with mixed section types")
        
        # Check for artificial context brackets
        artificial_context = sum(1 for chunk in chunks 
                               if '[Previous context:' in chunk.get('text', '') or 
                               '[Context:' in chunk.get('text', ''))
        
        if artificial_context == 0:
            logger.info("  ✅ No artificial context brackets")
        else:
            logger.info(f"  ⚠️  {artificial_context} chunks with artificial context")
        
        # Check hierarchy consistency
        if hierarchy_levels:
            max_level = max(hierarchy_levels.keys())
            min_level = min(hierarchy_levels.keys())
            logger.info(f"  ✅ Hierarchy spans {max_level - min_level + 1} levels ({min_level}-{max_level})")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to analyze chunks: {str(e)}")
        return False

def main():
    """Main test execution"""
    
    logger.info("🚀 Starting hierarchical chunker test")
    
    try:
        success = test_hierarchical_chunker()
        
        if success:
            logger.info("✅ Hierarchical chunker test completed successfully!")
        else:
            logger.error("❌ Hierarchical chunker test failed")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Test execution failed: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
