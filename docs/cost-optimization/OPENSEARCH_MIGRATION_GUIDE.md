# OpenSearch Migration Implementation Guide
## Serverless to Managed Migration for Cost Optimization

**Target Savings**: $534/month (79% cost reduction)  
**Implementation Effort**: 16-24 hours  
**Risk Level**: Low (parallel deployment strategy)  

---

## 🎯 MIGRATION OVERVIEW

### **Current State**
- **Service**: OpenSearch Serverless
- **Collections**: 2 active collections
  - `solve-global-kr-search-v2` (keyword search)
  - `solve-global-kr-vectors-v2` (vector search)
- **Cost**: $674/month
- **Limitation**: Standby replicas cannot be disabled

### **Target State**
- **Service**: Amazon OpenSearch Service (Managed)
- **Configuration**: Multi-AZ cluster with dedicated masters
- **Cost**: $135-140/month
- **Benefits**: Full control, better cost efficiency, production-ready

---

## 🏗️ TECHNICAL ARCHITECTURE

### **Managed Cluster Configuration**
```python
# CDK Implementation
managed_opensearch = opensearch.Domain(
    self, "ClimateRiskManagedOpenSearch",
    version=opensearch.EngineVersion.OPENSEARCH_2_11,
    
    # Production-ready capacity
    capacity=opensearch.CapacityConfig(
        data_nodes=2,
        data_node_instance_type="t3.small.search",  # $0.036/hour
        master_nodes=3,
        master_node_instance_type="t3.small.search"
    ),
    
    # Storage configuration
    ebs=opensearch.EbsOptions(
        volume_size=20,  # GB per node
        volume_type=ec2.EbsDeviceVolumeType.GP3,
        iops=3000,
        throughput=125
    ),
    
    # High availability
    zone_awareness=opensearch.ZoneAwarenessConfig(
        enabled=True,
        availability_zone_count=2
    ),
    
    # Security
    node_to_node_encryption=True,
    encryption_at_rest=opensearch.EncryptionAtRestOptions(enabled=True),
    enforce_https=True,
    
    # VPC configuration
    vpc=vpc,
    vpc_subnets=[ec2.SubnetSelection(
        subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
    )],
    security_groups=[opensearch_security_group],
    
    # Backup configuration
    automated_snapshot_start_hour=2,  # 2 AM UTC
    
    # Logging
    logging=opensearch.LoggingOptions(
        slow_search_log_enabled=True,
        app_log_enabled=True,
        slow_index_log_enabled=True
    )
)
```

### **Security Group Configuration**
```python
opensearch_security_group = ec2.SecurityGroup(
    self, "OpenSearchSecurityGroup",
    vpc=vpc,
    description="Security group for managed OpenSearch cluster",
    allow_all_outbound=True
)

# Allow access from Lambda functions
opensearch_security_group.add_ingress_rule(
    peer=ec2.Peer.security_group_id(lambda_security_group.security_group_id),
    connection=ec2.Port.tcp(443),
    description="HTTPS access from Lambda functions"
)
```

---

## 📋 IMPLEMENTATION PHASES

### **Phase 1: Preparation and Setup** (4-6 hours)

#### **Step 1.1: Create CDK Stack**
```bash
# Create new CDK stack for managed OpenSearch
cd /Users/chris/climate-risk-rag-aws/cdk
cp stacks/data_stack.py stacks/managed_opensearch_stack.py

# Modify to include managed OpenSearch configuration
# Remove serverless collections, add managed domain
```

#### **Step 1.2: Deploy Managed Cluster**
```bash
# Deploy in parallel to existing serverless
cdk deploy solve-global-kr-rag-managed-opensearch --profile solve-global

# Verify cluster health
aws opensearch describe-domain --domain-name climate-risk-managed \
  --profile solve-global --region us-east-1
```

#### **Step 1.3: Configure Monitoring**
```python
# CloudWatch alarms for cluster health
cluster_health_alarm = cloudwatch.Alarm(
    self, "OpenSearchClusterHealth",
    metric=managed_opensearch.metric_cluster_status_red(),
    threshold=0,
    evaluation_periods=1,
    alarm_description="OpenSearch cluster is in red status"
)

search_latency_alarm = cloudwatch.Alarm(
    self, "OpenSearchSearchLatency",
    metric=managed_opensearch.metric_search_latency(),
    threshold=1000,  # milliseconds
    evaluation_periods=2,
    alarm_description="OpenSearch search latency is high"
)
```

#### **Step 1.4: Test Connectivity**
```python
# Create test Lambda function to verify connectivity
test_function = lambda_.Function(
    self, "OpenSearchConnectivityTest",
    runtime=lambda_.Runtime.PYTHON_3_11,
    handler="test_connectivity.handler",
    code=lambda_.Code.from_asset("../lambda/opensearch_test"),
    vpc=vpc,
    environment={
        "OPENSEARCH_ENDPOINT": managed_opensearch.domain_endpoint,
        "OPENSEARCH_DOMAIN": managed_opensearch.domain_name
    }
)
```

