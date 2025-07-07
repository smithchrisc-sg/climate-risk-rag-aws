"""
TextExtractor Lambda Stack - Complete Version
Creates Lambda functions with proper VPC configuration and dependencies
Captures all manual configurations for complete CDK deployment
"""

from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
    aws_ec2 as ec2,
    Duration,
    CfnOutput,
    Tags
)
from constructs import Construct
import os


class TextExtractorLambdaStackComplete(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.Vpc, messaging_stack, database_url: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.vpc = vpc
        self.messaging_stack = messaging_stack

        # Create Lambda layer for dependencies (captures manual dependency management)
        self.textextractor_layer = lambda_.LayerVersion(
            self, "TextExtractorLayer",
            layer_version_name="solve-global-kr-textextractor-layer",
            code=lambda_.Code.from_asset("../layers/build/textextractor-layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="TextExtractor dependencies including psycopg2-binary and utilities"
        )

        # Get isolated subnets (where RDS is located)
        isolated_subnets = self.vpc.select_subnets(
            subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
        )

        # TextExtractor Initiator Lambda (captures manual configuration)
        self.textextractor_initiator = lambda_.Function(
            self, "TextExtractorInitiator",
            function_name="solve-global-kr-textextractor-initiator",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="text_extractor_initiator.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/text_extractor_initiator"),
            layers=[self.textextractor_layer],
            timeout=Duration.minutes(5),
            memory_size=1024,
            vpc=self.vpc,
            vpc_subnets=isolated_subnets,  # Same subnets as RDS
            security_groups=[messaging_stack.lambda_security_group],
            role=messaging_stack.textextractor_lambda_role,
            environment={
                "DATABASE_URL": database_url,
                "TEXTRACT_SNS_TOPIC_ARN": messaging_stack.textract_completion_topic.topic_arn,
                "TEXTRACT_SERVICE_ROLE_ARN": messaging_stack.textract_service_role.role_arn,
                "OUTPUT_BUCKET": f"solve-global-kr-chunks-{self.account}-{self.region}"
            },
            description="Initiates async Textract jobs for document processing"
        )

        # TextExtractor Processor Lambda (captures manual configuration)
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
            vpc_subnets=isolated_subnets,  # Same subnets as RDS
            security_groups=[messaging_stack.lambda_security_group],
            role=messaging_stack.textextractor_lambda_role,
            environment={
                "DATABASE_URL": database_url,
                "OUTPUT_BUCKET": f"solve-global-kr-chunks-{self.account}-{self.region}",
                "NEXT_STAGE_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/placeholder/text-chunker-queue"
            },
            description="Processes completed Textract jobs and extracts structured data"
        )

        # Add SQS event source to processor (captures manual event source mapping)
        self.textextractor_processor.add_event_source(
            lambda_event_sources.SqsEventSource(
                messaging_stack.textextractor_queue,
                batch_size=1,  # Process one message at a time
                max_batching_window=Duration.seconds(5),
                report_batch_item_failures=True
            )
        )

        # TextExtractor Trigger Lambda for testing (captures manual testing setup)
        self.textextractor_trigger = lambda_.Function(
            self, "TextExtractorTrigger",
            function_name="solve-global-kr-textextractor-trigger",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.lambda_handler",
            code=lambda_.Code.from_inline("""
import json
import boto3

def lambda_handler(event, context):
    '''Manual trigger for TextExtractor Initiator - Used for testing'''
    
    # Default test document if none specified
    default_document = {
        'bucket': 'solve-global-kr-documents-861276078413-us-east-1',
        'key': 'documents/006893d2_93170cb9.pdf'
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
            FunctionName='solve-global-kr-textextractor-initiator',
            InvocationType='Event',  # Async invocation
            Payload=json.dumps(s3_event)
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'TextExtractor triggered',
                'document': document,
                'status': response['StatusCode']
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
            description="Manual trigger for TextExtractor testing"
        )

        # Grant trigger function permission to invoke initiator (captures manual permission)
        self.textextractor_initiator.grant_invoke(self.textextractor_trigger)

        # Outputs
        CfnOutput(
            self, "TextExtractorInitiatorFunctionName",
            value=self.textextractor_initiator.function_name,
            description="TextExtractor Initiator Lambda function name",
            export_name="TextExtractorInitiatorFunctionName"
        )

        CfnOutput(
            self, "TextExtractorInitiatorFunctionArn",
            value=self.textextractor_initiator.function_arn,
            description="TextExtractor Initiator Lambda function ARN",
            export_name="TextExtractorInitiatorFunctionArn"
        )

        CfnOutput(
            self, "TextExtractorProcessorFunctionName",
            value=self.textextractor_processor.function_name,
            description="TextExtractor Processor Lambda function name",
            export_name="TextExtractorProcessorFunctionName"
        )

        CfnOutput(
            self, "TextExtractorProcessorFunctionArn",
            value=self.textextractor_processor.function_arn,
            description="TextExtractor Processor Lambda function ARN",
            export_name="TextExtractorProcessorFunctionArn"
        )

        CfnOutput(
            self, "TextExtractorTriggerFunctionName",
            value=self.textextractor_trigger.function_name,
            description="TextExtractor Trigger Lambda function name (for testing)",
            export_name="TextExtractorTriggerFunctionName"
        )

        CfnOutput(
            self, "TextExtractorLayerArn",
            value=self.textextractor_layer.layer_version_arn,
            description="TextExtractor Lambda layer ARN",
            export_name="TextExtractorLayerArn"
        )

        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Component", "TextExtractor")
        Tags.of(self).add("Environment", "Development")
        Tags.of(self).add("ManagedBy", "CDK")
