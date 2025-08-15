# Neptune-FTS Integration - Next Steps Implementation Guide
**Date**: August 6, 2025, 19:30:00 UTC  
**Estimated Time**: 6-8 hours (dedicated session recommended)  
**Cost Impact**: +$12-28/month additional AWS costs

## 🎯 **IMPLEMENTATION OVERVIEW**

### **Objective**
Deploy Neptune-OpenSearch full-text search integration using a customized CloudFormation stack optimized for ontology-focused, cost-effective operation.

### **Approach**
**Hybrid CloudFormation Strategy**: Use AWS-provided CloudFormation template with custom modifications for selective ontology indexing and cost optimization.

### **Expected Outcome**
- ✅ Working `neptune-fts:query()` function in SPARQL queries
- ✅ OntologyManager methods return FTS results from Neptune
- ✅ Ontology data automatically indexed, document data filtered out
- ✅ Monthly costs controlled under $30 additional

## 📋 **PHASE 1: ENABLE NEPTUNE STREAMS** (30-45 minutes)

### **Step 1.1: Enable Neptune Streams**
```bash
1. Enable Neptune Streams Parameter: ✅ DONE
bash
   # Set neptune_streams = 1 in parameter group
   aws neptune modify-db-cluster-parameter-group \
       --db-cluster-parameter-group-name solve-global-kr-neptune-s3-cluster-params \
       --parameters ParameterName=neptune_streams,ParameterValue=1,ApplyMethod=pending-reboot
   


2. Reboot Neptune Instance: ✅ IN PROGRESS
  bash
   # Reboot to apply streams parameter
   aws neptune reboot-db-instance \
       --db-instance-identifier solve-global-kr-neptune-s3-instance

```

### **Step 1.2: Verify Stream Endpoint**
```bash
# Get the stream endpoint URL (needed for CloudFormation)
NEPTUNE_ENDPOINT="solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
STREAM_ENDPOINT="https://${NEPTUNE_ENDPOINT}:8182/sparql/stream"
echo "Stream Endpoint: $STREAM_ENDPOINT"
```

### **Step 1.3: Test Stream Accessibility**
```bash
# Test stream endpoint accessibility (should return stream metadata)
curl -X GET "$STREAM_ENDPOINT" \
    --aws-sigv4 "aws:amz:us-east-1:neptune-db" \
    --user "$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY"
```

### **Expected Results**
- ✅ Neptune cluster shows `EnabledCloudwatchLogsExports: ["audit"]`
- ✅ Stream endpoint responds with stream metadata
- ✅ No errors in Neptune cluster logs

## 📋 **PHASE 2: PREPARE CLOUDFORMATION DEPLOYMENT** (45-60 minutes)

### **Step 2.1: Download CloudFormation Template**
```bash
# Create deployment directory
mkdir -p /Users/chris/climate-risk-rag-aws/neptune-fts-deployment
cd /Users/chris/climate-risk-rag-aws/neptune-fts-deployment

# Download the Neptune-to-OpenSearch CloudFormation template
curl -o neptune-to-opensearch-stack.json \
    "https://s3.amazonaws.com/aws-neptune-customer-samples/neptune-stream/neptune_to_es_via_streams.json"
```

