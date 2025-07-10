# OpenSearch Cost Optimization Analysis
## Date: 2025-07-10T03:15:00Z
## Current Cost: $101.16 (9 days) = $337/month projected
## Service: Amazon OpenSearch Serverless

---

## EXECUTIVE SUMMARY

**Critical Finding**: OpenSearch Serverless is the largest cost driver at $101.16 over 9 days, representing 52% of total AWS spend. The service is configured as a SEARCH-type collection with standby replicas enabled, which significantly increases costs.

**Immediate Opportunity**: Multiple cost reduction strategies available, from configuration optimization to complete service replacement, with potential savings of $200-300/month.

---

## CURRENT OPENSEARCH CONFIGURATION

### **Service Details**
- **Service Type**: Amazon OpenSearch Serverless (not traditional cluster)
- **Collection Name**: `solve-global-kr-search`
- **Collection ID**: `oxxw312s6cktjq4t31k7`
- **Type**: SEARCH (optimized for search workloads)
- **Status**: ACTIVE
- **Standby Replicas**: ENABLED ⚠️ (Major cost driver)

### **Current Usage**
- **Primary Users**: Keyword indexer Lambda functions
- **Functions Using OpenSearch**:
  - `async-keyword-indexer` stack
  - `keyword-indexer` stack
  - Vector embeddings pipeline (potentially)

### **Cost Structure**
- **Current**: $101.16 (9 days) = $11.24/day
- **Monthly Projection**: $337/month
- **Cost Components**:
  - **Compute**: Search processing units
  - **Storage**: Indexed data storage
  - **Standby Replicas**: High availability (expensive)

---

## OPENSEARCH SERVERLESS PRICING ANALYSIS

### **OpenSearch Serverless Cost Factors**
1. **Search Compute Units (SCUs)**
   - **Base**: 0.5 SCU minimum per collection
   - **Cost**: ~$0.24/hour per SCU
   - **Monthly**: ~$175/month for minimum 0.5 SCU

2. **Indexing Compute Units (ICUs)**
   - **Usage-based**: For data ingestion
   - **Cost**: ~$0.24/hour per ICU
   - **Variable**: Based on indexing activity

3. **Storage**
   - **Cost**: ~$0.024/GB/month
   - **Minimal**: For our data volumes

4. **Standby Replicas** ⚠️
   - **Impact**: Doubles compute costs
   - **Current**: ENABLED (major cost driver)
   - **Benefit**: High availability and performance

### **Why Costs Are High**
1. **Minimum SCU**: 0.5 SCU always running = ~$175/month base
2. **Standby Replicas**: Doubles compute costs = ~$350/month
3. **Search-Optimized**: Higher performance = higher cost
4. **Always-On**: No ability to stop/start like EC2

---

## COST OPTIMIZATION OPTIONS

### **OPTION 1: OPTIMIZE CURRENT OPENSEARCH SERVERLESS** 💰
**Potential Savings**: $150-200/month

#### **1A. Disable Standby Replicas**
- **Action**: Modify collection to disable standby replicas
- **Savings**: ~50% reduction in compute costs
- **Impact**: Reduced availability during maintenance
- **Risk**: Lower performance during peak usage
- **Implementation**: Update CDK configuration

#### **1B. Switch to TIMESERIES Type**
- **Current**: SEARCH type (expensive)
- **Alternative**: TIMESERIES type (cheaper for log-like data)
- **Savings**: ~30-40% cost reduction
- **Consideration**: May not suit keyword search use case

#### **1C. Optimize Data Retention**
- **Action**: Implement data lifecycle policies
- **Savings**: Reduce storage costs (minimal impact)
- **Implementation**: Delete old indices, compress data

### **OPTION 2: SWITCH TO OPENSEARCH MANAGED CLUSTER** 💰💰
**Potential Savings**: $200-250/month

#### **2A. Small OpenSearch Cluster**
- **Configuration**: 1x t3.small.search instance
- **Cost**: ~$25-35/month
- **Pros**: Much cheaper, full control, can stop/start
- **Cons**: Need to manage, less serverless

#### **2B. Development-Optimized Cluster**
- **Configuration**: 1x t3.micro.search (if available)
- **Cost**: ~$15-20/month
- **Pros**: Minimal cost for development
- **Cons**: Limited performance, single point of failure

