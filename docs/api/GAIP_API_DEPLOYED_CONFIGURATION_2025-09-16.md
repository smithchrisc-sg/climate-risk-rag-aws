# GAIP API Deployed Configuration - 2025-09-16

## Current Deployment Status: ✅ OPERATIONAL

The GAIP Knowledge Repository API is fully deployed and operational with JWT Bearer token authentication.

## API Gateway Configuration

### Base Information
- **API Gateway ID**: `43l6kohmrf`
- **API Name**: `gaip-api`
- **Description**: GAIP Knowledge Repository API
- **Type**: Regional API Gateway
- **Created**: 2025-09-16

### Endpoints
- **Primary Endpoint**: `https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1`
- **Alternative Endpoint**: `https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/prod`
- **Working Stage**: `/v1` (recommended)
- **Search Endpoint**: `POST /search`

### Stages
| Stage | Status | Description | Last Deployed |
|-------|--------|-------------|---------------|
| `v1` | ✅ Active | Primary production stage | 2025-09-16 16:36:14 |
| `prod` | ⚠️ Limited | Alternative stage (may have permission issues) | 2025-09-16 16:22:31 |

## Authentication Configuration

### JWT Authorizer
- **Lambda Function**: `gaip-jwt-authorizer`
- **Authorizer ID**: `1u77w8`
- **Type**: TOKEN authorizer
- **Identity Source**: `method.request.header.Authorization`
- **Handler**: `handler.lambda_handler`
- **Runtime**: Python 3.11
- **Memory**: 256MB
- **Timeout**: 10 seconds

### JWT Token Requirements
- **Header Format**: `Authorization: Bearer <jwt_token>`
- **Algorithm**: HS256
- **Secret**: `dev-test-secret-key-change-for-production` (stored in Lambda env var)
- **Required Claims**:
  - `sub`: User ID
  - `org`: Organization
  - `roles`: Array including 'search'
  - `exp`: Expiration timestamp
  - `type`: Token type

### Available Test Tokens
| User Type | Expiry | Roles | Location |
|-----------|--------|-------|----------|
| Admin | 2025-12-15 | admin, search | `/JWT_TOKENS.md` |
| Researcher | 2025-10-16 | search | `/JWT_TOKENS.md` |
| External | 2025-09-23 | search | `/JWT_TOKENS.md` |

## Lambda Functions

### 1. Search Lambda (`gaip-search-lambda`)
- **Function Name**: `gaip-search-lambda`
- **Runtime**: Python 3.11
- **Handler**: `handler.lambda_handler`
- **Memory**: 1024MB
- **Timeout**: 60 seconds
- **VPC**: Enabled (subnets: subnet-03d8bd6cf3491f38c, subnet-0c0be1dd59f70f70e)
- **Security Group**: sg-0c9e10b9cfb4c9eb0

#### Layers (in order)
1. `knowledge-graph-layer:61` (19.2MB) - KG utilities, entity alignment
2. `database-core-layer:16` (17.3MB) - DatabaseManager, PostgreSQL utilities  
3. `database-dependencies:2` (3.3MB) - Database connection libraries
4. `opensearch-dependencies:4` (2.5MB) - OpenSearch client library

#### Environment Variables
```
OPENSEARCH_ENDPOINT=https://vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=veqpat-kegba2-zapbyZ
NEPTUNE_ENDPOINT=solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com
NEPTUNE_PORT=8182
DATABASE_SECRET_NAME=rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863
DB_HOST=solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com
DB_NAME=climate_risk_rag
DB_PORT=5432
POSTGRES_HOST=solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com
POSTGRES_DATABASE=climate_risk_rag
IAMAuthEnabledOnSourceStream=true
```

### 2. JWT Authorizer Lambda (`gaip-jwt-authorizer`)
- **Function Name**: `gaip-jwt-authorizer`
- **Runtime**: Python 3.11
- **Handler**: `handler.lambda_handler`
- **Memory**: 256MB
- **Timeout**: 10 seconds
- **Dependencies**: PyJWT 2.8.0

#### Environment Variables
```
JWT_SECRET=dev-test-secret-key-change-for-production
```

## API Method Configuration

### POST /search
- **Authorization Type**: CUSTOM
- **Authorizer**: gaip-jwt-authorizer (1u77w8)
- **API Key Required**: false
- **Integration Type**: AWS_PROXY
- **Integration Target**: gaip-search-lambda
- **Timeout**: 29 seconds

### OPTIONS /search (CORS)
- **Authorization Type**: NONE
- **Integration Type**: MOCK
- **Response Headers**:
  - `Access-Control-Allow-Origin: *`
  - `Access-Control-Allow-Methods: POST,OPTIONS`
  - `Access-Control-Allow-Headers: Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token`

## Data Sources Integration

### OpenSearch
- **Endpoint**: vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com
- **Authentication**: Username/password (admin/veqpat-kegba2-zapbyZ)
- **Purpose**: Keyword search, document indexing
- **Access**: Via opensearch-dependencies layer

### Neptune Graph Database
- **Endpoint**: solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com
- **Port**: 8182
- **Protocol**: HTTPS (SPARQL over HTTP)
- **Purpose**: Entity alignment, graph queries
- **Access**: Via knowledge-graph-layer