### **Step 2.2: Create Optimized Parameters File**
```yaml
# File: neptune-fts-parameters.yaml
Parameters:
  # Network Configuration (Use existing infrastructure)
  VPC: vpc-051c21d88c7dc3819
  SubnetIds: 
    - subnet-00efdcc220a613ae3  # Database subnet 1
    - subnet-0e9efc5fdf29e9da0   # Database subnet 2
  SecurityGroupIds:
    - sg-0c9e10b9cfb4c9eb0      # Lambda security group
    - sg-09820dfa36321a5e1      # OpenSearch security group
  RouteTableIds: "rtb-0123456789abcdef0,rtb-0987654321fedcba0"  # Get actual route table IDs

  # Stream Poller (Cost-optimized for ontology updates)
  ApplicationName: "NeptuneOntologyFTS"
  LambdaMemorySize: 1024                    # Reduced from default 2048
  StreamRecordsBatchSize: 5000              # Maximum efficiency
  MaxPollingWaitTime: 600                   # 10 minutes (vs 60 seconds default)
  MaxPollingInterval: 900                   # Maximum timeout
  StepFunctionFallbackPeriod: 15            # 15 minutes (vs 5 minutes default)
  StepFunctionFallbackPeriodUnit: "minutes"

  # Neptune Stream Configuration
  NeptuneStreamEndpoint: "https://solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182/sparql/stream"
  QueryEngine: "Sparql"
  IAMAuthEnabledOnSourceStream: "false"
  StreamDBClusterResourceId: ""             # Not needed for non-IAM auth

  # Target OpenSearch (Use existing domain)
  ElasticSearchEndpoint: "vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com"
  NumberOfShards: 2                         # Reduced from default 5
  NumberOfReplica: 1                        # Keep default
  
  # Ontology-focused filtering
  PropertiesToExclude: "document_content,chunk_text,extracted_text,file_content"
  DatatypesToExclude: ""                    # Keep all ontology datatypes
  EnableNonStringIndexing: "true"           # Keep full capability
  ReplicationScope: "All"                   # Include all RDF data types
  IgnoreMissingDocument: "true"             # Handle missing docs gracefully

  # VPC Endpoints (Use existing if available)
  CreateDDBVPCEndPoint: "false"             # Check if already exists
  CreateMonitoringEndPoint: "false"         # Check if already exists

  # Monitoring (Minimal for cost control)
  CreateCloudWatchAlarm: "false"            # Skip alarms initially
  NotificationSNSTopicArn: ""
  NotificationEmail: ""
```

### **Step 2.3: Verify Route Table IDs**
```bash
# Get actual route table IDs for database subnets
aws ec2 describe-route-tables \
    --filters "Name=association.subnet-id,Values=subnet-00efdcc220a613ae3,subnet-0e9efc5fdf29e9da0" \
    --query 'RouteTables[*].RouteTableId' \
    --output text
```

### **Step 2.4: Check Existing VPC Endpoints**
```bash
# Check if DynamoDB VPC endpoint exists
aws ec2 describe-vpc-endpoints \
    --filters "Name=vpc-id,Values=vpc-051c21d88c7dc3819" "Name=service-name,Values=com.amazonaws.us-east-1.dynamodb" \
    --query 'VpcEndpoints[*].VpcEndpointId'

# Check if monitoring VPC endpoint exists  
aws ec2 describe-vpc-endpoints \
    --filters "Name=vpc-id,Values=vpc-051c21d88c7dc3819" "Name=service-name,Values=com.amazonaws.us-east-1.monitoring" \
    --query 'VpcEndpoints[*].VpcEndpointId'
```

## 📋 **PHASE 3: DEPLOY CLOUDFORMATION STACK** (60-90 minutes)

### **Step 3.1: Validate CloudFormation Template**
```bash
# Validate template syntax
aws cloudformation validate-template \
    --template-body file://neptune-to-opensearch-stack.json

# Estimate costs (optional)
aws cloudformation estimate-template-cost \
    --template-body file://neptune-to-opensearch-stack.json \
    --parameters file://neptune-fts-parameters.yaml
```

### **Step 3.2: Deploy CloudFormation Stack**
```bash
# Deploy the stack
aws cloudformation create-stack \
    --stack-name neptune-ontology-fts \
    --template-body file://neptune-to-opensearch-stack.json \
    --parameters file://neptune-fts-parameters.yaml \
    --capabilities CAPABILITY_IAM \
    --on-failure ROLLBACK

# Monitor deployment progress
aws cloudformation describe-stacks \
    --stack-name neptune-ontology-fts \
    --query 'Stacks[0].StackStatus'
```

### **Step 3.3: Monitor Deployment**
```bash
# Watch stack events (run in separate terminal)
watch -n 30 'aws cloudformation describe-stack-events \
    --stack-name neptune-ontology-fts \
    --query "StackEvents[0:5].[Timestamp,ResourceStatus,ResourceType,LogicalResourceId]" \
    --output table'

# Check for completion (typically 15-30 minutes)
aws cloudformation wait stack-create-complete \
    --stack-name neptune-ontology-fts
```