### **Phase 2: Data Migration** (8-12 hours)

#### **Step 2.1: Create Migration Lambda**
```python
# Lambda function for data migration
migration_function = lambda_.Function(
    self, "OpenSearchMigrationFunction",
    runtime=lambda_.Runtime.PYTHON_3_11,
    handler="migrate_data.handler",
    code=lambda_.Code.from_asset("../lambda/opensearch_migration"),
    timeout=Duration.minutes(15),
    memory_size=2048,
    vpc=vpc,
    environment={
        "SOURCE_ENDPOINT": "https://i7dzyfap1fe42z9delui.us-east-1.aoss.amazonaws.com",
        "TARGET_ENDPOINT": managed_opensearch.domain_endpoint,
        "SOURCE_TYPE": "serverless",
        "TARGET_TYPE": "managed"
    }
)
```

#### **Step 2.2: Migration Script**
```python
# Migration logic (pseudo-code)
def migrate_opensearch_data():
    # 1. Create indices in managed cluster
    create_keyword_index()
    create_vector_index()
    
    # 2. Migrate keyword search data
    migrate_index_data(
        source="solve-global-kr-search-v2",
        target="climate-risk-keyword-index"
    )
    
    # 3. Migrate vector search data
    migrate_index_data(
        source="solve-global-kr-vectors-v2", 
        target="climate-risk-vector-index"
    )
    
    # 4. Verify data integrity
    verify_migration_success()
```

#### **Step 2.3: Implement Dual-Write**
```python
# Update Lambda functions to write to both systems
def dual_write_opensearch(document_data):
    try:
        # Write to serverless (existing)
        write_to_serverless(document_data)
        
        # Write to managed (new)
        write_to_managed(document_data)
        
        return {"status": "success", "dual_write": True}
    except Exception as e:
        # Log error but don't fail if one system is down
        logger.error(f"Dual write error: {e}")
        return {"status": "partial", "error": str(e)}
```

### **Phase 3: Cutover and Validation** (4-6 hours)

#### **Step 3.1: Switch Read Traffic**
```python
# Update Lambda environment variables
def update_lambda_endpoints():
    functions_to_update = [
        "keyword-indexer",
        "async-keyword-indexer-worker", 
        "vector-embeddings-worker"
    ]
    
    new_endpoint = managed_opensearch.domain_endpoint
    
    for function_name in functions_to_update:
        update_function_configuration(
            function_name=function_name,
            environment_variables={
                "OPENSEARCH_ENDPOINT": new_endpoint
            }
        )
```

#### **Step 3.2: Validation Testing**
```bash
# Run comprehensive tests
python3 test_opensearch_functionality.py --endpoint managed

# Performance testing
python3 performance_test.py --compare-endpoints

# Load testing
python3 load_test.py --duration 30m --concurrent-users 10
```

#### **Step 3.3: Monitor Stability**
```python
# 48-hour monitoring period
monitoring_metrics = [
    "search_latency",
    "indexing_rate", 
    "error_rate",
    "cluster_health",
    "cpu_utilization",
    "memory_utilization"
]

# Automated rollback triggers
rollback_conditions = {
    "error_rate": "> 5%",
    "search_latency": "> 2000ms", 
    "cluster_health": "red"
}
```

#### **Step 3.4: Decommission Serverless**
```bash
# After 48 hours of stable operation
aws opensearchserverless delete-collection \
  --id i7dzyfap1fe42z9delui --profile solve-global

aws opensearchserverless delete-collection \
  --id rui72a7agqnqo77vk34b --profile solve-global

# Clean up security policies
aws opensearchserverless delete-security-policy \
  --name kr-search-v2-encryption --type encryption --profile solve-global
```

---

## 🔧 OPERATIONAL PROCEDURES

### **Daily Operations**
```bash
# Health check script
#!/bin/bash
DOMAIN_NAME="climate-risk-managed"
REGION="us-east-1"
PROFILE="solve-global"

# Check cluster health
aws opensearch describe-domain --domain-name $DOMAIN_NAME \
  --profile $PROFILE --region $REGION \
  --query 'DomainStatus.Processing'

# Check cluster metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ES \
  --metric-name ClusterStatus.red \
  --dimensions Name=DomainName,Value=$DOMAIN_NAME \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Maximum \
  --profile $PROFILE --region $REGION
```

### **Weekly Maintenance**
```python
# Automated maintenance script
def weekly_maintenance():
    # 1. Review performance metrics
    analyze_performance_metrics()
    
    # 2. Check storage utilization
    check_storage_usage()
    
    # 3. Review slow queries
    analyze_slow_query_logs()
    
    # 4. Update index templates if needed
    optimize_index_templates()
    
    # 5. Generate weekly report
    generate_maintenance_report()
```

