# OpenSearch Managed Service Migration Plan
**Date**: 2025-07-25  
**Project**: Climate Risk RAG System  
**Migration Type**: OpenSearch Serverless → Managed Service  

## 📊 **Migration Overview**

### **Goal**: Migrate from OpenSearch Serverless to Managed Service
### **Expected Savings**: ~$2,012/month (88% cost reduction)
### **Timeline**: 2-3 days (clean slate migration)
### **Downtime**: <30 minutes (with proper planning)

---

## 💰 **Cost Analysis**

### **Current Serverless Costs (Estimated)**
```
Base OCU (OpenSearch Compute Units):
- Vector Collection: 2 OCUs minimum = $700/month
- Search Collection: 2 OCUs minimum = $700/month
- Standby Replicas: +50% = $700/month
Total Compute: ~$2,100/month

Storage (estimated for 100K docs):
- Vector embeddings: ~50GB = $150/month
- Keyword index: ~10GB = $30/month
Total Storage: ~$180/month

TOTAL CURRENT: ~$2,280/month
```

### **Revised Production Sizing (Chunk-Based)**
```
Initial Load: 10K documents × 400 chunks/doc = 4M chunks
Vector Embeddings: 4M chunks × 1536 dims × 4 bytes = 24GB
Keyword Index: 4M chunks × ~500 bytes avg = 2GB  
Total Storage Needed: ~26GB (with growth buffer: 50GB)

Weekly Growth: 100 docs × 400 chunks = 40K chunks (~100MB/week)
Annual Growth: ~5GB/year

Query Load: 200-1000 searches/day = 8-42/hour (very low)
```

### **Managed Service Costs**
```
Data Nodes: 2 × t3.medium.search = $121.60/month
Master Nodes: 3 × t3.small.search = $131.40/month
Storage: 100GB GP3 = $10/month (50GB × 2 nodes)
Data Transfer: ~$5/month

TOTAL MANAGED: ~$268/month
SAVINGS: ~$2,012/month (88% reduction)
```

---

## 🏗️ **Recommended Managed Service Configuration**

### **Cluster Design**
```yaml
Domain Name: climate-risk-opensearch
Version: OpenSearch 2.11

Data Nodes:
  Instance Type: t3.medium.search  # Upgraded for 4M chunks
  Count: 2 (for HA)
  Storage: 50GB GP3 per node
  
Master Nodes:
  Instance Type: t3.small.search  
  Count: 3 (minimum for HA)
  
Network:
  VPC: vpc-051c21d88c7dc3819 (same as Neptune)
  Subnets: subnet-03d8bd6cf3491f38c, subnet-0c0be1dd59f70f70e
  Security Groups: sg-0c9e10b9cfb4c9eb0 (same as Lambda functions)
  
Access:
  Authentication: IAM-based
  Encryption: At rest and in transit
  Auto-tune: Enabled
```

---

## 📅 **Migration Timeline**

### **Day 1: Infrastructure Setup (4-5 hours)**
1. **Create OpenSearch Managed Domain** (20 minutes setup + 15-20 minutes creation)
2. **Configure VPC, Security Groups, IAM** (included in domain creation)
3. **Wait for cluster initialization** (~20 minutes)
4. **Create index templates and mappings** (30 minutes)
5. **Test connectivity** (15 minutes)

### **Day 2: Code Integration (3-4 hours)**
1. **Update Lambda environment variables** (30 minutes)
2. **Modify OpenSearch client configuration** (1 hour)
3. **Test with sample data** (1-2 hours)
4. **Update any hardcoded endpoints** (30 minutes)

### **Day 3: Validation & Cutover (2-3 hours)**
1. **End-to-end pipeline testing** (1-2 hours)
2. **Performance validation** (30 minutes)
3. **Switch production traffic** (15 minutes)
4. **Monitor and cleanup serverless** (30 minutes)

---

## 🔧 **Implementation Scripts**

### **Script 1: Domain Creation**
**File**: `scripts/create_opensearch_domain_revised.py`
**Purpose**: Create properly sized OpenSearch managed domain

**Usage**:
```bash
# Create domain
python3 scripts/create_opensearch_domain_revised.py

# Check status
python3 scripts/create_opensearch_domain_revised.py status

# Delete if needed
python3 scripts/create_opensearch_domain_revised.py delete
```

### **Script 2: Lambda Configuration**
**File**: `scripts/update_lambda_opensearch_config.py`
**Purpose**: Update Lambda functions and create index templates

**Usage**:
```bash
# Update all Lambda functions
python3 scripts/update_lambda_opensearch_config.py update-lambdas

# Set up index templates
python3 scripts/update_lambda_opensearch_config.py setup-indices

# Check migration status
python3 scripts/update_lambda_opensearch_config.py status

# Run complete setup
python3 scripts/update_lambda_opensearch_config.py all
```