### **OPTION 3: ALTERNATIVE SEARCH SOLUTIONS** 💰💰💰
**Potential Savings**: $250-300/month

#### **3A. Amazon CloudSearch**
- **Cost**: ~$50-100/month for small instances
- **Pros**: Managed, cheaper than OpenSearch
- **Cons**: Less flexible, older technology

#### **3B. DynamoDB + Search**
- **Cost**: ~$10-30/month for our data volumes
- **Pros**: Very cost-effective, serverless
- **Cons**: Limited search capabilities, requires redesign

#### **3C. RDS PostgreSQL Full-Text Search**
- **Cost**: $0 (using existing RDS instance)
- **Pros**: No additional cost, good text search
- **Cons**: Less sophisticated than OpenSearch

#### **3D. S3 + Lambda Search**
- **Cost**: ~$5-15/month
- **Pros**: Very cheap, serverless
- **Cons**: Slower, requires custom implementation

### **OPTION 4: ELIMINATE SEARCH FUNCTIONALITY** 💰💰💰💰
**Potential Savings**: $300+/month

#### **4A. Assess Search Necessity**
- **Question**: Is OpenSearch actually being used in production?
- **Analysis**: Check Lambda function logs and usage metrics
- **Action**: If unused, completely remove OpenSearch

#### **4B. Temporary Removal**
- **Strategy**: Remove OpenSearch for development phase
- **Re-implement**: Add back when actually needed for production
- **Savings**: Complete elimination of $337/month cost

---

## FUNCTIONALITY IMPACT ANALYSIS

### **Current OpenSearch Usage**
Based on code analysis, OpenSearch is used for:
1. **Keyword Indexing**: Document keyword extraction and indexing
2. **Vector Embeddings**: Potentially storing vector embeddings
3. **Search Functionality**: Text and semantic search capabilities

### **Impact of Each Option**

#### **Option 1 (Optimize Serverless)**
- **Functionality**: ✅ Maintained
- **Performance**: ⚠️ Slightly reduced (no standby replicas)
- **Availability**: ⚠️ Reduced during maintenance
- **Development**: ✅ No code changes needed

#### **Option 2 (Managed Cluster)**
- **Functionality**: ✅ Maintained or improved
- **Performance**: ⚠️ May be slower on small instances
- **Availability**: ⚠️ Single instance = single point of failure
- **Development**: ⚠️ Minor configuration changes needed

#### **Option 3 (Alternative Solutions)**
- **Functionality**: ⚠️ May require feature compromises
- **Performance**: ⚠️ Varies by solution
- **Availability**: ✅ Most alternatives are reliable
- **Development**: 🚨 Significant code changes required

#### **Option 4 (Eliminate)**
- **Functionality**: 🚨 Search features lost
- **Performance**: N/A
- **Availability**: N/A
- **Development**: ⚠️ Code cleanup needed

---

## RECOMMENDED APPROACH

### **PHASE 1: IMMEDIATE COST REDUCTION** (Today)
**Target Savings**: $150-200/month

1. **Disable Standby Replicas**
   - **Action**: Update CDK configuration to disable standby replicas
   - **Savings**: ~50% cost reduction
   - **Risk**: Minimal for development environment
   - **Implementation**: 30 minutes

2. **Assess Actual Usage**
   - **Action**: Check CloudWatch metrics for OpenSearch usage
   - **Goal**: Determine if search is actively used
   - **Timeline**: 1 hour analysis

### **PHASE 2: ARCHITECTURE EVALUATION** (This Week)
**Target Savings**: $200-250/month

1. **Evaluate Search Necessity**
   - **Question**: Is OpenSearch required for current development?
   - **Analysis**: Review Lambda function usage and logs
   - **Decision**: Keep, optimize, or eliminate

2. **Consider Managed Cluster**
   - **If keeping search**: Evaluate t3.small.search cluster
   - **Cost comparison**: $25-35/month vs $337/month
   - **Performance testing**: Ensure adequate for use case

### **PHASE 3: LONG-TERM OPTIMIZATION** (Next Week)
**Target Savings**: $250-300/month

1. **Implement Chosen Solution**
   - **If eliminating**: Remove OpenSearch completely
   - **If switching**: Deploy managed cluster
   - **If optimizing**: Fine-tune serverless configuration

