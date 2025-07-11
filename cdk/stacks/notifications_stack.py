"""
Notifications Stack for Climate Risk RAG System
Sets up S3 event notifications between data lake buckets and Lambda functions
"""

from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    CfnOutput,
    Tags
)
from constructs import Construct


class NotificationsStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, data_lake_stack, compute_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Set up S3 event notifications
        self._setup_s3_event_triggers(data_lake_stack, compute_stack)
        
        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Environment", "Development")
        Tags.of(self).add("Architecture", "Notifications")

    def _setup_s3_event_triggers(self, data_lake_stack, compute_stack):
        """Set up S3 event notifications for the processing pipeline"""
        
        # Source documents upload triggers text extraction (end-state)
        data_lake_stack.source_documents_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED_PUT,
            s3n.LambdaDestination(compute_stack.text_extractor_function),
            s3.NotificationKeyFilter(suffix=".pdf")
        )
        
        # PDF upload triggers text extraction (legacy)
        data_lake_stack.documents_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED_PUT,
            s3n.LambdaDestination(compute_stack.text_extractor_function),
            s3.NotificationKeyFilter(prefix="documents/", suffix=".pdf")
        )
        
        # Extracted text triggers chunking
        data_lake_stack.extracted_text_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED_PUT,
            s3n.LambdaDestination(compute_stack.text_chunker_function),
            s3.NotificationKeyFilter(prefix="extracted_text/", suffix=".txt")
        )
        
        # Chunk creation triggers embedding generation and NER processing
        data_lake_stack.chunks_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED_PUT,
            s3n.LambdaDestination(compute_stack.embedding_generator_function),
            s3.NotificationKeyFilter(prefix="chunks/", suffix=".json")
        )
        
        data_lake_stack.chunks_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED_PUT,
            s3n.LambdaDestination(compute_stack.ner_processor_function),
            s3.NotificationKeyFilter(prefix="chunks/", suffix=".json")
        )
        
        # NER results trigger knowledge graph updates
        data_lake_stack.ner_results_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED_PUT,
            s3n.LambdaDestination(compute_stack.entity_extractor_function),
            s3.NotificationKeyFilter(prefix="ner_results/", suffix="ner_summary.json")
        )
