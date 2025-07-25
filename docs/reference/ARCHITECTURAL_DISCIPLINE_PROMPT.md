# Architectural Discipline Prompt - Climate Risk RAG System
**Version**: 1.0  
**Date**: 2025-07-25  
**Purpose**: Ensure rigorous adherence to established architecture and patterns  

## Pre-Development Checklist Prompt

Before making ANY changes to the Climate Risk RAG system, use this prompt to ensure architectural discipline:

---

## 🏗️ **ARCHITECTURAL DISCIPLINE CHECKLIST**

### **INFRASTRUCTURE ALIGNMENT** ✅
- [ ] **Does this change align with the Infrastructure Reference Guide** (`docs/infrastructure/INFRASTRUCTURE_REFERENCE.md`)?
- [ ] **Are we using the correct subnets, security groups, and IAM permissions** as documented?
- [ ] **Does the messaging follow established patterns** (see `MESSAGING_ALIGNMENT_SUMMARY.md`)?
- [ ] **Are environment variables consistent** with deployed system naming conventions?

### **LAYER INTEGRITY** 🔒
- [ ] **Are we modifying any Lambda layers** (database-layer, knowledge-graph-layer, etc.)?
  - **If YES**: What is the strong justification? Have I requested permission?
  - **If NO**: Proceed with layer usage as-is
- [ ] **Are we adding new dependencies** that should be in a layer vs. inline?
- [ ] **Are we changing method signatures** in shared utilities (DatabaseManager, KnowledgeGraphManager)?

### **CODE CLEANLINESS** 🧹
- [ ] **Will this create any temporary/test files** that need cleanup?
- [ ] **Are we creating any `{filename}_updated`, `{filename}_fixed`, `{filename}_test` variants**?
  - **If YES**: Plan for consolidation back to single clean filename
- [ ] **Are we adding test code directly into production Lambda functions**?
  - **If YES**: Plan for removal after testing is complete

### **TESTING STRATEGY** 💰
- [ ] **Does this require testing with expensive services** (Textract ~$1.50/1000 pages, Comprehend ~$0.019/doc, Bedrock ~$0.002/doc)?
- [ ] **Can we test with existing processed documents** to avoid re-processing costs?
- [ ] **Are we starting tests with `invoke_pipeline_test.py`** for end-to-end consistency?
- [ ] **Have we limited test scope** to minimum viable validation (5-10 documents max)?

### **CHANGE JUSTIFICATION** 📋
- [ ] **What specific problem does this change solve**?
- [ ] **Why can't this be accomplished with existing infrastructure**?
- [ ] **Have I documented the impact** on existing components?
- [ ] **Is this change reversible** without data loss or system disruption?

---

## 🚫 **PROHIBITED ACTIONS WITHOUT APPROVAL**

### **Infrastructure Changes**
- Adding new SNS topics, SQS queues, or S3 buckets
- Modifying existing security group rules or subnet configurations
- Changing IAM roles or policies beyond documented patterns
- Creating new Lambda layers or modifying existing ones

### **Code Architecture Changes**
- Modifying DatabaseManager or KnowledgeGraphManager interfaces
- Changing standardized message formats or SNS topic names
- Adding new environment variables not following naming conventions
- Bypassing established error handling or logging patterns

### **Testing Violations**
- Running large-scale tests without cost estimation
- Creating permanent test artifacts in production buckets
- Testing with production data without proper cleanup procedures
- Skipping end-to-end pipeline validation

---

## ✅ **APPROVED PATTERNS TO FOLLOW**

### **Lambda Function Development**
```python
# ✅ CORRECT: Use existing layers and patterns
from utils.DatabaseManager import DatabaseManager
from utils.KnowledgeGraphManager import KnowledgeGraphManager

# ✅ CORRECT: Follow established error handling
try:
    result = db_manager.some_operation()
    logger.info(f"Operation successful: {result}")
except Exception as e:
    logger.error(f"Operation failed: {e}")
    raise

# ✅ CORRECT: Use standardized environment variables
topic_arn = os.environ.get('CHUNKS_READY_TOPIC_ARN')
```

