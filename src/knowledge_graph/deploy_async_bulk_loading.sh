#!/bin/bash
"""
Deploy Async Neptune Bulk Loading Infrastructure
Sets up Lambda functions, SNS topics, and EventBridge rules
"""

set -e

echo "🚀 DEPLOYING ASYNC NEPTUNE BULK LOADING INFRASTRUCTURE"
echo "======================================================="

# Configuration
PROFILE="solve-global"
REGION="us-east-1"
ACCOUNT_ID="861276078413"
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/nlp-integration-lambda-role"

# VPC Configuration
VPC_SUBNETS="subnet-0c0be1dd59f70f70e,subnet-03d8bd6cf3491f38c"
SECURITY_GROUP="sg-0c043bcb40f656321"

echo "📋 Configuration:"
echo "   Profile: $PROFILE"
echo "   Region: $REGION"
echo "   Account: $ACCOUNT_ID"
echo "   VPC Subnets: $VPC_SUBNETS"
echo "   Security Group: $SECURITY_GROUP"
echo ""

# Step 1: Create SNS Topic
echo "📢 Step 1: Creating SNS Topic..."
SNS_TOPIC_ARN=$(aws sns create-topic \
    --name neptune-bulk-load-jobs \
    --profile $PROFILE \
    --region $REGION \
    --query 'TopicArn' \
    --output text)

echo "   ✅ SNS Topic created: $SNS_TOPIC_ARN"

# Step 2: Create Lambda Functions
echo ""
echo "⚡ Step 2: Creating Lambda Functions..."

# Function 1: Async Job Initiator
echo "   Creating neptune-bulk-loader-async..."
zip -q neptune-bulk-loader-async.zip neptune_bulk_loader_async.py

aws lambda create-function \
    --function-name neptune-bulk-loader-async \
    --runtime python3.9 \
    --role $ROLE_ARN \
    --handler neptune_bulk_loader_async.lambda_handler \
    --zip-file fileb://neptune-bulk-loader-async.zip \
    --vpc-config SubnetIds=$VPC_SUBNETS,SecurityGroupIds=$SECURITY_GROUP \
    --timeout 60 \
    --memory-size 256 \
    --environment Variables="{SNS_TOPIC_ARN=$SNS_TOPIC_ARN}" \
    --profile $PROFILE \
    --region $REGION \
    --query 'FunctionArn' \
    --output text > /dev/null

echo "   ✅ neptune-bulk-loader-async created"

# Function 2: Job Monitor
echo "   Creating neptune-bulk-loader-monitor..."
zip -q neptune-bulk-loader-monitor.zip neptune_bulk_loader_monitor.py

aws lambda create-function \
    --function-name neptune-bulk-loader-monitor \
    --runtime python3.9 \
    --role $ROLE_ARN \
    --handler neptune_bulk_loader_monitor.lambda_handler \
    --zip-file fileb://neptune-bulk-loader-monitor.zip \
    --vpc-config SubnetIds=$VPC_SUBNETS,SecurityGroupIds=$SECURITY_GROUP \
    --timeout 60 \
    --memory-size 256 \
    --environment Variables="{SNS_TOPIC_ARN=$SNS_TOPIC_ARN}" \
    --profile $PROFILE \
    --region $REGION \
    --query 'FunctionArn' \
    --output text > /dev/null

echo "   ✅ neptune-bulk-loader-monitor created"

# Function 3: Completion Handler
echo "   Creating neptune-bulk-loader-completion..."
zip -q neptune-bulk-loader-completion.zip neptune_bulk_loader_completion.py

COMPLETION_FUNCTION_ARN=$(aws lambda create-function \
    --function-name neptune-bulk-loader-completion \
    --runtime python3.9 \
    --role $ROLE_ARN \
    --handler neptune_bulk_loader_completion.lambda_handler \
    --zip-file fileb://neptune-bulk-loader-completion.zip \
    --vpc-config SubnetIds=$VPC_SUBNETS,SecurityGroupIds=$SECURITY_GROUP \
    --timeout 300 \
    --memory-size 256 \
    --profile $PROFILE \
    --region $REGION \
    --query 'FunctionArn' \
    --output text)

echo "   ✅ neptune-bulk-loader-completion created"

# Step 3: Subscribe Lambda to SNS Topic
echo ""
echo "🔗 Step 3: Connecting SNS Topic to Lambda..."

aws sns subscribe \
    --topic-arn $SNS_TOPIC_ARN \
    --protocol lambda \
    --notification-endpoint $COMPLETION_FUNCTION_ARN \
    --profile $PROFILE \
    --region $REGION > /dev/null

# Grant SNS permission to invoke Lambda
aws lambda add-permission \
    --function-name neptune-bulk-loader-completion \
    --statement-id sns-invoke \
    --action lambda:InvokeFunction \
    --principal sns.amazonaws.com \
    --source-arn $SNS_TOPIC_ARN \
    --profile $PROFILE \
    --region $REGION > /dev/null

echo "   ✅ SNS subscription created"

# Step 4: Create EventBridge Rule (Optional - for periodic monitoring)
echo ""
echo "⏰ Step 4: Creating EventBridge Rule (Optional)..."

RULE_ARN=$(aws events put-rule \
    --name neptune-bulk-load-job-monitor \
    --schedule-expression 'rate(5 minutes)' \
    --description 'Monitor Neptune bulk loading jobs periodically' \
    --profile $PROFILE \
    --region $REGION \
    --query 'RuleArn' \
    --output text)

echo "   ✅ EventBridge rule created: $RULE_ARN"

# Step 5: Clean up zip files
echo ""
echo "🧹 Step 5: Cleaning up..."
rm -f neptune-bulk-loader-*.zip

echo "   ✅ Cleanup completed"

# Step 6: Summary
echo ""
echo "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo "====================================="
echo ""
echo "📋 Deployed Resources:"
echo "   SNS Topic: $SNS_TOPIC_ARN"
echo "   Lambda Functions:"
echo "     - neptune-bulk-loader-async (Job Initiator)"
echo "     - neptune-bulk-loader-monitor (Status Monitor)"  
echo "     - neptune-bulk-loader-completion (Completion Handler)"
echo "   EventBridge Rule: $RULE_ARN"
echo ""
echo "🚀 Usage:"
echo "   1. Generate TTL files: python3 ttl_s3_pipeline_async.py"
echo "   2. Jobs will be submitted asynchronously"
echo "   3. Monitor progress via SNS notifications"
echo "   4. Completion handler will validate results"
echo ""
echo "📊 Monitoring:"
echo "   - Check Lambda logs in CloudWatch"
echo "   - Monitor SNS topic for job notifications"
echo "   - EventBridge rule runs every 5 minutes"
