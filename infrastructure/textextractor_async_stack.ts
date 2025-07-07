import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as lambdaEventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';

export interface TextExtractorAsyncStackProps extends cdk.StackProps {
  documentsBucket: s3.IBucket;
  textBucket: s3.IBucket;
  database: rds.IDatabaseInstance;
  vpc: ec2.IVpc;
  databaseSecurityGroup: ec2.ISecurityGroup;
}

export class TextExtractorAsyncStack extends cdk.Stack {
  public readonly textractCompletionTopic: sns.Topic;
  public readonly chunkingQueue: sqs.Queue;
  public readonly initiatorLambda: lambda.Function;
  public readonly processorLambda: lambda.Function;

  constructor(scope: Construct, id: string, props: TextExtractorAsyncStackProps) {
    super(scope, id, props);

    // SNS Topic for Textract completion notifications
    this.textractCompletionTopic = new sns.Topic(this, 'TextractCompletionTopic', {
      topicName: 'textract-completion',
      displayName: 'Textract Job Completion Notifications'
    });

    // Dead Letter Queue for failed chunking messages
    const chunkingDlq = new sqs.Queue(this, 'ChunkingDeadLetterQueue', {
      queueName: 'text-chunking-dlq',
      retentionPeriod: cdk.Duration.days(14)
    });

    // SQS Queue for triggering text chunking
    this.chunkingQueue = new sqs.Queue(this, 'ChunkingQueue', {
      queueName: 'text-chunking-queue',
      visibilityTimeout: cdk.Duration.minutes(15), // Match chunking Lambda timeout
      deadLetterQueue: {
        queue: chunkingDlq,
        maxReceiveCount: 3
      }
    });

    // IAM Role for Textract to publish to SNS
    const textractServiceRole = new iam.Role(this, 'TextractServiceRole', {
      assumedBy: new iam.ServicePrincipal('textract.amazonaws.com'),
      description: 'Role for Textract to publish completion notifications to SNS',
      inlinePolicies: {
        TextractSNSPublish: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ['sns:Publish'],
              resources: [this.textractCompletionTopic.topicArn]
            })
          ]
        })
      }
    });

    // Lambda execution role for database access
    const lambdaExecutionRole = new iam.Role(this, 'TextExtractorLambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaVPCAccessExecutionRole')
      ],
      inlinePolicies: {
        TextractAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'textract:StartDocumentAnalysis',
                'textract:GetDocumentAnalysis'
              ],
              resources: ['*']
            })
          ]
        }),
        S3Access: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                's3:GetObject',
                's3:HeadObject'
              ],
              resources: [
                props.documentsBucket.arnForObjects('*')
              ]
            }),
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                's3:PutObject',
                's3:PutObjectAcl'
              ],
              resources: [
                props.textBucket.arnForObjects('*')
              ]
            })
          ]
        }),
        SQSAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'sqs:SendMessage'
              ],
              resources: [this.chunkingQueue.queueArn]
            })
          ]
        })
      }
    });

    // Common environment variables
    const commonEnvironment = {
      DATABASE_URL: `postgresql://postgres:${props.database.instanceEndpoint.socketAddress}/climate_risk_rag`,
      OUTPUT_BUCKET: props.textBucket.bucketName,
      AWS_REGION: this.region
    };

    // TextExtractor Initiator Lambda
    this.initiatorLambda = new lambda.Function(this, 'TextExtractorInitiator', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'text_extractor_initiator.handler',
      code: lambda.Code.fromAsset('lambda/text_extractor_initiator'),
      timeout: cdk.Duration.minutes(5),
      memorySize: 512,
      role: lambdaExecutionRole,
      vpc: props.vpc,
      securityGroups: [props.databaseSecurityGroup],
      environment: {
        ...commonEnvironment,
        TEXTRACT_SNS_TOPIC_ARN: this.textractCompletionTopic.topicArn,
        TEXTRACT_SERVICE_ROLE_ARN: textractServiceRole.roleArn
      },
      description: 'Initiates async Textract jobs for document text extraction'
    });

    // TextExtractor Processor Lambda
    this.processorLambda = new lambda.Function(this, 'TextExtractorProcessor', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'text_extractor_processor.handler',
      code: lambda.Code.fromAsset('lambda/text_extractor_processor'),
      timeout: cdk.Duration.minutes(15),
      memorySize: 1024,
      role: lambdaExecutionRole,
      vpc: props.vpc,
      securityGroups: [props.databaseSecurityGroup],
      environment: {
        ...commonEnvironment,
        NEXT_STAGE_QUEUE_URL: this.chunkingQueue.queueUrl
      },
      description: 'Processes completed Textract jobs and saves structured output'
    });

    // S3 Event Notification to trigger Initiator Lambda
    props.documentsBucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(this.initiatorLambda),
      {
        prefix: 'documents/',
        suffix: '.pdf'
      }
    );

    // SNS Subscription to trigger Processor Lambda
    this.processorLambda.addEventSource(
      new lambdaEventSources.SnsEventSource(this.textractCompletionTopic)
    );

    // CloudWatch Log Groups with retention
    new cdk.aws_logs.LogGroup(this, 'InitiatorLogGroup', {
      logGroupName: `/aws/lambda/${this.initiatorLambda.functionName}`,
      retention: cdk.aws_logs.RetentionDays.ONE_MONTH
    });

    new cdk.aws_logs.LogGroup(this, 'ProcessorLogGroup', {
      logGroupName: `/aws/lambda/${this.processorLambda.functionName}`,
      retention: cdk.aws_logs.RetentionDays.ONE_MONTH
    });

    // CloudWatch Alarms for monitoring
    const initiatorErrorAlarm = new cdk.aws_cloudwatch.Alarm(this, 'InitiatorErrorAlarm', {
      metric: this.initiatorLambda.metricErrors(),
      threshold: 5,
      evaluationPeriods: 2,
      treatMissingData: cdk.aws_cloudwatch.TreatMissingData.NOT_BREACHING
    });

    const processorErrorAlarm = new cdk.aws_cloudwatch.Alarm(this, 'ProcessorErrorAlarm', {
      metric: this.processorLambda.metricErrors(),
      threshold: 5,
      evaluationPeriods: 2,
      treatMissingData: cdk.aws_cloudwatch.TreatMissingData.NOT_BREACHING
    });

    // Queue depth alarm
    const queueDepthAlarm = new cdk.aws_cloudwatch.Alarm(this, 'ChunkingQueueDepthAlarm', {
      metric: this.chunkingQueue.metricApproximateNumberOfVisibleMessages(),
      threshold: 100,
      evaluationPeriods: 3,
      treatMissingData: cdk.aws_cloudwatch.TreatMissingData.NOT_BREACHING
    });

    // Outputs
    new cdk.CfnOutput(this, 'TextractCompletionTopicArn', {
      value: this.textractCompletionTopic.topicArn,
      description: 'ARN of SNS topic for Textract completion notifications'
    });

    new cdk.CfnOutput(this, 'ChunkingQueueUrl', {
      value: this.chunkingQueue.queueUrl,
      description: 'URL of SQS queue for text chunking triggers'
    });

    new cdk.CfnOutput(this, 'TextractServiceRoleArn', {
      value: textractServiceRole.roleArn,
      description: 'ARN of IAM role for Textract service'
    });

    new cdk.CfnOutput(this, 'InitiatorLambdaArn', {
      value: this.initiatorLambda.functionArn,
      description: 'ARN of TextExtractor Initiator Lambda'
    });

    new cdk.CfnOutput(this, 'ProcessorLambdaArn', {
      value: this.processorLambda.functionArn,
      description: 'ARN of TextExtractor Processor Lambda'
    });

    // Tags
    cdk.Tags.of(this).add('Component', 'TextExtractor');
    cdk.Tags.of(this).add('Stage', 'AsyncProcessing');
  }
}

// Usage example in main stack:
/*
import { TextExtractorAsyncStack } from './textextractor_async_stack';

// In your main stack constructor:
const textExtractorStack = new TextExtractorAsyncStack(this, 'TextExtractorAsync', {
  documentsBucket: this.documentsBucket,
  textBucket: this.textBucket,
  database: this.database,
  vpc: this.vpc,
  databaseSecurityGroup: this.databaseSecurityGroup
});
*/