### **Expected Results**
- ✅ Stack status: `CREATE_COMPLETE`
- ✅ Lambda poller function created and running
- ✅ DynamoDB lease table created
- ✅ Step Functions state machine operational
- ✅ OpenSearch indices being populated

## 📋 **PHASE 4: CUSTOMIZE FOR ONTOLOGY-ONLY INDEXING** (90-120 minutes)

### **Step 4.1: Identify Lambda Poller Function**
```bash
# Get Lambda function name from CloudFormation outputs
LAMBDA_FUNCTION_NAME=$(aws cloudformation describe-stacks \
    --stack-name neptune-ontology-fts \
    --query 'Stacks[0].Outputs[?OutputKey==`NeptuneStreamPollerLambdaArn`].OutputValue' \
    --output text | cut -d':' -f7)

echo "Lambda Function: $LAMBDA_FUNCTION_NAME"
```

### **Step 4.2: Download Current Lambda Code**
```bash
# Download the Lambda function code for modification
aws lambda get-function \
    --function-name $LAMBDA_FUNCTION_NAME \
    --query 'Code.Location' \
    --output text | xargs curl -o lambda-code.zip

# Extract and examine
unzip lambda-code.zip -d lambda-code/
ls -la lambda-code/
```

### **Step 4.3: Create Ontology Filter Modification**
```python
# File: ontology_filter.py
# Add this filter to the Lambda poller code

ONTOLOGY_GRAPHS = [
    'http://climate-risk-ontology',
    'http://geonames-ontology'
]

EXCLUDED_PREDICATES = [
    'document_content',
    'chunk_text', 
    'extracted_text',
    'file_content',
    'processing_status'
]

def should_index_record(record):
    """
    Filter for ontology data only - reduces costs and index size
    """
    try:
        # Extract graph context
        graph_uri = record.get('eventData', {}).get('stmt', {}).get('graph', '')
        
        # Extract predicate
        predicate = record.get('eventData', {}).get('stmt', {}).get('predicate', '')
        
        # Extract object type
        obj_data = record.get('eventData', {}).get('stmt', {}).get('object', {})
        is_literal = obj_data.get('type') == 'literal'
        
        # Only index if:
        # 1. From ontology graphs
        # 2. Not excluded predicate
        # 3. Object is literal (searchable text)
        return (
            any(ontology in graph_uri for ontology in ONTOLOGY_GRAPHS) and
            not any(excluded in predicate for excluded in EXCLUDED_PREDICATES) and
            is_literal
        )
        
    except Exception as e:
        # Log error but don't fail processing
        print(f"Filter error: {e}")
        return False

# Integrate into existing poller logic
def process_stream_records(records):
    """Modified to include ontology filtering"""
    filtered_records = []
    
    for record in records:
        if should_index_record(record):
            filtered_records.append(record)
        else:
            print(f"Filtered out: {record.get('eventData', {}).get('stmt', {}).get('graph', 'unknown')}")
    
    print(f"Processing {len(filtered_records)} of {len(records)} records")
    return process_records_to_opensearch(filtered_records)
```

### **Step 4.4: Apply Lambda Modification**
```bash
# Create modified Lambda deployment package
# (This step requires careful integration with existing code)
# Consider creating a backup first

# Update Lambda function with modified code
aws lambda update-function-code \
    --function-name $LAMBDA_FUNCTION_NAME \
    --zip-file fileb://modified-lambda-code.zip
```

## 📋 **PHASE 5: TESTING & VALIDATION** (60-90 minutes)

### **Step 5.1: Test OpenSearch Index Creation**
```bash
# Check if Neptune FTS indices are created
curl -X GET "https://vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com/_cat/indices" \
    -u admin:veqpat-kegba2-zapbyZ

# Look for indices like: neptune-sparql-index
```

