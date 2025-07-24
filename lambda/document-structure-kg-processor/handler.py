#!/usr/bin/env python3
"""
Document Structure KG Processor Lambda Handler
Entry point for document structure knowledge graph processing
"""
import sys
import os

# Add lambda layer paths
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from document_structure_processor_refactored import DocumentStructureKGProcessor

def lambda_handler(event, context):
    """Lambda entry point for document structure KG processing"""
    processor = DocumentStructureKGProcessor()
    return processor.lambda_handler(event, context)
