# Climate Risk RAG Infrastructure Reference Guide

## Overview
This document provides comprehensive infrastructure mappings and configurations for the Climate Risk RAG system. Use this as a reference to ensure correct configuration on the first attempt when creating new Lambda functions, database connections, and other AWS resources.

**Last Updated:** August 5, 2025 - Post Knowledge Graph Layer Fix  
**Current Status:** Operational with corrected KG processing and dual-layer configuration

## Table of Contents
1. [VPC and Networking](#vpc-and-networking)
2. [Security Groups](#security-groups)
3. [Database Configuration](#database-configuration)
4. [OpenSearch Configuration](#opensearch-configuration)
5. [Lambda Configuration](#lambda-configuration)
6. [IAM Roles and Policies](#iam-roles-and-policies)
7. [Lambda Layers](#lambda-layers)
8. [S3 Buckets](#s3-buckets)
9. [Secrets Manager](#secrets-manager)
10. [Common Patterns](#common-patterns)
11. [Troubleshooting Checklist](#troubleshooting-checklist)

---

## VPC and Networking

### Primary VPC
- **VPC ID**: `vpc-051c21d88c7dc3819`
- **Name**: Climate Risk RAG VPC
- **Region**: `us-east-1`

### Subnet Configuration

#### Database Subnets (Use for Lambda functions that need PostgreSQL access)
- **Primary**: `subnet-0e9efc5fdf29e9da0`
- **Secondary**: `subnet-00efdcc220a613ae3`
- **Type**: Private subnets with database access
- **Use Case**: Lambda functions requiring PostgreSQL connectivity

#### Application/Neptune Subnets (General purpose + Neptune access)
- **Primary**: `subnet-03d8bd6cf3491f38c`
- **Secondary**: `subnet-0c0be1dd59f70f70e`
- **Type**: Private subnets with egress and S3 VPC endpoint access
- **Use Case**: Lambda functions requiring Neptune access, general processing
- **Special Features**: Enhanced routing for Neptune to reach S3 for bulk loading

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

#### Neptune Cluster Details (CURRENT)
- **Cluster Endpoint**: `solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com`
- **Reader Endpoint**: `solve-global-kr-neptune-s3.cluster-ro-cqhsckw0edl1.us-east-1.neptune.amazonaws.com`
- **Port**: `8182`
- **Engine**: `neptune`
- **Version**: Latest
- **Subnets**: `subnet-03d8bd6cf3491f38c`, `subnet-0c0be1dd59f70f70e` (Application/Neptune subnets)
- **Special Features**: Enhanced S3 access for bulk loading TTL files

#### Neptune Access Configuration

##### SPARQL Endpoint
```
https://solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182/sparql
```

##### Gremlin Endpoint
```
wss://solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182/gremlin
```

#### Lambda Environment Variables for Neptune

```python
environment={
    "NEPTUNE_ENDPOINT": "solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com",
    "NEPTUNE_PORT": "8182",
    "NEPTUNE_SPARQL_ENDPOINT": "https://solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182/sparql",
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

## OpenSearch Configuration

### Managed OpenSearch Domain (Cost-Optimized - CURRENT)
- **Domain Name**: `solve-global-kr-search`
- **Endpoint**: `https://vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com`
- **Version**: OpenSearch 2.19.0
- **Configuration**: 2-node m6g.large.search cluster
- **Cost**: ~$170/month (94% savings vs OpenSearch Serverless)
- **Network**: VPC access only (private)
- **Migration Date**: July 2025 (from OpenSearch Serverless)

### OpenSearch Cluster Details
- **Instance Type**: m6g.large.search
- **Node Count**: 2 (multi-AZ deployment)
- **Storage**: 20GB EBS gp3 per node (40GB total)
- **IOPS**: 3000 per volume
- **Throughput**: 125 MiB/s per volume
- **Subnets**: `subnet-0e9efc5fdf29e9da0`, `subnet-00efdcc220a613ae3` (database subnets)
- **Security Group**: `sg-09820dfa36321a5e1`

### Authentication Configuration
- **Method**: Basic Authentication (username/password)
- **Master Username**: `admin`
- **Master Password**: `veqpat-kegba2-zapbyZ`
- **Fine-grained Access Control**: Enabled
- **Encryption**: At rest, in transit, and node-to-node

### Dual Index Strategy

#### Documents Keyword Index (`documents_keyword`)
- **Purpose**: Document-level TF-IDF keyword search
- **Mapping**: Full document text with proper term frequency analysis
- **Analyzer**: Custom climate_analyzer with stemming and stop words
- **Fields**:
  - `doc_id` (keyword)
  - `title` (text with keyword field)
  - `content` (text with climate_analyzer)
  - `document_keywords` (keyword array)
  - `structure_info` (object with page/table counts)
  - `metadata` (object, not indexed)
  - `timestamp` (date)

#### Chunks Vector Index (`chunks_vector`)
- **Purpose**: Chunk-level semantic vector search with k-NN
- **Vector Dimension**: 1536 (Titan embeddings)
- **Vector Method**: HNSW with L2 distance
- **Fields**:
  - `chunk_id` (keyword)
  - `doc_id` (keyword) - Links chunks to documents
  - `chunk_index` (integer)
  - `text` (text)
  - `vector` (knn_vector with HNSW index)
  - `chunk_metadata` (object with page numbers, section types)
  - `embedding_metadata` (object with model info)
  - `timestamp` (date)

### Lambda Environment Variables for OpenSearch

```python
environment={
    "OPENSEARCH_ENDPOINT": "https://vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com",
    "OPENSEARCH_USERNAME": "admin",
    "OPENSEARCH_PASSWORD": "veqpat-kegba2-zapbyZ"
}
```

### OpenSearch Connection Pattern (Python)

```python
from opensearchpy import OpenSearch, RequestsHttpConnection

def create_opensearch_client():
    client = OpenSearch(
        hosts=[{'host': 'vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com', 'port': 443}],
        http_auth=('admin', 'veqpat-kegba2-zapbyZ'),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30,
        max_retries=3,
        retry_on_timeout=True
    )
    return client

# Test connection
client = create_opensearch_client()
info = client.info()
print(f"Connected to: {info.get('cluster_name')}")
```

### Security Group Configuration for OpenSearch

#### OpenSearch Security Group (`sg-09820dfa36321a5e1`)
- **Inbound Rules**:
  - TCP 443 from `sg-0c9e10b9cfb4c9eb0` (Lambda functions)
  - Description: "HTTPS from Lambda functions"

#### Lambda Functions Requiring OpenSearch Access
- **keyword-indexer**: Uses `documents_keyword` index
- **vector-embeddings-worker**: Uses `chunks_vector` index
- **Security Group**: `sg-0c9e10b9cfb4c9eb0`

### Index Management Commands

#### Create Documents Index
```python
documents_mapping = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
        "analysis": {
            "analyzer": {
                "climate_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "stop", "stemmer"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "doc_id": {"type": "keyword"},
            "title": {
                "type": "text",
                "analyzer": "climate_analyzer",
                "fields": {"keyword": {"type": "keyword"}}
            },
            "content": {"type": "text", "analyzer": "climate_analyzer"},
            "document_keywords": {"type": "keyword"},
            "structure_info": {
                "properties": {
                    "page_count": {"type": "integer"},
                    "table_count": {"type": "integer"},
                    "has_tables": {"type": "boolean"}
                }
            },
            "timestamp": {"type": "date"}
        }
    }
}

client.indices.create(index="documents_keyword", body=documents_mapping)
```

#### Create Chunks Vector Index
```python
chunks_mapping = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 100
        }
    },
    "mappings": {
        "properties": {
            "chunk_id": {"type": "keyword"},
            "doc_id": {"type": "keyword"},
            "chunk_index": {"type": "integer"},
            "text": {"type": "text", "analyzer": "standard"},
            "vector": {
                "type": "knn_vector",
                "dimension": 1536,
                "method": {
                    "name": "hnsw",
                    "space_type": "l2"
                }
            },
            "chunk_metadata": {
                "properties": {
                    "character_count": {"type": "integer"},
                    "page_numbers": {"type": "integer"},
                    "section_types": {"type": "keyword"}
                }
            },
            "timestamp": {"type": "date"}
        }
    }
}

client.indices.create(index="chunks_vector", body=chunks_mapping)
```

### Search Examples

#### Document-Level Keyword Search
```python
def search_documents(query_text, size=10):
    search_body = {
        "query": {
            "multi_match": {
                "query": query_text,
                "fields": ["title^2", "content", "document_keywords^1.5"],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        },
        "highlight": {
            "fields": {
                "content": {"fragment_size": 150, "number_of_fragments": 3},
                "title": {}
            }
        },
        "size": size
    }
    
    response = client.search(index="documents_keyword", body=search_body)
    return response['hits']['hits']
```

#### Chunk-Level Vector Search
```python
def search_chunks_by_vector(query_vector, size=10, doc_id_filter=None):
    search_body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "knn": {
                            "vector": {
                                "vector": query_vector,
                                "k": size
                            }
                        }
                    }
                ]
            }
        },
        "size": size
    }
    
    # Optional: Filter by specific document
    if doc_id_filter:
        search_body["query"]["bool"]["filter"] = [
            {"term": {"doc_id": doc_id_filter}}
        ]
    
    response = client.search(index="chunks_vector", body=search_body)
    return response['hits']['hits']
```

### Migration Notes

#### From OpenSearch Serverless (DEPRECATED)
- **Previous Collections**: 
  - `solve-global-kr-search-v2` (keyword) - DELETED
  - `solve-global-kr-vectors-v2` (vector) - DELETED
- **Cost Savings**: $1,500-2,200/month → $170/month (90-94% reduction)
- **Authentication Change**: AWS IAM → Basic authentication
- **Network Change**: Public serverless → VPC-private managed domain

#### Lambda Function Updates Required
- **Environment Variables**: Update `OPENSEARCH_ENDPOINT`, add `OPENSEARCH_USERNAME`/`OPENSEARCH_PASSWORD`
- **Authentication Code**: Replace AWS4Auth with basic authentication
- **Connection Class**: Continue using RequestsHttpConnection
- **Index Names**: Update to `documents_keyword` and `chunks_vector`

### Monitoring and Maintenance

#### CloudWatch Metrics
- **Cluster Health**: Monitor cluster status (green/yellow/red)
- **Storage Utilization**: Monitor EBS usage (currently 40GB total)
- **Search Latency**: Monitor query performance
- **Indexing Rate**: Monitor document ingestion

#### Scaling Considerations
- **Vertical Scaling**: Upgrade from m6g.large to m6g.xlarge if needed
- **Horizontal Scaling**: Add more nodes if search volume increases
- **Storage Scaling**: Increase EBS volume size as data grows
- **Regional Deployment**: Deploy in ap-southeast-1 for Singapore users

#### Backup and Recovery
- **Automated Snapshots**: Configured for 02:00 UTC daily
- **Manual Snapshots**: Available via AWS console or API
- **Cross-Region Backup**: Consider for production deployment

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

### SNS Topic Configuration

#### NLP Processing Topics

**Text Chunking Complete Topic**
```python
text_chunking_complete_topic = sns.Topic(
    self, "TextChunkingCompleteTopic", 
    topic_name="text-chunking-complete",
    display_name="Text Chunking Complete Topic"
)

# Subscribe nlp-initiator to chunks ready messages
text_chunking_complete_topic.add_subscription(
    sns_subscriptions.SqsSubscription(nlp_initiator_queue)
)
```

**NLP Jobs Submitted Topic (NEW - August 2025)**
```python
nlp_jobs_submitted_topic = sns.Topic(
    self, "NLPJobsSubmittedTopic",
    topic_name="nlp-jobs-submitted", 
    display_name="NLP Jobs Submitted Topic"
)

# Subscribe nlp-worker to jobs submitted messages
nlp_jobs_submitted_topic.add_subscription(
    sns_subscriptions.SqsSubscription(nlp_worker_queue)
)
```

**NLP Processing Complete Topic**
```python
nlp_processing_complete_topic = sns.Topic(
    self, "NLPProcessingCompleteTopic",
    topic_name="nlp-processing-complete",
    display_name="NLP Processing Complete Topic"
)
```

#### KG Integration Topics

**KG Triples Ready Topic**
```python
kg_triples_ready_topic = sns.Topic(
    self, "KGTriplesReadyTopic",
    topic_name="kg-triples-ready",
    display_name="KG Triples Ready Topic"
)

# Subscribe KG Integration Worker to the topic
kg_triples_ready_topic.add_subscription(
    sns_subscriptions.LambdaSubscription(kg_integration_worker)
)
```

### NLP Processing Lambda Functions

#### NLP Initiator Function
```python
nlp_initiator = _lambda.Function(
    self, "NLPInitiator",
    function_name="nlp-initiator",
    runtime=_lambda.Runtime.PYTHON_3_11,
    handler="handler.lambda_handler",
    code=_lambda.Code.from_asset("lambda/nlp-initiator"),
    timeout=Duration.minutes(5),
    memory_size=512,
    vpc=vpc,
    vpc_subnets=ec2.SubnetSelection(subnets=[
        ec2.Subnet.from_subnet_id(self, "NLPInitiatorSubnet1", "subnet-03d8bd6cf3491f38c"),
        ec2.Subnet.from_subnet_id(self, "NLPInitiatorSubnet2", "subnet-0c0be1dd59f70f70e")
    ]),
    security_groups=[nlp_security_group],
    layers=[database_core_layer, database_dependencies_layer],
    environment={
        "DATABASE_SECRET_NAME": database_secret.secret_name,
        "DB_HOST": database.cluster_endpoint.hostname,
        "DB_PORT": "5432",
        "DB_NAME": "climate_risk_rag",
        "COMPREHEND_REGION": "us-east-1",
        "COMPREHEND_OUTPUT_BUCKET": ner_results_bucket.bucket_name,
        "COMPREHEND_DATA_ACCESS_ROLE_ARN": comprehend_data_access_role.role_arn,
        "NLP_JOBS_SUBMITTED_TOPIC_ARN": nlp_jobs_submitted_topic.topic_arn
    }
)
```

#### NLP Worker Function  
```python
nlp_worker = _lambda.Function(
    self, "NLPWorker",
    function_name="nlp-worker", 
    runtime=_lambda.Runtime.PYTHON_3_11,
    handler="handler.lambda_handler",
    code=_lambda.Code.from_asset("lambda/nlp-worker"),
    timeout=Duration.minutes(15),
    memory_size=1024,
    vpc=vpc,
    vpc_subnets=ec2.SubnetSelection(subnets=[
        ec2.Subnet.from_subnet_id(self, "NLPWorkerSubnet1", "subnet-03d8bd6cf3491f38c"),
        ec2.Subnet.from_subnet_id(self, "NLPWorkerSubnet2", "subnet-0c0be1dd59f70f70e")
    ]),
    security_groups=[nlp_security_group],
    layers=[database_core_layer, database_dependencies_layer],
    environment={
        "DATABASE_SECRET_NAME": database_secret.secret_name,
        "DB_HOST": database.cluster_endpoint.hostname,
        "DB_PORT": "5432", 
        "DB_NAME": "climate_risk_rag",
        "COMPREHEND_REGION": "us-east-1",
        "NER_RESULTS_BUCKET": ner_results_bucket.bucket_name,
        "NLP_COMPLETION_TOPIC_ARN": nlp_processing_complete_topic.topic_arn
    }
)
```

#### Text Chunker Processor Function
```python
text_chunker_processor = _lambda.Function(
    self, "TextChunkerProcessor",
    function_name="text-chunker-processor",
    runtime=_lambda.Runtime.PYTHON_3_11,
    handler="handler.lambda_handler", 
    code=_lambda.Code.from_asset("lambda/text-chunker-processor"),
    timeout=Duration.minutes(10),
    memory_size=1024,
    vpc=vpc,
    vpc_subnets=ec2.SubnetSelection(subnets=[
        ec2.Subnet.from_subnet_id(self, "ChunkerSubnet1", "subnet-03d8bd6cf3491f38c"),
        ec2.Subnet.from_subnet_id(self, "ChunkerSubnet2", "subnet-0c0be1dd59f70f70e")
    ]),
    security_groups=[processing_security_group],
    layers=[database_core_layer, database_dependencies_layer],
    environment={
        "DATABASE_SECRET_NAME": database_secret.secret_name,
        "DB_HOST": database.cluster_endpoint.hostname,
        "DB_PORT": "5432",
        "DB_NAME": "climate_risk_rag", 
        "TEXT_BUCKET": text_bucket.bucket_name,
        "CHUNKS_BUCKET": chunks_bucket.bucket_name,
        "CHUNKS_READY_TOPIC_ARN": text_chunking_complete_topic.topic_arn
    }
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

### NLP Integration IAM Policy

#### Policy Document (Updated August 2025)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "comprehend:DetectEntities",
        "comprehend:DetectKeyPhrases", 
        "comprehend:StartEntitiesDetectionJob",
        "comprehend:StartKeyPhrasesDetectionJob",
        "comprehend:DescribeEntitiesDetectionJob",
        "comprehend:DescribeKeyPhrasesDetectionJob",
        "comprehend:ListEntitiesDetectionJobs",
        "comprehend:ListKeyPhrasesDetectionJobs"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject", 
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::solve-global-kr-*/*",
        "arn:aws:s3:::solve-global-kr-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": [
        "arn:aws:sns:us-east-1:861276078413:nlp-worker",
        "arn:aws:sns:us-east-1:861276078413:nlp-processing-complete",
        "arn:aws:sns:us-east-1:861276078413:comprehend-entity-completion",
        "arn:aws:sns:us-east-1:861276078413:comprehend-keyphrase-completion",
        "arn:aws:sns:us-east-1:861276078413:nlp-jobs-submitted"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ],
      "Resource": [
        "arn:aws:sqs:us-east-1:861276078413:nlp-worker-queue",
        "arn:aws:sqs:us-east-1:861276078413:nlp-worker-entity-queue", 
        "arn:aws:sqs:us-east-1:861276078413:nlp-worker-keyphrase-queue"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": "arn:aws:iam::861276078413:role/comprehend-data-access-role"
    }
  ]
}
```

#### CDK Policy Creation
```python
nlp_integration_policy = iam.ManagedPolicy(
    self, "NLPIntegrationPolicy",
    managed_policy_name="nlp-integration-policy",
    description="Policy for NLP integration Lambda functions",
    document=iam.PolicyDocument.from_json(nlp_policy_document)
)

# Attach to NLP Lambda role
nlp_lambda_role.add_managed_policy(nlp_integration_policy)
```

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

### Available Layers (CURRENT VERSIONS)

#### Knowledge Graph Layer (CORRECTED - v30)
- **ARN**: `arn:aws:lambda:us-east-1:861276078413:layer:knowledge-graph-layer:30`
- **Contents**: rdflib 7.1.4, isodate 0.7.2, requests-aws4auth, KG processing utilities
- **Size**: 16.5MB (32 packages)
- **Use Case**: Functions requiring knowledge graph processing and RDF operations
- **Build Script**: `layers/knowledge-graph-layer/build_layer.sh` (ONLY use this script)
- **Critical Fix**: Proper `/python/` directory structure, explicit isodate dependency

#### Database Core Layer (STABLE - v17)
- **ARN**: `arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities:17`
- **Contents**: DatabaseManager, PostgreSQL drivers, core utilities
- **Size**: 17.3MB
- **Use Case**: Functions requiring database connectivity and document ID management

#### Dual Layer Requirement for KG Functions
**CRITICAL**: Knowledge graph functions MUST have BOTH layers:
```python
layers=[
    lambda_.LayerVersion.from_layer_version_arn(
        self, "KnowledgeGraphLayer",
        layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:knowledge-graph-layer:30"
    ),
    lambda_.LayerVersion.from_layer_version_arn(
        self, "DatabaseLayer",
        layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:climate-risk-core-utilities:17"
    )
]
```

### Layer Build Standards (CRITICAL)
- **Python Version**: ALWAYS use `python3` command, never `python`
- **Build Script**: Use ONLY `layers/knowledge-graph-layer/build_layer.sh`
- **Structure Validation**: ALWAYS verify `/python/` directory structure before deployment
- **Testing**: Run end-to-end pipeline test after layer updates
- **CDK Sync**: Update CDK layer references immediately after deployment

### Current KG Functions Using Dual Layers
- **document-structure-kg-processor**: Processes document structure, generates RDF triples
- **kg-triple-loader**: Loads TTL files into Neptune graph database

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

### Core Buckets (CURRENT)
- **Source Documents**: `solve-global-kr-dl-source-861276078413-us-east-1`
- **Text**: `solve-global-kr-dl-text-861276078413-us-east-1`
- **Chunks**: `solve-global-kr-dl-chunks-861276078413-us-east-1`
- **Neptune TTL**: `solve-global-kr-dl-neptune-ttl-861276078413-us-east-1` (KG triples)
- **Cache**: `solve-global-kr-cache-861276078413-us-east-1`

### Environment Variables Pattern

```python
environment={
    "SOURCE_DOCUMENTS_BUCKET": f"solve-global-kr-dl-source-{self.account}-{self.region}",
    "TEXT_BUCKET": f"solve-global-kr-dl-text-{self.account}-{self.region}",
    "CHUNKS_BUCKET": f"solve-global-kr-dl-chunks-{self.account}-{self.region}",
    "TTL_BUCKET": f"solve-global-kr-dl-neptune-ttl-{self.account}-{self.region}"
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

*Last Updated: 2025-08-05 (Knowledge Graph Layer Fixed - v30 Deployed)*  
*Version: 3.0*  
*Status: Operational with corrected KG processing and dual-layer configuration*
