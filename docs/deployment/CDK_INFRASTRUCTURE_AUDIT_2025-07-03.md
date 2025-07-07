# CDK Infrastructure Audit - TextExtractor Pipeline
## Date: 2025-07-03T21:30:00Z

## 🎯 **Audit Objective**
Ensure all manual configurations made during TextExtractor deployment are captured in CDK infrastructure code to enable complete recreation from scratch.

## 📊 **Current Infrastructure State**

### **✅ What's Already in CDK**
1. **TextExtractor Messaging Stack** (`textextractor_messaging_stack.py`)
   - SNS Topic for Textract completion notifications
   - SQS Queue for async processing
   - Dead Letter Queue for error handling
   - Basic IAM roles for Lambda and Textract service
   - Queue subscription to SNS topic

2. **Networking Stack** (`networking_stack.py`)
   - VPC with public, private, and isolated subnets
   - Security groups (basic)
   - NAT Gateway and Internet Gateway
   - Route tables

3. **Data Stack** (`data_stack.py`)
   - RDS PostgreSQL instance
   - OpenSearch cluster
   - Neptune graph database

## ❌ **Critical Gaps in CDK (Manual Configurations)**

### **1. Lambda Security Group - MISSING**
**Current Manual Configuration:**
```
Security Group ID: sg-08518057bfb59e735
Name: solve-global-kr-lambda-sg
VPC: vpc-051c21d88c7dc3819
Egress Rules:
  - TCP 5432 → sg-09bc56a537bf7ac12 (RDS access)
  - TCP 443 → 0.0.0.0/0 (HTTPS for AWS APIs)
```

**CDK Gap:** No Lambda-specific security group defined in CDK

### **2. RDS Security Group Rules - INCOMPLETE**
**Current Manual Configuration:**
```
RDS Security Group: sg-09bc56a537bf7ac12
Additional Ingress Rule:
  - TCP 5432 ← sg-08518057bfb59e735 (Lambda access)
```

**CDK Gap:** Lambda → RDS security group rule not defined

### **3. Lambda Functions - COMPLETELY MISSING**
**Current Manual Deployment:**
- TextExtractor Initiator Lambda
- TextExtractor Processor Lambda  
- TextExtractor Trigger Lambda
- VPC configuration for Lambda functions
- Environment variables
- Event source mappings (SQS → Lambda)

**CDK Gap:** No Lambda functions defined in CDK at all

### **4. Lambda Layer Dependencies - MISSING**
**Current Manual Process:**
- Platform-specific psycopg2 binary installation
- Utility module packaging
- Dependency management

**CDK Gap:** No automated dependency management

## 🔧 **Required CDK Updates**

### **Priority 1: Critical Infrastructure Gaps**

#### **1. Update TextExtractor Messaging Stack**
Add Lambda security group and proper RDS access:

```python
# Add to textextractor_messaging_stack.py

# Lambda Security Group
self.lambda_security_group = ec2.SecurityGroup(
    self, "LambdaSecurityGroup",
    vpc=vpc,  # Need VPC reference
    security_group_name="solve-global-kr-lambda-sg",
    description="Security group for TextExtractor Lambda functions",
    allow_all_outbound=False
)

# Lambda → RDS access
self.lambda_security_group.add_egress_rule(
    peer=ec2.Peer.security_group_id(rds_security_group_id),
    connection=ec2.Port.tcp(5432),
    description="PostgreSQL access"
)

# Lambda → AWS APIs access
self.lambda_security_group.add_egress_rule(
    peer=ec2.Peer.any_ipv4(),
    connection=ec2.Port.tcp(443),
    description="HTTPS for AWS API calls"
)
```

#### **2. Create TextExtractor Lambda Stack**
Complete Lambda function definitions with proper VPC configuration:

```python
# New file: textextractor_lambda_stack_fixed.py

class TextExtractorLambdaStack(Stack):
    def __init__(self, scope, construct_id, vpc, messaging_stack, data_stack, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        # Lambda functions with proper VPC configuration
        self.initiator = lambda_.Function(
            self, "TextExtractorInitiator",
            function_name="solve-global-kr-textextractor-initiator",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="text_extractor_initiator.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/text_extractor_initiator"),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            security_groups=[messaging_stack.lambda_security_group],
            environment={
                "DATABASE_URL": data_stack.database_url,
                "TEXTRACT_SNS_TOPIC_ARN": messaging_stack.textract_completion_topic.topic_arn,
                # ... other env vars
            },
            timeout=Duration.minutes(5),
            memory_size=1024
        )
```

#### **3. Fix Stack Dependencies**
Update main CDK app to properly reference VPC and other resources:

```python
# Update app.py
textextractor_lambda_stack = TextExtractorLambdaStack(
    app,
    f"{project_name}-textextractor-lambda",
    vpc=networking_stack.vpc,
    messaging_stack=textextractor_messaging_stack,
    data_stack=data_stack,
    env=env
)
```

### **Priority 2: Automation & Dependencies**

#### **4. Lambda Layer Management**
Add proper Lambda layer with dependencies:

```python
# Add to lambda stack
self.dependencies_layer = lambda_.LayerVersion(
    self, "TextExtractorDependencies",
    layer_version_name="textextractor-dependencies",
    code=lambda_.Code.from_asset("../layers/build/textextractor-deps"),
    compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
    description="TextExtractor dependencies including psycopg2"
)
```

#### **5. Event Source Mappings**
Add SQS → Lambda triggers:

```python
# Add to lambda stack
self.processor.add_event_source(
    lambda_event_sources.SqsEventSource(
        messaging_stack.textextractor_queue,
        batch_size=1,
        max_batching_window=Duration.seconds(5),
        report_batch_item_failures=True
    )
)
```

## 📋 **Implementation Plan**

### **Phase 1: Fix Critical Gaps (Immediate)**
1. **Update Messaging Stack** - Add Lambda security group
2. **Update Data Stack** - Add RDS security group rules  
3. **Create Lambda Stack** - Complete Lambda function definitions
4. **Update Main App** - Fix stack dependencies and references

### **Phase 2: Automation (Next Session)**
1. **Lambda Layer Build** - Automate dependency packaging
2. **Deployment Scripts** - CDK-based deployment
3. **Environment Management** - Parameterize configurations
4. **Testing Integration** - Automated testing in CDK

### **Phase 3: Production Readiness (Future)**
1. **Multi-Environment** - Dev/Staging/Prod configurations
2. **Monitoring** - CloudWatch dashboards and alarms
3. **Security Hardening** - Least privilege IAM policies
4. **Cost Optimization** - Resource tagging and monitoring

## 🚨 **Immediate Action Items**

### **1. Create Fixed CDK Stacks**
- Update `textextractor_messaging_stack.py` with security groups
- Create `textextractor_lambda_stack_complete.py` with full Lambda definitions
- Update `app.py` with proper stack dependencies

### **2. Test CDK Deployment**
- Deploy to test environment
- Verify all manual configurations are captured
- Test complete pipeline functionality

### **3. Create Deployment Documentation**
- Step-by-step CDK deployment guide
- Environment setup instructions
- Troubleshooting guide for common issues

## 🔍 **Verification Checklist**

### **Infrastructure Recreation Test**
- [ ] Deploy from scratch in new AWS account/region
- [ ] Verify all security groups and rules created
- [ ] Confirm Lambda functions have proper VPC access
- [ ] Test database connectivity from Lambda
- [ ] Validate complete async pipeline functionality

### **Configuration Completeness**
- [ ] All manual security group rules in CDK
- [ ] All Lambda environment variables defined
- [ ] All IAM permissions properly scoped
- [ ] All VPC configurations captured
- [ ] All event source mappings defined

## 📊 **Current vs Target State**

### **Current State (Manual + CDK)**
```
✅ SNS/SQS Infrastructure (CDK)
✅ Basic IAM Roles (CDK)
✅ VPC/Networking (CDK)
✅ RDS Database (CDK)
❌ Lambda Security Group (Manual)
❌ Lambda Functions (Manual)
❌ VPC Configuration (Manual)
❌ Event Mappings (Manual)
```

### **Target State (100% CDK)**
```
✅ SNS/SQS Infrastructure (CDK)
✅ Complete IAM Roles (CDK)
✅ VPC/Networking (CDK)
✅ RDS Database (CDK)
✅ Lambda Security Group (CDK)
✅ Lambda Functions (CDK)
✅ VPC Configuration (CDK)
✅ Event Mappings (CDK)
```

## 🎯 **Success Criteria**

1. **Complete CDK Recreation**: Entire infrastructure deployable from CDK alone
2. **No Manual Steps**: Zero manual configuration required post-deployment
3. **Functional Validation**: Complete TextExtractor pipeline working after CDK deployment
4. **Documentation**: Clear deployment guide for future use
5. **Repeatability**: Consistent deployment across environments

---

**Status**: 🔧 **CDK INFRASTRUCTURE GAPS IDENTIFIED - UPDATES REQUIRED**
**Priority**: **HIGH** - Required for production deployment repeatability
**Estimated Effort**: 2-3 hours to implement all fixes
**Next Action**: Implement Priority 1 CDK updates
