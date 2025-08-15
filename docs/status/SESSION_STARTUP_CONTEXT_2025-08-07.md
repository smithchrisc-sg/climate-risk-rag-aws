# Session Startup Context - Quick Reference
**Date**: August 7, 2025  
**Purpose**: Immediate context for resuming work - READ THIS FIRST

## 🚀 **IMMEDIATE STATUS - READ FIRST**

### **✅ What Just Happened (Today's Session)**
- **Neptune-FTS integration COMPLETED and DEPLOYED**
- **Ontology positive filtering system IMPLEMENTED**
- **CloudFormation stack `NeptuneQuickStart` is LIVE and RUNNING**
- **Lambda function processing Neptune streams every 10 minutes**
- **Cost-optimized configuration active**

### **🎯 NEXT IMMEDIATE ACTION NEEDED**
**Priority 1**: Analyze real ontology data in Neptune to refine filtering rules
**Why**: Current filtering uses example rules - need real data patterns
**Risk**: May be filtering wrong data or missing important predicates

## 📊 **CRITICAL SYSTEM STATE**

### **Active AWS Resources (LIVE & BILLING)**
```
CloudFormation Stack: NeptuneQuickStart (CREATE_COMPLETE)
Lambda Function: NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3
DynamoDB Table: NeptuneOntologyFTS-LeaseTable
Neptune Cluster: solve-global-kr-neptune-s3 (RUNNING)
OpenSearch Domain: solve-global-kr-search (RUNNING - $200/month)
```

### **Current Configuration**
- **Filtering**: DISABLED by default (safe deployment)
- **Polling**: Every 10 minutes (cost-optimized)
- **Memory**: 1024MB (reduced from 2048MB)
- **Logging**: INFO level

### **To Enable Filtering** (when ready):
```bash
aws lambda update-function-configuration \
    --function-name "NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3" \
    --environment Variables='{"ONTOLOGY_FILTERING_ENABLED":"true"}'
```

## 💰 **COST ALERT STATUS**

### **Current Monthly Costs (Approximate)**
- **Neptune**: ~$400/month (db.r5.large)
- **OpenSearch**: ~$200/month (2×m6g.large.search)
- **Lambda**: ~$50/month (all functions)
- **S3**: ~$20/month (document storage)
- **Total**: ~$670/month baseline

### **⚠️ HIGH-COST SERVICES TO WATCH**
1. **AWS Textract**: $1.50 per 1,000 pages - LIMIT TEST DOCS
2. **Comprehend** (future): $0.0001 per unit - BATCH PROCESSING
3. **Titan Embeddings** (future): $0.0001 per 1K tokens - CACHE RESULTS

### **Daily Cost Check Command**:
```bash
# Check costs before any testing
aws ce get-cost-and-usage --time-period Start=2025-08-01,End=2025-08-08 --granularity DAILY --metrics BlendedCost
```

## 🔧 **KEY FILES & LOCATIONS**

### **Neptune-FTS Integration Files (Just Created)**
```
/lambda/neptune-stream-poller/
├── ontology_filter.py                    # ⭐ MAIN FILTERING LOGIC
├── lambda_function.py                    # Entry point
├── deploy_with_filtering.sh              # Deploy with filtering enabled
├── INTEGRATION_COMPLETE.md               # Integration status
└── neptune_to_es/
    ├── neptune_sparql_es_handler.py      # ⭐ MODIFIED - filtering added
    └── neptune_sparql_es_string_indexing_handler.py  # ⭐ MODIFIED
```

### **Key Infrastructure Files**
```
/cdk/                                     # Infrastructure definitions
/lambda/admin_ontology_manager/           # ⭐ SPARQL query interface
/lambda/shared_layer/                     # Common utilities
/docs/status/                             # ⭐ All context documents
```

### **Critical Configuration Files**
```
/neptune-fts-deployment/
├── neptune-to-opensearch-optimized.json # Cost-optimized template
└── parameters.json                       # Your infrastructure values
```

## 🎯 **IMMEDIATE NEXT STEPS CHECKLIST**

### **Step 1: Verify System Status (5 minutes)**
```bash
# Check CloudFormation stack
aws cloudformation describe-stacks --stack-name NeptuneQuickStart

# Check Lambda function
aws lambda get-function-configuration --function-name "NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3"

# Check recent logs
aws logs tail /aws/lambda/NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3 --since 1h
```

### **Step 2: Analyze Neptune Data (30 minutes)**
```python
# Via admin_ontology_manager Lambda - key queries to run:

# 1. List all graphs
query1 = "SELECT DISTINCT ?g WHERE { GRAPH ?g { ?s ?p ?o } }"

# 2. Count triples per graph  
query2 = "SELECT ?g (COUNT(*) as ?count) WHERE { GRAPH ?g { ?s ?p ?o } } GROUP BY ?g ORDER BY DESC(?count)"

# 3. List predicates per graph
query3 = "SELECT DISTINCT ?g ?p WHERE { GRAPH ?g { ?s ?p ?o } } ORDER BY ?g ?p"

# 4. Sample literal values for FTS
query4 = "SELECT ?g ?p ?o WHERE { GRAPH ?g { ?s ?p ?o . FILTER(isLiteral(?o)) } } LIMIT 50"
```

### **Step 3: Update Filtering Rules (15 minutes)**
Based on analysis, update `/lambda/neptune-stream-poller/ontology_filter.py`:
```python
# Replace example rules with real graph URIs and predicates found
self.filtering_rules = {
    'REAL_GRAPH_URI_FROM_ANALYSIS': {
        'REAL_PREDICATE_URI_1',
        'REAL_PREDICATE_URI_2',
        # etc.
    }
}
```

