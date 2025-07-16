"""
Source Document Events Stack
Creates SNS/SQS infrastructure for source document events
"""

from aws_cdk import (
    Stack,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
    aws_sqs as sqs,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
    Duration,
    CfnOutput,
    Tags
)
from constructs import Construct


class SourceDocumentEventsStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create SNS Topic for S3 event notifications
        self.source_document_events_topic = sns.Topic(
            self, "SourceDocumentEventsTopic",
            topic_name="solve-global-kr-source-document-events",
            display_name="Climate Risk RAG Source Document Events"
        )

        # Create SQS Queue for TextExtractor Initiator
        # Dead Letter Queue first
        self.textextractor_initiator_dlq = sqs.Queue(
            self, "TextExtractorInitiatorDLQ",
            queue_name="solve-global-kr-textextractor-initiator-dlq",
            retention_period=Duration.days(14),
            visibility_timeout=Duration.minutes(5)
        )

        # Main processing queue
        self.textextractor_initiator_queue = sqs.Queue(
            self, "TextExtractorInitiatorQueue",
            queue_name="solve-global-kr-textextractor-initiator-queue",
            visibility_timeout=Duration.minutes(5),  # Lambda timeout + buffer
            retention_period=Duration.days(4),
            receive_message_wait_time=Duration.seconds(20),  # Long polling
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=5,
                queue=self.textextractor_initiator_dlq
            )
        )

        # Subscribe SQS queue to SNS topic
        self.source_document_events_topic.add_subscription(
            sns_subscriptions.SqsSubscription(
                self.textextractor_initiator_queue,
                raw_message_delivery=True  # Don't wrap in SNS envelope
            )
        )

        # Import existing source documents bucket
        self.source_documents_bucket = s3.Bucket.from_bucket_name(
            self, "SourceDocumentsBucket",
            bucket_name=f"solve-global-kr-dl-source-documents-{self.account}-{self.region}"
        )

        # Add S3 event notification to SNS topic
        self.source_documents_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.SnsDestination(self.source_document_events_topic),
            s3.NotificationKeyFilter(
                prefix="data_lake/",
                suffix=".pdf"
            )
        )

        # Add SNS topic policy to allow S3 to publish to it
        self.source_document_events_topic.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("s3.amazonaws.com")],
                actions=["sns:Publish"],
                resources=[self.source_document_events_topic.topic_arn],
                conditions={
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:s3:::{self.source_documents_bucket.bucket_name}"
                    }
                }
            )
        )

        # Import existing TextExtractor Initiator Lambda function
        self.textextractor_initiator_function = lambda_.Function.from_function_name(
            self, "TextExtractorInitiatorFunction",
            function_name="solve-global-kr-textextractor-initiator"
        )

        # Add SQS event source to TextExtractor Initiator Lambda function
        self.textextractor_initiator_function.add_event_source(
            lambda_event_sources.SqsEventSource(
                self.textextractor_initiator_queue,
                batch_size=1,
                max_batching_window=Duration.seconds(5)
            )
        )

        # Outputs
        CfnOutput(
            self, "SourceDocumentEventsTopicArn",
            value=self.source_document_events_topic.topic_arn,
            description="SNS Topic ARN for Source Document Events",
            export_name="SourceDocumentEventsTopicArn"
        )

        CfnOutput(
            self, "TextExtractorInitiatorQueueUrl",
            value=self.textextractor_initiator_queue.queue_url,
            description="SQS Queue URL for TextExtractor Initiator",
            export_name="TextExtractorInitiatorQueueUrl"
        )

        CfnOutput(
            self, "TextExtractorInitiatorQueueArn",
            value=self.textextractor_initiator_queue.queue_arn,
            description="SQS Queue ARN for TextExtractor Initiator",
            export_name="TextExtractorInitiatorQueueArn"
        )

        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Component", "SourceDocumentEvents")
        Tags.of(self).add("Environment", "Development")
