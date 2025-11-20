# Climate Risk RAG System - Infrastructure Stacks Guide

**Last Updated:** August 5, 2025  
**Status:** Operational with Knowledge Graph Layer v30 and Managed OpenSearch  
**Architecture:** Event-driven serverless microservices on AWS

## 🏗️ **Overview**

The Climate Risk RAG system is built using AWS CDK with a modular stack architecture that creates a complete serverless microservices platform. The system has evolved from OpenSearch Serverless to managed OpenSearch (94% cost savings) and now includes corrected knowledge graph processing with proper dual-layer Lambda configuration.

## 📊 **Current Architecture & Key Updates**

### **Recent Major Changes (2025)**
- **Knowledge Graph Layer Fixed**: Corrected rdflib import issues with proper `/python/` structure
- **OpenSearch Migration**: Moved from Serverless ($1,500-2,200/month) to Managed ($170/month)
- **Neptune Enhancement**: New cluster with S3 bulk loading capabilities
- **Dual Layer Configuration**: KG functions now require both KG and database layers
- **Cost Optimization**: 90-94% reduction in search infrastructure costs

## 📊 **Stack Architecture & Dependencies**

```mermaid
graph TD
    A[NetworkingStack] --> B[DataLakeStack]
    A --> C[DataStack]
    D[AiMlStack] --> E[MicroservicesComputeStack]
    B --> E
    C --> E
    
    A --> F[VPC, Subnets, Security Groups]
    B --> G[7 S3 Buckets + Lifecycle Policies]
    C --> H[OpenSearch, Neptune, RDS]
    D --> I[Bedrock, IAM Roles, AI/ML Permissions]
    E --> J[11 Lambda Functions, API Gateway, Step Functions]
```

## 🔧 **Stack Details**

### **1. NetworkingStack** 
**File:** `cdk/stacks/networking_stack.py`  
**Purpose:** Foundation networking infrastructure

#### **Resources Created:**
```yaml
VPC Configuration:
  - CIDR: 10.0.0.0/16
  - Availability Zones: 2
  - DNS Support: Enabled
  
Subnets (per AZ):
  - Public Subnet: /24 (for NAT Gateways, Load Balancers)
  - Private Subnet: /24 (for Lambda functions, databases)
  - Isolated Subnet: /24 (for highly secure resources)

Security Groups:
  - Lambda Security Group: Outbound HTTPS, database access
  - Database Security Group: Inbound from Lambda SG only
  - OpenSearch Security Group: Port 443 from Lambda SG
```

#### **Key Features:**
- **Multi-AZ Design:** High availability across 2 availability zones
- **Layered Security:** Public, private, and isolated subnet tiers
- **Least Privilege:** Security groups with minimal required access
- **DNS Resolution:** Enabled for service discovery

#### **Outputs:**
- VPC ID and ARN
- Subnet IDs for each tier
- Security Group IDs
- NAT Gateway IPs

---

### **2. DataLakeStack**
**File:** `cdk/stacks/data_lake_stack.py`  
**Purpose:** S3-based data lake for document processing pipeline

#### **Resources Created:**
```yaml
S3 Buckets (7 total):
  1. documents-bucket: Raw PDF/document uploads
  2. extracted-text-bucket: Textract output
  3. chunks-bucket: Processed text chunks
  4. embeddings-bucket: Vector embeddings
  5. ner-results-bucket: Named entity recognition results
  6. knowledge-graph-data-bucket: Graph data exports
  7. query-cache-bucket: Cached query results

Lifecycle Policies:
  - Transition to IA after 30 days
  - Archive to Glacier after 90 days
  - Delete old versions after 365 days
```

#### **Key Features:**
- **Event-Driven Architecture:** S3 events trigger Lambda processing
- **Cost Optimization:** Intelligent tiering and lifecycle policies
- **Security:** Server-side encryption, block public access
- **Versioning:** Enabled for data protection and rollback
- **Cross-Region Replication:** Optional for disaster recovery

#### **Bucket Structure:**
```
documents-bucket/
├── documents/           # Raw uploads
├── failed/             # Processing failures
└── archive/            # Completed processing

extracted-text-bucket/
├── extracted_text/     # Textract JSON output
└── metadata/          # Processing metadata

chunks-bucket/
├── chunks/            # Individual text chunks
└── summaries/         # Document summaries

embeddings-bucket/
├── vectors/           # Titan embeddings
└── indices/          # OpenSearch index data

ner-results-bucket/
├── entities/         # Extracted entities
├── relationships/    # Entity relationships
└── summaries/       # NER processing summaries
```

