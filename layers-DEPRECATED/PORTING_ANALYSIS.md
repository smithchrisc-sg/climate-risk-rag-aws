# Code Porting Analysis: SQLite to PostgreSQL + AWS Infrastructure
## Climate Risk RAG System Layer Components

## 🎯 **Executive Summary**

This analysis identifies the changes required to port the existing POC code from SQLite-based local infrastructure to PostgreSQL-based AWS infrastructure for use in Lambda layers. The main changes involve database abstraction, connection management, configuration, and AWS service integration.

## 📊 **Components Analysis**

### **1. DatabaseManager.py - MAJOR CHANGES REQUIRED**

**Current State:**
- Uses SQLite with file-based database (`sqlite3` module)
- Schema loaded from local SQL file
- Direct file system access for schema validation
- Connection pooling not implemented

**Required Changes:**
```python
# FROM: SQLite-based
import sqlite3
self.db_path = db_path
conn = sqlite3.connect(self.db_path)

# TO: PostgreSQL-based
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
self.connection_string = connection_string
self.connection_pool = ThreadedConnectionPool(1, 20, connection_string)
```

**Specific Modifications:**
1. **Database Connection:**
   - Replace `sqlite3.connect()` with `psycopg2.connect()`
   - Implement connection pooling for Lambda efficiency
   - Add connection retry logic with exponential backoff

2. **SQL Syntax Changes:**
   - `INSERT OR REPLACE` → `INSERT ... ON CONFLICT ... DO UPDATE`
   - `PRAGMA` statements → PostgreSQL-specific configuration
   - SQLite-specific functions → PostgreSQL equivalents

3. **Schema Management:**
   - Move from file-based schema to embedded schema or environment-based
   - Replace SQLite schema with PostgreSQL schema
   - Add proper foreign key constraints and indexes

4. **Transaction Management:**
   - Implement proper transaction handling for PostgreSQL
   - Add connection cleanup and error handling

### **2. DocumentIDManager.py - MODERATE CHANGES REQUIRED**

**Current State:**
- Depends on DatabaseManager for all database operations
- Uses local file paths for document storage
- Simple metadata structure

**Required Changes:**
```python
# FROM: Local file paths
def __init__(self, db_path: str):
    self.db_manager = DatabaseManager(db_path)

# TO: AWS-based configuration
def __init__(self, database_url: str, s3_bucket: str = None):
    self.db_manager = DatabaseManager(database_url)
    self.s3_bucket = s3_bucket
```

**Specific Modifications:**
1. **Initialization:**
   - Change from file path to database URL
   - Add optional S3 bucket configuration
   - Environment variable support for configuration

2. **Document ID Generation:**
   - Current logic is fine, but may need S3 key integration
   - Add support for S3-based content hashing

3. **Metadata Handling:**
   - Ensure compatibility with PostgreSQL JSON fields
   - Add validation for metadata structure

### **3. ProvenanceTracker.py - MINOR CHANGES REQUIRED**

**Current State:**
- File-based provenance logging
- In-memory data structure
- Simple JSON serialization

**Required Changes:**
```python
# FROM: File-based storage
def set_provenance_file(self, provenance_file: str):
    self.provenance_file = Path(provenance_file)

# TO: Database or S3-based storage
def set_provenance_storage(self, storage_type: str, connection_info: Dict):
    if storage_type == 'database':
        self.db_manager = DatabaseManager(connection_info['url'])
    elif storage_type == 's3':
        self.s3_bucket = connection_info['bucket']
```

**Specific Modifications:**
1. **Storage Backend:**
   - Add database storage option
   - Add S3 storage option for large provenance data
   - Keep file-based as fallback

2. **Data Structure:**
   - Optimize for Lambda memory constraints
   - Add batch writing capabilities

### **4. TextCleaner.py - MINIMAL CHANGES REQUIRED**

**Current State:**
- Pure text processing logic
- No database dependencies
- Stateless operations

**Required Changes:**
- ✅ **No major changes needed**
- Minor: Add AWS-specific text processing if needed
- Minor: Optimize for Lambda memory usage

