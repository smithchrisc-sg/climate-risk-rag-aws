# Complete TextExtractor CDK Deployment Guide

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
AWS_PROFILE=solve-global aws lambda invoke \
  --function-name solve-global-kr-textextractor-trigger \
  --region us-east-1 \
  /tmp/test-response.json

cat /tmp/test-response.json
```

### 4. Monitor Logs
```bash
# Check initiator logs
AWS_PROFILE=solve-global aws logs filter-log-events \
  --log-group-name "/aws/lambda/solve-global-kr-textextractor-initiator" \
  --region us-east-1

# Check processor logs  
AWS_PROFILE=solve-global aws logs filter-log-events \
  --log-group-name "/aws/lambda/solve-global-kr-textextractor-processor" \
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
AWS_PROFILE=solve-global aws lambda get-function \
  --function-name solve-global-kr-textextractor-initiator \
  --query 'Configuration.VpcConfig'

# Check security groups
AWS_PROFILE=solve-global aws ec2 describe-security-groups \
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
