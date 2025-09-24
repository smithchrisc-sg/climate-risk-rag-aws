# GAIP API Quick Reference

## 🚀 Live API Endpoint
```
POST https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search
```

## 🔐 Authentication
```
Authorization: Bearer <jwt_token>
```

## 📝 Request Example
```bash
curl -X POST https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "query": "climate risk North Macedonia",
    "filters": {
      "categories": ["climate", "risk-assessment"],
      "regions": ["North Macedonia"]
    },
    "parameters": {
      "limit": 10
    }
  }'
```

## 🎯 Test Webapp
```
http://gaip-api-test-webapp-1758042975.s3-website-us-east-1.amazonaws.com/test.html
```

## 🔑 JWT Tokens (Local Development)
See `/JWT_TOKENS.md` in project root for test tokens.

## 📊 Key Response Fields
```json
{
  "results": [
    {
      "document_id": "string",
      "title": "string", 
      "score": 0.85,
      "source_url": "string",
      "highlights": {
        "content": ["highlighted text"],
        "title": ["highlighted title"]
      }
    }
  ],
  "pagination": {
    "total_results": 8,
    "returned_results": 8,
    "limit": 10
  },
  "execution_time": 0.756
}
```

## 🛠️ Lambda Functions
- **Search**: `gaip-search-lambda` (multi-modal search)
- **Auth**: `gaip-jwt-authorizer` (JWT validation)

## 📋 Status
- ✅ **Operational**: JWT authentication working
- ✅ **Multi-modal**: OpenSearch + Neptune + PostgreSQL
- ✅ **CORS**: Configured for web access
- ✅ **Test Infrastructure**: Webapp deployed

## 📚 Documentation
- **Full Config**: `GAIP_API_DEPLOYED_CONFIGURATION_2025-09-16.md`
- **Implementation Plan**: `GAIP_API_IMPLEMENTATION_PLAN_2025-09-16.md`
- **OpenAPI Spec**: `solve-global-gaip-kr-api.yaml`
