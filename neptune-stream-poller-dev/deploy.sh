#!/bin/bash

# Deploy script for Neptune Stream Poller with Ontology Filtering
set -e

FUNCTION_NAME="SG-NeptuneFullTextSearch--NeptuneStreamPollerLambd-F6zwO5b5630f"
LAYER_NAME="neptune-streams-layer"

echo "Deploying Neptune Stream Poller with Ontology Filtering..."

# Build first
./build.sh

# Update the layer
echo "Updating Lambda layer..."
LAYER_VERSION=$(aws lambda publish-layer-version \
    --layer-name $LAYER_NAME \
    --zip-file fileb://neptune-streams-layer-with-filtering.zip \
    --compatible-runtimes python3.9 \
    --description "Neptune streams poller layer with ontology filtering" \
    --query 'Version' --output text)

echo "New layer version: $LAYER_VERSION"

# Update the function code
echo "Updating Lambda function code..."
aws lambda update-function-code \
    --function-name $FUNCTION_NAME \
    --zip-file fileb://neptune-stream-poller-with-filtering.zip

# Update the function configuration to use the new layer version
echo "Updating function configuration to use new layer..."
aws lambda update-function-configuration \
    --function-name $FUNCTION_NAME \
    --layers "arn:aws:lambda:us-east-1:861276078413:layer:$LAYER_NAME:$LAYER_VERSION"

echo "Deployment complete!"
echo "Function: $FUNCTION_NAME"
echo "Layer: $LAYER_NAME:$LAYER_VERSION"
echo ""
echo "Monitor logs with:"
echo "aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
