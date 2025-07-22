#!/usr/bin/env python3
"""
Complete Climate Risk RAG System Deployment Script
Automated deployment based on REDEPLOYMENT_GUIDE.md
"""

import subprocess
import json
import time
import sys
import os
from typing import Dict, List, Optional

class ClimateRiskRAGDeployer:
    """Automated deployer for Climate Risk RAG system"""
    
    def __init__(self, profile: str = "solve-global", region: str = "us-east-1"):
        self.profile = profile
        self.region = region
        self.account_id = "861276078413"
        
        # Standardized configuration
        self.layers = {
            "database_core": "arn:aws:lambda:us-east-1:861276078413:layer:database-core-layer:16",
            "database_dependencies": "arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies:2",
            "opensearch_dependencies": "arn:aws:lambda:us-east-1:861276078413:layer:opensearch-dependencies:4"
        }
        
        self.iam_role = "arn:aws:iam::861276078413:role/document-processing-lambda-role"
        
        self.vpc_config = {
            "SubnetIds": "subnet-03d8bd6cf3491f38c,subnet-0c0be1dd59f70f70e",
            "SecurityGroupIds": "sg-0c9e10b9cfb4c9eb0"
        }
        
        self.standard_env = {
            "DATABASE_SECRET_NAME": "rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863",
            "DB_PORT": "5432",
            "DB_NAME": "climate_risk_rag",
            "DB_HOST": "solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com"
        }
    
    def run_command(self, command: List[str], description: str) -> bool:
        """Run AWS CLI command with error handling"""
        print(f"🔄 {description}")
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            print(f"✅ {description} - Success")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ {description} - Failed")
            print(f"Error: {e.stderr}")
            return False
    
    def create_iam_role(self) -> bool:
        """Create document processing Lambda role"""
        print("\n📋 Creating IAM Role and Policy...")
        
        # Create trust policy
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        # Create policy document
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": "arn:aws:logs:*:*:*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "ec2:CreateNetworkInterface",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DeleteNetworkInterface",
                        "ec2:AttachNetworkInterface",
                        "ec2:DetachNetworkInterface"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "textract:StartDocumentTextDetection",
                        "textract:StartDocumentAnalysis",
                        "textract:GetDocumentTextDetection",
                        "textract:GetDocumentAnalysis"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "comprehend:DetectEntities",
                        "comprehend:DetectKeyPhrases",
                        "comprehend:StartEntitiesDetectionJob",
                        "comprehend:StartKeyPhrasesDetectionJob",
                        "comprehend:DescribeEntitiesDetectionJob",
                        "comprehend:DescribeKeyPhrasesDetectionJob",
                        "comprehend:ListEntitiesDetectionJobs",
                        "comprehend:ListKeyPhrasesDetectionJobs"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:ListBucket",
                        "s3:DeleteObject"
                    ],
                    "Resource": [
                        "arn:aws:s3:::solve-global-kr-*",
                        "arn:aws:s3:::solve-global-kr-*/*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": ["sns:Publish"],
                    "Resource": [f"arn:aws:sns:{self.region}:{self.account_id}:*"]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "sqs:ReceiveMessage",
                        "sqs:DeleteMessage",
                        "sqs:GetQueueAttributes"
                    ],
                    "Resource": [f"arn:aws:sqs:{self.region}:{self.account_id}:*"]
                },
                {
                    "Effect": "Allow",
                    "Action": ["secretsmanager:GetSecretValue"],
                    "Resource": [f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:rds!db-*"]
                },
                {
                    "Effect": "Allow",
                    "Action": ["iam:PassRole"],
                    "Resource": [
                        f"arn:aws:iam::{self.account_id}:role/comprehend-data-access-role",
                        f"arn:aws:iam::{self.account_id}:role/solve-global-kr-textract-service-role"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "es:ESHttpPost",
                        "es:ESHttpPut",
                        "es:ESHttpGet",
                        "es:ESHttpDelete"
                    ],
                    "Resource": [f"arn:aws:es:{self.region}:{self.account_id}:domain/solve-global-kr-*/*"]
                }
            ]
        }
        
        # Write policies to temp files
        with open('/tmp/trust-policy.json', 'w') as f:
            json.dump(trust_policy, f)
        
        with open('/tmp/document-processing-policy.json', 'w') as f:
            json.dump(policy_document, f)
        
        # Create role
        success = self.run_command([
            "aws", "iam", "create-role",
            "--role-name", "document-processing-lambda-role",
            "--assume-role-policy-document", "file:///tmp/trust-policy.json",
            "--profile", self.profile
        ], "Creating IAM role")
        
        if not success:
            return False
        
        # Create policy
        success = self.run_command([
            "aws", "iam", "create-policy",
            "--policy-name", "document-processing-policy",
            "--policy-document", "file:///tmp/document-processing-policy.json",
            "--profile", self.profile
        ], "Creating IAM policy")
        
        if not success:
            return False
        
        # Attach policy to role
        return self.run_command([
            "aws", "iam", "attach-role-policy",
            "--role-name", "document-processing-lambda-role",
            "--policy-arn", f"arn:aws:iam::{self.account_id}:policy/document-processing-policy",
            "--profile", self.profile
        ], "Attaching policy to role")
    
    def create_sns_topics(self) -> bool:
        """Create required SNS topics"""
        print("\n📋 Creating SNS Topics...")
        
        topics = [
            "text-extraction-complete",
            "text-chunking-complete",
            "solve-global-kr-textract-completion",
            "solve-global-kr-source-document-events"
        ]
        
        for topic in topics:
            success = self.run_command([
                "aws", "sns", "create-topic",
                "--name", topic,
                "--profile", self.profile
            ], f"Creating SNS topic: {topic}")
            
            if not success:
                return False
        
        return True
    
    def setup_sns_subscriptions(self) -> bool:
        """Set up SNS to SQS subscriptions"""
        print("\n📋 Setting up SNS Subscriptions...")
        
        subscriptions = [
            {
                "topic": f"arn:aws:sns:{self.region}:{self.account_id}:text-extraction-complete",
                "queue": f"arn:aws:sqs:{self.region}:{self.account_id}:text-chunker-queue"
            },
            {
                "topic": f"arn:aws:sns:{self.region}:{self.account_id}:text-chunking-complete",
                "queue": f"arn:aws:sqs:{self.region}:{self.account_id}:keyword-indexer-initiator-queue"
            },
            {
                "topic": f"arn:aws:sns:{self.region}:{self.account_id}:text-chunking-complete",
                "queue": f"arn:aws:sqs:{self.region}:{self.account_id}:nlp-worker-queue"
            },
            {
                "topic": f"arn:aws:sns:{self.region}:{self.account_id}:solve-global-kr-textract-completion",
                "queue": f"arn:aws:sqs:{self.region}:{self.account_id}:solve-global-kr-textextractor-processor"
            },
            {
                "topic": f"arn:aws:sns:{self.region}:{self.account_id}:solve-global-kr-source-document-events",
                "queue": f"arn:aws:sqs:{self.region}:{self.account_id}:solve-global-kr-textextractor-initiator-queue"
            }
        ]
        
        for sub in subscriptions:
            success = self.run_command([
                "aws", "sns", "subscribe",
                "--topic-arn", sub["topic"],
                "--protocol", "sqs",
                "--notification-endpoint", sub["queue"],
                "--profile", self.profile
            ], f"Subscribing {sub['queue'].split(':')[-1]} to {sub['topic'].split(':')[-1]}")
            
            if not success:
                return False
        
        return True
    
    def deploy_lambda_function(self, function_config: Dict) -> bool:
        """Deploy a single Lambda function"""
        print(f"\n📋 Deploying {function_config['name']}...")
        
        # Create zip file
        zip_command = [
            "zip", "-r", f"{function_config['name']}.zip", ".",
            "-x", "*.pyc", "*__pycache__*", "*.DS_Store"
        ]
        
        original_dir = os.getcwd()
        try:
            os.chdir(function_config['source_dir'])
            success = self.run_command(zip_command, f"Creating zip for {function_config['name']}")
            if not success:
                return False
        finally:
            os.chdir(original_dir)
        
        # Prepare environment variables
        env_vars = {**self.standard_env, **function_config.get('additional_env', {})}
        env_string = ','.join([f'{k}={v}' for k, v in env_vars.items()])
        
        # Create Lambda function
        create_command = [
            "aws", "lambda", "create-function",
            "--function-name", function_config['name'],
            "--runtime", "python3.11",
            "--role", self.iam_role,
            "--handler", "handler.lambda_handler",
            "--zip-file", f"fileb://{function_config['source_dir']}/{function_config['name']}.zip",
            "--timeout", str(function_config.get('timeout', 300)),
            "--memory-size", str(function_config.get('memory_size', 512)),
            "--layers", *function_config['layers'],
            "--environment", f"Variables={{{env_string}}}",
            "--vpc-config", f"SubnetIds={self.vpc_config['SubnetIds']},SecurityGroupIds={self.vpc_config['SecurityGroupIds']}",
            "--profile", self.profile
        ]
        
        success = self.run_command(create_command, f"Creating Lambda function: {function_config['name']}")
        if not success:
            return False
        
        # Create event source mapping if specified
        if 'event_source_arn' in function_config:
            time.sleep(5)  # Wait for function to be ready
            mapping_command = [
                "aws", "lambda", "create-event-source-mapping",
                "--function-name", function_config['name'],
                "--event-source-arn", function_config['event_source_arn'],
                "--batch-size", "10",
                "--maximum-batching-window-in-seconds", "5",
                "--profile", self.profile
            ]
            
            success = self.run_command(mapping_command, f"Creating event source mapping for {function_config['name']}")
            if not success:
                return False
        
        return True
    
    def deploy_all_functions(self) -> bool:
        """Deploy all Lambda functions"""
        print("\n🚀 Deploying Lambda Functions...")
        
        functions = [
            {
                "name": "cleanup-service",
                "source_dir": "lambda/cleanup-service",
                "layers": [self.layers["database_core"], self.layers["database_dependencies"]],
                "timeout": 300,
                "memory_size": 512
            },
            {
                "name": "pipeline-test-function",
                "source_dir": "lambda/pipeline-test-function",
                "layers": [self.layers["database_core"], self.layers["database_dependencies"]],
                "timeout": 300,
                "memory_size": 512,
                "additional_env": {
                    "SOURCE_BUCKET": "solve-global-kr-dl-source-documents-861276078413-us-east-1"
                }
            },
            {
                "name": "text-extractor-initiator",
                "source_dir": "lambda/text-extractor-initiator",
                "layers": [self.layers["database_core"], self.layers["database_dependencies"]],
                "timeout": 300,
                "memory_size": 512,
                "additional_env": {
                    "TEXTRACT_SNS_TOPIC_ARN": f"arn:aws:sns:{self.region}:{self.account_id}:solve-global-kr-textract-completion",
                    "TEXTRACT_SERVICE_ROLE_ARN": f"arn:aws:iam::{self.account_id}:role/solve-global-kr-textract-service-role",
                    "OUTPUT_BUCKET": "solve-global-kr-dl-text-861276078413-us-east-1"
                },
                "event_source_arn": f"arn:aws:sqs:{self.region}:{self.account_id}:solve-global-kr-textextractor-initiator-queue"
            },
            {
                "name": "text-extractor-processor",
                "source_dir": "lambda/text-extractor-processor",
                "layers": [self.layers["database_core"], self.layers["database_dependencies"]],
                "timeout": 300,
                "memory_size": 512,
                "additional_env": {
                    "OUTPUT_BUCKET": "solve-global-kr-dl-text-861276078413-us-east-1",
                    "COMPLETION_TOPIC_ARN": f"arn:aws:sns:{self.region}:{self.account_id}:text-extraction-complete"
                },
                "event_source_arn": f"arn:aws:sqs:{self.region}:{self.account_id}:solve-global-kr-textextractor-processor"
            },
            {
                "name": "text-chunker-processor",
                "source_dir": "lambda/text-chunker-processor",
                "layers": [self.layers["database_core"], self.layers["database_dependencies"]],
                "timeout": 300,
                "memory_size": 1024,
                "additional_env": {
                    "TEXT_BUCKET": "solve-global-kr-dl-text-861276078413-us-east-1",
                    "CHUNKS_BUCKET": "solve-global-kr-dl-chunks-861276078413-us-east-1",
                    "CHUNKS_READY_TOPIC_ARN": f"arn:aws:sns:{self.region}:{self.account_id}:text-chunking-complete"
                },
                "event_source_arn": f"arn:aws:sqs:{self.region}:{self.account_id}:text-chunker-queue"
            }
        ]
        
        for function_config in functions:
            success = self.deploy_lambda_function(function_config)
            if not success:
                return False
            time.sleep(2)  # Brief pause between deployments
        
        return True
    
    def run_test(self) -> bool:
        """Run pipeline test to validate deployment"""
        print("\n🧪 Running Pipeline Test...")
        
        try:
            result = subprocess.run([
                "python3", "invoke_pipeline_test.py", 
                "--num-documents", "1", 
                "--min-size-mb", "1", 
                "--max-size-mb", "2"
            ], capture_output=True, text=True, check=True)
            
            print("✅ Pipeline test completed successfully")
            print("📊 Test output:")
            print(result.stdout)
            return True
            
        except subprocess.CalledProcessError as e:
            print("❌ Pipeline test failed")
            print(f"Error: {e.stderr}")
            return False
    
    def deploy_complete_system(self) -> bool:
        """Deploy the complete Climate Risk RAG system"""
        print("🚀 Starting Complete Climate Risk RAG System Deployment")
        print("=" * 60)
        
        steps = [
            ("Creating IAM Role and Policy", self.create_iam_role),
            ("Creating SNS Topics", self.create_sns_topics),
            ("Setting up SNS Subscriptions", self.setup_sns_subscriptions),
            ("Deploying Lambda Functions", self.deploy_all_functions),
            ("Running Pipeline Test", self.run_test)
        ]
        
        for step_name, step_function in steps:
            print(f"\n📋 Step: {step_name}")
            success = step_function()
            if not success:
                print(f"❌ Deployment failed at step: {step_name}")
                return False
            print(f"✅ Step completed: {step_name}")
        
        print("\n🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("✅ All components deployed and tested")
        print("📋 System ready for document processing")
        
        return True

def main():
    """Main deployment function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Climate Risk RAG System Deployment Script")
        print("Usage: python3 deploy_complete_system.py")
        print("This script deploys the complete system based on REDEPLOYMENT_GUIDE.md")
        return
    
    deployer = ClimateRiskRAGDeployer()
    success = deployer.deploy_complete_system()
    
    if success:
        print("\n🎯 Next Steps:")
        print("1. Deploy keyword indexing functions")
        print("2. Deploy vector embedding functions")
        print("3. Deploy NLP processing functions")
        print("4. Run end-to-end testing")
        sys.exit(0)
    else:
        print("\n❌ Deployment failed. Check logs above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