### **Monthly Optimization**
```python
def monthly_optimization():
    # 1. Capacity planning review
    analyze_capacity_trends()
    
    # 2. Cost optimization check
    review_instance_utilization()
    
    # 3. Security updates
    check_for_security_updates()
    
    # 4. Backup verification
    verify_snapshot_integrity()
    
    # 5. Performance tuning
    optimize_cluster_settings()
```

---

## 📊 MONITORING AND ALERTING

### **Key Metrics to Monitor**
```yaml
Cluster Health:
  - Cluster status (green/yellow/red)
  - Node count and status
  - Shard allocation status

Performance:
  - Search latency (p50, p95, p99)
  - Indexing rate and latency
  - Query throughput
  - CPU and memory utilization

Storage:
  - Disk usage per node
  - Storage growth rate
  - Free storage remaining

Errors:
  - Search errors
  - Indexing errors
  - Cluster exceptions
```

### **Alert Thresholds**
```python
alert_thresholds = {
    "cluster_status_red": 0,  # Immediate alert
    "cluster_status_yellow": 300,  # 5 minute threshold
    "search_latency_p95": 1000,  # milliseconds
    "cpu_utilization": 80,  # percentage
    "memory_utilization": 85,  # percentage
    "disk_usage": 75,  # percentage
    "error_rate": 5  # percentage
}
```

---

## 🚨 ROLLBACK PROCEDURES

### **Automated Rollback Triggers**
```python
def check_rollback_conditions():
    conditions = {
        "high_error_rate": get_error_rate() > 10,
        "high_latency": get_avg_latency() > 2000,
        "cluster_red": get_cluster_status() == "red",
        "data_loss": verify_data_integrity() == False
    }
    
    if any(conditions.values()):
        trigger_rollback()
        return True
    return False

def trigger_rollback():
    # 1. Switch Lambda functions back to serverless
    revert_lambda_endpoints()
    
    # 2. Notify operations team
    send_rollback_notification()
    
    # 3. Preserve managed cluster for analysis
    tag_cluster_for_investigation()
```

### **Manual Rollback Process**
```bash
# Emergency rollback procedure
# 1. Update Lambda environment variables
aws lambda update-function-configuration \
  --function-name keyword-indexer \
  --environment Variables='{
    "OPENSEARCH_ENDPOINT": "https://i7dzyfap1fe42z9delui.us-east-1.aoss.amazonaws.com"
  }' \
  --profile solve-global

# 2. Verify serverless collections still exist
aws opensearchserverless list-collections --profile solve-global

# 3. Test functionality
python3 test_opensearch_functionality.py --endpoint serverless

# 4. Monitor for stability
# 5. Investigate managed cluster issues
```

---

## 💰 COST TRACKING

### **Pre-Migration Baseline**
```yaml
Current Monthly Costs:
  OpenSearch Serverless: $674
  Total System: ~$670

Daily Cost: ~$22.47
Hourly Cost: ~$0.94
```

### **Post-Migration Target**
```yaml
Projected Monthly Costs:
  Managed OpenSearch: $135-140
  Total Savings: $534-539
  Percentage Reduction: 79-80%

Daily Cost: ~$4.50
Hourly Cost: ~$0.19
```

### **Cost Monitoring Setup**
```python
# Cost tracking Lambda
def track_opensearch_costs():
    # Get current month costs
    current_costs = get_service_costs("OpenSearch")
    
    # Compare to baseline
    savings = baseline_cost - current_costs
    
    # Update cost dashboard
    update_cost_metrics(savings)
    
    # Alert if costs exceed threshold
    if current_costs > expected_cost * 1.1:
        send_cost_alert()
```

---

## ✅ SUCCESS CRITERIA

### **Technical Success**
- [ ] Cluster health: Green status maintained
- [ ] Performance: Search latency < 500ms (p95)
- [ ] Availability: 99.9% uptime achieved
- [ ] Data integrity: 100% data migration verified
- [ ] Functionality: All search features working

### **Cost Success**
- [ ] Monthly savings: $500+ achieved
- [ ] Cost reduction: 75%+ from baseline
- [ ] ROI positive: Within 3 months

### **Operational Success**
- [ ] Monitoring: All alerts configured and tested
- [ ] Documentation: Runbooks and procedures complete
- [ ] Team training: Operations team comfortable with new system
- [ ] Rollback tested: Emergency procedures validated

---

## 📅 IMPLEMENTATION TIMELINE

### **Pre-Implementation** (1 week)
- [ ] System stability verification
- [ ] Team availability confirmation
- [ ] Rollback procedures tested
- [ ] Stakeholder approval obtained

### **Implementation Window** (2-3 days)
- **Day 1**: Deploy managed cluster, test connectivity
- **Day 2**: Migrate data, implement dual-write
- **Day 3**: Switch traffic, validate functionality

### **Post-Implementation** (1 week)
- **Days 1-2**: Intensive monitoring
- **Days 3-7**: Stability verification
- **Week 2**: Decommission serverless if stable

---

This guide provides the complete roadmap for migrating from OpenSearch Serverless to Managed OpenSearch, achieving significant cost savings while maintaining system reliability and performance.
