# Architectural Discipline Prompt - Climate Risk RAG System
**Version**: 2.0  
**Date**: 2025-08-11  
**Purpose**: Ensure rigorous adherence to established architecture and patterns  
**Updated**: Incorporates lessons learned from Neptune FTS integration challenges  

## Pre-Development Checklist Prompt

Before making ANY changes to the Climate Risk RAG system:

---

## 🏗️ **ARCHITECTURAL DISCIPLINE CHECKLIST**

### **INFRASTRUCTURE ALIGNMENT** ✅
- [ ] **Does this change align with the Infrastructure Reference Guide** (`docs/infrastructure/INFRASTRUCTURE_REFERENCE.md`)?
- [ ] **Are we using the correct subnets, security groups, and IAM permissions** as documented?
- [ ] **Does the messaging follow established patterns** (see `MESSAGING_ALIGNMENT_SUMMARY.md`)?
- [ ] **Are environment variables consistent** with deployed system naming conventions?

### **🚨 CRITICAL: SERVICE INTEGRATION CHECKS** 🔗
- [ ] **Are we integrating services that require IAM authentication consistency**?
  - **Neptune + OpenSearch**: Both MUST use IAM auth or both MUST use basic auth
  - **Lambda + OpenSearch**: Lambda role MUST be mapped in OpenSearch FGAC
  - **Cross-service calls**: All calling principals MUST have proper permissions
- [ ] **Are security groups configured for service-to-service communication**?
  - **Neptune → OpenSearch**: Neptune SG must allow outbound HTTPS (443)
  - **OpenSearch**: Must allow inbound HTTPS (443) from calling service SGs
  - **Lambda → Neptune**: Lambda SG must allow outbound to Neptune port (8182)
- [ ] **Are we modifying authentication methods on existing services**?
  - **If YES**: Document impact on ALL dependent services
  - **If NO**: Verify current auth methods are compatible

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

### **🔍 METHODICAL PROBLEM-SOLVING APPROACH** 🧠
- [ ] **Am I being conservative and methodical** rather than making rapid changes?
- [ ] **Have I isolated the root cause** before implementing solutions?
- [ ] **Am I testing ONE change at a time** rather than multiple simultaneous changes?
- [ ] **Have I documented the current working state** before making modifications?
- [ ] **Am I preserving working configurations** while troubleshooting?
- [ ] **Have I created proper version control** (git commits) for rollback capability?

---

## 🚫 **PROHIBITED ACTIONS WITHOUT APPROVAL**

### **Infrastructure Changes**
- Adding new SNS topics, SQS queues, or S3 buckets
- Modifying existing security group rules or subnet configurations
- Changing IAM roles or policies beyond documented patterns
- Creating new Lambda layers or modifying existing ones

### **🚨 CRITICAL: Service Integration Anti-Patterns**
- **NEVER change authentication methods** on one service without considering dependent services
- **NEVER modify security groups** without verifying all service-to-service connectivity
- **NEVER assume IAM permissions** work without testing the complete authentication chain
- **NEVER disable/enable IAM authentication** without understanding the full impact
- **NEVER flip-flop between configurations** - be methodical and test thoroughly
- **NEVER make multiple simultaneous changes** when troubleshooting integration issues

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

### **🔗 Service Integration Patterns**
```python
# ✅ CORRECT: Verify authentication compatibility before integration
# Neptune with IAM auth + OpenSearch with FGAC = Compatible
# Neptune without IAM auth + OpenSearch with FGAC = Authentication mismatch

# ✅ CORRECT: Check security group connectivity
# Neptune SG: Allow outbound HTTPS (443) to OpenSearch
# OpenSearch SG: Allow inbound HTTPS (443) from Neptune SG

# ✅ CORRECT: Verify IAM role mapping in OpenSearch FGAC
# All calling principals must be mapped to appropriate OpenSearch roles
```

### **🧪 Integration Testing Approach**
```bash
# ✅ CORRECT: Test connectivity first
curl -k -u "admin:password" "https://opensearch-endpoint/_cluster/health"

# ✅ CORRECT: Test authentication chain
aws lambda invoke --function-name test-function response.json

# ✅ CORRECT: Test one component at a time
# 1. Basic connectivity
# 2. Authentication
# 3. Service integration
# 4. End-to-end functionality
```

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
- **Map service dependencies and authentication requirements**
- **Document current working state before changes**
- Estimate testing costs and scope
- Document expected changes and impacts

### **2. Implementation Phase**
- Use existing patterns and layers
- Follow established naming conventions
- **Make ONE change at a time when troubleshooting**
- **Test each change before proceeding to the next**
- Implement proper error handling and logging
- Avoid creating temporary file variants

### **3. Testing Phase**
- Start with `invoke_pipeline_test.py`
- **Test service connectivity before integration**
- **Verify authentication chains work end-to-end**
- Use minimal document sets (3-5 documents)
- Test with existing processed data when possible
- Monitor AWS costs during testing

### **4. Troubleshooting Phase (When Things Go Wrong)**
- **STOP making changes and assess the current state**
- **Document the exact error messages and symptoms**
- **Identify the root cause before implementing solutions**
- **Test fixes in isolation, one at a time**
- **Preserve working configurations while debugging**
- **Use version control to enable quick rollbacks**

### **5. Cleanup Phase**
- Remove any temporary test code
- Consolidate any file variants to single clean versions
- Update documentation if patterns changed
- Commit clean, production-ready code

