#!/usr/bin/env python3
"""
Fix TextExtractor IAM permissions to include data lake buckets
"""

import boto3
import json

def fix_textextractor_iam():
    """Update the TextExtractor IAM role to include data lake bucket permissions"""
    
    iam_client = boto3.client('iam', region_name='us-east-1')
    role_name = 'solve-global-kr-textextractor-lambda-role'
    policy_name = 'TextExtractorPermissions'
    account_id = '861276078413'
    region = 'us-east-1'
    
    print(f"Updating IAM policy for role: {role_name}")
    
    # Updated policy document with data lake buckets
    updated_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": [
                    "textract:GetDocumentAnalysis",
                    "textract:GetDocumentTextDetection",
                    "textract:StartDocumentAnalysis",
                    "textract:StartDocumentTextDetection"
                ],
                "Resource": "*",
                "Effect": "Allow"
            },
            {
                "Action": [
                    "s3:DeleteObject",
                    "s3:GetObject",
                    "s3:PutObject"
                ],
                "Resource": [
                    f"arn:aws:s3:::solve-global-kr-chunks-{account_id}-{region}/*",
                    f"arn:aws:s3:::solve-global-kr-documents-{account_id}-{region}/*",
                    f"arn:aws:s3:::solve-global-kr-text-new-{account_id}-{region}/*",
                    # Add data lake buckets
                    f"arn:aws:s3:::solve-global-kr-dl-source-documents-{account_id}-{region}/*",
                    f"arn:aws:s3:::solve-global-kr-dl-text-{account_id}-{region}/*",
                    f"arn:aws:s3:::solve-global-kr-dl-chunks-{account_id}-{region}/*"
                ],
                "Effect": "Allow"
            },
            {
                "Action": [
                    "s3:ListBucket"
                ],
                "Resource": [
                    f"arn:aws:s3:::solve-global-kr-chunks-{account_id}-{region}",
                    f"arn:aws:s3:::solve-global-kr-documents-{account_id}-{region}",
                    f"arn:aws:s3:::solve-global-kr-text-new-{account_id}-{region}",
                    # Add data lake buckets
                    f"arn:aws:s3:::solve-global-kr-dl-source-documents-{account_id}-{region}",
                    f"arn:aws:s3:::solve-global-kr-dl-text-{account_id}-{region}",
                    f"arn:aws:s3:::solve-global-kr-dl-chunks-{account_id}-{region}"
                ],
                "Effect": "Allow"
            },
            {
                "Action": [
                    "sqs:DeleteMessage",
                    "sqs:GetQueueAttributes",
                    "sqs:ReceiveMessage",
                    "sqs:SendMessage"
                ],
                "Resource": [
                    f"arn:aws:sqs:{region}:{account_id}:solve-global-kr-textextractor-dlq",
                    f"arn:aws:sqs:{region}:{account_id}:solve-global-kr-textextractor-processor",
                    f"arn:aws:sqs:{region}:{account_id}:text-chunker-queue"
                ],
                "Effect": "Allow"
            },
            {
                "Action": "sns:Publish",
                "Resource": [
                    f"arn:aws:sns:{region}:{account_id}:solve-global-kr-textract-completion",
                    f"arn:aws:sns:{region}:{account_id}:text-extraction-complete"
                ],
                "Effect": "Allow"
            },
            {
                "Action": "secretsmanager:GetSecretValue",
                "Resource": f"arn:aws:secretsmanager:{region}:{account_id}:secret:*",
                "Effect": "Allow"
            }
        ]
    }
    
    try:
        # Update the inline policy
        response = iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(updated_policy)
        )
        
        print("✅ Successfully updated IAM policy!")
        print("Added permissions for data lake buckets:")
        print("  - solve-global-kr-dl-source-documents-861276078413-us-east-1")
        print("  - solve-global-kr-dl-text-861276078413-us-east-1") 
        print("  - solve-global-kr-dl-chunks-861276078413-us-east-1")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating IAM policy: {e}")
        return False

if __name__ == "__main__":
    fix_textextractor_iam()
