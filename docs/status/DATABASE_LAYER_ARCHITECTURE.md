# Database Layer Architecture & Refactoring Plan

## 🎯 **Target Architecture**

### **Dedicated Database Layer: `database-core-layer`**
**Purpose**: Single-focused layer containing ONLY database access functionality

**Contents**:
```
database-core-layer/
├── python/
│   └── utils/
│       ├── __init__.py
│       ├── DatabaseManager.py      # Core database connection & operations
│       ├── DocumentIDManager.py    # Document ID management
│       └── database_config.py      # Database configuration utilities
├── requirements.txt                # psycopg2-binary, boto3 (minimal)
└── layer_info.json                # Layer metadata
```

**What's EXCLUDED** (moved to other layers):
- OpenSearch dependencies
- Vector/embedding utilities  
- NLP processing utilities
- S3 utilities (unless database-specific)
- Any non-database functionality

### **Standard Environment Variables**
**Required for ALL Lambda functions**:
```bash
# Database Connection
DATABASE_SECRET_NAME="rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863"
DB_HOST="solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com"
DB_NAME="climate_risk_rag"
DB_PORT="5432"

# Connection Method (NO hardcoded passwords)
DATABASE_CONNECTION_METHOD="secrets_manager"
```

### **Standard VPC Configuration**
**Required for ALL Lambda functions**:
```bash
# VPC Configuration
VPC_ID="vpc-051c21d88c7dc3819"
SECURITY_GROUPS=["sg-database-access"]  # New dedicated security group
SUBNETS=["subnet-03d8bd6cf3491f38c", "subnet-0c0be1dd59f70f70e"]
```

### **Standard Import Pattern**
**Required for ALL Lambda functions**:
```python
# Standard database imports (identical across all functions)
try:
    from utils.DatabaseManager import DatabaseManager
    from utils.DocumentIDManager import DocumentIDManager
    logger.info("Database utilities imported successfully")
except ImportError as e:
    logger.error(f"Failed to import database utilities: {e}")
    raise ImportError(f"Database utilities import failed: {e}")
```

## 📋 **Current State Analysis**

### **Existing Layers to Refactor**:
1. `climate-risk-core-utilities:12` - Contains mixed utilities
2. `database-dependencies:2` - Contains database + other dependencies  
3. `database-dependencies-pipeline:3` - Contains database + pipeline utilities

### **Functions to Standardize**:
| Function | Current Layer | Current Security Group | Status |
|----------|---------------|----------------------|--------|
| text-chunker-pipeline | core:12, db:2 | sg-099296a5c809e8d9d | Mixed config |
| nlp-processor | core:12, db-pipeline:3 | none | No VPC |
| nlp-worker | core:12, db-pipeline:3 | sg-099296a5c809e8d9d | Mixed config |
| vector-embeddings-* | core:12, db-pipeline:3 | sg-0709acdc3f0cccd7f | Different SG |
| cleanup-service | core:12, db:2, opensearch:2 | sg-099296a5c809e8d9d | Mixed layers |
| pipeline-test | core:12, db:2 | sg-099296a5c809e8d9d | Mixed config |

## 🚀 **Refactoring Plan**

### **Phase 1: Create Dedicated Database Layer**

#### **Step 1.1: Extract Database Components**
```bash
# Create new layer structure
mkdir -p database-core-layer/python/utils

# Extract ONLY database components from existing layers
cp utils/DatabaseManager.py database-core-layer/python/utils/
cp utils/DocumentIDManager.py database-core-layer/python/utils/
```

#### **Step 1.2: Clean Database Components**
```python
# DatabaseManager.py - Focus ONLY on database operations
class DatabaseManager:
    def __init__(self):
        # Use ONLY Secrets Manager (no hardcoded passwords)
        self.secret_name = os.environ['DATABASE_SECRET_NAME']
        self.db_host = os.environ['DB_HOST']
        self.db_name = os.environ['DB_NAME']
        self.db_port = os.environ['DB_PORT']
        
    def _get_database_credentials(self):
        # Always use Secrets Manager
        return self._get_secret_value(self.secret_name)
        
    def get_connection_string(self):
        # Build connection string from secrets
        creds = self._get_database_credentials()
        return f"postgresql://{creds['username']}:{creds['password']}@{self.db_host}:{self.db_port}/{self.db_name}?sslmode=require"
```

#### **Step 1.3: Create Layer Package**
```bash
# requirements.txt (minimal dependencies)
psycopg2-binary==2.9.7
boto3>=1.28.0

# Build and deploy layer
cd database-core-layer
zip -r database-core-layer.zip .
aws lambda publish-layer-version \
  --layer-name database-core-layer \
  --zip-file fileb://database-core-layer.zip \
  --compatible-runtimes python3.11
```

### **Phase 2: Create Standard Security Group**

#### **Step 2.1: CDK Security Group Definition**
```typescript
// In CDK stack
const databaseAccessSecurityGroup = new ec2.SecurityGroup(this, 'DatabaseAccessSG', {
  vpc: vpc,
  description: 'Security group for Lambda functions accessing RDS database',
  securityGroupName: 'lambda-database-access'
});

// Allow outbound to RDS
databaseAccessSecurityGroup.addEgressRule(
  ec2.Peer.ipv4(vpc.vpcCidrBlock),
  ec2.Port.tcp(5432),
  'Allow outbound to RDS PostgreSQL'
);
```

#### **Step 2.2: Update RDS Security Group**
```typescript
// Update RDS security group to allow Lambda access
rdsSecurityGroup.addIngressRule(
  databaseAccessSecurityGroup,
  ec2.Port.tcp(5432),
  'Allow Lambda database access'
);
```

