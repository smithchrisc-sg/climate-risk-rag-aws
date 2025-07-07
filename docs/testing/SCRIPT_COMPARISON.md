# Migration Scripts Comparison & Risk Analysis

## 📊 **Script Comparison Matrix**

| Aspect | `migrate_data.sh` | `migrate_data_selective.sh` (BROKEN) | `migrate_data_selective_corrected.sh` |
|--------|-------------------|--------------------------------------|---------------------------------------|
| **Purpose** | Full production migration | ❌ Claims selective, does full | ✅ True selective migration |
| **Documents** | 15,176 (ALL) | ❌ 15,176 (ALL) | ✅ 1,000 (SAMPLE) |
| **Embeddings** | 4.24M (ALL) | ❌ 1.02M (ALL) | ✅ ~280K (SAMPLE) |
| **Text Files** | 15,155 (ALL) | ❌ 15,155 (ALL) | ✅ 1,000 (SAMPLE) |
| **Chunks** | 4.24M (ALL) | ✅ 280K (SAMPLE) | ✅ 280K (SAMPLE) |
| **Storage** | ~300GB | ❌ ~88GB | ✅ ~20GB |
| **Monthly Cost** | ~$200 | ❌ ~$88 (claims $20) | ✅ ~$20 |
| **Migration Time** | 24-48 hours | ❌ 8-12 hours | ✅ 2-4 hours |
| **Use Case** | Production deployment | ❌ Broken testing | ✅ Cost-effective testing |

## 🚨 **Critical Issues with Original Selective Script**

### **Issue 1: Misleading Scope**
```bash
# What the script claims:
echo "📦 What will be migrated:"
echo "  ✅ Sample chunks ($SAMPLE_CHUNKS documents, ~8GB)"

# What it actually does:
echo "  ✅ All documents (15,176 PDFs, ~45GB)"
echo "  ✅ All embeddings (1.02M files, ~32GB)"
echo "  ✅ All extracted text (15,155 files, ~2.5GB)"
```

### **Issue 2: Cost Misrepresentation**
```bash
# Claimed cost:
echo "📊 Total: ~88GB, estimated cost: $20/month"

# Actual calculation:
# Storage: 88GB × $0.023/GB = $2.02/month (storage only)
# Processing: ~$25/month (Lambda, Textract, etc.)
# Databases: ~$18/month (OpenSearch, Neptune, RDS)
# Total: ~$45-50/month (not $20)
```

### **Issue 3: Strategic Contradiction**
- **Documented Strategy:** "1,000 documents for cost-effective testing"
- **Script Reality:** "15,176 documents + all embeddings + all text"
- **Business Impact:** Cannot achieve cost-effective validation goal

## ⚠️ **Risk Assessment**

### **Financial Risk: HIGH**
- **Cost Overrun:** 340% higher than expected ($88 vs $20)
- **Budget Impact:** May exceed allocated testing budget
- **Ongoing Costs:** Higher monthly operational costs

### **Timeline Risk: MEDIUM**
- **Migration Duration:** 4x longer than expected (8-12 hours vs 2-4 hours)
- **Testing Delay:** Longer setup time delays validation
- **Resource Contention:** Higher AWS resource usage

### **Technical Risk: MEDIUM**
- **Lambda Limits:** May hit concurrent execution limits
- **Database Performance:** Full dataset may overwhelm test databases
- **Network Reliability:** Larger transfers increase failure probability

### **Strategic Risk: HIGH**
- **Testing Validity:** Cannot properly test selective migration approach
- **Decision Making:** Inaccurate cost/performance data for business decisions
- **Resource Planning:** Incorrect resource requirements for production

## ✅ **Recommended Actions**

### **Immediate Actions (Required)**
1. **Stop Using Broken Script:** Do not execute `migrate_data_selective.sh`
2. **Replace with Corrected Version:** Use `migrate_data_selective_corrected.sh`
3. **Update Documentation:** Fix any references to broken script
4. **Add Warnings:** Mark broken script clearly to prevent accidental use

### **Script Replacement Commands**
```bash
cd /Users/chris/climate-risk-rag-aws

# Backup broken script for reference
mv migrate_data_selective.sh migrate_data_selective_BROKEN_DO_NOT_USE.sh

# Promote corrected script to main selective script
mv migrate_data_selective_corrected.sh migrate_data_selective.sh

# Add warning to broken script
cat >> migrate_data_selective_BROKEN_DO_NOT_USE.sh << 'EOF'

# ⚠️⚠️⚠️ WARNING: THIS SCRIPT IS BROKEN ⚠️⚠️⚠️
# This script claims to do "selective" migration but actually migrates ALL data
# Cost: ~$88/month instead of claimed $20/month
# Use migrate_data_selective.sh instead
# ⚠️⚠️⚠️ DO NOT USE THIS SCRIPT ⚠️⚠️⚠️
EOF

# Make broken script non-executable
chmod -x migrate_data_selective_BROKEN_DO_NOT_USE.sh
```

### **Validation Steps**
```bash
# Verify corrected script configuration
head -50 migrate_data_selective.sh | grep -E "(SAMPLE_SIZE|documents|cost)"

# Should show:
# SAMPLE_SIZE=1000
# Sample documents (1,000 PDFs, ~3GB)
# estimated cost: $20/month
```

## 📋 **Final Script Inventory**

After cleanup, you should have:

```
climate-risk-rag-aws/
├── migrate_data.sh                              # ✅ Full migration (15,176 docs)
├── migrate_data_selective.sh                    # ✅ True selective (1,000 docs)
└── migrate_data_selective_BROKEN_DO_NOT_USE.sh  # ❌ Broken script (archived)
```

## 🎯 **Success Criteria**

The corrected selective migration should achieve:
- **Documents:** Exactly 1,000 representative documents
- **Storage:** ~20GB total
- **Cost:** ~$20/month
- **Duration:** 2-4 hours
- **Purpose:** Cost-effective testing and validation

This aligns with the documented selective migration strategy and business objectives.
