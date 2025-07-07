# Lambda Layers Deployment and Management Guide
## Climate Risk RAG System

## 🎯 **Overview**

This guide provides complete instructions for deploying, managing, and maintaining the Lambda layers for the Climate Risk RAG system. The layer architecture includes 11 layers optimized for performance, cost, and maintainability.

## 📋 **Prerequisites**

### **Required Tools**
- AWS CLI v2.x configured with appropriate credentials
- Node.js 18+ and npm (for CDK)
- Python 3.11+ and pip
- jq (for JSON parsing in scripts)
- zip/unzip utilities

### **AWS Permissions Required**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:*",
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PassRole",
        "s3:GetObject",
        "s3:PutObject",
        "cloudformation:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### **Environment Setup**
```bash
# Set AWS region
export AWS_REGION=us-east-1

# Set AWS profile (if using named profiles)
export AWS_PROFILE=your-profile-name

# Verify AWS configuration
aws sts get-caller-identity
```

## 🚀 **Quick Start Deployment**

### **1. Prepare Application Source Code**
```bash
cd /Users/chris/climate-risk-rag-aws/layers

# Prepare application source from POC
./build-scripts/prepare-app-source.sh
```

### **2. Build All Layers**
```bash
# Build all layers (foundation + application)
./build-scripts/build-all-layers.sh

# Build and deploy in one step
./build-scripts/build-all-layers.sh --deploy
```

### **3. Deploy CDK Infrastructure**
```bash
cd infrastructure

# Install dependencies
npm install

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy layers infrastructure
cdk deploy

# Deploy for specific environment
cdk deploy --context environment=prod
```

### **4. Test Layer Deployment**
```bash
cd ../tests

# Test all layers
./test-all-layers.sh
```

## 📦 **Layer Architecture Details**

### **Foundation Layers (Third-party Dependencies)**

| Layer | Size | Description | Functions Using |
|-------|------|-------------|-----------------|
| **aws-core-layer** | 30MB | AWS SDK, requests, utilities | All 17 functions |
| **data-processing-layer** | 80MB | NumPy, Pandas, SciPy | 8 functions |
| **database-layer** | 40MB | PostgreSQL, OpenSearch, Redis | 6 functions |
| **nlp-core-layer** | 200MB | Transformers, tokenizers | 7 functions |
| **pytorch-layer** | 400MB | PyTorch framework | 5 functions |
| **knowledge-graph-layer** | 120MB | RDF, SPARQL, OWL | 4 functions |
| **web-template-layer** | 60MB | Jinja2, BeautifulSoup | 3 functions |
| **nlp-models-layer** | 800MB | spaCy, sentence-transformers | 4 functions |

### **Application Layers (Shared Code)**

| Layer | Size | Description | Components |
|-------|------|-------------|------------|
| **climate-risk-core-layer** | 15MB | Core utilities | DocumentIDManager, DatabaseManager, ProvenanceTracker, TextCleaner |
| **kg-shared-layer** | 25MB | Knowledge graph components | OntologyManager, types, ComponentMatcher, TermMatcher |
| **rag-shared-layer** | 20MB | RAG system components | SearchProcessorBase, ScoreNormalizer, TemplateManager |

## 🔧 **Detailed Build Process**

### **Building Individual Layers**

```bash
# Build specific foundation layer
pip install -r requirements/aws-core.txt \
    -t built-layers/aws-core-layer/python \
    --platform manylinux2014_x86_64 \
    --only-binary=all

cd built-layers/aws-core-layer
zip -r ../aws-core-layer.zip .

# Deploy specific layer
aws lambda publish-layer-version \
    --layer-name climate-risk-rag-aws-core-dev \
    --zip-file fileb://built-layers/aws-core-layer.zip \
    --compatible-runtimes python3.11 \
    --description "AWS SDK and core utilities"
```

### **Building Application Layers**

```bash
# Prepare application source
mkdir -p built-layers/climate-risk-core-layer/python/climate_risk_rag

# Copy utilities
cp -r app-source/utils built-layers/climate-risk-core-layer/python/climate_risk_rag/
cp app-source/document_processing/DocumentMetadata.py \
   built-layers/climate-risk-core-layer/python/climate_risk_rag/

# Create __init__.py files
find built-layers/climate-risk-core-layer/python -type d -exec touch {}/__init__.py \;

# Create deployment package
cd built-layers/climate-risk-core-layer
zip -r ../climate-risk-core-layer.zip .
```