### **Script 3: Serverless Cleanup**
**File**: `scripts/cleanup_serverless_opensearch.py`
**Purpose**: Clean up serverless collections after migration

**Usage**:
```bash
# Check cleanup status
python3 scripts/cleanup_serverless_opensearch.py status

# List current collections
python3 scripts/cleanup_serverless_opensearch.py list

# Clean up collections (with confirmation)
python3 scripts/cleanup_serverless_opensearch.py cleanup

# Show cost savings
python3 scripts/cleanup_serverless_opensearch.py savings
```

---

## 📋 **Migration Execution Checklist**

### **Pre-Migration**
- [ ] Confirm no critical data in current serverless collections
- [ ] Backup any configuration or templates needed
- [ ] Notify team of planned migration window
- [ ] Verify Lambda functions can be updated
- [ ] Review cost savings estimates

### **Day 1: Infrastructure**
- [ ] Run domain creation script
- [ ] Monitor creation progress (15-20 minutes)
- [ ] Verify domain is accessible
- [ ] Set up index templates
- [ ] Test basic connectivity

### **Day 2: Application Updates**
- [ ] Update Lambda environment variables
- [ ] Test OpenSearch client connections
- [ ] Verify index creation works
- [ ] Run sample pipeline test
- [ ] Check all functions updated correctly

### **Day 3: Validation & Cleanup**
- [ ] Run end-to-end pipeline test (3+ documents)
- [ ] Verify vector and keyword search work
- [ ] Monitor performance and errors
- [ ] Clean up serverless collections
- [ ] Verify cost reduction in billing

### **Post-Migration**
- [ ] Monitor system for 24-48 hours
- [ ] Document any issues or optimizations
- [ ] Update team on new endpoints
- [ ] Schedule regular cost reviews

---

## 🚨 **Rollback Plan**

### **If Issues Arise**:
1. **Keep serverless collections** until migration is validated
2. **Revert Lambda environment variables** to original serverless endpoints
3. **Delete managed domain** if needed to stop costs
4. **Total rollback time**: <30 minutes

### **Rollback Commands**:
```bash
# Revert Lambda functions (manual process)
# Update environment variables back to:
# OPENSEARCH_ENDPOINT: https://rui72a7agqnqo77vk34b.us-east-1.aoss.amazonaws.com
# OPENSEARCH_USE_SERVERLESS: true
# OPENSEARCH_SERVICE: aoss

# Delete managed domain
python3 scripts/create_opensearch_domain_revised.py delete
```

---

## 🎯 **Success Criteria**

### **Technical Success**
- [ ] OpenSearch managed domain is operational
- [ ] All Lambda functions connect successfully
- [ ] Vector search returns relevant results
- [ ] Keyword search functions properly
- [ ] End-to-end pipeline processes documents
- [ ] No errors in CloudWatch logs

### **Cost Success**
- [ ] Monthly OpenSearch costs reduced by >80%
- [ ] No unexpected charges from managed service
- [ ] Serverless collections successfully deleted
- [ ] Cost monitoring alerts updated

### **Performance Success**
- [ ] Search latency similar or better than serverless
- [ ] Indexing performance adequate for workload
- [ ] No capacity issues with 4M chunk projection
- [ ] Auto-scaling works as expected

---

## 📞 **Support & Troubleshooting**

### **Common Issues**
1. **Domain creation fails**: Check VPC/subnet configuration
2. **Lambda connection fails**: Verify security groups and IAM roles
3. **Index creation fails**: Check index templates and mappings
4. **Performance issues**: Consider instance type upgrades

### **Monitoring**
- **CloudWatch Metrics**: Monitor cluster health, search latency
- **OpenSearch Dashboards**: Available at domain endpoint/_dashboards
- **Cost Explorer**: Track actual vs. projected savings

### **Key Contacts**
- **AWS Support**: For infrastructure issues
- **Development Team**: For application integration issues
- **Cost Management**: For billing questions

---

## 💡 **Future Optimizations**

### **Phase 2 Considerations**
- **Instance Right-sizing**: Monitor usage and adjust instance types
- **Index Optimization**: Tune shard counts and replica settings
- **Cost Optimization**: Consider reserved instances for long-term savings
- **Performance Tuning**: Optimize query patterns and caching

### **Scaling Considerations**
- **Growth Planning**: Monitor storage and compute usage trends
- **Capacity Planning**: Plan for 100K document target
- **Performance Monitoring**: Set up alerts for latency and errors

---

**Document Version**: 1.0  
**Last Updated**: 2025-07-25  
**Next Review**: After migration completion
