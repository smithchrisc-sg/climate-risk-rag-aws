"""
TextExtractor Messaging Stack - Complete Version
Creates SNS/SQS infrastructure + Lambda security groups for async TextExtractor pipeline
Captures all manual configurations for complete CDK deployment
"""

from aws_cdk import (
    Stack,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
    aws_sqs as sqs,
    aws_iam as iam,
    aws_ec2 as ec2,
    Duration,
    CfnOutput,
    Tags
)
from constructs import Construct


class TextExtractorMessagingStackComplete(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.Vpc, rds_security_group_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.vpc = vpc

        # Create SNS Topic for Textract completion notifications
        self.textract_completion_topic = sns.Topic(
            self, "TextractCompletionTopic",
            topic_name="solve-global-kr-textract-completion",
            display_name="Climate Risk RAG Textract Completion Notifications"
        )

        # Create SQS Queue for TextExtractor Processor
        # Dead Letter Queue first
        self.textextractor_dlq = sqs.Queue(
            self, "TextExtractorDLQ",
            queue_name="solve-global-kr-textextractor-dlq",
            retention_period=Duration.days(14),
            visibility_timeout=Duration.minutes(5)
        )

        # Main processing queue
        self.textextractor_queue = sqs.Queue(
            self, "TextExtractorQueue",
            queue_name="solve-global-kr-textextractor-processor",
            visibility_timeout=Duration.minutes(15),  # Lambda timeout + buffer
            retention_period=Duration.days(4),
            receive_message_wait_time=Duration.seconds(20),  # Long polling
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=self.textextractor_dlq
            )
        )

        # Subscribe SQS queue to SNS topic
        self.textract_completion_topic.add_subscription(
            sns_subscriptions.SqsSubscription(
                self.textextractor_queue,
                raw_message_delivery=True  # Don't wrap in SNS envelope
            )
        )

        # Create Lambda Security Group (captures manual configuration)
        self.lambda_security_group = ec2.SecurityGroup(
            self, "LambdaSecurityGroup",
            vpc=self.vpc,
            security_group_name="solve-global-kr-lambda-sg",
            description="Security group for TextExtractor Lambda functions",
            allow_all_outbound=False
        )

        # Lambda → RDS access (captures manual rule)
        self.lambda_security_group.add_egress_rule(
            peer=ec2.Peer.security_group_id(rds_security_group_id),
            connection=ec2.Port.tcp(5432),
            description="PostgreSQL database access"
        )

        # Lambda → AWS APIs access (captures manual rule)
        self.lambda_security_group.add_egress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="HTTPS for AWS API calls"
        )

        # Lambda → AWS APIs access for Textract (additional rule)
        self.lambda_security_group.add_egress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="HTTP for AWS API calls"
        )

        # Update RDS Security Group to allow Lambda access (captures manual rule)
        rds_security_group = ec2.SecurityGroup.from_security_group_id(
            self, "RDSSecurityGroup",
            security_group_id=rds_security_group_id
        )
        
        rds_security_group.add_ingress_rule(
            peer=ec2.Peer.security_group_id(self.lambda_security_group.security_group_id),
            connection=ec2.Port.tcp(5432),
            description="Lambda access to PostgreSQL"
        )

        # Create IAM role for Textract service
        self.textract_service_role = iam.Role(
            self, "TextractServiceRole",
            role_name="solve-global-kr-textract-service-role",
            assumed_by=iam.ServicePrincipal("textract.amazonaws.com"),
            inline_policies={
                "TextractSNSPublish": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "sns:Publish"
                            ],
                            resources=[self.textract_completion_topic.topic_arn]
                        )
                    ]
                )
            }
        )

        # Create comprehensive IAM role for TextExtractor Lambda functions
        self.textextractor_lambda_role = iam.Role(
            self, "TextExtractorLambdaRole",
            role_name="solve-global-kr-textextractor-lambda-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole")
            ],
            inline_policies={
                "TextExtractorPermissions": iam.PolicyDocument(
                    statements=[
                        # Textract permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "textract:StartDocumentTextDetection",
                                "textract:StartDocumentAnalysis",
                                "textract:GetDocumentTextDetection",
                                "textract:GetDocumentAnalysis"
                            ],
                            resources=["*"]
                        ),
                        # S3 permissions for document buckets
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:DeleteObject"
                            ],
                            resources=[
                                f"arn:aws:s3:::solve-global-kr-documents-{self.account}-{self.region}/*",
                                f"arn:aws:s3:::solve-global-kr-chunks-{self.account}-{self.region}/*"
                            ]
                        ),
                        # S3 bucket listing permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:ListBucket"
                            ],
                            resources=[
                                f"arn:aws:s3:::solve-global-kr-documents-{self.account}-{self.region}",
                                f"arn:aws:s3:::solve-global-kr-chunks-{self.account}-{self.region}"
                            ]
                        ),
                        # SQS permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "sqs:ReceiveMessage",
                                "sqs:DeleteMessage",
                                "sqs:GetQueueAttributes",
                                "sqs:SendMessage"
                            ],
                            resources=[
                                self.textextractor_queue.queue_arn,
                                self.textextractor_dlq.queue_arn
                            ]
                        ),
                        # SNS permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "sns:Publish"
                            ],
                            resources=[self.textract_completion_topic.topic_arn]
                        ),
                        # Secrets Manager for database credentials
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "secretsmanager:GetSecretValue"
                            ],
                            resources=[
                                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:*"
                            ]
                        ),
                        # Lambda invoke permissions (for trigger function)
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "lambda:InvokeFunction"
                            ],
                            resources=[
                                f"arn:aws:lambda:{self.region}:{self.account}:function:solve-global-kr-textextractor-*"
                            ]
                        )
                    ]
                )
            }
        )

        # Outputs for Lambda functions to use
        CfnOutput(
            self, "TextractCompletionTopicArn",
            value=self.textract_completion_topic.topic_arn,
            description="SNS Topic ARN for Textract completion notifications",
            export_name="TextractCompletionTopicArn"
        )

        CfnOutput(
            self, "TextExtractorQueueUrl",
            value=self.textextractor_queue.queue_url,
            description="SQS Queue URL for TextExtractor Processor",
            export_name="TextExtractorQueueUrl"
        )

        CfnOutput(
            self, "TextExtractorQueueArn",
            value=self.textextractor_queue.queue_arn,
            description="SQS Queue ARN for TextExtractor Processor",
            export_name="TextExtractorQueueArn"
        )

        CfnOutput(
            self, "TextractServiceRoleArn",
            value=self.textract_service_role.role_arn,
            description="IAM Role ARN for Textract service",
            export_name="TextractServiceRoleArn"
        )

        CfnOutput(
            self, "TextExtractorLambdaRoleArn",
            value=self.textextractor_lambda_role.role_arn,
            description="IAM Role ARN for TextExtractor Lambda functions",
            export_name="TextExtractorLambdaRoleArn"
        )

        CfnOutput(
            self, "LambdaSecurityGroupId",
            value=self.lambda_security_group.security_group_id,
            description="Security Group ID for TextExtractor Lambda functions",
            export_name="LambdaSecurityGroupId"
        )

        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Component", "TextExtractor")
        Tags.of(self).add("Environment", "Development")
        Tags.of(self).add("ManagedBy", "CDK")
