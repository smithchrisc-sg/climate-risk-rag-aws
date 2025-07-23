# Climate Risk RAG Infrastructure Reference Guide

## Overview
This document provides comprehensive infrastructure mappings and configurations for the Climate Risk RAG system. Use this as a reference to ensure correct configuration on the first attempt when creating new Lambda functions, database connections, and other AWS resources.

## Table of Contents
1. [VPC and Networking](#vpc-and-networking)
2. [Security Groups](#security-groups)
3. [Database Configuration](#database-configuration)
4. [Lambda Configuration](#lambda-configuration)
5. [IAM Roles and Policies](#iam-roles-and-policies)
6. [Lambda Layers](#lambda-layers)
7. [S3 Buckets](#s3-buckets)
8. [Secrets Manager](#secrets-manager)
9. [Common Patterns](#common-patterns)
10. [Troubleshooting Checklist](#troubleshooting-checklist)

---

## VPC and Networking

### Primary VPC
- **VPC ID**: `vpc-051c21d88c7dc3819`
- **Name**: Climate Risk RAG VPC
- **Region**: `us-east-1`

### Subnet Configuration

#### Database Subnets (Use for Lambda functions that need database access)
- **Primary**: `subnet-0e9efc5fdf29e9da0`
- **Secondary**: `subnet-00efdcc220a613ae3`
- **Type**: Private subnets with database access
- **Use Case**: Lambda functions requiring PostgreSQL connectivity

#### Application Subnets (General purpose)
- **Primary**: `subnet-03d8bd6cf3491f38c`
- **Secondary**: `subnet-0c0be1dd59f70f70e`
- **Type**: Private subnets with egress
- **Use Case**: Lambda functions without database requirements

### CDK Subnet Selection Patterns

```python
# For database-connected Lambda functions
vpc_subnets=ec2.SubnetSelection(subnets=[
    ec2.Subnet.from_subnet_id(self, "DatabaseSubnet1", subnet_id="subnet-0e9efc5fdf29e9da0"),
    ec2.Subnet.from_subnet_id(self, "DatabaseSubnet2", subnet_id="subnet-00efdcc220a613ae3")
])

# For general Lambda functions
vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)
```

---

## Security Groups

### Database Security Group
- **ID**: `sg-09bc56a537bf7ac12`
- **Name**: PostgreSQL Database Security Group
- **Purpose**: Controls access to RDS PostgreSQL instance

#### Inbound Rules (Port 5432)
- `sg-08518057bfb59e735` - Text Extractor Lambda functions
- `sg-0ddb2f3a4b57adfd3` - Text Chunker Lambda
- `sg-099296a5c809e8d9d` - Text Chunker Pipeline Lambda
- `sg-0709acdc3f0cccd7f` - Keyword Indexer Lambda
- `sg-0c9e10b9cfb4c9eb0` - Async Keyword Indexer Lambdas
- `sg-0c043bcb40f656321` - KG Lambda functions
- `sg-048961fc0bd1504c5` - Pipeline Test Lambda
- `174.165.97.22/32` - External IP access

### Neptune Security Group
- **ID**: `sg-0c8afac0f49164069`
- **Name**: Neptune Database Security Group
- **Purpose**: Controls access to Neptune graph database cluster

#### Inbound Rules (Port 8182)
- `sg-0c9e10b9cfb4c9eb0` - Lambda functions requiring Neptune access
- **Critical**: Must include Lambda security group for KG integration worker connectivity

#### Configuration Notes
- **SPARQL Endpoint**: Port 8182 for SPARQL queries and updates
- **Gremlin Endpoint**: Port 8182 for Gremlin graph traversal queries
- **VPC Access Only**: No public internet access configured

### Lambda Security Groups

#### Standard Lambda Security Group
- **ID**: `sg-0c9e10b9cfb4c9eb0`
- **Name**: Lambda Functions Security Group
- **Purpose**: General Lambda function network access
- **Outbound Rules**:
  - TCP 5432 to `sg-09bc56a537bf7ac12` (Database access)
  - TCP 8182 to `sg-0c8afac0f49164069` (Neptune access)
  - TCP 443 to `0.0.0.0/0` (HTTPS)
  - All traffic to `0.0.0.0/0` (General egress)

#### Text Extractor Lambda Security Group
- **ID**: `sg-08518057bfb59e735`
- **Name**: solve-global-kr-lambda-sg
- **Outbound Rules**:
  - TCP 5432 to `sg-09bc56a537bf7ac12` (Database access)
  - TCP 443 to `0.0.0.0/0` (HTTPS)
  - All traffic to `0.0.0.0/0` (General egress)

#### Pipeline Test Lambda Security Group
- **ID**: `sg-048961fc0bd1504c5`
- **Name**: Pipeline Test Function Security Group
- **Outbound Rules**:
  - TCP 5432 to `sg-09bc56a537bf7ac12` (Database access)
  - All traffic to `0.0.0.0/0` (General egress)

### Security Group Creation Pattern

```python
# Lambda security group with database and Neptune access
lambda_sg = ec2.SecurityGroup(
    self, "LambdaSecurityGroup",
    vpc=vpc,
    description="Security group for Lambda function with database and Neptune access",
    allow_all_outbound=True
)

# Neptune security group
neptune_sg = ec2.SecurityGroup(
    self, "NeptuneSecurityGroup",
    vpc=vpc,
    description="Security group for Neptune database cluster",
    allow_all_outbound=False
)

# Add ingress rule for Lambda to Neptune access
neptune_sg.add_ingress_rule(
    peer=lambda_sg,
    connection=ec2.Port.tcp(8182),
    description="Lambda access to Neptune SPARQL/Gremlin endpoint"
)
```

### Critical Security Group Configuration for KG Integration

**Important**: The KG Integration Worker requires specific security group configuration to access Neptune:

1. **Lambda Security Group** (`sg-0c9e10b9cfb4c9eb0`) must be assigned to KG Integration Worker
2. **Neptune Security Group** (`sg-0c8afac0f49164069`) must have ingress rule allowing Lambda security group on port 8182
3. **Subnets** must be Neptune-accessible subnets (`subnet-03d8bd6cf3491f38c`, `subnet-0c0be1dd59f70f70e`)

**Common Issue**: Lambda functions cannot connect to Neptune without proper security group ingress rules, even with correct VPC and subnet configuration.

# Add specific database outbound rule
lambda_sg.add_egress_rule(
    peer=ec2.SecurityGroup.from_security_group_id(
        self, "DatabaseSG", 
        security_group_id="sg-09bc56a537bf7ac12"
    ),
    connection=ec2.Port.tcp(5432),
    description="Allow PostgreSQL access to database"
)

# Add inbound rule to database security group
database_sg = ec2.SecurityGroup.from_security_group_id(
    self, "DatabaseSecurityGroup",
    security_group_id="sg-09bc56a537bf7ac12"
)

database_sg.add_ingress_rule(
    peer=lambda_sg,
    connection=ec2.Port.tcp(5432),
    description="Allow Lambda to connect to PostgreSQL"
)
```

---

## Database Configuration

### RDS PostgreSQL Instance
- **Endpoint**: `solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com`
- **Port**: `5432`
- **Database Name**: `climate_risk_rag`
- **Username**: `postgres`
- **IP Address**: `10.0.5.109`
- **Subnets**: `subnet-0e9efc5fdf29e9da0`, `subnet-00efdcc220a613ae3`

### Database URL Construction

#### Get Password from Secrets Manager
```bash
aws secretsmanager get-secret-value \
  --secret-id "rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863" \
  --query 'SecretString' --output text
```

#### Current Password (as of 2025-07-11)
`c0xfd_t#PBUqV(pLM-9IqM59G:>c`

#### Complete Database URL
```
postgresql://postgres:c0xfd_t#PBUqV(pLM-9IqM59G:>c@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require
```

#### CDK Environment Variable Pattern
```python
environment={
    "DATABASE_URL": "postgresql://postgres:c0xfd_t#PBUqV(pLM-9IqM59G:>c@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require"
}
```

### Neptune Graph Database Configuration

#### Neptune Cluster Details
- **Cluster Endpoint**: `solve-global-kr-rag-data-neptunedbcluster-1234567890.cluster-cqhsckw0edl1.neptune.amazonaws.com`
- **Reader Endpoint**: `solve-global-kr-rag-data-neptunedbcluster-1234567890.cluster-ro-cqhsckw0edl1.neptune.amazonaws.com`
- **Port**: `8182`
- **Engine**: `neptune`
- **Version**: Latest
- **Subnets**: `subnet-03d8bd6cf3491f38c`, `subnet-0c0be1dd59f70f70e`

#### Neptune Access Configuration

##### SPARQL Endpoint
```
https://solve-global-kr-rag-data-neptunedbcluster-1234567890.cluster-cqhsckw0edl1.neptune.amazonaws.com:8182/sparql
```

##### Gremlin Endpoint
```
wss://solve-global-kr-rag-data-neptunedbcluster-1234567890.cluster-cqhsckw0edl1.neptune.amazonaws.com:8182/gremlin
```

#### Lambda Environment Variables for Neptune

```python
environment={
    "NEPTUNE_ENDPOINT": "solve-global-kr-rag-data-neptunedbcluster-1234567890.cluster-cqhsckw0edl1.neptune.amazonaws.com",
    "NEPTUNE_PORT": "8182",
    "NEPTUNE_SPARQL_ENDPOINT": "https://solve-global-kr-rag-data-neptunedbcluster-1234567890.cluster-cqhsckw0edl1.neptune.amazonaws.com:8182/sparql",
    "AWS_REGION": "us-east-1"
}
```

#### Neptune Authentication
- **Method**: AWS Signature Version 4 (AWS4Auth)
- **Service**: `neptune-db`
- **Required Libraries**: `requests-aws4auth`, `requests`
- **IAM Permissions**: `neptune-db:*` actions required

#### Neptune Connection Pattern (Python)

```python
import requests
from requests_aws4auth import AWS4Auth
import boto3

# Get AWS credentials
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    'us-east-1',
    'neptune-db',
    session_token=credentials.token
)

# SPARQL query example
sparql_endpoint = "https://your-neptune-endpoint:8182/sparql"
query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"

response = requests.post(
    sparql_endpoint,
    data={'query': query},
    headers={'Content-Type': 'application/x-www-form-urlencoded'},
    auth=awsauth
)
```

#### Database Schema Updates for KG Integration

```sql
-- Updated processing stages to include KG stages
ALTER TABLE document_processing_status 
DROP CONSTRAINT IF EXISTS valid_stages;

ALTER TABLE document_processing_status 
ADD CONSTRAINT valid_stages 
CHECK (stage IN (
    'text_extraction', 
    'text_chunking', 
    'vector_embeddings', 
    'nlp_processing', 
    'kg_doc_structure',     -- Document structure KG processing
    'kg_triples_load'       -- Neptune knowledge graph loading
));
```

---

## Lambda Configuration

### Standard Lambda Configuration for Database Access

```python
lambda_.Function(
    self, "DatabaseConnectedFunction",
    function_name="solve-global-kr-your-function-name",
    runtime=lambda_.Runtime.PYTHON_3_11,
    handler="your_handler.lambda_handler",
    code=lambda_.Code.from_asset("../lambda/your_function"),
    role=lambda_role,
    timeout=Duration.minutes(15),
    memory_size=1024,
    vpc=vpc,
    vpc_subnets=ec2.SubnetSelection(subnets=[
        ec2.Subnet.from_subnet_id(self, "DatabaseSubnet1", subnet_id="subnet-0e9efc5fdf29e9da0"),
        ec2.Subnet.from_subnet_id(self, "DatabaseSubnet2", subnet_id="subnet-00efdcc220a613ae3")
    ]),
    layers=[
        lambda_.LayerVersion.from_layer_version_arn(
            self, "CoreUtilitiesLayer",
            layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:climate-risk-core-utilities:2"
        ),
        lambda_.LayerVersion.from_layer_version_arn(
            self, "DatabaseDependenciesLayer",
            layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:database-dependencies:2"
        )
    ],
    environment={
        "DATABASE_URL": "postgresql://postgres:c0xfd_t#PBUqV(pLM-9IqM59G:>c@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require",
        "LAMBDA_ENVIRONMENT": "true"
    }
)
```

### Knowledge Graph Integration Components

#### Document Structure KG Processor Configuration

```python
document_structure_kg_processor = lambda_.Function(
    self, "DocumentStructureKGProcessor",
    function_name="solve-global-kr-document-structure-kg-processor",
    runtime=lambda_.Runtime.PYTHON_3_11,
    handler="handler.lambda_handler",
    code=lambda_.Code.from_asset("../lambda/document-structure-kg-processor"),
    role=lambda_role,
    timeout=Duration.minutes(15),
    memory_size=1024,
    vpc=vpc,
    vpc_subnets=ec2.SubnetSelection(subnets=[
        ec2.Subnet.from_subnet_id(self, "DatabaseSubnet1", subnet_id="subnet-0e9efc5fdf29e9da0"),
        ec2.Subnet.from_subnet_id(self, "DatabaseSubnet2", subnet_id="subnet-00efdcc220a613ae3")
    ]),
    layers=[database_layer, requests_layer],
    environment={
        "DATABASE_URL": database_url,
        "KG_TRIPLES_READY_TOPIC_ARN": kg_triples_ready_topic.topic_arn,
        "LAMBDA_ENVIRONMENT": "true"
    }
)
```

#### KG Integration Worker Configuration

```python
kg_integration_worker = lambda_.Function(
    self, "KGIntegrationWorker",
    function_name="solve-global-kr-kg-integration-worker",
    runtime=lambda_.Runtime.PYTHON_3_11,
    handler="handler.lambda_handler",
    code=lambda_.Code.from_asset("../lambda/kg-integration-worker"),
    role=lambda_role,
    timeout=Duration.minutes(15),
    memory_size=1024,
    vpc=vpc,
    vpc_subnets=ec2.SubnetSelection(subnets=[
        ec2.Subnet.from_subnet_id(self, "NeptuneSubnet1", subnet_id="subnet-03d8bd6cf3491f38c"),
        ec2.Subnet.from_subnet_id(self, "NeptuneSubnet2", subnet_id="subnet-0c0be1dd59f70f70e")
    ]),
    security_groups=[
        ec2.SecurityGroup.from_security_group_id(
            self, "LambdaSecurityGroup", 
            security_group_id="sg-0c9e10b9cfb4c9eb0"
        )
    ],
    layers=[database_layer, requests_layer],
    environment={
        "DATABASE_URL": database_url,
        "NEPTUNE_ENDPOINT": "solve-global-kr-rag-data-neptunedbcluster-1234567890.cluster-cqhsckw0edl1.neptune.amazonaws.com",
        "NEPTUNE_PORT": "8182",
        "LAMBDA_ENVIRONMENT": "true"
    }
)
```

### SNS Topic Configuration for KG Integration

#### KG Triples Ready Topic

```python
kg_triples_ready_topic = sns.Topic(
    self, "KGTriplesReadyTopic",
    topic_name="solve-global-kr-kg-triples-ready",
    display_name="KG Triples Ready Topic"
)

# Subscribe KG Integration Worker to the topic
kg_triples_ready_topic.add_subscription(
    sns_subscriptions.LambdaSubscription(kg_integration_worker)
)
```

### Processing Stages Configuration

#### Database Schema Updates

```sql
-- Updated valid stages constraint to include KG processing stages
ALTER TABLE document_processing_status 
DROP CONSTRAINT IF EXISTS valid_stages;

ALTER TABLE document_processing_status 
ADD CONSTRAINT valid_stages 
CHECK (stage IN (
    'text_extraction', 
    'text_chunking', 
    'vector_embeddings', 
    'nlp_processing', 
    'kg_doc_structure', 
    'kg_triples_load'
));
```

#### Standard SNS Message Format for KG Processing

```json
{
  "doc_id": "document_identifier",
  "processing_type": "kg_triples_ready",
  "ttl_location": "s3://solve-global-kr-processed-documents/kg-ttl/document_id.ttl",
  "schema_version": "1.0",
  "timestamp": "2025-07-23T00:33:00Z",
  "metadata": {
    "ttl_size": 58808,
    "chunk_count": 72,
    "dublin_core_elements": ["title", "creator", "subject", "description", "date", "type", "format", "identifier"]
  }
}
```

---

## IAM Roles and Policies

### Standard Lambda Execution Role for Database Access

```python
lambda_role = iam.Role(
    self, "LambdaExecutionRole",
    assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
    managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
        iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
    ],
    inline_policies={
        "CustomLambdaPolicy": iam.PolicyDocument(
            statements=[
                # S3 permissions for all project buckets
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:ListBucket",
                        "s3:CopyObject",
                        "s3:GetObjectMetadata",
                        "s3:PutObjectMetadata"
                    ],
                    resources=[
                        "arn:aws:s3:::solve-global-kr-*",
                        "arn:aws:s3:::solve-global-kr-*/*"
                    ]
                ),
                # Lambda invoke permissions
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["lambda:InvokeFunction"],
                    resources=[f"arn:aws:lambda:{self.region}:{self.account}:function:solve-global-kr-*"]
                ),
                # RDS permissions
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "rds:DescribeDBInstances",
                        "rds:DescribeDBClusters"
                    ],
                    resources=["*"]
                ),
                # Secrets Manager permissions
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["secretsmanager:GetSecretValue"],
                    resources=[f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:*"]
                )
            ]
        )
    }
)
```

---

## Lambda Layers

### Available Layers

#### Core Utilities Layer (Contains DocumentIDManager)
- **ARN**: `arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities:2`
- **Contents**: DocumentIDManager, DatabaseManager, core utilities
- **Use Case**: Functions requiring document ID management

#### Database Dependencies Layer
- **ARN**: `arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies:2`
- **Contents**: PostgreSQL drivers, database connection libraries
- **Use Case**: Functions requiring database connectivity

#### Text Extractor Layer
- **ARN**: `arn:aws:lambda:us-east-1:861276078413:layer:textextractor-layer:1`
- **Contents**: Text extraction utilities
- **Use Case**: Document processing functions

### Layer Usage Pattern

```python
layers = [
    lambda_.LayerVersion.from_layer_version_arn(
        self, "CoreUtilitiesLayer",
        layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:climate-risk-core-utilities:2"
    ),
    lambda_.LayerVersion.from_layer_version_arn(
        self, "DatabaseDependenciesLayer",
        layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:database-dependencies:2"
    )
]
```

---

## S3 Buckets

### Standard Bucket Naming Convention
`solve-global-kr-{purpose}-{account}-{region}`

### Core Buckets
- **Documents**: `solve-global-kr-documents-861276078413-us-east-1`
- **Source Documents**: `solve-global-kr-dl-source-documents-861276078413-us-east-1`
- **Text**: `solve-global-kr-dl-text-861276078413-us-east-1`
- **Chunks**: `solve-global-kr-dl-chunks-861276078413-us-east-1`
- **Cache**: `solve-global-kr-cache-861276078413-us-east-1`

### Environment Variables Pattern

```python
environment={
    "EXISTING_DOCUMENTS_BUCKET": f"solve-global-kr-documents-{self.account}-{self.region}",
    "SOURCE_DOCUMENTS_BUCKET": f"solve-global-kr-dl-source-documents-{self.account}-{self.region}",
    "TEXT_BUCKET": f"solve-global-kr-dl-text-{self.account}-{self.region}",
    "CHUNKS_BUCKET": f"solve-global-kr-dl-chunks-{self.account}-{self.region}",
    "SQLITE_S3_BUCKET": f"solve-global-kr-cache-{self.account}-{self.region}",
    "SQLITE_S3_KEY": "database/corpus_document_ids.db",
    "SQLITE_DB_PATH": "/tmp/corpus_document_ids.db"
}
```

---

## Secrets Manager

### Database Credentials
- **Secret ID**: `rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863`
- **ARN**: `arn:aws:secretsmanager:us-east-1:861276078413:secret:rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863-XPOgCM`

### Retrieving Secrets

#### CLI Command
```bash
aws secretsmanager get-secret-value \
  --secret-id "rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863" \
  --query 'SecretString' --output text | jq -r '.password'
```

#### Python Code
```python
import boto3
import json

def get_db_password():
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863')
    secret = json.loads(response['SecretString'])
    return secret['password']
```

---

## Common Patterns

### Complete Lambda Function Template

```python
class YourLambdaStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Import existing VPC
        vpc = ec2.Vpc.from_lookup(self, "ExistingVPC", vpc_id="vpc-051c21d88c7dc3819")
        
        # Create security group
        lambda_sg = ec2.SecurityGroup(
            self, "LambdaSecurityGroup",
            vpc=vpc,
            description="Security group for Lambda function",
            allow_all_outbound=True
        )
        
        # Add database access rule
        lambda_sg.add_egress_rule(
            peer=ec2.SecurityGroup.from_security_group_id(
                self, "DatabaseSG", 
                security_group_id="sg-09bc56a537bf7ac12"
            ),
            connection=ec2.Port.tcp(5432),
            description="Allow PostgreSQL access"
        )
        
        # Create IAM role
        lambda_role = iam.Role(
            self, "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        
        # Import subnets
        subnet1 = ec2.Subnet.from_subnet_id(self, "DatabaseSubnet1", subnet_id="subnet-0e9efc5fdf29e9da0")
        subnet2 = ec2.Subnet.from_subnet_id(self, "DatabaseSubnet2", subnet_id="subnet-00efdcc220a613ae3")
        
        # Create Lambda function
        self.lambda_function = lambda_.Function(
            self, "LambdaFunction",
            function_name="solve-global-kr-your-function-name",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="your_handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/your_function"),
            role=lambda_role,
            timeout=Duration.minutes(15),
            memory_size=1024,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[subnet1, subnet2]),
            security_groups=[lambda_sg],
            layers=[
                lambda_.LayerVersion.from_layer_version_arn(
                    self, "CoreUtilitiesLayer",
                    layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:climate-risk-core-utilities:2"
                ),
                lambda_.LayerVersion.from_layer_version_arn(
                    self, "DatabaseDependenciesLayer",
                    layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:database-dependencies:2"
                )
            ],
            environment={
                "DATABASE_URL": "postgresql://postgres:c0xfd_t#PBUqV(pLM-9IqM59G:>c@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require",
                "EXISTING_DOCUMENTS_BUCKET": f"solve-global-kr-documents-{self.account}-{self.region}",
                "LAMBDA_ENVIRONMENT": "true"
            }
        )
        
        # Add inbound rule to database security group
        database_sg = ec2.SecurityGroup.from_security_group_id(
            self, "DatabaseSecurityGroup",
            security_group_id="sg-09bc56a537bf7ac12"
        )
        
        database_sg.add_ingress_rule(
            peer=lambda_sg,
            connection=ec2.Port.tcp(5432),
            description="Allow Lambda to connect to PostgreSQL"
        )
```

---

## Troubleshooting Checklist

### Database Connectivity Issues

1. **Check Subnets**
   - ✅ Lambda in database subnets: `subnet-0e9efc5fdf29e9da0`, `subnet-00efdcc220a613ae3`
   - ❌ Lambda in application subnets: `subnet-03d8bd6cf3491f38c`, `subnet-0c0be1dd59f70f70e`

2. **Check Security Groups**
   - ✅ Lambda security group has outbound rule to database security group on port 5432
   - ✅ Database security group has inbound rule from Lambda security group on port 5432

3. **Check Database Password**
   - ✅ Get current password from Secrets Manager: `rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863`
   - ✅ Update DATABASE_URL environment variable with correct password

4. **Check Lambda Layers**
   - ✅ Use `climate-risk-core-utilities:2` for DocumentIDManager
   - ✅ Use `database-dependencies:2` for PostgreSQL drivers

### Common Error Messages and Solutions

#### "Connection timed out"
- **Cause**: Lambda not in database subnets or missing security group rules
- **Solution**: Use database subnets and add security group rules

#### "Password authentication failed"
- **Cause**: Incorrect password in DATABASE_URL
- **Solution**: Get current password from Secrets Manager and update environment variable

#### "'DatabaseManager' object has no attribute 'get_document_metadata'"
- **Cause**: Wrong Lambda layer version
- **Solution**: Use `climate-risk-core-utilities:2` instead of `climate-risk-core-utilities-db:5`

#### "duplicate key value violates unique constraint"
- **Cause**: Document already exists in database (normal behavior)
- **Solution**: This is expected behavior, not an error

### Verification Commands

```bash
# Check Lambda VPC configuration
aws lambda get-function --function-name your-function-name --query 'Configuration.VpcConfig'

# Check security group rules
aws ec2 describe-security-groups --group-ids sg-048961fc0bd1504c5

# Get database password
aws secretsmanager get-secret-value --secret-id "rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863"

# Check Lambda layers
aws lambda get-function --function-name your-function-name --query 'Configuration.Layers'
```

---

## Quick Reference Card

### Essential IDs
- **VPC**: `vpc-051c21d88c7dc3819`
- **Database Subnets**: `subnet-0e9efc5fdf29e9da0`, `subnet-00efdcc220a613ae3`
- **Database Security Group**: `sg-09bc56a537bf7ac12`
- **Database Secret**: `rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863`
- **Core Utilities Layer**: `climate-risk-core-utilities:2`
- **Database Dependencies Layer**: `database-dependencies:2`

### Database Connection
```
postgresql://postgres:c0xfd_t#PBUqV(pLM-9IqM59G:>c@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require
```

### Account & Region
- **Account**: `861276078413`
- **Region**: `us-east-1`

---

*Last Updated: 2025-07-11*  
*Version: 1.0*