### **5. NERAnalyzer.py - MODERATE CHANGES REQUIRED**

**Current State:**
- Uses matplotlib for visualization (not Lambda-compatible)
- File-based output for analysis
- Pandas for data processing

**Required Changes:**
```python
# FROM: File-based visualization
import matplotlib.pyplot as plt
def _generate_visualizations(self, output_dir, ner_system):
    plt.savefig(output_dir / 'chart.png')

# TO: S3-based or data-only output
def _generate_analysis_data(self, ner_system):
    return {
        'statistics': self.entity_stats,
        'charts_data': self.chart_data  # Data for client-side rendering
    }
```

**Specific Modifications:**
1. **Visualization:**
   - Remove matplotlib dependency (not Lambda-compatible)
   - Generate data structures for client-side visualization
   - Optional: Save charts to S3 if needed

2. **Output Management:**
   - Replace file-based output with S3 or database storage
   - Add streaming capabilities for large datasets

### **6. Knowledge Graph Components - MAJOR CHANGES REQUIRED**

**Current State:**
- Direct SPARQL endpoint connections
- Local embedding model loading
- File-based caching

**Required Changes:**
```python
# FROM: Direct endpoint connection
self.query_endpoint = SPARQLWrapper(endpoint_url)

# TO: AWS Neptune integration
import boto3
self.neptune_client = boto3.client('neptune')
# Or use Neptune-specific libraries
```

**Specific Modifications:**
1. **Neptune Integration:**
   - Replace direct SPARQL with Neptune-optimized queries
   - Add IAM authentication for Neptune
   - Implement connection pooling

2. **Embedding Models:**
   - Move large models to separate layer or S3
   - Implement lazy loading for Lambda
   - Add caching strategies

3. **Caching:**
   - Replace file-based caching with Redis or DynamoDB
   - Implement distributed caching for Lambda

## 🔧 **Infrastructure Changes Required**

### **1. Database Schema Migration**

**SQLite Schema → PostgreSQL Schema:**
```sql
-- FROM: SQLite-specific
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    -- SQLite syntax
);

-- TO: PostgreSQL-specific
CREATE TABLE IF NOT EXISTS documents (
    doc_id VARCHAR(255) PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- PostgreSQL syntax with proper types
);
```

### **2. Configuration Management**

**Environment Variables Required:**
```python
# Database Configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
DATABASE_POOL_SIZE = int(os.environ.get('DATABASE_POOL_SIZE', '10'))

# AWS Configuration
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
S3_BUCKET = os.environ.get('S3_BUCKET')

# Neptune Configuration (if used)
NEPTUNE_ENDPOINT = os.environ.get('NEPTUNE_ENDPOINT')
NEPTUNE_PORT = os.environ.get('NEPTUNE_PORT', '8182')
```

### **3. Connection Management**

**Lambda-Optimized Connection Handling:**
```python
class LambdaOptimizedDatabaseManager:
    _connection_pool = None
    
    @classmethod
    def get_connection_pool(cls):
        if cls._connection_pool is None:
            cls._connection_pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=5,  # Limited for Lambda
                dsn=DATABASE_URL
            )
        return cls._connection_pool
    
    def get_connection(self):
        return self.get_connection_pool().getconn()
    
    def return_connection(self, conn):
        self.get_connection_pool().putconn(conn)
```

## 📋 **Detailed Porting Plan**

### **Phase 1: Core Database Layer (Week 1)**

**1.1 Create New DatabaseManager**
```python
# File: layers/app-source/utils/DatabaseManager.py
class PostgreSQLDatabaseManager:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connection_pool = self._create_connection_pool()
    
    def _create_connection_pool(self):
        return ThreadedConnectionPool(
            minconn=1,
            maxconn=int(os.environ.get('DB_POOL_SIZE', '10')),
            dsn=self.connection_string
        )
```

**1.2 PostgreSQL Schema Creation**
```sql
-- File: layers/app-source/utils/schema/postgresql_schema.sql
-- Convert SQLite schema to PostgreSQL
-- Add proper constraints, indexes, and types
```