### **6. Validation Phase**
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
- **Service integration changes that affect authentication methods**
- **Security group modifications that impact service connectivity**

### **When to Proceed Independently**
- Bug fixes within existing Lambda functions
- Adding logging or monitoring within established patterns
- Refactoring code without changing interfaces
- Documentation updates and improvements

### **🚨 Service Integration Decision Tree**
```
Are you integrating two AWS services?
├─ YES → Do they both use the same authentication method?
│  ├─ YES → Proceed with connectivity and permission checks
│  └─ NO → STOP - Seek approval for authentication alignment
└─ NO → Follow standard development workflow
```

### **Cost Thresholds**
- **Green Light** (<$5): Proceed with standard testing
- **Yellow Light** ($5-$25): Document cost justification
- **Red Light** (>$25): Require explicit approval before testing

### **🔧 Troubleshooting Decision Framework**
1. **Connectivity Issue**: Check security groups and network ACLs first
2. **Authentication Issue**: Verify IAM roles, policies, and service-specific auth settings
3. **Permission Issue**: Check both IAM policies AND service-specific access controls (e.g., OpenSearch FGAC)
4. **Integration Issue**: Verify both services use compatible authentication methods
5. **Unknown Issue**: Document symptoms, test one component at a time

---

## 📚 **REFERENCE DOCUMENTS**

### **Required Reading Before Changes**
- `docs/infrastructure/INFRASTRUCTURE_REFERENCE.md` - Complete infrastructure mappings
- `docs/infrastructure/MESSAGING_ALIGNMENT_SUMMARY.md` - SNS topic and messaging patterns
- `docs/status/PROJECT_CONTEXT_SUMMARY_*.md` - Latest project status and architecture
- **`CURRENT_STATE_ARCHITECTURE_2025-08-11.md`** - Complete current system architecture
- **`docs/status/PROJECT_CONTEXT_SUMMARY_2025-08-11.md`** - Latest working configuration

### **Testing Guidelines**
- `docs/testing/TESTING_GUIDE.md` - Testing strategies and cost management
- `invoke_pipeline_test.py` - Primary testing entry point
- Cost thresholds and monitoring procedures

### **Development Patterns**
- `docs/design/LAMBDA_LAYER_DESIGN_UPDATED.md` - Layer usage patterns
- Existing Lambda function implementations as reference
- CDK patterns in `cdk/app_production_ready_fixed.py`

### **🎓 Lessons Learned from Neptune FTS Integration**
- **Authentication Consistency**: Services must use compatible auth methods
- **Security Group Dependencies**: Service-to-service connectivity requires explicit rules
- **IAM vs Service-Specific Access**: Both layers must be configured (e.g., IAM + OpenSearch FGAC)
- **Methodical Troubleshooting**: One change at a time prevents cascading issues
- **Version Control**: Clean git history enables safe rollbacks
- **Testing Environment**: Use Lambda functions for testing when EC2 has compatibility issues

---

## 🎯 **SUCCESS CRITERIA**

A change is considered successful when:
- ✅ All infrastructure aligns with reference documentation
- ✅ **Service integrations use compatible authentication methods**
- ✅ **Security groups allow required service-to-service connectivity**
- ✅ **IAM roles are properly mapped in service-specific access controls**
- ✅ No temporary files or code variants remain
- ✅ End-to-end pipeline test passes
- ✅ Cost impact is within expected bounds
- ✅ No breaking changes to existing functionality
- ✅ Documentation is updated appropriately
- ✅ **Changes are methodical and reversible**

---

## 🧠 **CORE PRINCIPLES FOR COMPLEX INTEGRATIONS**

### **The "Conservative and Methodical" Approach**
1. **Document the current working state** before making any changes
2. **Make ONE change at a time** when troubleshooting
3. **Test each change thoroughly** before proceeding
4. **Preserve working configurations** while debugging
5. **Use version control** for safe rollbacks
6. **Understand the root cause** before implementing solutions

### **Service Integration Golden Rules**
1. **Authentication Consistency**: All integrated services must use compatible auth methods
2. **Network Connectivity**: Security groups must explicitly allow service-to-service communication
3. **Permission Layers**: Configure BOTH IAM permissions AND service-specific access controls
4. **Testing Strategy**: Test connectivity → authentication → permissions → integration
5. **Rollback Plan**: Always have a way to revert to the last working state

---

**Remember**: We've built a solid, working system. The goal is to enhance it thoughtfully while maintaining the architectural integrity that makes it reliable and cost-effective.

**When integrating services**: Verify authentication compatibility, security group connectivity, and permission layers BEFORE attempting integration.

**When troubleshooting**: Be conservative and methodical. One change at a time. Document everything. Test thoroughly.

If you must update a layer - and you have permission - Always use the standard build scripts to update layers. Same with lambda - always use standard build and deployment scripts.

**When in doubt**: Ask first, implement second. It's better to discuss architectural decisions upfront than to refactor later.

**Note**: python3 is required

---

## 🚨 **EMERGENCY ROLLBACK PROCEDURES**

If a change breaks the system:
1. **STOP making additional changes immediately**
2. **Document the current error state and symptoms**
3. **Use git to rollback to the last working commit**
4. **Restore any modified AWS configurations to previous state**
5. **Test that the rollback restored functionality**
6. **Analyze what went wrong before attempting fixes**

**Remember**: It's better to have a working system with the old approach than a broken system with the new approach.