## 🏗️ **CDK Infrastructure Management**

### **CDK Project Structure**
```
infrastructure/
├── app.ts                 # CDK app entry point
├── lambda-layers-stack.ts # Layer definitions
├── cdk.json              # CDK configuration
├── package.json          # Dependencies
└── tsconfig.json         # TypeScript config
```

### **Environment-Specific Deployment**

```bash
# Development environment
cdk deploy --context environment=dev

# Production environment
cdk deploy --context environment=prod

# Custom layer prefix
cdk deploy --context layerPrefix=my-custom-prefix
```

### **CDK Useful Commands**

```bash
# Show differences
cdk diff

# Synthesize CloudFormation
cdk synth

# List stacks
cdk list

# Destroy stack
cdk destroy
```

## 🔍 **Layer Management**

### **Using the Layer Manager Tool**

```bash
cd management

# List all layers
./layer-manager.py list

# List with version details
./layer-manager.py list --versions

# Check layer usage
./layer-manager.py usage climate-risk-rag-aws-core-dev

# Update a layer
./layer-manager.py update climate-risk-rag-aws-core-dev ../built-layers/aws-core-layer.zip

# Clean up old versions (keep 3 latest)
./layer-manager.py cleanup climate-risk-rag-aws-core-dev --keep 3

# Generate comprehensive report
./layer-manager.py report --output layer-report.json

# Validate layer compatibility
./layer-manager.py validate climate-risk-rag-aws-core-dev
```

### **Layer Version Management**

```bash
# List all versions of a layer
aws lambda list-layer-versions \
    --layer-name climate-risk-rag-aws-core-dev

# Delete specific version
aws lambda delete-layer-version \
    --layer-name climate-risk-rag-aws-core-dev \
    --version-number 5

# Get layer version details
aws lambda get-layer-version \
    --layer-name climate-risk-rag-aws-core-dev \
    --version-number 1
```

## 🧪 **Testing and Validation**

### **Automated Testing**

```bash
cd tests

# Test all layers
./test-all-layers.sh

# Test specific layer functionality
aws lambda invoke \
    --function-name test-layer-aws-core-layer \
    --payload '{"test_imports": [{"module": "boto3"}]}' \
    response.json
```

### **Manual Testing**

```bash
# Create test function with layer
aws lambda create-function \
    --function-name test-my-layer \
    --runtime python3.11 \
    --role arn:aws:iam::ACCOUNT:role/lambda-execution-role \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://test-function.zip \
    --layers arn:aws:lambda:us-east-1:ACCOUNT:layer:climate-risk-rag-aws-core-dev:1

# Test import functionality
aws lambda invoke \
    --function-name test-my-layer \
    --payload '{}' \
    response.json
```

## 📊 **Monitoring and Maintenance**

### **Layer Usage Monitoring**

```bash
# Generate usage report
./management/layer-manager.py report --output monthly-report.json

# Check for unused layers
./management/layer-manager.py list | grep "Functions using: 0"

# Monitor layer sizes
aws lambda list-layers --query 'Layers[?contains(LayerName, `climate-risk-rag`)].{Name:LayerName,Size:LatestMatchingVersion.CodeSize}'
```

### **Automated Maintenance Tasks**

```bash
#!/bin/bash
# maintenance.sh - Weekly maintenance script

# Clean up old versions (keep 3 latest)
for layer in $(aws lambda list-layers --query 'Layers[?contains(LayerName, `climate-risk-rag`)].LayerName' --output text); do
    ./management/layer-manager.py cleanup "$layer" --keep 3
done

# Generate weekly report
./management/layer-manager.py report --output "reports/weekly-$(date +%Y-%m-%d).json"

# Validate all layers
for layer in $(aws lambda list-layers --query 'Layers[?contains(LayerName, `climate-risk-rag`)].LayerName' --output text); do
    ./management/layer-manager.py validate "$layer"
done
```

## 🔄 **Update Procedures**

### **Updating Foundation Layers**