### PostgreSQL RDS
- **Host**: solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com
- **Database**: climate_risk_rag
- **Port**: 5432
- **Authentication**: AWS Secrets Manager (rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863)
- **Purpose**: Document metadata, audit trail
- **Access**: Via database-core-layer and database-dependencies

## Request/Response Format

### Request Format
```json
{
  "query": "climate risk North Macedonia",
  "filters": {
    "categories": ["climate", "risk-assessment"],
    "regions": ["North Macedonia"]
  },
  "parameters": {
    "limit": 10,
    "include_facets": false
  }
}
```

### Response Format
```json
{
  "results": [
    {
      "document_id": "string",
      "title": "string",
      "summary": "string", 
      "score": 0.85,
      "document_type": "string",
      "categories": ["string"],
      "regions": ["string"],
      "publication_date": "2023-01-01",
      "source_url": "string",
      "highlights": {
        "content": ["highlighted text"],
        "title": ["highlighted title"]
      },
      "metadata": {
        "search_types": ["keyword"],
        "matched_concepts": ["concept"],
        "file_size": 1024,
        "processing_status": "completed"
      }
    }
  ],
  "pagination": {
    "cursor": null,
    "next_cursor": null,
    "total_results": 8,
    "returned_results": 8,
    "limit": 10
  },
  "execution_time": 0.756,
  "query": "climate risk North Macedonia"
}
```

## Security Configuration

### CORS Headers
- **Access-Control-Allow-Origin**: `*`
- **Access-Control-Allow-Methods**: `POST, OPTIONS`
- **Access-Control-Allow-Headers**: `Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token`

### IAM Roles
- **Lambda Execution Role**: `document-processing-lambda-role`
- **API Gateway Invoke Permission**: Configured for both Lambda functions

## Test Infrastructure

### Test Webapp
- **URL**: `http://gaip-api-test-webapp-1758042975.s3-website-us-east-1.amazonaws.com/test.html`
- **S3 Bucket**: `gaip-api-test-webapp-1758042975`
- **Files**: `index.html`, `test.html`
- **Features**: 
  - API endpoint configuration
  - JWT token input
  - Search query testing
  - Results display with highlighting
  - Local storage for settings

### Token Management
- **Generation Script**: `scripts/generate_api_keys.py`
- **Token Storage**: `JWT_TOKENS.md` (project root)
- **Backup Location**: `scripts/test_api_keys.json` (gitignored)

## Monitoring and Logging

### CloudWatch Log Groups
- `/aws/lambda/gaip-search-lambda` - Search function logs
- `/aws/lambda/gaip-jwt-authorizer` - Authorization logs
- API Gateway execution logs (if enabled)

### Key Metrics to Monitor
- Request count and latency
- Authentication success/failure rates
- Search result counts
- Error rates by type
- Lambda function duration and memory usage

## Deployment History

### 2025-09-16 Major Milestones
1. **10:15** - Initial API Gateway creation
2. **14:05** - Search Lambda deployment with multi-modal architecture
3. **16:18** - JWT authorizer implementation
4. **16:22** - Authentication integration and CORS configuration
5. **16:36** - Final deployment to v1 stage
6. **16:45** - Handler configuration fix and operational status

## Known Issues and Limitations

### Current Limitations
- JWT secret stored in Lambda environment (should use Secrets Manager for production)
- CORS allows all origins (`*`) - should be restricted for production
- No rate limiting implemented
- Test tokens have long expiry times
- No request/response size limits configured

### Future Improvements Needed
- Move JWT secret to AWS Secrets Manager
- Implement proper CORS origin restrictions
- Add API Gateway throttling and rate limiting
- Implement request validation
- Add comprehensive monitoring and alerting
- Set up automated deployment pipeline

## Production Readiness Checklist

### ✅ Completed
- [x] JWT Bearer token authentication
- [x] Multi-modal search functionality
- [x] CORS configuration
- [x] Error handling and logging
- [x] Integration with all data sources
- [x] Test infrastructure

### ⚠️ Needs Attention for Production
- [ ] JWT secret in Secrets Manager
- [ ] CORS origin restrictions
- [ ] Rate limiting and throttling
- [ ] Request validation
- [ ] Comprehensive monitoring
- [ ] Automated deployment
- [ ] Load testing
- [ ] Security audit

## Contact and Maintenance

### Key Files for Maintenance
- **API Configuration**: This document
- **Lambda Code**: `lambda/search/` and `lambda/jwt-authorizer/`
- **Test Infrastructure**: `test-webapp/`
- **Token Management**: `JWT_TOKENS.md`, `scripts/generate_api_keys.py`

### Deployment Commands
```bash
# Update search Lambda code
cd scripts && python3 update_code_only.py

# Update JWT authorizer
cd lambda/jwt-authorizer
zip -r jwt-authorizer.zip .
aws lambda update-function-code --function-name gaip-jwt-authorizer --zip-file fileb://jwt-authorizer.zip

# Deploy API Gateway changes
aws apigateway create-deployment --rest-api-id 43l6kohmrf --stage-name v1
```

---

**Document Version**: 1.0  
**Last Updated**: 2025-09-16  
**Status**: Production Ready (with noted limitations)  
**Next Review**: 2025-10-01