## 🚨 **CRITICAL CONTEXT - DON'T FORGET**

### **Why We Built This**
- **Problem**: Neptune has ALL data (documents + ontologies) 
- **Solution**: Filter to index ONLY ontology predicates for FTS
- **Goal**: Enable entity alignment (NLP results → ontology concepts)
- **Example**: "Jakarta" → `<gn:1642911> gn:name "Jakarta"`

### **Positive Filtering Philosophy**
- **OLD**: Exclude bad patterns (blacklist)
- **NEW**: Include only what we want (whitelist)
- **Benefit**: 80-90% cost reduction, precise results

### **Integration Architecture**
```
Neptune Streams → Lambda Poller → Ontology Filter → OpenSearch
                                       ↓
                               Only index whitelisted
                               ontology predicates
```

## 🔍 **DEBUGGING & TROUBLESHOOTING**

### **If Lambda Not Working**
```bash
# Check logs for errors
aws logs filter-log-events --log-group-name /aws/lambda/NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3 --start-time $(date -d '1 hour ago' +%s)000

# Check DynamoDB lease table
aws dynamodb scan --table-name NeptuneOntologyFTS-LeaseTable

# Check Neptune streams are enabled
aws neptune describe-db-clusters --db-cluster-identifier solve-global-kr-neptune-s3
```

### **If Costs Spike**
```bash
# Immediately disable filtering to reduce processing
aws lambda update-function-configuration \
    --function-name "NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3" \
    --environment Variables='{"ONTOLOGY_FILTERING_ENABLED":"false"}'

# Check what's causing costs
aws ce get-cost-and-usage --time-period Start=2025-08-07,End=2025-08-08 --granularity DAILY --metrics BlendedCost --group-by Type=DIMENSION,Key=SERVICE
```

### **If FTS Queries Don't Work**
```python
# Test basic FTS query via admin_ontology_manager
test_query = """
PREFIX neptune-fts: <http://aws.amazon.com/neptune/vocab/v01/services/fts#>
SELECT ?s ?p ?o WHERE {
    ?s ?p ?o .
    FILTER(neptune-fts:query(neptune-fts:field('object'), 'test'))
} LIMIT 5
"""
```

## 📚 **CONTEXT DOCUMENTS TO REFERENCE**

### **Primary Context (Read These)**
1. **`PROJECT_CONTEXT_SUMMARY_2025-08-07.md`** - Complete project overview
2. **`NEXT_STEPS_2025-08-07.md`** - Detailed roadmap
3. **`/lambda/neptune-stream-poller/INTEGRATION_COMPLETE.md`** - Integration details

### **Technical References**
1. **`NEPTUNE_OPENSEARCH_INTEGRATION_GUIDE.md`** - Technical implementation
2. **`NEPTUNE_OPENSEARCH_REUSE_ANALYSIS.md`** - Cost analysis
3. **`INFRASTRUCTURE_REFERENCE.md`** - Current AWS resources

### **Work History**
1. **Previous conversation summaries** in `/docs/status/`
2. **Lambda function READMEs** for component details
3. **CDK documentation** for infrastructure

## 🎯 **SUCCESS CRITERIA FOR NEXT SESSION**

### **Must Achieve**
- ✅ **Real ontology data analyzed** and documented
- ✅ **Filtering rules updated** with actual graph URIs and predicates
- ✅ **FTS queries tested** with real data
- ✅ **Cost impact measured** (before/after filtering)

### **Should Achieve**
- ✅ **Entity alignment prototype** working
- ✅ **Performance baseline** established
- ✅ **Monitoring enhanced** with real metrics

### **Could Achieve**
- ✅ **Multilanguage matching** implemented
- ✅ **Advanced FTS queries** optimized
- ✅ **Production deployment** planned

## 🚀 **CONVERSATION STARTERS**

### **To Resume Immediately**
- "Let's analyze the real ontology data in Neptune to update our filtering rules"
- "I want to test the Neptune-FTS integration we just deployed"
- "Let's check the current costs and verify the system is working"

### **If Issues Encountered**
- "The Lambda function isn't working - let's debug the logs"
- "Costs are higher than expected - let's investigate"
- "FTS queries aren't returning results - let's troubleshoot"

### **For Advanced Work**
- "Let's implement entity alignment using the FTS integration"
- "I want to optimize performance and add monitoring"
- "Let's plan the production deployment strategy"

## ⚡ **QUICK COMMANDS REFERENCE**

```bash
# Check system status
aws cloudformation describe-stacks --stack-name NeptuneQuickStart --query 'Stacks[0].StackStatus'

# Monitor Lambda
aws logs tail /aws/lambda/NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3 --follow

# Check costs
aws ce get-cost-and-usage --time-period Start=2025-08-07,End=2025-08-08 --granularity DAILY --metrics BlendedCost

# Deploy changes
cd /Users/chris/climate-risk-rag-aws/lambda/neptune-stream-poller && ./deploy.sh

# Enable/disable filtering
aws lambda update-function-configuration --function-name "NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3" --environment Variables='{"ONTOLOGY_FILTERING_ENABLED":"true"}'
```

---

## 🎯 **FINAL CONTEXT CHECK**

### **System State**: ✅ Neptune-FTS deployed and running
### **Next Priority**: 🎯 Analyze real ontology data
### **Cost Status**: 💰 Monitoring required, filtering disabled (safe)
### **Risk Level**: 🟡 Medium (need real data analysis)
### **Documentation**: 📚 Complete and comprehensive

**Ready to resume work with full context and clear next steps!**
