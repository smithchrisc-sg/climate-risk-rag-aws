# Climate Risk Document Search API
## Partner Integration Documentation v1.0

---

## 📋 **Overview**

The Climate Risk Document Search API provides a unified interface for searching across our comprehensive collection of climate risk documents. The API uses advanced search technologies to deliver highly relevant results with contextual snippets and rich metadata.

### **Key Features**
- **Single endpoint** for all search operations
- **Natural language queries** - search using plain English
- **Intelligent result ranking** using proprietary algorithms
- **Rich contextual snippets** with highlighted search terms
- **Comprehensive metadata** for faceted search experiences
- **Efficient pagination** for large result sets
- **Rate limiting** and authentication for secure access

---

## 🔐 **Authentication**

The API uses **JWT Bearer token authentication**. Include your token in the Authorization header:

```http
Authorization: Bearer your_jwt_token_here
```

**Token Management:**
- Tokens expire after 1 hour
- Refresh tokens are provided for seamless renewal
- Contact support for initial token provisioning

---

## 🔍 **Search Endpoint**

### **Base URL**
```
Production: https://api.climaterisk.com/v1
Staging: https://staging-api.climaterisk.com/v1
```

### **Endpoint**
```http
POST /search
Content-Type: application/json
Authorization: Bearer {token}
```

---

## 📤 **Request Format**

### **Basic Search Request**
```json
{
  "query": "climate risk financial modeling approaches",
  "parameters": {
    "max_results": 20,
    "include_snippets": true
  }
}
```

### **Advanced Search Request**
```json
{
  "query": "sea level rise infrastructure damage",
  "parameters": {
    "max_results": 50,
    "snippet_length": 300,
    "relevance_threshold": 0.7
  },
  "filters": {
    "categories": ["physical_risk", "infrastructure"],
    "date_range": {
      "start": "2023-01-01",
      "end": "2024-12-31"
    },
    "document_types": ["pdf", "report"]
  },
  "options": {
    "include_facets": true,
    "highlight_matches": true
  }
}
```

### **Request Parameters**

#### **Required**
| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | Natural language search query (1-500 characters) |

#### **Optional Parameters**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_results` | integer | 20 | Number of results to return (1-100) |
| `include_snippets` | boolean | true | Include text excerpts in results |
| `snippet_length` | integer | 200 | Length of text snippets (50-500 chars) |
| `relevance_threshold` | number | 0.0 | Minimum relevance score (0.0-1.0) |
| `cursor` | string | - | Pagination cursor for next page |

#### **Filter Options**
| Filter | Type | Description | Example |
|--------|------|-------------|---------|
| `document_ids` | array | Search specific documents | `["doc_001", "doc_002"]` |
| `document_types` | array | Filter by file type | `["pdf", "report"]` |
| `categories` | array | Filter by content categories | `["environmental", "financial"]` |
| `regions` | array | Filter by geographic regions | `["coastal", "urban"]` |
| `date_range` | object | Filter by upload date | `{"start": "2023-01-01", "end": "2024-12-31"}` |
| `file_size_range` | object | Filter by file size | `{"min_mb": 1, "max_mb": 50}` |
| `custom_tags` | array | Filter by custom tags | `["high_priority", "validated"]` |

#### **Sort Options**
| Field | Description |
|-------|-------------|
| `relevance` | Sort by search relevance (default) |
| `upload_date` | Sort by document upload date |
| `file_size` | Sort by file size |
| `title` | Sort alphabetically by title |

---

## 📥 **Response Format**

### **Successful Response**
```json
{
  "status": "success",
  "query_id": "search_12345_67890",
  "execution_time_ms": 285,
  "total_results": 156,
  "returned_results": 20,
  "results": [
    {
      "document_id": "doc_001",
      "document_url": "https://documents.yourapi.com/doc_001",
      "title": "Climate Risk Assessment Report 2024",
      "relevance_score": 0.95,
      "snippets": [
        {
          "text": "Climate <mark>risk</mark> <mark>financial</mark> <mark>modeling</mark> requires sophisticated approaches...",
          "page_number": 12,
          "section": "Methodology"
        }
      ],
      "metadata": {
        "document_type": "pdf",
        "file_size_mb": 12.5,
        "page_count": 45,
        "upload_date": "2024-03-15T10:30:00Z",
        "categories": ["environmental", "financial"],
        "regions": ["global", "coastal"],
        "language": "en",
        "author": "Climate Risk Institute",
        "publication_year": 2024
      }
    }
  ],
  "facets": {
    "categories": {
      "environmental": 89,
      "financial": 67
    },
    "document_types": {
      "pdf": 120,
      "report": 36
    }
  },
  "pagination": {
    "current_page": 1,
    "total_pages": 8,
    "has_next": true,
    "next_cursor": "eyJzY29yZSI6MC44NSwiaWQiOiJkb2NfMDI3In0="
  }
}
```

### **Response Fields**

#### **Result Object**
| Field | Type | Description |
|-------|------|-------------|
| `document_id` | string | Unique document identifier |
| `document_url` | string | Direct URL to access the document |
| `title` | string | Document title |
| `relevance_score` | number | Relevance score (0.0-1.0) |
| `snippets` | array | Text excerpts with context |
| `metadata` | object | Document metadata and properties |