### **Phase 3: Standardize Lambda Functions**

#### **Step 3.1: Function Update Template**
```typescript
// CDK Lambda function template
const lambdaFunction = new lambda.Function(this, 'FunctionName', {
  // Standard configuration
  layers: [
    databaseCoreLayer,  // New dedicated database layer
    // Other function-specific layers
  ],
  
  // Standard VPC configuration
  vpc: vpc,
  securityGroups: [databaseAccessSecurityGroup],
  vpcSubnets: {
    subnets: [privateSubnet1, privateSubnet2]
  },
  
  // Standard environment variables
  environment: {
    DATABASE_SECRET_NAME: databaseSecret.secretName,
    DB_HOST: rdsInstance.instanceEndpoint.hostname,
    DB_NAME: 'climate_risk_rag',
    DB_PORT: '5432',
    DATABASE_CONNECTION_METHOD: 'secrets_manager',
    // Function-specific variables...
  }
});
```

## 📋 **Function-by-Function Refactoring Plan**

### **Priority 1: Critical Functions (Week 1)**

#### **pipeline-test-function**
```bash
# Current issues: Mixed layers, hardcoded password
# Actions:
1. Update to use database-core-layer
2. Remove hardcoded DATABASE_URL
3. Add standard environment variables
4. Update VPC to use standard security group
5. Test database connectivity
```

#### **cleanup-service**
```bash
# Current issues: Multiple mixed layers
# Actions:
1. Replace database-dependencies:2 with database-core-layer
2. Keep opensearch-dependencies:2 (function-specific)
3. Remove hardcoded DATABASE_URL
4. Add standard environment variables
5. Test database connectivity
```

### **Priority 2: Pipeline Functions (Week 2)**

#### **text-chunker-pipeline**
```bash
# Current issues: Old layer version, hardcoded password
# Actions:
1. Update from database-dependencies:2 to database-core-layer
2. Remove hardcoded DATABASE_URL
3. Verify VPC configuration (already uses correct security group)
4. Test pipeline functionality
```

#### **nlp-processor**
```bash
# Current issues: Not in VPC, mixed layer
# Actions:
1. Update from database-dependencies-pipeline:3 to database-core-layer
2. Add VPC configuration (currently has none)
3. Add standard security group
4. Test database connectivity
```

#### **nlp-worker**
```bash
# Current issues: Mixed layer
# Actions:
1. Update from database-dependencies-pipeline:3 to database-core-layer
2. Verify VPC configuration
3. Test database connectivity
```

### **Priority 3: Vector Embeddings (Week 3)**

#### **vector-embeddings-processor & worker**
```bash
# Current issues: Different security group, mixed layer
# Actions:
1. Update from database-dependencies-pipeline:3 to database-core-layer
2. Update security group from sg-0709acdc3f0cccd7f to standard
3. Test database connectivity
4. Test vector processing functionality
```

## 🛠️ **CDK Implementation Changes**

### **New CDK Constructs Required**:

```typescript
// 1. Database Core Layer
const databaseCoreLayer = new lambda.LayerVersion(this, 'DatabaseCoreLayer', {
  code: lambda.Code.fromAsset('layers/database-core-layer'),
  compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
  description: 'Core database utilities (DatabaseManager, DocumentIDManager)'
});

// 2. Standard Security Group
const databaseAccessSG = new ec2.SecurityGroup(this, 'DatabaseAccessSG', {
  vpc: vpc,
  description: 'Standard security group for database access'
});

// 3. Standard Environment Variables
const standardDatabaseEnv = {
  DATABASE_SECRET_NAME: databaseSecret.secretName,
  DB_HOST: rdsInstance.instanceEndpoint.hostname,
  DB_NAME: 'climate_risk_rag',
  DB_PORT: '5432',
  DATABASE_CONNECTION_METHOD: 'secrets_manager'
};

// 4. Standard VPC Configuration
const standardVpcConfig = {
  vpc: vpc,
  securityGroups: [databaseAccessSG],
  vpcSubnets: { subnets: [privateSubnet1, privateSubnet2] }
};
```

### **Function Update Pattern**:
```typescript
// Apply to ALL Lambda functions
const updateLambdaFunction = (functionName: string, specificLayers: lambda.ILayerVersion[] = []) => {
  return new lambda.Function(this, functionName, {
    // Standard database configuration
    layers: [databaseCoreLayer, ...specificLayers],
    environment: { ...standardDatabaseEnv, ...functionSpecificEnv },
    ...standardVpcConfig,
    
    // Function-specific configuration
    code: lambda.Code.fromAsset(`lambda/${functionName}`),
    handler: `${functionName}.lambda_handler`,
    // ... other function-specific settings
  });
};
```

## ✅ **Success Criteria**

### **Technical Validation**:
1. All functions use identical database import pattern
2. All functions use same database-core-layer
3. All functions use same VPC/security group configuration
4. All functions connect via Secrets Manager (no hardcoded passwords)
5. Database password rotation works automatically

### **Functional Validation**:
1. Pipeline test function can create database records
2. Cleanup service can clean database records
3. All pipeline stages can read/write database
4. Integration tests pass end-to-end
5. No regression in existing functionality

## 📅 **Implementation Timeline**

- **Week 1**: Create database-core-layer, fix critical functions (pipeline-test, cleanup)
- **Week 2**: Update pipeline functions (text-chunker, NLP)
- **Week 3**: Update vector embeddings functions
- **Week 4**: CDK refactoring, full integration testing
- **Week 5**: Documentation, monitoring, validation

This architecture ensures consistent, maintainable database access across all pipeline stages while eliminating the current configuration inconsistencies.
