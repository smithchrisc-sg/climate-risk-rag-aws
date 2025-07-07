#!/usr/bin/env python3
"""
Deploy Text Chunker with DocumentIDManager Integration
Phase 1: AWS Lambda Deployment Testing
"""

import boto3
import json
import os
import sys
import subprocess
import time
from datetime import datetime
from typing import Dict, List

def check_prerequisites():
    """Check that all prerequisites are in place"""
    
    print("🔍 Checking Prerequisites")
    print("=" * 50)
    
    # Check AWS CLI configuration
    try:
        session = boto3.Session(profile_name='solve-global')
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        print(f"✅ AWS Profile: solve-global")
        print(f"✅ Account: {identity['Account']}")
        print(f"✅ Region: {session.region_name}")
    except Exception as e:
        print(f"❌ AWS configuration error: {e}")
        return False
    
    # Check CDK installation
    try:
        result = subprocess.run(['cdk', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ CDK Version: {result.stdout.strip()}")
        else:
            print("❌ CDK not installed or not in PATH")
            return False
    except Exception as e:
        print(f"❌ CDK check failed: {e}")
        return False
    
    # Check lambda layer source exists
    layer_path = '/Users/chris/climate-risk-rag-aws/layers/app-source'
    if os.path.exists(layer_path):
        print(f"✅ Lambda layer source: {layer_path}")
    else:
        print(f"❌ Lambda layer source not found: {layer_path}")
        return False
    
    # Check text chunker source exists
    chunker_path = '/Users/chris/climate-risk-rag-aws/lambda/text_chunker'
    if os.path.exists(chunker_path):
        print(f"✅ Text chunker source: {chunker_path}")
    else:
        print(f"❌ Text chunker source not found: {chunker_path}")
        return False
    
    return True

def build_lambda_layers():
    """Build required lambda layers"""
    
    print("\n🔧 Building Lambda Layers")
    print("=" * 50)
    
    # Create layers build directory if it doesn't exist
    layers_build_dir = '/Users/chris/climate-risk-rag-aws/layers/build'
    os.makedirs(layers_build_dir, exist_ok=True)
    
    # Build climate-risk-core layer (app-source)
    print("Building climate-risk-core layer...")
    core_layer_dir = f"{layers_build_dir}/climate-risk-core-layer"
    os.makedirs(f"{core_layer_dir}/python", exist_ok=True)
    
    # Copy app-source to layer
    subprocess.run([
        'cp', '-r', 
        '/Users/chris/climate-risk-rag-aws/layers/app-source/',
        f"{core_layer_dir}/python/"
    ], check=True)
    
    print("✅ Climate Risk Core Layer built")
    
    # For now, create placeholder directories for other layers
    # In production, these would contain actual dependencies
    for layer_name in ['data-processing-layer', 'nlp-core-layer']:
        layer_dir = f"{layers_build_dir}/{layer_name}"
        os.makedirs(f"{layer_dir}/python", exist_ok=True)
        
        # Create a simple __init__.py to make it a valid Python package
        with open(f"{layer_dir}/python/__init__.py", 'w') as f:
            f.write("# Placeholder layer\n")
        
        print(f"✅ {layer_name} placeholder created")
    
    return True

def create_text_chunker_app():
    """Create a minimal CDK app for text chunker deployment"""
    
    print("\n📝 Creating Text Chunker CDK App")
    print("=" * 50)
    
    app_content = '''#!/usr/bin/env python3
"""
Text Chunker CDK App - Phase 1 Deployment
"""

import aws_cdk as cdk
from stacks.text_chunker_stack import TextChunkerStack

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account="861276078413",
    region="us-east-1"
)

# For Phase 1, we'll create a minimal deployment without full messaging integration
# This allows us to test the lambda function deployment and layer access

# Create a minimal VPC reference (assuming existing VPC)
# In production, this would reference the actual networking stack
class MockVpc:
    def __init__(self):
        pass

mock_vpc = MockVpc()

# Create a minimal messaging stack reference
class MockMessagingStack:
    def __init__(self):
        pass

mock_messaging = MockMessagingStack()

# Text Chunker Stack
text_chunker_stack = TextChunkerStack(
    app,
    "solve-global-kr-text-chunker-phase1",
    vpc=mock_vpc,
    messaging_stack=mock_messaging,
    env=env,
    description="Text Chunker Phase 1 - Lambda deployment testing"
)

app.synth()
'''
    
    with open('/Users/chris/climate-risk-rag-aws/cdk/app_text_chunker.py', 'w') as f:
        f.write(app_content)
    
    print("✅ Text Chunker CDK app created")
    return True

def update_text_chunker_stack_for_phase1():
    """Update text chunker stack for Phase 1 deployment (without full VPC integration)"""
    
    print("\n🔄 Updating Text Chunker Stack for Phase 1")
    print("=" * 50)
    
    # Create a simplified version of the text chunker stack for Phase 1
    simplified_stack = '''"""
Text Chunker Stack - Phase 1 Deployment
Simplified version for lambda deployment testing without full VPC integration
"""

import json
from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_logs as logs,
    Duration,
    CfnOutput,
    Tags
)
from constructs import Construct


class TextChunkerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
                 vpc, messaging_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create lambda layers for shared dependencies
        self._create_lambda_layers()
        
        # Create text chunker lambda function (simplified for Phase 1)
        self._create_text_chunker_lambda()
        
        # Create outputs
        self._create_outputs()

        # Tags
        Tags.of(self).add("Project", "ClimateRiskRAG")
        Tags.of(self).add("Component", "TextChunker")
        Tags.of(self).add("Phase", "Phase1-Testing")

    def _create_lambda_layers(self):
        """Create lambda layers for shared dependencies"""
        
        # Climate Risk Core Layer (DocumentIDManager, DatabaseManager, etc.)
        self.climate_risk_core_layer = lambda_.LayerVersion(
            self, "ClimateRiskCoreLayer",
            layer_version_name="climate-risk-core-utilities",
            code=lambda_.Code.from_asset("../layers/build/climate-risk-core-layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Core application utilities (DocumentIDManager, DatabaseManager, etc.)",
        )

    def _create_text_chunker_lambda(self):
        """Create the text chunker lambda function for Phase 1 testing"""
        
        # Environment variables for text chunker
        text_chunker_env = {
            'CHUNKS_BUCKET': f'solve-global-kr-chunks-{self.account}-{self.region}',
            'TEXT_BUCKET': f'solve-global-kr-text-new-{self.account}-{self.region}',
            'PHASE': 'PHASE1_TESTING',
            'COORDINATION_TOPIC_ARN': '',  # Empty for Phase 1
        }
        
        # Create IAM role for text chunker
        self.text_chunker_role = iam.Role(
            self, "TextChunkerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "TextChunkerPolicy": iam.PolicyDocument(
                    statements=[
                        # S3 permissions for reading text and storing chunks
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:DeleteObject",
                                "s3:ListBucket"
                            ],
                            resources=[
                                f"arn:aws:s3:::solve-global-kr-text-new-{self.account}-{self.region}",
                                f"arn:aws:s3:::solve-global-kr-text-new-{self.account}-{self.region}/*",
                                f"arn:aws:s3:::solve-global-kr-chunks-{self.account}-{self.region}",
                                f"arn:aws:s3:::solve-global-kr-chunks-{self.account}-{self.region}/*"
                            ]
                        ),
                        # CloudWatch Logs permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents"
                            ],
                            resources=["*"]
                        )
                    ]
                )
            }
        )
        
        # Text Chunker Lambda Function
        self.text_chunker_function = lambda_.Function(
            self, "TextChunkerFunction",
            function_name="solve-global-kr-text-chunker-phase1",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="text_chunker_processor.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/text_chunker"),
            timeout=Duration.minutes(5),  # Shorter timeout for Phase 1 testing
            memory_size=512,  # Lower memory for Phase 1 testing
            environment=text_chunker_env,
            role=self.text_chunker_role,
            layers=[
                self.climate_risk_core_layer
            ],
            description="Text chunker Phase 1 - Lambda deployment testing",
            log_retention=logs.RetentionDays.ONE_WEEK
        )

    def _create_outputs(self):
        """Create CloudFormation outputs"""
        
        CfnOutput(
            self, "TextChunkerFunctionName",
            value=self.text_chunker_function.function_name,
            description="Text Chunker Lambda function name"
        )
        
        CfnOutput(
            self, "TextChunkerFunctionArn", 
            value=self.text_chunker_function.function_arn,
            description="Text Chunker Lambda function ARN"
        )
        
        CfnOutput(
            self, "ClimateRiskCoreLayerArn",
            value=self.climate_risk_core_layer.layer_version_arn,
            description="Climate Risk Core Layer ARN"
        )
'''
    
    with open('/Users/chris/climate-risk-rag-aws/cdk/stacks/text_chunker_stack.py', 'w') as f:
        f.write(simplified_stack)
    
    print("✅ Text Chunker Stack updated for Phase 1")
    return True

def deploy_text_chunker():
    """Deploy the text chunker using CDK"""
    
    print("\n🚀 Deploying Text Chunker")
    print("=" * 50)
    
    # Change to CDK directory
    os.chdir('/Users/chris/climate-risk-rag-aws/cdk')
    
    # Set AWS profile
    env = os.environ.copy()
    env['AWS_PROFILE'] = 'solve-global'
    
    try:
        # CDK bootstrap (if needed)
        print("Checking CDK bootstrap...")
        bootstrap_result = subprocess.run([
            'cdk', 'bootstrap', 
            '--app', 'python app_text_chunker.py',
            '--profile', 'solve-global'
        ], capture_output=True, text=True, env=env)
        
        if bootstrap_result.returncode == 0:
            print("✅ CDK bootstrap successful")
        else:
            print(f"⚠️  CDK bootstrap: {bootstrap_result.stderr}")
        
        # CDK deploy
        print("Deploying text chunker stack...")
        deploy_result = subprocess.run([
            'cdk', 'deploy', 
            '--app', 'python app_text_chunker.py',
            '--profile', 'solve-global',
            '--require-approval', 'never'
        ], capture_output=True, text=True, env=env)
        
        if deploy_result.returncode == 0:
            print("✅ Text Chunker deployment successful!")
            print("\nDeployment Output:")
            print(deploy_result.stdout)
            return True
        else:
            print(f"❌ Deployment failed: {deploy_result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Deployment error: {e}")
        return False

def test_lambda_function():
    """Test the deployed lambda function"""
    
    print("\n🧪 Testing Deployed Lambda Function")
    print("=" * 50)
    
    try:
        # Create AWS Lambda client
        session = boto3.Session(profile_name='solve-global')
        lambda_client = session.client('lambda')
        
        # Test function exists and is accessible
        function_name = 'solve-global-kr-text-chunker-phase1'
        
        # Get function configuration
        response = lambda_client.get_function(FunctionName=function_name)
        
        print(f"✅ Function found: {function_name}")
        print(f"✅ Runtime: {response['Configuration']['Runtime']}")
        print(f"✅ Handler: {response['Configuration']['Handler']}")
        print(f"✅ Memory: {response['Configuration']['MemorySize']} MB")
        print(f"✅ Timeout: {response['Configuration']['Timeout']} seconds")
        
        # Check layers
        layers = response['Configuration'].get('Layers', [])
        print(f"✅ Layers: {len(layers)} layer(s) attached")
        for layer in layers:
            print(f"   - {layer['Arn']}")
        
        # Test function invocation with a simple test event
        test_event = {
            'Records': [{
                'body': json.dumps({
                    'Message': json.dumps({
                        'doc_id': 'test_phase1',
                        'stage': 'test',
                        'test_mode': True
                    })
                })
            }]
        }
        
        print("\nTesting function invocation...")
        invoke_response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        if invoke_response['StatusCode'] == 200:
            payload = json.loads(invoke_response['Payload'].read())
            print("✅ Function invocation successful!")
            print(f"Response: {json.dumps(payload, indent=2)}")
            return True
        else:
            print(f"❌ Function invocation failed: {invoke_response}")
            return False
            
    except Exception as e:
        print(f"❌ Lambda testing error: {e}")
        return False

def run_phase1_deployment():
    """Run Phase 1 deployment and testing"""
    
    print("🚀 Text Chunker Phase 1 Deployment")
    print("=" * 80)
    print(f"Started at: {datetime.utcnow().isoformat()}")
    print()
    
    steps = [
        ("Prerequisites Check", check_prerequisites),
        ("Build Lambda Layers", build_lambda_layers),
        ("Create CDK App", create_text_chunker_app),
        ("Update Stack for Phase 1", update_text_chunker_stack_for_phase1),
        ("Deploy Text Chunker", deploy_text_chunker),
        ("Test Lambda Function", test_lambda_function)
    ]
    
    results = []
    
    for step_name, step_func in steps:
        print(f"\n{'='*20} {step_name} {'='*20}")
        try:
            result = step_func()
            results.append((step_name, result))
            if result:
                print(f"✅ {step_name} completed successfully")
            else:
                print(f"❌ {step_name} failed")
                break
        except Exception as e:
            print(f"❌ {step_name} failed with exception: {e}")
            results.append((step_name, False))
            break
    
    # Summary
    print("\n" + "=" * 80)
    print("🎯 Phase 1 Deployment Results")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for step_name, result in results:
        status = "✅ SUCCESS" if result else "❌ FAILED"
        print(f"{status}: {step_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal Steps: {len(results)}")
    print(f"Successful: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 Phase 1 deployment completed successfully!")
        print("Text chunker is deployed and ready for integration testing.")
    else:
        print(f"\n⚠️  Phase 1 deployment failed at step: {results[-1][0]}")
    
    return failed == 0

if __name__ == "__main__":
    success = run_phase1_deployment()
    sys.exit(0 if success else 1)