#### **Metadata Fields**
| Field | Type | Description |
|-------|------|-------------|
| `document_type` | string | File type (pdf, report, etc.) |
| `file_size_mb` | number | File size in megabytes |
| `page_count` | integer | Number of pages |
| `upload_date` | string | ISO 8601 upload timestamp |
| `categories` | array | Content categories |
| `regions` | array | Geographic regions covered |
| `language` | string | Document language code |
| `author` | string | Document author |
| `publication_year` | integer | Year of publication |
| `custom_tags` | array | Custom classification tags |

---

## ❌ **Error Responses**

### **Validation Error (400)**
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": [
      {
        "field": "parameters.max_results",
        "issue": "Value must be between 1 and 100",
        "provided_value": "150"
      }
    ]
  },
  "request_id": "req_12345",
  "timestamp": "2024-07-09T15:30:00Z"
}
```

### **Authentication Error (401)**
```json
{
  "status": "error",
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Invalid or expired authentication token"
  },
  "request_id": "req_12346",
  "timestamp": "2024-07-09T15:30:00Z"
}
```

### **Rate Limit Error (429)**
```json
{
  "status": "error",
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Rate limit exceeded.",
    "details": {
      "limit": 100,
      "window": "1 hour",
      "reset_time": "2024-07-09T16:30:00Z",
      "retry_after_seconds": 1800
    }
  },
  "request_id": "req_12347",
  "timestamp": "2024-07-09T15:30:00Z"
}
```

---

## 🚦 **Rate Limits**

| Limit Type | Restriction |
|------------|-------------|
| Requests per minute | 60 |
| Requests per hour | 1,000 |
| Requests per day | 10,000 |
| Concurrent requests | 5 |

**Rate Limit Headers:**
- `X-RateLimit-Limit`: Request limit for the time window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Time when the rate limit resets

---

## 📄 **Pagination**

The API uses **cursor-based pagination** for efficient handling of large result sets.

### **First Page Request**
```json
{
  "query": "climate risk",
  "parameters": {
    "max_results": 20
  }
}
```

### **Next Page Request**
```json
{
  "query": "climate risk",
  "parameters": {
    "max_results": 20,
    "cursor": "eyJzY29yZSI6MC44NSwiaWQiOiJkb2NfMDI3In0="
  }
}
```

**Pagination Response Fields:**
- `current_page`: Current page number
- `total_pages`: Total number of pages
- `has_next`: Boolean indicating if more results exist
- `next_cursor`: Cursor string for the next page

---

## 💡 **Best Practices**

### **Query Optimization**
- Use **specific terms** for better relevance
- Combine **multiple concepts** in a single query
- Use **natural language** rather than keyword lists
- Example: `"financial impact of sea level rise on infrastructure"` vs `"financial sea level infrastructure"`

### **Filtering Strategy**
- Apply **broad filters first** (date range, document type)
- Use **categories** to narrow domain-specific results
- Combine **multiple filter types** for precision
- Use **facets** to understand result distribution

### **Performance Tips**
- Set appropriate `max_results` (20-50 for UI, higher for batch processing)
- Use `relevance_threshold` to filter low-quality results
- Enable `include_facets` only when needed for UI
- Implement **client-side caching** for repeated queries

### **Error Handling**
- Always check the `status` field in responses
- Implement **exponential backoff** for rate limit errors
- Store `request_id` for support inquiries
- Handle **network timeouts** gracefully

---

## 🧪 **Example Use Cases**

### **1. Basic Document Search**
```json
{
  "query": "carbon pricing mechanisms",
  "parameters": {
    "max_results": 10,
    "include_snippets": true
  }
}
```

### **2. Filtered Research Query**
```json
{
  "query": "renewable energy transition risks",
  "filters": {
    "categories": ["transition_risk", "energy"],
    "publication_year_range": {
      "start": 2022,
      "end": 2024
    }
  },
  "options": {
    "include_facets": true
  }
}
```

### **3. Targeted Document Analysis**
```json
{
  "query": "physical climate risks coastal areas",
  "filters": {
    "regions": ["coastal"],
    "document_types": ["report"]
  },
  "parameters": {
    "relevance_threshold": 0.8,
    "snippet_length": 400
  }
}
```

---

## 🔧 **Integration Support**

### **Getting Started**
1. **Request API credentials** from your account manager
2. **Review this documentation** and the OpenAPI specification
3. **Test with staging environment** before production integration
4. **Implement error handling** and rate limiting in your application

### **OpenAPI Specification**
The complete OpenAPI 3.0 specification is available at:
- **File**: `climate-risk-search-api-v1.yaml`
- **Interactive docs**: Available upon request

### **Support Channels**
- **Technical Support**: api-support@climaterisk.com
- **Account Management**: partnerships@climaterisk.com
- **Documentation**: Available in developer portal

### **SLA & Availability**
- **Uptime**: 99.9% availability target
- **Response Time**: <500ms average response time
- **Support**: Business hours (9 AM - 5 PM EST)

---

## 📊 **Response Time Expectations**

| Query Complexity | Expected Response Time |
|------------------|----------------------|
| Simple keyword queries | <200ms |
| Complex multi-filter queries | <500ms |
| Large result sets (50+ results) | <800ms |
| Faceted search queries | <600ms |

---

## 🔒 **Security & Compliance**

- **Data Encryption**: All data transmitted over HTTPS/TLS 1.3
- **Token Security**: JWT tokens with short expiration times
- **Access Logging**: All API access is logged for security monitoring
- **Rate Limiting**: Protects against abuse and ensures fair usage
- **Data Privacy**: No query data is stored or used for other purposes

---

**Questions or need assistance with integration? Contact our technical support team at api-support@climaterisk.com**
