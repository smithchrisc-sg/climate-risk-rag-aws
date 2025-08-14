"""
NLP-KG Processor

Main processing logic for converting NLP results into knowledge graph triples
through ontology alignment and entity processing.
"""

import json
import logging
import traceback
from typing import Dict, List, Any

from .message_parser import MessageParser
from .component_manager import ComponentManager
from .document_processor import DocumentProcessor
from .response_builder import ResponseBuilder

logger = logging.getLogger(__name__)


class NLPKGProcessor:
    """
    Main processor class that orchestrates the NLP-KG processing pipeline.
    """
    
    def __init__(self):
        """Initialize the processor with required components."""
        self.message_parser = MessageParser()
        self.component_manager = ComponentManager()
        self.document_processor = DocumentProcessor()
        self.response_builder = ResponseBuilder()
    
    def process(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Process the Lambda event through the complete NLP-KG pipeline.
        
        Args:
            event: Lambda event containing SNS message
            context: Lambda context object
            
        Returns:
            Lambda response with processing results
        """
        try:
            # Phase 1: Message Receipt and Validation
            logger.info("Phase 1: Processing SNS message")
            processing_requests = self.message_parser.parse_sns_message(event)
            
            if not processing_requests:
                logger.warning("No valid processing requests found in message")
                return self.response_builder.success_response("No processing requests to handle")
            
            # Phase 2: Component Initialization
            logger.info("Phase 2: Initializing layer components")
            components = self.component_manager.initialize_components()
            
            # Process each document request
            results = []
            for request in processing_requests:
                try:
                    result = self.document_processor.process_document_request(request, components)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to process request {request.get('document_id', 'unknown')}: {str(e)}")
                    results.append({
                        'document_id': request.get('document_id', 'unknown'),
                        'status': 'failed',
                        'error': str(e)
                    })
            
            # Build summary response
            successful = len([r for r in results if r['status'] == 'success'])
            total = len(results)
            
            logger.info(f"Processing complete: {successful}/{total} documents successful")
            
            return self.response_builder.success_response({
                'message': f'Processed {successful}/{total} documents successfully',
                'results': results
            })
            
        except Exception as e:
            logger.error(f"Lambda execution failed: {str(e)}")
            logger.error(traceback.format_exc())
            return self.response_builder.error_response(f"Lambda execution failed: {str(e)}")