---

### **3. DataStack**
**File:** `cdk/stacks/data_stack.py`  
**Purpose:** Managed databases for search, knowledge graph, and metadata

#### **Resources Created:**
```yaml
Managed OpenSearch Domain (CURRENT):
  - Domain: solve-global-kr-search
  - Endpoint: vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com
  - Version: OpenSearch 2.19.0
  - Instance Type: m6g.large.search (2 nodes)
  - Storage: 20GB EBS gp3 per node
  - Cost: ~$170/month (94% savings vs Serverless)
  - Authentication: Basic auth (admin/veqpat-kegba2-zapbyZ)
  - Network: VPC private access only

Neptune Graph Database (ENHANCED):
  - Cluster: solve-global-kr-neptune-s3
  - Endpoint: solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com
  - Instance: db.t3.medium (cost-optimized)
  - Multi-AZ: Enabled for HA
  - Backup: 7-day retention
  - Special Features: Enhanced S3 access for TTL bulk loading
  - Subnets: Application/Neptune subnets with S3 VPC endpoint routing

RDS PostgreSQL (STABLE):
  - Endpoint: solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com
  - Instance: db.t3.micro (cost-optimized)
  - Storage: 20GB GP2 with auto-scaling
  - Backup: 7-day retention
  - Security: Encrypted at rest and in transit
```

#### **Database Purposes:**
- **OpenSearch:** Dual-index strategy (documents_keyword + chunks_vector) for hybrid search
- **Neptune:** Knowledge graph storage with RDF triples and SPARQL queries
- **RDS:** Document metadata, processing status, pipeline coordination

#### **Migration Notes:**
```yaml
OpenSearch Serverless → Managed OpenSearch (July 2025):
  - Cost Reduction: $1,500-2,200/month → $170/month
  - Authentication: AWS IAM → Basic username/password
  - Network: Public serverless → VPC private domain
  - Performance: Variable → Consistent dedicated instances
```

#### **Security Configuration:**
```python
# Database access restricted to Lambda security group
database_security_group.add_ingress_rule(
    peer=lambda_security_group,
    connection=ec2.Port.tcp(5432),  # PostgreSQL
    description="Lambda access to RDS"
)

database_security_group.add_ingress_rule(
    peer=lambda_security_group,
    connection=ec2.Port.tcp(8182),  # Neptune
    description="Lambda access to Neptune"
)
```

---

### **4. AiMlStack**
**File:** `cdk/stacks/ai_ml_stack.py`  
**Purpose:** AI/ML service permissions and configurations

#### **Resources Created:**
```yaml
IAM Role: AiMlServiceRole
  Permissions:
    - Bedrock: InvokeModel, ListFoundationModels
    - Textract: DetectDocumentText, AnalyzeDocument
    - Comprehend: DetectEntities, DetectSentiment
    - Titan: Embedding generation
    - Lambda: VPC execution role

Bedrock Model Access:
  - Claude 3 Haiku: Fast responses
  - Claude 3 Sonnet: Balanced performance
  - Titan Text Express: Embeddings
  - Titan Embeddings: Vector generation
```

#### **Service Configurations:**
```python
# Bedrock permissions for LLM access
bedrock_policy = iam.PolicyStatement(
    effect=iam.Effect.ALLOW,
    actions=[
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:ListFoundationModels"
    ],
    resources=[
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-*",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-*",
        "arn:aws:bedrock:*::foundation-model/amazon.titan-*"
    ]
)

# Textract permissions for document processing
textract_policy = iam.PolicyStatement(
    effect=iam.Effect.ALLOW,
    actions=[
        "textract:DetectDocumentText",
        "textract:AnalyzeDocument",
        "textract:GetDocumentAnalysis"
    ],
    resources=["*"]
)
```

---

### **5. ComputeStack** (Legacy)
**File:** `cdk/stacks/compute_stack.py`  
**Status:** Superseded by MicroservicesComputeStack
**Purpose:** Original monolithic compute design (kept for reference)

---

### **6. MicroservicesComputeStack** (Primary)
**File:** `cdk/stacks/microservices_compute_stack.py`  
**Purpose:** Complete microservices compute infrastructure

