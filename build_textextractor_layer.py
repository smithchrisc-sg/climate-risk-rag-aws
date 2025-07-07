#!/usr/bin/env python3
"""
Build TextExtractor Lambda Layer for CDK Deployment
Creates proper Lambda layer with all dependencies for CDK deployment
"""

import os
import subprocess
import shutil
import zipfile
import tempfile
from pathlib import Path

def build_textextractor_layer():
    """Build TextExtractor Lambda layer with all dependencies"""
    print("🔧 Building TextExtractor Lambda Layer for CDK")
    print("=" * 50)
    
    # Create build directory structure
    build_dir = Path("/Users/chris/climate-risk-rag-aws/layers/build/textextractor-layer")
    python_dir = build_dir / "python"
    
    # Clean and create directories
    if build_dir.exists():
        shutil.rmtree(build_dir)
    
    python_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Created build directory: {build_dir}")
    
    # Install Lambda-compatible dependencies
    print("📦 Installing Lambda-compatible dependencies...")
    
    # Install psycopg2-binary for Lambda runtime
    subprocess.run([
        "pip", "install", 
        "--platform", "manylinux2014_x86_64",
        "--target", str(python_dir),
        "--implementation", "cp",
        "--python-version", "3.11",
        "--only-binary=:all:",
        "--upgrade",
        "psycopg2-binary==2.9.7"
    ], check=True)
    
    # Install other dependencies
    subprocess.run([
        "pip", "install", 
        "--target", str(python_dir),
        "boto3>=1.26.0",
        "requests>=2.28.0"
    ], check=True)
    
    print("✅ Dependencies installed")
    
    # Copy utility modules
    print("📋 Copying utility modules...")
    utils_src = Path("/Users/chris/climate-risk-rag-aws/layers/app-source/utils")
    
    for util_file in ["DatabaseManager.py", "DocumentIDManager.py"]:
        src_file = utils_src / util_file
        if src_file.exists():
            shutil.copy2(src_file, python_dir)
            print(f"   ✅ Copied {util_file}")
        else:
            print(f"   ⚠️  {util_file} not found")
    
    # Create layer info file
    layer_info = {
        "name": "textextractor-layer",
        "description": "TextExtractor dependencies including psycopg2-binary and utilities",
        "compatible_runtimes": ["python3.11"],
        "dependencies": [
            "psycopg2-binary==2.9.7",
            "boto3>=1.26.0", 
            "requests>=2.28.0"
        ],
        "utilities": [
            "DatabaseManager.py",
            "DocumentIDManager.py"
        ]
    }
    
    import json
    with open(build_dir / "layer-info.json", 'w') as f:
        json.dump(layer_info, f, indent=2)
    
    # Calculate layer size
    total_size = sum(f.stat().st_size for f in python_dir.rglob('*') if f.is_file())
    size_mb = total_size / (1024 * 1024)
    
    print(f"✅ Layer built successfully")
    print(f"📊 Layer size: {size_mb:.1f} MB")
    print(f"📁 Layer location: {build_dir}")
    
    return build_dir

def create_deployment_guide():
    """Create deployment guide for complete CDK setup"""
    guide_content = """# Complete TextExtractor CDK Deployment Guide

## Prerequisites
1. AWS CLI configured with solve-global profile
2. CDK installed and bootstrapped
3. Python 3.11+ installed
4. Required dependencies installed

## Step-by-Step Deployment

### 1. Build Lambda Layer
```bash
cd /Users/chris/climate-risk-rag-aws
python build_textextractor_layer.py
```

### 2. Deploy Infrastructure (Complete)
```bash
cd cdk
export AWS_PROFILE=solve-global
cdk deploy --app "python app_complete.py" --all --require-approval never
```

### 3. Verify Deployment
```bash
# Test the pipeline
AWS_PROFILE=solve-global aws lambda invoke \\
  --function-name solve-global-kr-textextractor-trigger \\
  --region us-east-1 \\
  /tmp/test-response.json

cat /tmp/test-response.json
```

### 4. Monitor Logs
```bash
# Check initiator logs
AWS_PROFILE=solve-global aws logs filter-log-events \\
  --log-group-name "/aws/lambda/solve-global-kr-textextractor-initiator" \\
  --region us-east-1

# Check processor logs  
AWS_PROFILE=solve-global aws logs filter-log-events \\
  --log-group-name "/aws/lambda/solve-global-kr-textextractor-processor" \\
  --region us-east-1
```

## Infrastructure Created

### SNS/SQS Messaging
- SNS Topic: solve-global-kr-textract-completion
- SQS Queue: solve-global-kr-textextractor-processor
- Dead Letter Queue: solve-global-kr-textextractor-dlq

### Lambda Functions
- TextExtractor Initiator (VPC-enabled)
- TextExtractor Processor (VPC-enabled, SQS-triggered)
- TextExtractor Trigger (for testing)

### Security Groups
- Lambda Security Group with RDS access
- RDS Security Group updated for Lambda access

### IAM Roles
- TextExtractor Lambda Role (comprehensive permissions)
- Textract Service Role (SNS publish permissions)

## Troubleshooting

### Common Issues
1. **VPC Connectivity**: Ensure Lambda functions are in isolated subnets
2. **Security Groups**: Verify Lambda → RDS security group rules
3. **Dependencies**: Check Lambda layer includes psycopg2-binary
4. **Permissions**: Verify IAM roles have all required permissions

### Verification Commands
```bash
# Check Lambda VPC configuration
AWS_PROFILE=solve-global aws lambda get-function \\
  --function-name solve-global-kr-textextractor-initiator \\
  --query 'Configuration.VpcConfig'

# Check security groups
AWS_PROFILE=solve-global aws ec2 describe-security-groups \\
  --group-names solve-global-kr-lambda-sg

# Test database connectivity (from local)
cd /Users/chris/climate-risk-rag-aws/layers/app-source/utils
source /tmp/database_url.sh
python -c "from DatabaseManager import DatabaseManager; db = DatabaseManager(); print('✅ Database connection working')"
```

## Success Criteria
- [ ] All CDK stacks deploy successfully
- [ ] Lambda functions have VPC access
- [ ] Database connectivity working
- [ ] Complete async pipeline functional
- [ ] Test trigger returns success response
- [ ] Textract jobs complete and update database

## Cost Monitoring
- Monitor Textract usage (100 pages/month free tier)
- Lambda execution costs should be minimal
- SQS/SNS costs negligible for development

---
Generated: 2025-07-03T21:30:00Z
"""
    
    guide_path = Path("/Users/chris/climate-risk-rag-aws/docs/COMPLETE_CDK_DEPLOYMENT_GUIDE.md")
    with open(guide_path, 'w') as f:
        f.write(guide_content)
    
    print(f"📖 Deployment guide created: {guide_path}")

if __name__ == "__main__":
    try:
        build_dir = build_textextractor_layer()
        create_deployment_guide()
        
        print("\n🎉 TextExtractor Layer Build Complete!")
        print("\n📋 Next Steps:")
        print("1. Deploy complete CDK infrastructure:")
        print("   cd cdk && cdk deploy --app 'python app_complete.py' --all")
        print("2. Test the pipeline:")
        print("   AWS_PROFILE=solve-global aws lambda invoke --function-name solve-global-kr-textextractor-trigger --region us-east-1 /tmp/test.json")
        
    except Exception as e:
        print(f"❌ Build failed: {e}")
        exit(1)
