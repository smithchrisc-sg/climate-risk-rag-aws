#!/usr/bin/env python3
"""
Manual NLP Infrastructure Deployment
Creates NLP integration components using AWS CLI/boto3
"""
import boto3
import json
import zipfile
import os
from datetime import datetime

def create_nlp_infrastructure():
    """Create NLP integration infrastructure manually"""
    
    print("MANUAL NLP INFRASTRUCTURE DEPLOYMENT")
    print("=" * 50)
    
    session = boto3.Session(profile_name='solve-global')
    
    # AWS clients
    s3_client = session.client('s3', region_name='us-east-1')
    sns_client = session.client('sns', region_name='us-east-1')
    sqs_client = session.client('sqs', region_name='us-east-1')
    lambda_client = session.client('lambda', region_name='us-east-1')
    iam_client = session.client('iam', region_name='us-east-1')
    
    account_id = "861276078413"
    region = "us-east-1"
    
    # Step 1: Create S3 bucket for NLP results
    bucket_name = "solve-global-kr-ner-results-{}-{}".format(account_id, region)
    
    try:
        s3_client.create_bucket(Bucket=bucket_name)
        print("SUCCESS: Created S3 bucket {}".format(bucket_name))
    except Exception as e:
        if 'BucketAlreadyExists' in str(e) or 'BucketAlreadyOwnedByYou' in str(e):
            print("INFO: S3 bucket {} already exists".format(bucket_name))
        else:
            print("ERROR creating S3 bucket: {}".format(str(e)))
    
    # Step 2: Create SNS topics
    try:
        nlp_worker_topic = sns_client.create_topic(Name='nlp-worker')
        nlp_worker_topic_arn = nlp_worker_topic['TopicArn']
        print("SUCCESS: Created SNS topic nlp-worker")
        
        nlp_completion_topic = sns_client.create_topic(Name='nlp-processing-complete')
        nlp_completion_topic_arn = nlp_completion_topic['TopicArn']
        print("SUCCESS: Created SNS topic nlp-processing-complete")
        
    except Exception as e:
        print("ERROR creating SNS topics: {}".format(str(e)))
        return
    
    # Step 3: Create SQS queue for NLP worker
    try:
        # Create DLQ first
        dlq_response = sqs_client.create_queue(
            QueueName='nlp-worker-dlq',
            Attributes={
                'MessageRetentionPeriod': str(14 * 24 * 60 * 60)  # 14 days
            }
        )
        dlq_url = dlq_response['QueueUrl']
        
        # Get DLQ ARN
        dlq_attrs = sqs_client.get_queue_attributes(
            QueueUrl=dlq_url,
            AttributeNames=['QueueArn']
        )
        dlq_arn = dlq_attrs['Attributes']['QueueArn']
        
        # Create main queue with DLQ
        queue_response = sqs_client.create_queue(
            QueueName='nlp-worker-queue',
            Attributes={
                'VisibilityTimeout': str(15 * 60),  # 15 minutes
                'RedrivePolicy': json.dumps({
                    'deadLetterTargetArn': dlq_arn,
                    'maxReceiveCount': 3
                })
            }
        )
        queue_url = queue_response['QueueUrl']
        
        # Get queue ARN
        queue_attrs = sqs_client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['QueueArn']
        )
        queue_arn = queue_attrs['Attributes']['QueueArn']
        
        print("SUCCESS: Created SQS queue nlp-worker-queue with DLQ")
        
        # Subscribe queue to SNS topic
        sns_client.subscribe(
            TopicArn=nlp_worker_topic_arn,
            Protocol='sqs',
            Endpoint=queue_arn
        )
        
        # Add queue policy to allow SNS to send messages
        queue_policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": "*",
                "Action": "sqs:SendMessage",
                "Resource": queue_arn,
                "Condition": {
                    "ArnEquals": {
                        "aws:SourceArn": nlp_worker_topic_arn
                    }
                }
            }]
        }
        
        sqs_client.set_queue_attributes(
            QueueUrl=queue_url,
            Attributes={
                'Policy': json.dumps(queue_policy)
            }
        )
        
        print("SUCCESS: Configured SQS-SNS integration")
        
    except Exception as e:
        print("ERROR creating SQS infrastructure: {}".format(str(e)))
        return
    
    # Step 4: Create IAM role for Lambda functions
    try:
        # Create execution role
        assume_role_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        role_name = "nlp-integration-lambda-role"
        
        try:
            iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy),
                Description="Role for NLP integration Lambda functions"
            )
            print("SUCCESS: Created IAM role {}".format(role_name))
        except Exception as e:
            if 'EntityAlreadyExists' in str(e):
                print("INFO: IAM role {} already exists".format(role_name))
            else:
                raise
        
        # Attach policies
        policies = [
            'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
            'arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole'
        ]
        
        for policy_arn in policies:
            iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
        
        # Create custom policy for NLP services
        nlp_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "comprehend:DetectEntities",
                        "comprehend:DetectKeyPhrases"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject"
                    ],
                    "Resource": [
                        "arn:aws:s3:::solve-global-kr-*/*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "sns:Publish"
                    ],
                    "Resource": [
                        nlp_worker_topic_arn,
                        nlp_completion_topic_arn
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "sqs:ReceiveMessage",
                        "sqs:DeleteMessage",
                        "sqs:GetQueueAttributes"
                    ],
                    "Resource": queue_arn
                }
            ]
        }
        
        try:
            iam_client.create_policy(
                PolicyName='nlp-integration-policy',
                PolicyDocument=json.dumps(nlp_policy),
                Description='Policy for NLP integration Lambda functions'
            )
            print("SUCCESS: Created custom IAM policy")
        except Exception as e:
            if 'EntityAlreadyExists' in str(e):
                print("INFO: Custom IAM policy already exists")
            else:
                print("WARNING: Could not create custom policy: {}".format(str(e)))
        
        # Attach custom policy
        custom_policy_arn = "arn:aws:iam::{}:policy/nlp-integration-policy".format(account_id)
        try:
            iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn=custom_policy_arn
            )
        except Exception as e:
            print("WARNING: Could not attach custom policy: {}".format(str(e)))
        
        role_arn = "arn:aws:iam::{}:role/{}".format(account_id, role_name)
        print("SUCCESS: Configured IAM permissions")
        
    except Exception as e:
        print("ERROR creating IAM role: {}".format(str(e)))
        return
    
    print("\nNLP INFRASTRUCTURE DEPLOYMENT COMPLETED")
    print("=" * 50)
    print("S3 Bucket: {}".format(bucket_name))
    print("SNS Topics: nlp-worker, nlp-processing-complete")
    print("SQS Queue: nlp-worker-queue (with DLQ)")
    print("IAM Role: {}".format(role_name))
    print("\nNext: Deploy Lambda functions manually or via simplified deployment")
    
    return {
        'bucket_name': bucket_name,
        'nlp_worker_topic_arn': nlp_worker_topic_arn,
        'nlp_completion_topic_arn': nlp_completion_topic_arn,
        'queue_arn': queue_arn,
        'role_arn': role_arn
    }

def main():
    """Deploy NLP infrastructure manually"""
    
    print("Starting manual NLP infrastructure deployment...")
    print("This creates the core infrastructure needed for NLP integration")
    
    try:
        result = create_nlp_infrastructure()
        
        if result:
            print("\nMANUAL DEPLOYMENT SUCCESSFUL!")
            print("Core NLP infrastructure is ready")
            print("Lambda functions can now be deployed separately")
            
            # Save configuration
            with open('nlp_infrastructure_config.json', 'w') as f:
                json.dump(result, f, indent=2)
            
            print("Configuration saved to: nlp_infrastructure_config.json")
        
    except Exception as e:
        print("DEPLOYMENT FAILED: {}".format(str(e)))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