```bash
# 1. Update requirements file
vim requirements/aws-core.txt

# 2. Rebuild layer
./build-scripts/build-all-layers.sh

# 3. Deploy updated layer
aws lambda publish-layer-version \
    --layer-name climate-risk-rag-aws-core-dev \
    --zip-file fileb://built-layers/aws-core-layer.zip \
    --compatible-runtimes python3.11

# 4. Test new version
./tests/test-all-layers.sh

# 5. Update functions to use new version (if needed)
```

### **Updating Application Layers**

```bash
# 1. Update source code in POC
# (Make changes to /Volumes/G-RAID Photo 24TB/climate_risk_rag/src)

# 2. Prepare updated source
./build-scripts/prepare-app-source.sh

# 3. Rebuild application layers
./build-scripts/build-all-layers.sh

# 4. Deploy updates
./build-scripts/build-all-layers.sh --deploy

# 5. Test updated layers
./tests/test-all-layers.sh
```

### **Rolling Updates**

```bash
# Deploy to dev environment first
cdk deploy --context environment=dev

# Test in dev
./tests/test-all-layers.sh

# Deploy to production
cdk deploy --context environment=prod

# Monitor production deployment
./management/layer-manager.py report
```

## 🚨 **Troubleshooting**

### **Common Issues**

**Layer Size Too Large**
```bash
# Check layer size
aws lambda get-layer-version --layer-name LAYER_NAME --version-number VERSION

# Optimize layer size
find built-layers/LAYER_NAME -name "*.pyc" -delete
find built-layers/LAYER_NAME -name "__pycache__" -type d -exec rm -rf {} +
```

**Import Errors**
```bash
# Check Python path in layer
unzip -l built-layers/LAYER_NAME.zip | grep python

# Verify module structure
./tests/test-all-layers.sh
```

**Permission Errors**
```bash
# Check IAM role permissions
aws iam get-role --role-name lambda-execution-role

# Verify layer permissions
aws lambda get-layer-version-policy --layer-name LAYER_NAME --version-number VERSION
```

### **Debug Commands**

```bash
# List all layers with details
aws lambda list-layers --query 'Layers[?contains(LayerName, `climate-risk-rag`)]'

# Check function layer configuration
aws lambda get-function --function-name FUNCTION_NAME --query 'Configuration.Layers'

# Test layer import in Python
python3 -c "import sys; sys.path.insert(0, '/opt/python'); import MODULE_NAME"
```

## 📈 **Performance Optimization**

### **Layer Size Optimization**

```bash
# Remove unnecessary files
find built-layers/LAYER_NAME -name "*.dist-info" -type d -exec rm -rf {} +
find built-layers/LAYER_NAME -name "tests" -type d -exec rm -rf {} +
find built-layers/LAYER_NAME -name "docs" -type d -exec rm -rf {} +

# Use only-binary for pip installs
pip install --only-binary=all -t LAYER_DIR PACKAGE_NAME
```

### **Cold Start Optimization**

```bash
# Use smaller, focused layers
# Avoid loading heavy modules at import time
# Pre-compile Python files
python -m compileall built-layers/LAYER_NAME/python
```

## 🔐 **Security Best Practices**

### **Layer Security**

```bash
# Scan for vulnerabilities
pip-audit --requirement requirements/LAYER_NAME.txt

# Check for sensitive data
grep -r "password\|secret\|key" built-layers/LAYER_NAME/

# Verify layer integrity
sha256sum built-layers/LAYER_NAME.zip
```

### **Access Control**

```bash
# Set layer permissions
aws lambda add-layer-version-permission \
    --layer-name LAYER_NAME \
    --version-number VERSION \
    --statement-id allow-account \
    --action lambda:GetLayerVersion \
    --principal ACCOUNT_ID
```

## 📚 **Additional Resources**

### **AWS Documentation**
- [Lambda Layers](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)
- [Layer Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)

### **Monitoring Tools**
- CloudWatch Logs for layer usage
- AWS X-Ray for performance tracing
- Cost Explorer for layer costs

### **Automation Scripts**
- `build-scripts/build-all-layers.sh` - Complete build automation
- `management/layer-manager.py` - Layer management CLI
- `tests/test-all-layers.sh` - Automated testing

This comprehensive guide provides everything needed to successfully deploy, manage, and maintain the Lambda layers for the Climate Risk RAG system.