#### **Resources Created:**
```yaml
Lambda Functions (Current Active Functions):
  Document Processing Pipeline:
    - text-extractor: Textract integration
    - text-chunker: Structured chunking
    - keyword-indexer: OpenSearch document indexing
    - vector-embeddings: Titan embeddings + OpenSearch chunks
    - document-structure-kg-processor: Knowledge graph processing (DUAL LAYERS)
    - kg-triple-loader: Neptune TTL loading (DUAL LAYERS)

  Utility Functions:
    - pipeline-test-function: End-to-end testing
    - document-validator: Input validation

Lambda Layer Configuration (CRITICAL):
  Knowledge Graph Functions Require BOTH:
    - knowledge-graph-layer:30 (rdflib 7.1.4, isodate 0.7.2)
    - climate-risk-core-utilities:17 (DatabaseManager)

API Gateway:
  - REST API: Climate Risk RAG API
  - Endpoints: /query (POST), /health (GET)
  - Authentication: API keys
  - CORS: Enabled for web applications
```

#### **Knowledge Graph Lambda Functions (Updated):**

| **Function** | **Runtime** | **Memory** | **Timeout** | **Layers** | **Subnets** |
|--------------|-------------|------------|-------------|------------|-------------|
| document-structure-kg-processor | Python 3.11 | 1024 MB | 5 min | KG:30 + DB:17 | Application/Neptune |
| kg-triple-loader | Python 3.11 | 1024 MB | 15 min | KG:30 + DB:17 | Application/Neptune |

#### **Critical Configuration Requirements:**
```python
# Knowledge Graph Functions MUST have both layers
kg_function = lambda_.Function(
    self, "KGFunction",
    layers=[
        lambda_.LayerVersion.from_layer_version_arn(
            self, "KnowledgeGraphLayer",
            layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:knowledge-graph-layer:30"
        ),
        lambda_.LayerVersion.from_layer_version_arn(
            self, "DatabaseLayer", 
            layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:climate-risk-core-utilities:17"
        )
    ],
    vpc_subnets=ec2.SubnetSelection(subnets=[
        ec2.Subnet.from_subnet_id(self, "NeptuneSubnet1", subnet_id="subnet-03d8bd6cf3491f38c"),
        ec2.Subnet.from_subnet_id(self, "NeptuneSubnet2", subnet_id="subnet-0c0be1dd59f70f70e")
    ]),
    environment={
        "NEPTUNE_ENDPOINT": "solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com",
        "NEPTUNE_PORT": "8182",
        "TTL_BUCKET": "solve-global-kr-dl-neptune-ttl-861276078413-us-east-1"
    }
)
```

#### **Event Triggers Configuration:**
```python
# S3 Event Triggers (Document Processing)
documents_bucket.add_event_notification(
    s3n.EventType.OBJECT_CREATED,
    s3n.LambdaDestination(text_extractor),
    s3n.NotificationKeyFilter(prefix="documents/", suffix=".pdf")
)

extracted_text_bucket.add_event_notification(
    s3n.EventType.OBJECT_CREATED,
    s3n.LambdaDestination(text_chunker),
    s3n.NotificationKeyFilter(prefix="extracted_text/", suffix=".txt")
)

# API Gateway Integration
query_resource = api.root.add_resource("query")
query_integration = apigateway.StepFunctionsIntegration(
    state_machine=query_workflow
)
query_resource.add_method("POST", query_integration)
```

## 🚀 **Deployment Guide**

### **Prerequisites**
```bash
# Install AWS CDK
npm install -g aws-cdk

# Install Python dependencies
pip install -r requirements.txt

# Configure AWS credentials
aws configure

# Bootstrap CDK (first time only)
cdk bootstrap

# CRITICAL: Always use python3
python3 --version  # Verify Python 3.x
```

### **Deployment Commands**

#### **1. Deploy All Stacks (Recommended)**
```bash
cd cdk/
cdk deploy --all --require-approval never
```

#### **2. Deploy Individual Stacks (Advanced)**
```bash
# Deploy in dependency order
cdk deploy climate-risk-rag-networking
cdk deploy climate-risk-rag-data-lake  
cdk deploy climate-risk-rag-data
cdk deploy climate-risk-rag-ai-ml
cdk deploy climate-risk-rag-microservices-compute
```

#### **3. Layer Management (CRITICAL)**
```bash
# Build knowledge graph layer (ONLY use this script)
cd layers/knowledge-graph-layer
./build_layer.sh

# Deploy layer manually if needed
aws lambda publish-layer-version \
  --layer-name knowledge-graph-layer \
  --zip-file fileb://knowledge-graph-layer-v1.0.2.zip \
  --compatible-runtimes python3.11 python3.12

# Update CDK with new layer version immediately
# Edit cdk/app.py to reference new layer version
```

