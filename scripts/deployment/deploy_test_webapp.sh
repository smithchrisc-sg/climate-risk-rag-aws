#!/bin/bash

# Deploy test webapp to S3 static website hosting

BUCKET_NAME="gaip-api-test-webapp-$(date +%s)"
REGION="us-east-1"

echo "Creating S3 bucket: $BUCKET_NAME"

# Create bucket
aws s3 mb s3://$BUCKET_NAME --region $REGION

# Enable static website hosting
aws s3 website s3://$BUCKET_NAME --index-document index.html

# Upload files
echo "Uploading test webapp..."
aws s3 cp ../test-webapp/index.html s3://$BUCKET_NAME/index.html

# Make bucket public for static website
aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::'$BUCKET_NAME'/*"
    }
  ]
}'

# Get website URL
WEBSITE_URL="http://$BUCKET_NAME.s3-website-$REGION.amazonaws.com"

echo ""
echo "✅ Test webapp deployed successfully!"
echo "🌐 URL: $WEBSITE_URL"
echo ""
echo "Next steps:"
echo "1. Open the URL in your browser"
echo "2. Run: python3 generate_api_keys.py"
echo "3. Copy an API key from test_api_keys.json"
echo "4. Paste API endpoint and key into the form"
echo "5. Test search with 'climate risk North Macedonia'"
echo ""
echo "To delete later: aws s3 rb s3://$BUCKET_NAME --force"