### **Testing Approach**
```bash
# ✅ CORRECT: Start with end-to-end pipeline test
cd /Users/chris/climate-risk-rag-aws
python3 invoke_pipeline_test.py --num-documents 3 --force

# ✅ CORRECT: Test individual components with existing data
# Only after pipeline test confirms data availability
```

### **CDK Infrastructure**
```python
# ✅ CORRECT: Use documented subnet and security group IDs
vpc_subnets=ec2.SubnetSelection(subnets=[
    ec2.Subnet.from_subnet_id(self, "DatabaseSubnet1", subnet_id="subnet-0e9efc5fdf29e9da0"),
    ec2.Subnet.from_subnet_id(self, "DatabaseSubnet2", subnet_id="subnet-00efdcc220a613ae3")
])

# ✅ CORRECT: Use existing layers by ARN
layers=[
    lambda_.LayerVersion.from_layer_version_arn(
        self, "DatabaseLayer",
        layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:climate-risk-core-utilities:2"
    )
]
```

---

## 🔄 **DEVELOPMENT WORKFLOW**

### **1. Planning Phase**
- Review this checklist completely
- Identify required infrastructure components
- Estimate testing costs and scope
- Document expected changes and impacts

### **2. Implementation Phase**
- Use existing patterns and layers
- Follow established naming conventions
- Implement proper error handling and logging
- Avoid creating temporary file variants

### **3. Testing Phase**
- Start with `invoke_pipeline_test.py`
- Use minimal document sets (3-5 documents)
- Test with existing processed data when possible
- Monitor AWS costs during testing

### **4. Cleanup Phase**
- Remove any temporary test code
- Consolidate any file variants to single clean versions
- Update documentation if patterns changed
- Commit clean, production-ready code

### **5. Validation Phase**
- Verify end-to-end pipeline still works
- Confirm no breaking changes to existing components
- Validate cost impact is within expected bounds
- Document any new patterns for future reference

---

## 💡 **DECISION FRAMEWORK**

### **When to Seek Approval**
- Any infrastructure addition or modification
- Changes to shared layers or utilities
- New testing approaches that may incur significant costs
- Architectural patterns that deviate from established norms

### **When to Proceed Independently**
- Bug fixes within existing Lambda functions
- Adding logging or monitoring within established patterns
- Refactoring code without changing interfaces
- Documentation updates and improvements

### **Cost Thresholds**
- **Green Light** (<$5): Proceed with standard testing
- **Yellow Light** ($5-$25): Document cost justification
- **Red Light** (>$25): Require explicit approval before testing

---

## 📚 **REFERENCE DOCUMENTS**

### **Required Reading Before Changes**
- `docs/infrastructure/INFRASTRUCTURE_REFERENCE.md` - Complete infrastructure mappings
- `docs/infrastructure/MESSAGING_ALIGNMENT_SUMMARY.md` - SNS topic and messaging patterns
- `docs/status/PROJECT_CONTEXT_SUMMARY_*.md` - Latest project status and architecture

### **Testing Guidelines**
- `docs/testing/TESTING_GUIDE.md` - Testing strategies and cost management
- `invoke_pipeline_test.py` - Primary testing entry point
- Cost thresholds and monitoring procedures

### **Development Patterns**
- `docs/design/LAMBDA_LAYER_DESIGN_UPDATED.md` - Layer usage patterns
- Existing Lambda function implementations as reference
- CDK patterns in `cdk/app_production_ready_fixed.py`

---

## 🎯 **SUCCESS CRITERIA**

A change is considered successful when:
- ✅ All infrastructure aligns with reference documentation
- ✅ No temporary files or code variants remain
- ✅ End-to-end pipeline test passes
- ✅ Cost impact is within expected bounds
- ✅ No breaking changes to existing functionality
- ✅ Documentation is updated appropriately

---

**Remember**: We've built a solid, working system. The goal is to enhance it thoughtfully while maintaining the architectural integrity that makes it reliable and cost-effective.

**When in doubt**: Ask first, implement second. It's better to discuss architectural decisions upfront than to refactor later.
