#!/bin/bash

# Deploy Neptune Stream Poller with Ontology Positive Filtering Enabled
# This script deploys the enhanced Lambda with example filtering configuration

set -e

# Configuration
LAMBDA_FUNCTION_NAME="NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3"
PACKAGE_NAME="neptune-stream-poller-with-filtering.zip"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Deploying Neptune Stream Poller with Ontology Positive Filtering"
echo "=================================================================="

# Change to the Lambda directory
cd "$SCRIPT_DIR"

# Clean up previous builds
echo "🧹 Cleaning up previous builds..."
rm -f "$PACKAGE_NAME"
rm -rf __pycache__
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Create deployment package
echo "📦 Creating deployment package with ontology filtering..."
zip -r "$PACKAGE_NAME" . \
    -x "*.zip" \
    -x "*.md" \
    -x "deploy*.sh" \
    -x "__pycache__/*" \
    -x "*/__pycache__/*" \
    -x "*.pyc" \
    -x ".DS_Store" \
    -x "*/.*"

# Check package size
PACKAGE_SIZE=$(du -h "$PACKAGE_NAME" | cut -f1)
echo "📊 Package size: $PACKAGE_SIZE"

# Deploy to AWS Lambda
echo "☁️  Deploying to AWS Lambda..."
aws lambda update-function-code \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --zip-file "fileb://$PACKAGE_NAME"

# Wait for update to complete
echo "⏳ Waiting for deployment to complete..."
aws lambda wait function-updated \
    --function-name "$LAMBDA_FUNCTION_NAME"

# Configure environment variables for ontology filtering
echo "🔧 Configuring ontology positive filtering..."
aws lambda update-function-configuration \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --environment Variables='{
        "ONTOLOGY_FILTERING_ENABLED": "true",
        "LOG_FILTERED_RECORDS": "true",
        "MaxPollingWaitTime": "600",
        "AdditionalParams": "{ \"ElasticSearchEndpoint\": \"vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com\", \"NumberOfShards\": \"2\", \"NumberOfReplica\": \"1\", \"IgnoreMissingDocument\": \"true\", \"ReplicationScope\": \"all\", \"GeoLocationFields\": \"\", \"DatatypesToExclude\": \"\", \"PropertiesToExclude\": \"\", \"EnableNonStringIndexing\": \"true\"}",
        "LoggingLevel": "INFO",
        "StreamRecordsHandler": "neptune_to_es.neptune_sparql_es_handler.ElasticSearchSparqlHandler",
        "MaxPollingInterval": "600",
        "LeaseTable": "NeptuneOntologyFTS-LeaseTable",
        "NeptuneStreamEndpoint": "https://solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182/sparql/stream",
        "StartingCheckpoint": "0:0",
        "Application": "NeptuneOntologyFTS",
        "StreamRecordsBatchSize": "5000"
    }'

# Wait for configuration update
echo "⏳ Waiting for configuration update..."
aws lambda wait function-updated \
    --function-name "$LAMBDA_FUNCTION_NAME"

# Get function info
echo "ℹ️  Updated function information:"
aws lambda get-function-configuration \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --query '{FunctionName:FunctionName,Runtime:Runtime,Handler:Handler,MemorySize:MemorySize,Timeout:Timeout,LastModified:LastModified}' \
    --output table

echo ""
echo "✅ Deployment with ontology positive filtering completed successfully!"
echo ""
echo "🎯 Filtering Configuration:"
echo "  • Positive filtering: ENABLED"
echo "  • Detailed logging: ENABLED"
echo "  • Example ontologies: Geonames, Climate Risk, RDFS, SKOS"
echo ""
echo "📋 Example filtering rules active:"
echo "  • Geonames: gn:name, gn:alternateName, gn:officialName, gn:shortName"
echo "  • Climate Risk: rdfs:label, skos:prefLabel, skos:altLabel, skos:definition"
echo "  • RDFS: rdfs:label, rdfs:comment"
echo "  • SKOS: skos:prefLabel, skos:altLabel, skos:definition, skos:note"
echo ""
echo "📊 Monitoring:"
echo "  • CloudWatch logs: /aws/lambda/$LAMBDA_FUNCTION_NAME"
echo "  • Look for: 'Ontology positive filtering: X → Y records'"
echo "  • Dashboard: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=neptune-stream-poller-NeptuneOntologyFTS"
echo ""
echo "🔧 To customize filtering rules, update the ontology_filter.py file and redeploy"
echo "🔧 To disable filtering: aws lambda update-function-configuration --function-name $LAMBDA_FUNCTION_NAME --environment Variables='{\"ONTOLOGY_FILTERING_ENABLED\":\"false\"}'"