### **Post-Deployment Validation**
```bash
# Test pipeline with single document (ALWAYS BE FRUGAL)
python3 invoke_pipeline_test.py --num-documents 1 --max-size-mb 4

# Check Lambda function configurations
aws lambda get-function --function-name document-structure-kg-processor
aws lambda get-function --function-name kg-triple-loader

# Verify dual layer configuration
aws lambda get-function --function-name document-structure-kg-processor \
  --query 'Configuration.Layers[*].Arn'
```

## 🔧 **Operations Guide**

### **Monitoring & Logging**

#### **CloudWatch Dashboards**
Each stack creates CloudWatch resources:
```yaml
Networking Stack:
  - VPC Flow Logs
  - NAT Gateway metrics

Data Lake Stack:
  - S3 bucket metrics
  - Object count and size tracking

Data Stack:
  - OpenSearch cluster health
  - Neptune performance metrics
  - RDS connection and query metrics

Microservices Stack:
  - Lambda function metrics (duration, errors, invocations)
  - API Gateway request metrics
  - Step Functions execution metrics
```

#### **Log Groups**
```bash
# Lambda function logs
/aws/lambda/climate-risk-text-extractor
/aws/lambda/climate-risk-query-analyzer
/aws/lambda/climate-risk-response-generator

# API Gateway logs
/aws/apigateway/climate-risk-microservices-api

# Step Functions logs
/aws/stepfunctions/climate-risk-query-workflow
```

### **Scaling Configuration**

#### **Lambda Scaling**
```python
# Reserved concurrency for critical functions
text_extractor.add_environment("RESERVED_CONCURRENCY", "50")
query_analyzer.add_environment("RESERVED_CONCURRENCY", "100")

# Provisioned concurrency for low latency
query_analyzer.add_provisioned_concurrency_config(
    provisioned_concurrent_executions=10
)
```

#### **Database Scaling**
```yaml
OpenSearch:
  - Auto-scaling: Enabled
  - Min instances: 1
  - Max instances: 3
  - Target utilization: 70%

Neptune:
  - Read replicas: 1-2 based on load
  - Instance scaling: Manual upgrade

RDS:
  - Auto-scaling storage: Enabled
  - Max storage: 100GB
  - Read replicas: Optional
```

### **Security Management**

#### **IAM Roles & Policies**
```bash
# View Lambda execution role
aws iam get-role --role-name climate-risk-rag-microservices-compute-*

# Check policy attachments
aws iam list-attached-role-policies --role-name <role-name>

# Review security groups
aws ec2 describe-security-groups --group-names climate-risk-*
```

#### **Encryption Status**
```yaml
S3 Buckets: SSE-S3 encryption enabled
RDS: Encryption at rest enabled
Neptune: Encryption at rest enabled
OpenSearch: Encryption at rest and in transit
Lambda: Environment variables encrypted with KMS
```

### **Cost Optimization**

#### **Resource Right-Sizing**
```yaml
Development Environment:
  Neptune: db.t3.medium
  RDS: db.t3.micro
  Lambda: 512MB-1024MB memory
  OpenSearch: Serverless (on-demand)

Production Environment:
  Neptune: db.r5.large (if needed)
  RDS: db.t3.small with read replicas
  Lambda: Provisioned concurrency for critical functions
  OpenSearch: Dedicated instances for consistent performance
```

#### **Cost Monitoring**
```bash
# Check monthly costs by service
aws ce get-cost-and-usage \
  --time-period Start=2024-07-01,End=2024-07-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE

# Set up billing alerts
aws budgets create-budget \
  --account-id <account-id> \
  --budget file://budget-config.json
```

## 🔍 **Troubleshooting Guide**

### **Common Issues**

#### **1. Stack Deployment Failures**
```bash
# Check CloudFormation events
aws cloudformation describe-stack-events --stack-name <stack-name>

# Common fixes
cdk destroy <stack-name>  # Remove failed stack
cdk deploy <stack-name>   # Redeploy

# Dependency issues
cdk deploy --all --concurrency 1  # Deploy sequentially
```

#### **2. Lambda Function Errors**
```bash
# Check function logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/climate-risk-text-extractor \
  --start-time $(date -d '1 hour ago' +%s)000

# Common issues:
# - VPC configuration (check security groups)
# - IAM permissions (check execution role)
# - Memory/timeout limits
# - Environment variables
```

#### **3. Database Connection Issues**
```bash
# Test Neptune connectivity
aws neptune describe-db-clusters

# Test RDS connectivity
aws rds describe-db-instances

# Check security group rules
aws ec2 describe-security-groups --group-ids <sg-id>
```

