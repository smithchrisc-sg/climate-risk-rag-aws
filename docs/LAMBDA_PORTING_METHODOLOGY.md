# Lambda Function Porting Methodology

## Overview

This document outlines the systematic approach for porting existing Lambda functions to integrate with the new audit-first database design while preserving all original functionality. This methodology was developed during the successful porting of the vector embeddings pipeline and should be followed for all remaining functions.

## Core Philosophy

### Audit-First Database Design
- **Preserve Original Functionality**: All existing capabilities must remain intact
- **Add Audit Capabilities**: Enhance with comprehensive tracking and status management
- **Database-Centric**: All state changes flow through the locked `DatabaseManager`
- **Immutable History**: Create audit trails for all processing stages

### Integration Principles
- **Minimal Code Changes**: Preserve existing business logic where possible
- **Enhanced Error Handling**: Add robust error tracking with database persistence
- **Status Tracking**: Implement comprehensive stage-based status management
- **Backward Compatibility**: Ensure existing integrations continue to work

## Key Constraints

### 1. Locked DatabaseManager
- **Cannot modify** `shared/database_core/database_manager.py`
- **Must use existing methods** for all database operations
- **Follow established patterns** for connection pooling and error handling
- **Respect audit schema** requirements

### 2. Infrastructure Requirements
- **VPC Configuration**: Use application subnets, not database subnets
- **Security Groups**: Use `sg-0c9e10b9cfb4c9eb0` (Async Keyword Indexer Lambdas)
- **IAM Permissions**: Create specific policies for each function's requirements
- **Layer Dependencies**: Use existing layers where possible

### 3. Message Flow Integrity
- **Preserve SNS/SQS patterns**: Maintain existing message formats
- **Stage-based processing**: Each function handles specific pipeline stages
- **Error propagation**: Ensure failures are properly communicated

## Reference Documents

### Essential Reading
1. **`shared/database_core/database_manager.py`** - Core database interface
2. **`shared/database_core/document_id_manager.py`** - Document ID management
3. **`migrate_to_audit_schema.sql`** - Database schema structure
4. **Working examples**:
   - `lambda/vector-embeddings-initiator/src/vector_embeddings_initiator.py`
   - `lambda/vector-embeddings-worker/src/vector_embeddings_worker.py`
   - `lambda/keyword-indexer-initiator/src/keyword_indexer_initiator.py`
   - `lambda/keyword-indexer-worker/src/keyword_indexer_worker.py`

### Infrastructure References
- **VPC Subnets**: Application subnets (`subnet-03d8bd6cf3491f38c`, `subnet-0c0be1dd59f70f70e`)
- **Security Groups**: `sg-0c9e10b9cfb4c9eb0` for Lambda functions
- **OpenSearch Collections**:
  - Search: `solve-global-kr-search-v2` (`i7dzyfap1fe42z9delui`)
  - Vectors: `solve-global-kr-vectors-v2` (`rui72a7agqnqo77vk34b`)

## Porting Process

### Phase 1: Analysis and Planning

#### 1.1 Function Assessment
- **Identify current functionality**: What does the function do?
- **Map data flows**: Input → Processing → Output
- **Identify dependencies**: External services, S3 buckets, databases
- **Document message formats**: SNS/SQS message structures

#### 1.2 Database Integration Points
- **Status tracking**: Which stages need database status updates?
- **Error handling**: Where should failures be recorded?
- **Audit requirements**: What metadata needs to be tracked?

### Phase 2: Code Structure Setup

#### 2.1 Directory Structure
```
lambda/{function-name}/
├── README.md                 # Function documentation
├── handler.py               # Lambda entry point
├── requirements.txt         # Dependencies
└── src/
    └── {function_name}.py   # Main implementation
```

#### 2.2 Handler Pattern
```python
import sys
import os
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from {function_name} import {FunctionClass}

def lambda_handler(event, context):
    processor = {FunctionClass}()
    return processor.process_event(event, context)
```

### Phase 3: Core Implementation

#### 3.1 Database Integration
```python
from database_manager import DatabaseManager
from document_id_manager import DocumentIDManager

class FunctionImplementation:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.doc_id_manager = DocumentIDManager(self.db_manager)
```

#### 3.2 Status Management Pattern
```python
def update_status(self, doc_id: str, stage: str, status: str, metadata: dict = None):
    """Update document processing status with audit trail"""
    try:
        self.doc_id_manager.set_document_processing_status(
            doc_id=doc_id,
            stage=stage,
            status=status,
            metadata=metadata or {}
        )
        logger.info(f"Set document processing status: {doc_id} -> {stage} -> {status}")
    except Exception as e:
        logger.error(f"Failed to update status for {doc_id}: {e}")
        raise
```

#### 3.3 Error Handling Pattern
```python
def process_document(self, doc_id: str, data: dict):
    try:
        # Set status to in_progress
        self.update_status(doc_id, 'stage_name', 'in_progress')
        
        # Process the document
        result = self.do_processing(data)
        
        # Set status to completed
        self.update_status(doc_id, 'stage_name', 'completed', {
            'processing_metadata': result
        })
        
        return result
        
    except Exception as e:
        # Set status to failed
        self.update_status(doc_id, 'stage_name', 'failed', {
            'error': str(e),
            'error_type': type(e).__name__
        })
        raise
```