### **Step 5.2: Test Basic FTS Query**
```python
# File: test_neptune_fts.py
import boto3
import requests
from requests_aws4auth import AWS4Auth

def test_neptune_fts_query():
    """Test Neptune FTS integration"""
    
    # Neptune SPARQL endpoint
    sparql_endpoint = "https://solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182/sparql"
    
    # Test FTS query
    test_query = """
    PREFIX neptune-fts: <http://aws.amazon.com/neptune/vocab/v01/services/fts#>
    
    SELECT ?s ?p ?o ?score
    WHERE {
      ?s ?p ?o .
      FILTER(neptune-fts:query(neptune-fts:field('object'), 'climate'))
      BIND(neptune-fts:score() AS ?score)
    }
    ORDER BY DESC(?score)
    LIMIT 5
    """
    
    # Execute query with AWS authentication
    session = boto3.Session()
    credentials = session.get_credentials()
    
    auth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        'us-east-1',
        'neptune-db',
        session_token=credentials.token
    )
    
    response = requests.post(
        sparql_endpoint,
        data={'query': test_query},
        headers={
            'Accept': 'application/sparql-results+json',
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        auth=auth,
        timeout=30
    )
    
    if response.status_code == 200:
        results = response.json()
        print(f"✅ FTS Query successful: {len(results.get('results', {}).get('bindings', []))} results")
        return True
    else:
        print(f"❌ FTS Query failed: {response.status_code} - {response.text}")
        return False

if __name__ == "__main__":
    test_neptune_fts_query()
```

### **Step 5.3: Test OntologyManager Integration**
```python
# Run via admin_ontology_manager Lambda or local test
# File: test_ontology_manager_fts.py

import sys
sys.path.append('/opt/python')  # Lambda layer path

from utils.KnowledgeGraphManager import KnowledgeGraphManager

def test_ontology_manager_fts():
    """Test OntologyManager FTS methods"""
    
    try:
        # Initialize with Neptune-FTS enabled
        kg_manager = KnowledgeGraphManager()
        ontology_manager = kg_manager.ontology_manager
        
        # Test list_ontologies
        ontologies = ontology_manager.list_ontologies()
        print(f"✅ Available ontologies: {len(ontologies)}")
        
        # Test search_ontology_specific
        if ontologies:
            results = ontology_manager.search_ontology_specific(
                ontology_id='climate-risk',
                search_term='climate adaptation',
                limit=5
            )
            print(f"✅ Search results: {len(results)}")
            
            for result in results:
                print(f"  - {result.get('label', 'N/A')} (score: {result.get('score', 'N/A')})")
        
        return True
        
    except Exception as e:
        print(f"❌ OntologyManager test failed: {e}")
        return False
```

### **Step 5.4: Monitor Costs and Performance**
```bash
# Set up cost monitoring
aws budgets create-budget \
    --account-id 861276078413 \
    --budget '{
        "BudgetName": "Neptune-FTS-Monthly",
        "BudgetLimit": {
            "Amount": "50",
            "Unit": "USD"
        },
        "TimeUnit": "MONTHLY",
        "BudgetType": "COST"
    }'

# Monitor Lambda execution costs
aws logs describe-log-groups \
    --log-group-name-prefix "/aws/lambda/neptune" \
    --query 'logGroups[*].[logGroupName,storedBytes]'

# Monitor DynamoDB costs
aws dynamodb describe-table \
    --table-name $(aws cloudformation describe-stacks \
        --stack-name neptune-ontology-fts \
        --query 'Stacks[0].Outputs[?OutputKey==`LeaseDynamoDBTable`].OutputValue' \
        --output text) \
    --query 'Table.[TableSizeBytes,ItemCount]'
```

## 📋 **PHASE 6: OPTIMIZATION & DOCUMENTATION** (30-45 minutes)

### **Step 6.1: Performance Optimization**
```bash
# Adjust polling frequency based on actual usage
aws lambda update-function-configuration \
    --function-name $LAMBDA_FUNCTION_NAME \
    --environment Variables='{
        "MAX_POLLING_WAIT_TIME": "900",
        "BATCH_SIZE": "5000",
        "ONTOLOGY_FILTER_ENABLED": "true"
    }'
```

### **Step 6.2: Create Monitoring Dashboard**
```bash
# Create CloudWatch dashboard for Neptune-FTS monitoring
aws cloudwatch put-dashboard \
    --dashboard-name "Neptune-FTS-Monitoring" \
    --dashboard-body file://neptune-fts-dashboard.json
```