#### **4. S3 Event Trigger Issues**
```bash
# Check bucket notifications
aws s3api get-bucket-notification-configuration --bucket <bucket-name>

# Verify Lambda permissions
aws lambda get-policy --function-name <function-name>

# Test trigger manually
aws lambda invoke \
  --function-name climate-risk-text-extractor \
  --payload file://test-event.json \
  response.json
```

### **Performance Tuning**

#### **Lambda Optimization**
```python
# Memory allocation based on function type
text_extractor: 1024MB      # CPU-intensive Textract processing
embedding_generator: 1024MB # Memory for vector operations
query_analyzer: 512MB       # Lightweight NLP processing
response_generator: 1024MB  # LLM response generation
```

#### **Database Optimization**
```sql
-- RDS PostgreSQL indexes
CREATE INDEX idx_documents_status ON documents(processing_status);
CREATE INDEX idx_chunks_doc_id ON chunks(document_id);
CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat(vector);

-- Neptune graph optimization
// Create property indexes for frequent queries
:property-index create --label Document --property-key title
:property-index create --label Entity --property-key type
```

## 📋 **Stack Summary**

| **Stack** | **Primary Purpose** | **Key Resources** | **Dependencies** |
|-----------|--------------------|--------------------|------------------|
| **NetworkingStack** | Foundation networking | VPC, Subnets, Security Groups | None |
| **DataLakeStack** | Document storage pipeline | 7 S3 Buckets + Lifecycle | NetworkingStack |
| **DataStack** | Managed databases | OpenSearch, Neptune, RDS | NetworkingStack |
| **AiMlStack** | AI/ML service access | IAM Roles, Bedrock Config | None |
| **MicroservicesComputeStack** | Application logic | 11 Lambdas, API Gateway, Step Functions | All others |

### **Total Resource Count**
- **Lambda Functions:** 11
- **S3 Buckets:** 7
- **Databases:** 3 (OpenSearch, Neptune, RDS)
- **API Endpoints:** 2 (/query, /health)
- **Step Functions:** 1 (query processing workflow)
- **IAM Roles:** 5+
- **Security Groups:** 4

### **Estimated Monthly Costs (Updated August 2025)**
```yaml
Development Environment: $200-250/month
  - Lambda: $30-50 (includes KG processing)
  - S3: $20-30
  - OpenSearch Managed: $170 (was $1,500+ serverless)
  - Neptune: $30-50
  - RDS: $15-25
  - Other: $15-25

Production Environment: $350-500/month
  - Higher instance sizes
  - Read replicas
  - Provisioned concurrency
  - Enhanced monitoring
  - Multi-AZ deployments

Cost Savings Achieved:
  - OpenSearch: 90-94% reduction ($1,500-2,200 → $170)
  - Overall Infrastructure: ~75% cost reduction
```

### **Cost Management Best Practices**
```yaml
Testing Protocol:
  - ALWAYS use single document tests: --num-documents 1 --max-size-mb 4
  - Monitor Textract usage: ~$0.0015 per page processed
  - Track Comprehend costs when implemented
  - Monitor Titan embedding generation costs

Resource Optimization:
  - Use t3.micro/small instances for development
  - Enable auto-scaling for production
  - Implement lifecycle policies for S3 storage
  - Monitor and right-size Lambda memory allocation
```

---

## 📋 **Current System Status**

| **Component** | **Status** | **Version/Config** | **Notes** |
|---------------|------------|-------------------|-----------|
| **Knowledge Graph Layer** | ✅ Operational | v30 (corrected) | Fixed rdflib imports, dual-layer config |
| **OpenSearch** | ✅ Operational | Managed 2.19.0 | 94% cost savings vs Serverless |
| **Neptune** | ✅ Operational | solve-global-kr-neptune-s3 | Enhanced S3 bulk loading |
| **Pipeline** | ✅ Operational | End-to-end tested | Single document test successful |
| **Cost Optimization** | ✅ Achieved | ~75% reduction | Major savings on search infrastructure |

### **Total Resource Count (Current)**
- **Lambda Functions:** 8+ active
- **S3 Buckets:** 5 core buckets
- **Databases:** 3 (OpenSearch, Neptune, RDS)
- **Lambda Layers:** 2 (KG + Database)
- **Security Groups:** 4
- **Subnets:** 4 (2 database, 2 application/Neptune)

---

*Last Updated: August 5, 2025*  
*Status: Operational with Knowledge Graph Layer v30 and Managed OpenSearch*  
*Architecture: Event-driven serverless microservices with 75% cost optimization*
