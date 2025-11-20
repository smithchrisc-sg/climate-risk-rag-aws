# Configuration Files
**Purpose**: System configuration files and parameters

## Directory Structure

### `/lambda-env/` - Lambda Environment Variables
Configuration files for Lambda function environment variables.
- `keyword-indexer-env-vars.json` - Keyword indexer environment configuration
- `vector-embeddings-env-vars.json` - Vector embeddings environment configuration

### `/policies/` - IAM Policies & Permissions
IAM policy documents and permission configurations.
- `comprehend-sns-policy.json` - Comprehend SNS policy configuration

### `/stack-parameters/` - CDK Stack Parameters
CloudFormation/CDK stack parameter files.
- `neptune-stream-poller-stack-info.json` - Neptune stream poller stack information
- `neptune-stream-poller-stack-parameters.json` - Neptune stream poller parameters

## Usage
These configuration files are used during deployment and system setup. Reference them in deployment scripts and CDK configurations as needed.