### Phase 4: Infrastructure Configuration

#### 4.1 Lambda Configuration
- **Runtime**: Python 3.11
- **Memory**: Appropriate for function (256MB - 2048MB)
- **Timeout**: Based on processing requirements
- **VPC**: Application subnets with correct security group
- **Layers**: Include required dependencies

#### 4.2 IAM Permissions Template
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["secretsmanager:GetSecretValue"],
            "Resource": ["arn:aws:secretsmanager:us-east-1:861276078413:secret:rds!db-*"]
        },
        {
            "Effect": "Allow", 
            "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
            "Resource": ["arn:aws:s3:::bucket-name", "arn:aws:s3:::bucket-name/*"]
        },
        {
            "Effect": "Allow",
            "Action": ["lambda:InvokeFunction"],
            "Resource": ["arn:aws:lambda:us-east-1:861276078413:function:worker-function"]
        },
        {
            "Effect": "Allow",
            "Action": ["sns:Publish"],
            "Resource": ["arn:aws:sns:us-east-1:861276078413:completion-topic"]
        }
    ]
}
```

### Phase 5: Testing and Validation

#### 5.1 Unit Testing
- **Database operations**: Verify status updates work correctly
- **Error handling**: Test failure scenarios
- **Message processing**: Validate input/output formats

#### 5.2 Integration Testing
- **End-to-end flow**: Test complete pipeline stage
- **Database consistency**: Verify audit trail creation
- **Message flow**: Confirm SNS/SQS integration

#### 5.3 Production Validation
- **Deploy to staging**: Test with real data
- **Monitor logs**: Verify no errors or warnings
- **Check database**: Confirm status tracking works
- **Validate outputs**: Ensure downstream systems receive correct data

## Common Patterns and Solutions

### Database Connection Management
```python
def __init__(self):
    self.db_manager = DatabaseManager()
    logger.info("Database connection pool initialized successfully")
    logger.info("DatabaseManager initialized with connection pooling")
```

### Message Processing
```python
def process_event(self, event, context):
    """Process Lambda event with proper error handling"""
    try:
        # Parse event
        records = event.get('Records', [])
        results = []
        
        for record in records:
            result = self.process_record(record)
            results.append(result)
            
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Processing completed',
                'processed_records': len(results),
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"Lambda handler error: {e}")
        raise
```

### S3 Operations
```python
def load_from_s3(self, bucket: str, key: str):
    """Load data from S3 with error handling"""
    try:
        response = self.s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
    except Exception as e:
        logger.error(f"Failed to load from S3: s3://{bucket}/{key} - {e}")
        raise
```

## Troubleshooting Guide

### Common Issues

#### 1. Database Connection Timeouts
- **Cause**: Function in wrong subnets or security group
- **Solution**: Use application subnets (`subnet-03d8bd6cf3491f38c`, `subnet-0c0be1dd59f70f70e`)
- **Security Group**: `sg-0c9e10b9cfb4c9eb0`

#### 2. Permission Errors
- **Cause**: Missing IAM permissions
- **Solution**: Add specific permissions for required services
- **Check**: CloudWatch logs for specific permission errors

#### 3. OpenSearch Access Issues
- **Cause**: Wrong collection endpoint or missing data access policies
- **Solution**: Verify collection ID and update data access policies

#### 4. Layer Dependencies
- **Cause**: Missing or incompatible layers
- **Solution**: Use existing layers or create new ones with correct dependencies

### Debugging Steps
1. **Check CloudWatch logs** for specific error messages
2. **Verify environment variables** are set correctly
3. **Test database connectivity** in isolation
4. **Validate IAM permissions** with AWS CLI
5. **Check VPC configuration** matches working functions

## Success Criteria

### Functional Requirements
- ✅ All original functionality preserved
- ✅ Database status tracking implemented
- ✅ Error handling with audit trail
- ✅ Message flow integrity maintained
- ✅ Performance equivalent or better

### Technical Requirements
- ✅ Uses locked DatabaseManager correctly
- ✅ Proper infrastructure configuration
- ✅ Comprehensive error handling
- ✅ Audit trail creation
- ✅ Integration with existing pipeline

### Validation Checklist
- [ ] Function deploys without errors
- [ ] Database operations work correctly
- [ ] Status updates appear in database
- [ ] Error scenarios handled gracefully
- [ ] Integration tests pass
- [ ] Performance meets requirements
- [ ] Logs show expected behavior

## Remaining Functions to Port

Based on the current pipeline, the following functions likely need porting:

1. **Text Extraction Functions** - Convert documents to text
2. **Text Chunking Functions** - Split text into manageable chunks  
3. **Cleanup Functions** - Document lifecycle management
4. **Query/Search Functions** - RAG query processing

Each should follow this methodology for consistent implementation and integration with the audit-first database design.

## Conclusion

This methodology ensures systematic, reliable porting of Lambda functions while maintaining system integrity and adding comprehensive audit capabilities. Following these patterns will result in a robust, maintainable system with full traceability and error handling.