2. **Code Optimization**
   - **Update Lambda functions**: Point to new search solution
   - **Test functionality**: Ensure no regression
   - **Monitor costs**: Verify savings achieved

---

## IMPLEMENTATION DETAILS

### **Option 1A: Disable Standby Replicas (RECOMMENDED IMMEDIATE)**

#### **CDK Configuration Change**
```python
# In cdk/stacks/data_stack.py
self.opensearch_collection = opensearchserverless.CfnCollection(
    self, "OpenSearchCollection",
    name="solve-global-kr-search",
    type="SEARCH",
    description="Climate Risk RAG search collection",
    # ADD THIS LINE:
    standby_replicas="DISABLED"  # Reduces cost by ~50%
)
```

#### **Deployment Commands**
```bash
cd /Users/chris/climate-risk-rag-aws/cdk
cdk diff solve-global-kr-rag-data
cdk deploy solve-global-kr-rag-data --profile solve-global
```

### **Option 2: Switch to Managed Cluster**

#### **CDK Configuration Replacement**
```python
# Replace OpenSearch Serverless with managed cluster
self.opensearch_domain = opensearch.Domain(
    self, "OpenSearchDomain",
    version=opensearch.EngineVersion.OPENSEARCH_2_3,
    capacity=opensearch.CapacityConfig(
        data_nodes=1,
        data_node_instance_type="t3.small.search"
    ),
    ebs=opensearch.EbsOptions(
        volume_size=20,
        volume_type=ec2.EbsDeviceVolumeType.GP3
    ),
    zone_awareness=opensearch.ZoneAwarenessConfig(
        enabled=False  # Single AZ for cost savings
    ),
    removal_policy=RemovalPolicy.DESTROY  # For development
)
```

### **Option 4: Complete Elimination**

#### **Steps to Remove OpenSearch**
1. **Update Lambda Functions**: Remove OpenSearch dependencies
2. **Update CDK**: Comment out OpenSearch resources
3. **Deploy Changes**: Remove OpenSearch from infrastructure
4. **Verify Functionality**: Ensure application still works

---

## COST MONITORING

### **Before Optimization**
- **Daily Cost**: $11.24
- **Monthly Projection**: $337
- **Percentage of Total**: 52%

### **After Optimization Targets**
- **Option 1A (Disable Replicas)**: $5-6/day = $150-180/month
- **Option 2 (Managed Cluster)**: $1-2/day = $25-60/month
- **Option 4 (Eliminate)**: $0/day = $0/month

### **Success Metrics**
- **Cost Reduction**: >50% reduction in OpenSearch costs
- **Total Budget Impact**: Bring monthly total under $400
- **Functionality**: Maintain required search capabilities
- **Performance**: Acceptable response times for development

---

## RISK ASSESSMENT

### **Low Risk Options**
- **Disable Standby Replicas**: Minimal functionality impact
- **Switch to Managed Cluster**: Well-understood technology

### **Medium Risk Options**
- **Alternative Search Solutions**: Require code changes
- **Data Retention Optimization**: May affect search quality

### **High Risk Options**
- **Complete Elimination**: Loss of search functionality
- **Significant Architecture Changes**: Potential for bugs

---

## NEXT STEPS

### **Immediate (Today)**
1. **Disable standby replicas** in OpenSearch Serverless
2. **Check CloudWatch metrics** for actual usage
3. **Deploy optimization** and monitor cost impact

### **Short Term (This Week)**
1. **Evaluate search necessity** for current development
2. **Consider managed cluster** if search is needed
3. **Plan architecture changes** if eliminating search

### **Long Term (Next Week)**
1. **Implement chosen solution**
2. **Update application code** as needed
3. **Monitor cost savings** and functionality

---

## CONCLUSION

**OpenSearch Serverless is the primary cost driver** at $337/month projected, representing 52% of total AWS spend. **Immediate cost reduction of 50%** is possible by disabling standby replicas, with potential for **75-100% cost reduction** through architecture changes.

**Recommended immediate action**: Disable standby replicas to reduce costs by ~$150/month while evaluating whether search functionality is actually needed for current development phase.

**Long-term strategy**: Consider switching to a managed OpenSearch cluster ($25-35/month) or eliminating search functionality entirely if not actively used, achieving potential savings of $250-300/month.

This optimization alone could bring the total monthly AWS spend from $670 to $320-420, making it much more manageable for development and testing.
