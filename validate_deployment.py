#!/usr/bin/env python3
"""
Climate Risk RAG System Deployment Validation Script
Validates that all components are properly deployed and configured
"""

import subprocess
import json
import sys
from typing import Dict, List, Tuple, Optional

class DeploymentValidator:
    """Validates Climate Risk RAG system deployment"""
    
    def __init__(self, profile: str = "solve-global", region: str = "us-east-1"):
        self.profile = profile
        self.region = region
        self.account_id = "861276078413"
        self.validation_results = []
    
    def run_aws_command(self, command: List[str]) -> Tuple[bool, str]:
        """Run AWS CLI command and return success status and output"""
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr
    
    def validate_iam_role(self) -> bool:
        """Validate IAM role exists and has correct policies"""
        print("🔍 Validating IAM Role...")
        
        # Check if role exists
        success, output = self.run_aws_command([
            "aws", "iam", "get-role",
            "--role-name", "document-processing-lambda-role",
            "--profile", self.profile
        ])
        
        if not success:
            self.validation_results.append("❌ IAM role 'document-processing-lambda-role' not found")
            return False
        
        # Check if policy is attached
        success, output = self.run_aws_command([
            "aws", "iam", "list-attached-role-policies",
            "--role-name", "document-processing-lambda-role",
            "--profile", self.profile
        ])
        
        if success:
            policies = json.loads(output)
            policy_names = [p['PolicyName'] for p in policies['AttachedPolicies']]
            if 'document-processing-policy' in policy_names:
                self.validation_results.append("✅ IAM role and policy configured correctly")
                return True
            else:
                self.validation_results.append("❌ document-processing-policy not attached to role")
                return False
        
        self.validation_results.append("❌ Failed to check role policies")
        return False
    
    def validate_lambda_layers(self) -> bool:
        """Validate Lambda layers exist"""
        print("🔍 Validating Lambda Layers...")
        
        layers = {
            "database-core-layer:16": "arn:aws:lambda:us-east-1:861276078413:layer:database-core-layer:16",
            "database-dependencies:2": "arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies:2",
            "opensearch-dependencies:4": "arn:aws:lambda:us-east-1:861276078413:layer:opensearch-dependencies:4"
        }
        
        all_valid = True
        for layer_name, layer_arn in layers.items():
            success, output = self.run_aws_command([
                "aws", "lambda", "get-layer-version",
                "--layer-name", layer_name.split(':')[0],
                "--version-number", layer_name.split(':')[1],
                "--profile", self.profile
            ])
            
            if success:
                self.validation_results.append(f"✅ Layer {layer_name} exists")
            else:
                self.validation_results.append(f"❌ Layer {layer_name} not found")
                all_valid = False
        
        return all_valid
    
    def validate_sns_topics(self) -> bool:
        """Validate SNS topics exist"""
        print("🔍 Validating SNS Topics...")
        
        required_topics = [
            "text-extraction-complete",
            "text-chunking-complete", 
            "solve-global-kr-textract-completion",
            "solve-global-kr-source-document-events"
        ]
        
        success, output = self.run_aws_command([
            "aws", "sns", "list-topics",
            "--profile", self.profile
        ])
        
        if not success:
            self.validation_results.append("❌ Failed to list SNS topics")
            return False
        
        topics_data = json.loads(output)
        existing_topics = [t['TopicArn'].split(':')[-1] for t in topics_data['Topics']]
        
        all_valid = True
        for topic in required_topics:
            if topic in existing_topics:
                self.validation_results.append(f"✅ SNS topic {topic} exists")
            else:
                self.validation_results.append(f"❌ SNS topic {topic} not found")
                all_valid = False
        
        return all_valid
    
    def validate_sqs_queues(self) -> bool:
        """Validate SQS queues exist"""
        print("🔍 Validating SQS Queues...")
        
        required_queues = [
            "solve-global-kr-textextractor-initiator-queue",
            "solve-global-kr-textextractor-processor",
            "text-chunker-queue"
        ]
        
        success, output = self.run_aws_command([
            "aws", "sqs", "list-queues",
            "--profile", self.profile
        ])
        
        if not success:
            self.validation_results.append("❌ Failed to list SQS queues")
            return False
        
        queues_data = json.loads(output)
        existing_queues = [q.split('/')[-1] for q in queues_data.get('QueueUrls', [])]
        
        all_valid = True
        for queue in required_queues:
            if queue in existing_queues:
                self.validation_results.append(f"✅ SQS queue {queue} exists")
            else:
                self.validation_results.append(f"❌ SQS queue {queue} not found")
                all_valid = False
        
        return all_valid
    
    def validate_lambda_functions(self) -> bool:
        """Validate Lambda functions are deployed correctly"""
        print("🔍 Validating Lambda Functions...")
        
        required_functions = [
            "cleanup-service",
            "pipeline-test-function", 
            "text-extractor-initiator",
            "text-extractor-processor",
            "text-chunker-processor"
        ]
        
        all_valid = True
        for function_name in required_functions:
            # Check if function exists
            success, output = self.run_aws_command([
                "aws", "lambda", "get-function",
                "--function-name", function_name,
                "--profile", self.profile
            ])
            
            if not success:
                self.validation_results.append(f"❌ Lambda function {function_name} not found")
                all_valid = False
                continue
            
            function_data = json.loads(output)
            config = function_data['Configuration']
            
            # Validate configuration
            checks = []
            
            # Check runtime
            if config['Runtime'] == 'python3.11':
                checks.append("✅ Runtime: python3.11")
            else:
                checks.append(f"❌ Runtime: {config['Runtime']} (expected python3.11)")
                all_valid = False
            
            # Check role
            if 'document-processing-lambda-role' in config['Role']:
                checks.append("✅ IAM Role: document-processing-lambda-role")
            else:
                checks.append(f"❌ IAM Role: {config['Role']}")
                all_valid = False
            
            # Check layers
            if 'Layers' in config and len(config['Layers']) >= 2:
                layer_arns = [layer['Arn'] for layer in config['Layers']]
                if any('database-core-layer' in arn for arn in layer_arns):
                    checks.append("✅ Database core layer attached")
                else:
                    checks.append("❌ Database core layer missing")
                    all_valid = False
            else:
                checks.append("❌ Required layers missing")
                all_valid = False
            
            # Check VPC configuration
            if 'VpcConfig' in config and config['VpcConfig']['SubnetIds']:
                checks.append("✅ VPC configuration present")
            else:
                checks.append("❌ VPC configuration missing")
                all_valid = False
            
            self.validation_results.append(f"📋 Function {function_name}:")
            for check in checks:
                self.validation_results.append(f"  {check}")
        
        return all_valid
    
    def validate_event_source_mappings(self) -> bool:
        """Validate event source mappings exist"""
        print("🔍 Validating Event Source Mappings...")
        
        functions_with_mappings = [
            "text-extractor-initiator",
            "text-extractor-processor", 
            "text-chunker-processor"
        ]
        
        all_valid = True
        for function_name in functions_with_mappings:
            success, output = self.run_aws_command([
                "aws", "lambda", "list-event-source-mappings",
                "--function-name", function_name,
                "--profile", self.profile
            ])
            
            if success:
                mappings = json.loads(output)
                if mappings['EventSourceMappings']:
                    mapping = mappings['EventSourceMappings'][0]
                    state = mapping['State']
                    if state in ['Enabled', 'Enabling']:
                        self.validation_results.append(f"✅ Event source mapping for {function_name}: {state}")
                    else:
                        self.validation_results.append(f"❌ Event source mapping for {function_name}: {state}")
                        all_valid = False
                else:
                    self.validation_results.append(f"❌ No event source mapping for {function_name}")
                    all_valid = False
            else:
                self.validation_results.append(f"❌ Failed to check event source mapping for {function_name}")
                all_valid = False
        
        return all_valid
    
    def validate_s3_buckets(self) -> bool:
        """Validate S3 buckets exist"""
        print("🔍 Validating S3 Buckets...")
        
        required_buckets = [
            "solve-global-kr-dl-source-documents-861276078413-us-east-1",
            "solve-global-kr-dl-text-861276078413-us-east-1",
            "solve-global-kr-dl-chunks-861276078413-us-east-1"
        ]
        
        all_valid = True
        for bucket in required_buckets:
            success, output = self.run_aws_command([
                "aws", "s3api", "head-bucket",
                "--bucket", bucket,
                "--profile", self.profile
            ])
            
            if success:
                self.validation_results.append(f"✅ S3 bucket {bucket} exists")
            else:
                self.validation_results.append(f"❌ S3 bucket {bucket} not found")
                all_valid = False
        
        return all_valid
    
    def run_comprehensive_validation(self) -> bool:
        """Run comprehensive validation of the deployment"""
        print("🔍 Starting Comprehensive Deployment Validation")
        print("=" * 60)
        
        validation_steps = [
            ("IAM Role and Policy", self.validate_iam_role),
            ("Lambda Layers", self.validate_lambda_layers),
            ("SNS Topics", self.validate_sns_topics),
            ("SQS Queues", self.validate_sqs_queues),
            ("Lambda Functions", self.validate_lambda_functions),
            ("Event Source Mappings", self.validate_event_source_mappings),
            ("S3 Buckets", self.validate_s3_buckets)
        ]
        
        all_valid = True
        for step_name, validation_function in validation_steps:
            print(f"\n📋 Validating: {step_name}")
            step_valid = validation_function()
            if not step_valid:
                all_valid = False
        
        print("\n" + "=" * 60)
        print("📊 VALIDATION RESULTS")
        print("=" * 60)
        
        for result in self.validation_results:
            print(result)
        
        if all_valid:
            print("\n🎉 ALL VALIDATIONS PASSED!")
            print("✅ System is properly deployed and configured")
            print("🚀 Ready for document processing")
        else:
            print("\n❌ VALIDATION FAILED!")
            print("⚠️  Some components are missing or misconfigured")
            print("📋 Review the results above and fix issues")
        
        return all_valid

def main():
    """Main validation function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Climate Risk RAG System Deployment Validation Script")
        print("Usage: python3 validate_deployment.py")
        print("This script validates that all system components are properly deployed")
        return
    
    validator = DeploymentValidator()
    success = validator.run_comprehensive_validation()
    
    if success:
        print("\n🎯 System is ready for:")
        print("1. Document processing pipeline testing")
        print("2. Keyword indexing deployment")
        print("3. Vector embeddings deployment")
        print("4. End-to-end integration testing")
        sys.exit(0)
    else:
        print("\n🔧 Fix the issues above before proceeding")
        sys.exit(1)

if __name__ == "__main__":
    main()