### **Step 6.3: Document Final Configuration**
```markdown
# File: NEPTUNE_FTS_DEPLOYMENT_SUMMARY.md

## Deployment Summary
- **Stack Name**: neptune-ontology-fts
- **Lambda Function**: [Function Name]
- **DynamoDB Table**: [Table Name]
- **OpenSearch Indices**: neptune-sparql-index
- **Monthly Cost**: $[Actual Cost]

## Configuration
- **Polling Interval**: 10 minutes
- **Batch Size**: 5000 records
- **Ontology Filtering**: Enabled
- **Excluded Predicates**: document_content, chunk_text, extracted_text

## Testing Results
- ✅ FTS queries functional
- ✅ OntologyManager integration working
- ✅ Costs within budget
- ✅ Performance acceptable
```

## ⚠️ **COST MONITORING & SAFETY MEASURES**

### **Real-time Cost Tracking**
```bash
# Daily cost check command
aws ce get-cost-and-usage \
    --time-period Start=2025-08-06,End=2025-08-07 \
    --granularity DAILY \
    --metrics BlendedCost \
    --group-by Type=DIMENSION,Key=SERVICE \
    --query 'ResultsByTime[0].Groups[?Keys[0]==`Amazon Neptune` || Keys[0]==`Amazon OpenSearch Service` || Keys[0]==`AWS Lambda`]'
```

### **Emergency Shutdown Procedure**
```bash
# If costs exceed budget, disable stream processing
aws lambda update-function-configuration \
    --function-name $LAMBDA_FUNCTION_NAME \
    --environment Variables='{"PROCESSING_ENABLED": "false"}'

# Or pause the Step Functions state machine
aws stepfunctions stop-execution \
    --execution-arn [State Machine Execution ARN]
```

### **Cost Alerts**
- **$25 threshold**: Review and optimize
- **$50 threshold**: Consider pausing non-essential processing
- **$75 threshold**: Emergency shutdown procedures

## 🎯 **SUCCESS CRITERIA CHECKLIST**

### **Technical Success**
- [ ] Neptune Streams enabled and operational
- [ ] CloudFormation stack deployed successfully
- [ ] Lambda poller processing stream records
- [ ] OpenSearch indices populated with ontology data
- [ ] `neptune-fts:query()` returns results in SPARQL
- [ ] OntologyManager methods work with FTS
- [ ] Document data filtered out of indices

### **Cost Success**
- [ ] Monthly additional costs under $30
- [ ] DynamoDB usage optimized for infrequent updates
- [ ] Lambda execution time minimized
- [ ] No unexpected service charges

### **Performance Success**
- [ ] FTS queries respond within 2 seconds
- [ ] Ontology updates indexed within 15 minutes
- [ ] No impact on existing Neptune query performance
- [ ] OpenSearch cluster health remains green

## 📞 **TROUBLESHOOTING GUIDE**

### **Common Issues**
1. **Stream not accessible**: Check VPC connectivity and security groups
2. **Lambda timeout**: Increase memory allocation or timeout settings
3. **OpenSearch connection failed**: Verify authentication and network access
4. **High DynamoDB costs**: Reduce polling frequency or batch size
5. **FTS queries return no results**: Check index population and query syntax

### **Debug Commands**
```bash
# Check Lambda logs
aws logs tail /aws/lambda/$LAMBDA_FUNCTION_NAME --follow

# Check Neptune stream status
aws neptune describe-db-clusters \
    --db-cluster-identifier solve-global-kr-neptune-s3 \
    --query 'DBClusters[0].EnabledCloudwatchLogsExports'

# Check OpenSearch index health
curl -X GET "https://vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com/_cluster/health" \
    -u admin:veqpat-kegba2-zapbyZ
```

---

**ESTIMATED TOTAL TIME**: 6-8 hours  
**RECOMMENDED APPROACH**: Complete in single dedicated session to maintain context and momentum  
**ROLLBACK PLAN**: CloudFormation stack can be deleted if issues arise, returning to previous state