**1.3 SQL Query Conversion**
- Convert all SQLite-specific queries to PostgreSQL
- Add proper error handling and retry logic
- Implement connection pooling

### **Phase 2: Application Layer Updates (Week 2)**

**2.1 Update DocumentIDManager**
```python
class DocumentIDManager:
    def __init__(self, database_url: str, s3_bucket: str = None):
        self.db_manager = PostgreSQLDatabaseManager(database_url)
        self.s3_bucket = s3_bucket
        self.s3_client = boto3.client('s3') if s3_bucket else None
```

**2.2 Update ProvenanceTracker**
```python
class ProvenanceTracker:
    def __init__(self, storage_config: Dict[str, Any]):
        self.storage_type = storage_config.get('type', 'database')
        if self.storage_type == 'database':
            self.db_manager = PostgreSQLDatabaseManager(storage_config['url'])
        elif self.storage_type == 's3':
            self.s3_client = boto3.client('s3')
            self.bucket = storage_config['bucket']
```

### **Phase 3: Knowledge Graph Integration (Week 3)**

**3.1 Neptune Integration**
```python
class NeptuneOntologyManager:
    def __init__(self, neptune_endpoint: str, region: str):
        self.neptune_endpoint = neptune_endpoint
        self.region = region
        self.session = boto3.Session()
```

**3.2 Embedding Model Optimization**
```python
class LambdaOptimizedEmbeddingManager:
    _model = None
    
    @classmethod
    def get_model(cls):
        if cls._model is None:
            # Load from S3 or use smaller model
            cls._model = SentenceTransformer('all-MiniLM-L6-v2')
        return cls._model
```

### **Phase 4: Testing and Validation (Week 4)**

**4.1 Unit Tests**
- Test database connections and queries
- Test Lambda-specific optimizations
- Test error handling and retry logic

**4.2 Integration Tests**
- Test with actual PostgreSQL database
- Test with AWS services (S3, Neptune)
- Test Lambda deployment and execution

## 🚨 **Critical Considerations**

### **1. Lambda Constraints**
- **Memory Limits**: Optimize for 512MB-1GB memory usage
- **Execution Time**: Implement connection reuse across invocations
- **Cold Starts**: Minimize initialization time

### **2. Database Connection Management**
- **Connection Pooling**: Essential for Lambda performance
- **Connection Limits**: PostgreSQL has connection limits
- **Retry Logic**: Handle temporary connection failures

### **3. Error Handling**
- **Database Errors**: Proper PostgreSQL error handling
- **Network Errors**: Retry with exponential backoff
- **Lambda Timeouts**: Graceful degradation

### **4. Security**
- **Database Credentials**: Use AWS Secrets Manager
- **IAM Roles**: Proper permissions for AWS services
- **VPC Configuration**: Secure database access

## 📊 **Effort Estimation**

| Component | Complexity | Effort (Days) | Risk Level |
|-----------|------------|---------------|------------|
| DatabaseManager | High | 5-7 | High |
| DocumentIDManager | Medium | 2-3 | Medium |
| ProvenanceTracker | Medium | 2-3 | Low |
| TextCleaner | Low | 0.5 | Low |
| NERAnalyzer | Medium | 3-4 | Medium |
| KG Components | High | 5-7 | High |
| Testing & Integration | High | 3-5 | Medium |
| **Total** | - | **21-29 days** | - |

## 🎯 **Success Criteria**

1. **Functional Compatibility**: All existing functionality preserved
2. **Performance**: Sub-second response times for typical operations
3. **Reliability**: 99.9% success rate for database operations
4. **Scalability**: Handle concurrent Lambda executions
5. **Maintainability**: Clean, well-documented code

## 📝 **Next Steps**

1. **Review and Approve**: Review this analysis and approve the approach
2. **Environment Setup**: Set up PostgreSQL database and test environment
3. **Phase 1 Implementation**: Start with DatabaseManager conversion
4. **Iterative Testing**: Test each component as it's converted
5. **Integration Testing**: Full end-to-end testing with Lambda layers

This analysis provides a comprehensive roadmap for successfully porting the POC code to AWS infrastructure while maintaining functionality and optimizing for Lambda execution.
