#!/usr/bin/env python3
"""
Simple Chunking Test - Bypass library compatibility issues
Create chunks manually to complete end-to-end test
"""

import boto3
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_simple_chunks():
    """Create simple chunks manually for our test document"""
    
    s3 = boto3.client('s3', region_name='us-east-1')
    
    # Document details
    doc_id = "0ba290f6faab3c09"
    text_bucket = "solve-global-kr-dl-chunks-861276078413-us-east-1"
    text_key = "text/0ba290f6faab3c09.txt"
    chunks_bucket = "solve-global-kr-dl-chunks-861276078413-us-east-1"
    
    try:
        # Read the text file
        logger.info(f"Reading text from s3://{text_bucket}/{text_key}")
        response = s3.get_object(Bucket=text_bucket, Key=text_key)
        full_text = response['Body'].read().decode('utf-8')
        
        logger.info(f"Text length: {len(full_text)} characters")
        
        # Simple chunking - split by paragraphs and create ~1000 character chunks
        paragraphs = full_text.split('\n\n')
        chunks = []
        current_chunk = ""
        chunk_index = 0
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) > 1000 and current_chunk:
                # Save current chunk
                chunk_data = {
                    "doc_id": doc_id,
                    "chunk_id": f"{doc_id}_chunk_{chunk_index:04d}",
                    "text": current_chunk.strip(),
                    "chunk_index": chunk_index,
                    "created_at": datetime.utcnow().isoformat() + "Z",
                    "processing_method": "simple_manual_chunking"
                }
                chunks.append(chunk_data)
                chunk_index += 1
                current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        # Add final chunk
        if current_chunk.strip():
            chunk_data = {
                "doc_id": doc_id,
                "chunk_id": f"{doc_id}_chunk_{chunk_index:04d}",
                "text": current_chunk.strip(),
                "chunk_index": chunk_index,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "processing_method": "simple_manual_chunking"
            }
            chunks.append(chunk_data)
        
        logger.info(f"Created {len(chunks)} chunks")
        
        # Upload chunks to S3
        for chunk in chunks:
            chunk_key = f"chunks/{doc_id}/{chunk['chunk_id']}.json"
            s3.put_object(
                Bucket=chunks_bucket,
                Key=chunk_key,
                Body=json.dumps(chunk, indent=2),
                ContentType='application/json'
            )
            logger.info(f"Uploaded chunk: s3://{chunks_bucket}/{chunk_key}")
        
        # Create summary
        summary = {
            "doc_id": doc_id,
            "total_chunks": len(chunks),
            "total_characters": len(full_text),
            "average_chunk_size": len(full_text) // len(chunks) if chunks else 0,
            "chunks_location": f"s3://{chunks_bucket}/chunks/{doc_id}/",
            "processing_timestamp": datetime.utcnow().isoformat() + "Z",
            "processing_method": "simple_manual_chunking"
        }
        
        # Upload summary
        summary_key = f"chunks/{doc_id}/summary.json"
        s3.put_object(
            Bucket=chunks_bucket,
            Key=summary_key,
            Body=json.dumps(summary, indent=2),
            ContentType='application/json'
        )
        
        logger.info("✅ Simple chunking completed successfully")
        logger.info(f"✅ Created {len(chunks)} chunks")
        logger.info(f"✅ Average chunk size: {summary['average_chunk_size']} characters")
        logger.info(f"✅ Chunks location: {summary['chunks_location']}")
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Simple chunking failed: {e}")
        raise

if __name__ == "__main__":
    create_simple_chunks()
