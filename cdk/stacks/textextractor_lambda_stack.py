"""
TextExtractor Lambda Stack
Creates Lambda functions for async TextExtractor pipeline
"""

from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
    aws_ec2 as ec2,
    aws_iam as iam,
    Duration,
    CfnOutput,
    Tags,
    Fn
)
from constructs import Construct
import os


class TextExtractorLambdaStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.Vpc, messaging_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.vpc = vpc
        self.messaging_stack = messaging_stack

        # Import database URL from environment or use placeholder
        database_url = os.environ.get('DATABASE_URL', 'postgresql://user:PLACEHOLDER@localhost:5432/climate_risk_rag')

        # Create Lambda layer for shared dependencies
        self.textextractor_layer = lambda_.LayerVersion(
            self, "TextExtractorLayer",
            layer_version_name="solve-global-kr-textextractor-layer",
            code=lambda_.Code.from_asset("../layers/build/textextractor-layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Shared dependencies for TextExtractor functions"
        )

        # TextExtractor Initiator Lambda
        self.textextractor_initiator = lambda_.Function(
            self, "TextExtractorInitiator",
            function_name="solve-global-kr-textextractor-initiator",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="text_extractor_initiator.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/text_extractor_initiator"),
            layers=[self.textextractor_layer],
            timeout=Duration.minutes(5),
            memory_size=512,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            role=messaging_stack.textextractor_lambda_role,
            environment={
                "DATABASE_URL": database_url,
                "TEXTRACT_SNS_TOPIC_ARN": messaging_stack.textract_completion_topic.topic_arn,
                "TEXTRACT_SERVICE_ROLE_ARN": messaging_stack.textract_service_role.role_arn,
                "OUTPUT_BUCKET": f"solve-global-kr-chunks-{self.account}-{self.region}"
            },
            description="Initiates async Textract jobs for document processing"
        )

        # TextExtractor Processor Lambda
        self.textextractor_processor = lambda_.Function(
            self, "TextExtractorProcessor",
            function_name="solve-global-kr-textextractor-processor",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="text_extractor_processor.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/text_extractor_processor"),
            layers=[self.textextractor_layer],
            timeout=Duration.minutes(15),
            memory_size=1024,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            role=messaging_stack.textextractor_lambda_role,
            environment={
                "DATABASE_URL": database_url,
                "OUTPUT_BUCKET": f"solve-global-kr-chunks-{self.account}-{self.region}",
                "NEXT_STAGE_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/placeholder/text-chunker-queue"  # Placeholder
            },
            description="Processes completed Textract jobs and extracts structured data"
        )

        # Add SQS event source to processor
        self.textextractor_processor.add_event_source(
            lambda_event_sources.SqsEventSource(
                messaging_stack.textextractor_queue,
                batch_size=1,  # Process one message at a time
                max_batching_window=Duration.seconds(5),
                report_batch_item_failures=True
            )
        )

        # Create a manual trigger Lambda for testing
        self.textextractor_trigger = lambda_.Function(
            self, "TextExtractorTrigger",
            function_name="solve-global-kr-textextractor-trigger",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.lambda_handler",
            code=lambda_.Code.from_inline("""
import json
import boto3
import os

def lambda_handler(event, context):
    '''
    Manual trigger for TextExtractor Initiator
    Used for testing with existing documents
    '''
    
    # Default test document if none specified
    default_document = {
        'bucket': 'solve-global-kr-documents-861276078413-us-east-1',
        'key': 'documents/006893d2_93170cb9.pdf'  # Small test document
    }
    
    # Get document from event or use default
    document = event.get('document', default_document)
    
    # Create S3 event format that TextExtractor Initiator expects
    s3_event = {
        'Records': [{
            'eventSource': 'aws:s3',
            'eventName': 'ObjectCreated:Put',
            's3': {
                'bucket': {'name': document['bucket']},
                'object': {'key': document['key']}
            }
        }]
    }
    
    # Invoke TextExtractor Initiator
    lambda_client = boto3.client('lambda')
    
    try:
        response = lambda_client.invoke(
            FunctionName=os.environ['TEXTEXTRACTOR_INITIATOR_FUNCTION_NAME'],
            InvocationType='Event',  # Async invocation
            Payload=json.dumps(s3_event)
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'TextExtractor Initiator triggered successfully',
                'document': document,
                'response': {
                    'StatusCode': response['StatusCode']
                }
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'document': document
            })
        }
            """),
            timeout=Duration.minutes(1),
            memory_size=256,
            role=messaging_stack.textextractor_lambda_role,
            environment={
                "TEXTEXTRACTOR_INITIATOR_FUNCTION_NAME": self.textextractor_initiator.function_name
            },
            description="Manual trigger for TextExtractor testing"
        )

        # Grant trigger function permission to invoke initiator
        self.textextractor_initiator.grant_invoke(self.textextractor_trigger)

        # Outputs
        CfnOutput(
            self, "TextExtractorInitiatorFunctionName",
            value=self.textextractor_initiator.function_name,
            description="TextExtractor Initiator Lambda function name",
            export_name="TextExtractorInitiatorFunctionName"
        )

        CfnOutput(
            self, "TextExtractorProcessorFunctionName",
            value=self.textextractor_processor.function_name,
            description="TextExtractor Processor Lambda function name",
            export_name="TextExtractorProcessorFunctionName"
        )

        CfnOutput(
            self, "TextExtractorTriggerFunctionName",
            value=self.textextractor_trigger.function_name,
            description="TextExtractor Trigger Lambda function name (for testing)",
            export_name="TextExtractorTriggerFunctionName"
        )

        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Component", "TextExtractor")
        Tags.of(self).add("Environment", "Development")
