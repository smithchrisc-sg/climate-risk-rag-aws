# OpenSearch Cost Optimization Status Report
## Date: 2025-07-10T03:25:00Z
## Status: Standby Replicas Cannot Be Disabled on Existing Collection

---

## CURRENT SITUATION

**Issue Discovered**: Amazon OpenSearch Serverless **does not allow modification of standby replicas** after collection creation. The `standby_replicas` parameter is only available during initial collection creation and cannot be changed via:
- AWS CLI `update-collection` command (only supports description updates)
- CDK updates (parameter not supported in CfnCollection)
- AWS Console (no option to modify this setting)

**Current Configuration**:
- **Collection**: `solve-global-kr-search` (ID: oxxw312s6cktjq4t31k7)
- **Type**: SEARCH
- **Standby Replicas**: ENABLED (cannot be changed)
- **Cost Impact**: ~$337/month projected

---

## ALTERNATIVE COST OPTIMIZATION STRATEGIES

### **OPTION 1: RECREATE COLLECTION WITH OPTIMIZED SETTINGS** 💰💰
**Potential Savings**: $150-200/month

#### **Approach**:
1. **Create new collection** with `standby_replicas=DISABLED`
2. **Migrate data** from old collection to new collection
3. **Update Lambda functions** to use new collection endpoint
4. **Delete old collection** to stop charges

#### **Implementation Steps**:
```python
# In CDK, create new collection with different name
self.opensearch_collection_v2 = opensearchserverless.CfnCollection(
    self, "OpenSearchCollectionV2",
    name="solve-global-kr-search-v2",
    type="SEARCH",
    description="Climate Risk RAG search collection - cost optimized"
    # standby_replicas defaults to DISABLED for new collections
)
```

#### **Risks**:
- **Data Migration**: Need to reindex all data
- **Downtime**: Temporary loss of search functionality
- **Lambda Updates**: Need to update all references

### **OPTION 2: SWITCH TO TIMESERIES TYPE** 💰
**Potential Savings**: $50-100/month

#### **Approach**:
Create new collection with `type="TIMESERIES"` which is cheaper than `type="SEARCH"`

#### **Considerations**:
- **Functionality**: May not support all search features needed
- **Performance**: Optimized for time-series data, not general search
- **Compatibility**: Need to verify with current use case

### **OPTION 3: SWITCH TO MANAGED OPENSEARCH CLUSTER** 💰💰💰
**Potential Savings**: $250-300/month

#### **Approach**:
Replace OpenSearch Serverless with traditional managed OpenSearch cluster

#### **Configuration**:
```python
self.opensearch_domain = opensearch.Domain(
    self, "OpenSearchDomain",
    version=opensearch.EngineVersion.OPENSEARCH_2_3,
    capacity=opensearch.CapacityConfig(
        data_nodes=1,
        data_node_instance_type="t3.small.search"  # ~$25/month
    ),
    ebs=opensearch.EbsOptions(
        volume_size=20,
        volume_type=ec2.EbsDeviceVolumeType.GP3
    ),
    zone_awareness=opensearch.ZoneAwarenessConfig(enabled=False),
    removal_policy=RemovalPolicy.DESTROY
)
```

#### **Benefits**:
- **Cost**: ~$25-35/month vs $337/month
- **Control**: Full control over instance types and scaling
- **Features**: All OpenSearch features available

#### **Considerations**:
- **Management**: Need to handle updates and maintenance
- **Availability**: Single instance = single point of failure
- **Migration**: Significant infrastructure change

### **OPTION 4: ELIMINATE OPENSEARCH ENTIRELY** 💰💰💰💰
**Potential Savings**: $337/month (100%)

#### **Assessment Needed**:
1. **Check actual usage** of OpenSearch in current system
2. **Identify dependent functions** and their criticality
3. **Evaluate alternatives** for search functionality

#### **Alternative Search Solutions**:
- **PostgreSQL Full-Text Search**: Use existing RDS instance
- **DynamoDB + GSI**: For simple key-value search
- **S3 + Lambda**: Custom search implementation
- **No search**: If functionality is not currently used

---

## RECOMMENDED IMMEDIATE ACTION

### **STEP 1: USAGE ASSESSMENT** (Priority 1)
**Goal**: Determine if OpenSearch is actually being used

#### **Check CloudWatch Metrics**:
```bash
# Check OpenSearch usage metrics
aws logs describe-log-groups --profile solve-global --region us-east-1 | grep -i opensearch
aws cloudwatch get-metric-statistics --namespace AWS/AOSS --metric-name SearchRequestCount --dimensions Name=CollectionName,Value=solve-global-kr-search --start-time 2025-07-01T00:00:00Z --end-time 2025-07-10T00:00:00Z --period 86400 --statistics Sum --profile solve-global --region us-east-1
```

#### **Check Lambda Function Logs**:
- Review logs for keyword indexer functions
- Look for OpenSearch API calls and errors
- Assess frequency and importance of usage

### **STEP 2: DECISION MATRIX** (Priority 2)
Based on usage assessment:

| Usage Level | Recommended Action | Savings | Timeline |
|-------------|-------------------|---------|----------|
| **Not Used** | Eliminate entirely | $337/month | 1 day |
| **Light Usage** | Switch to managed cluster | $250-300/month | 2-3 days |
| **Moderate Usage** | Recreate with disabled replicas | $150-200/month | 3-5 days |
| **Heavy Usage** | Keep current, optimize elsewhere | $0/month | N/A |

---

## IMPLEMENTATION PLAN

### **IF OPENSEARCH IS NOT ACTIVELY USED** (Recommended)
1. **Backup any important data** (if exists)
2. **Update Lambda functions** to remove OpenSearch dependencies
3. **Delete OpenSearch collection** via CDK
4. **Deploy changes** and verify functionality
5. **Monitor cost reduction** over next billing cycle

### **IF OPENSEARCH IS NEEDED**
1. **Create new optimized collection** (different name)
2. **Migrate data** from old to new collection
3. **Update Lambda function configurations** with new endpoint
4. **Test functionality** thoroughly
5. **Delete old collection** once migration is verified

---

## COST IMPACT PROJECTIONS

### **Current State**:
- **OpenSearch**: $337/month
- **Total AWS**: $670/month

### **After Optimization**:
- **Eliminate OpenSearch**: $333/month total (-$337)
- **Managed Cluster**: $400/month total (-$270)
- **Recreate Serverless**: $500/month total (-$170)

---

## NEXT STEPS

### **Immediate (Today)**:
1. **Assess OpenSearch usage** via CloudWatch and logs
2. **Determine criticality** of search functionality
3. **Choose optimization strategy** based on usage

### **Short Term (This Week)**:
1. **Implement chosen strategy**
2. **Test functionality** after changes
3. **Monitor cost impact**

### **Success Criteria**:
- **Cost Reduction**: Achieve >$200/month savings
- **Functionality**: Maintain required search capabilities
- **Stability**: No regression in system performance

---

## CONCLUSION

**The standby replicas cannot be disabled on the existing OpenSearch Serverless collection**, but significant cost savings are still achievable through alternative approaches. The best strategy depends on actual usage patterns of the search functionality.

**Immediate Priority**: Assess whether OpenSearch is actively used in the current system. If not used, eliminating it entirely would save the full $337/month and bring total AWS costs to a manageable $333/month.

**Next Best Option**: If search is needed, switching to a managed OpenSearch cluster would save $250-300/month while maintaining full functionality.

The key is determining actual usage before making architectural changes.
