# GAIP Knowledge Repository Search API
## Partner Integration Documentation v2.0 - Solution-Focused

---

## 📋 **Overview**

The GAIP Knowledge Repository Search API provides a unified interface for searching across the Global Asia Insurance Partnership's comprehensive collection of vetted insurance and risk-related solutions and documents. The API uses advanced search technologies to deliver highly relevant solution-focused results for protection gap models, government policy frameworks, and geo-specific risk assessments.

**Supporting GAIP's Mission: Addressing Asia's Protection Gaps**

The Global Asia Insurance Partnership (GAIP) is a tripartite partnership between the global insurance industry, regulators and policymakers, and academia. This API supports GAIP's core objective to **Understand and Quantify Risk** through solution discovery and analysis:

- **Solution Discovery**: Finding relevant risk reduction, insurance penetration, and risk financing solutions
- **Risk Assessment**: Understanding solutions that address specific risk types (food, cyber, drought, health, etc.)
- **Geographic Analysis**: Solutions scoped to Asia, ASEAN+3, ASEAN, or specific countries/regions
- **Implementation Insights**: Access to solution outcomes, timelines, and contact information
- **PPP Analysis**: Understanding Public-Private Partnership involvement in solutions

### **Key Features**
- **Solution-focused search** across vetted knowledge repository with structured solution metadata
- **Natural language queries** for insurance and risk solution discovery
- **Multi-dimensional filtering** by solution category, risk type, geographic scope, and PPP involvement
- **Rich solution metadata** including implementation status, outcomes, and contact information
- **Repository metadata** endpoints for last update times and solution counts

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
Production: https://api.solve.global/gaip/v1
Staging: https://staging-api.solve.global/gaip/v1
```

### **Endpoints**
```http
POST /search                    # Search solutions and documents
GET /repository/last-update     # Get last repository update timestamp
GET /repository/solution-count  # Get total solution count
```

---

## 📤 **Request Format**

### **Basic Solution Search Request**
```json
{
  "query": "parametric insurance flood risk Southeast Asia",
  "parameters": {
    "max_results": 20,
    "include_snippets": true
  }
}
```

### **Advanced Solution Search Request**
```json
{
  "query": "agricultural insurance climate risk",
  "parameters": {
    "max_results": 50,
    "snippet_length": 300,
    "relevance_threshold": 0.7
  },
  "filters": {
    "solution_category": ["risk reduction", "insurance penetration"],
    "risk_type": ["drought", "flood", "agricultural"],
    "geographic_scope": ["ASEAN", "country"],
    "ppp_involvement": true,
    "regions": ["southeast_asia", "south_asia"],
    "date_range": {
      "start": "2023-01-01",
      "end": "2024-12-31"
    }
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

#### **Solution-Focused Filter Options**
| Filter | Type | Description | Example |
|--------|------|-------------|---------|
| `solution_category` | array | Solution categories (multiple allowed) | `["risk reduction", "insurance penetration", "risk financing"]` |
| `solution_type` | array | Solution subcategories (multiple allowed) | `["parametric insurance", "microinsurance"]` |
| `risk_type` | array | Risk types addressed (multiple allowed) | `["food", "cyber", "drought", "health", "flood"]` |
| `geographic_scope` | array | Geographic scope (multiple allowed) | `["Asia", "ASEAN+3", "ASEAN", "country"]` |
| `ppp_involvement` | boolean | Public-Private Partnership involvement | `true` |

#### **Additional Filter Options**
| Filter | Type | Description | Example |
|--------|------|-------------|---------|
| `document_ids` | array | Search specific documents | `["doc_001", "doc_002"]` |
| `document_types` | array | Filter by file type | `["pdf", "report"]` |
| `regions` | array | Filter by geographic regions | `["southeast_asia", "south_asia"]` |
| `date_range` | object | Filter by publication date | `{"start": "2023-01-01", "end": "2024-12-31"}` |

#### **Sort Options**
| Field | Description |
|-------|-------------|
| `relevance` | Sort by search relevance (default) |
| `upload_date` | Sort by document upload date |
| `file_size` | Sort by file size |
| `title` | Sort alphabetically by title |

---

## 📥 **Response Format**

### **Successful Search Response**
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
      "document_url": "https://documents.solve.global/gaip/doc_001",
      "solution_name": "Parametric Flood Insurance for Rice Farmers",
      "title": "Protection Gap Analysis: Flood Insurance in Southeast Asia 2024",
      "relevance_score": 0.95,
      "publication_date": "2024-03-15",
      "country_regions_covered": ["Thailand", "Vietnam", "Philippines"],
      "risk_types_addressed": ["flood", "agricultural", "climate"],
      "solution_categories": ["risk reduction", "insurance penetration"],
      "solution_types": ["parametric insurance", "index-based insurance"],
      "solution_implementation_timeline": "18-24 months",
      "last_kr_harvest_date": "2024-09-15T10:30:00Z",
      "solution_contact_info": {
        "organization": "Asian Development Bank",
        "email": "contact@adb.org",
        "website": "https://www.adb.org"
      },
      "implemented": "yes",
      "ppp_involvement": "yes",
      "summary_description": "This parametric insurance solution provides rapid payouts to rice farmers affected by flooding, using satellite data and weather indices to trigger automatic compensation.",
      "key_highlights": [
        "Automated payout system reduces claim processing time to 48 hours",
        "Covers 50,000+ smallholder farmers across three countries",
        "Uses satellite imagery and IoT sensors for accurate trigger mechanisms"
      ],
      "results_outcomes": "Reduced average claim settlement time from 6 months to 48 hours, increased farmer participation by 300%",
      "source_links": [
        {
          "url": "https://www.adb.org/projects/parametric-insurance",
          "title": "ADB Parametric Insurance Initiative",
          "type": "website"
        }
      ],
      "source": "World Bank",
      "snippets": [
        {
          "text": "Protection <mark>gap</mark> analysis reveals significant underinsurance in <mark>flood</mark>-prone regions...",
          "page_number": 12,
          "section": "Regional Assessment"
        }
      ],
      "metadata": {
        "document_type": "pdf",
        "file_size_mb": 12.5,
        "page_count": 45,
        "upload_date": "2024-03-15T10:30:00Z",
        "categories": ["protection_gap", "flood_insurance"],
        "regions": ["southeast_asia", "thailand", "vietnam"]
      }
    }
  ],
  "facets": {
    "solution_categories": {
      "risk_reduction": 89,
      "insurance_penetration": 67,
      "risk_financing": 45
    },
    "risk_types": {
      "flood": 120,
      "drought": 89,
      "agricultural": 156
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

### **Solution-Focused Response Fields**

#### **Core Solution Fields**
| Field | Type | Description |
|-------|------|-------------|
| `solution_name` | string | Name of the solution |
| `publication_date` | string | Publication date (YYYY-MM-DD) |
| `country_regions_covered` | array | Countries/regions covered |
| `risk_types_addressed` | array | Risk types addressed (ontology-matched) |
| `solution_categories` | array | Solution categories (risk reduction, insurance penetration, risk financing) |
| `solution_types` | array | Specific solution subcategories |
| `solution_implementation_timeline` | string | Implementation timeline if available |
| `last_kr_harvest_date` | string | Last knowledge repository harvest date |
| `implemented` | enum | Implementation status: "yes", "no", "unknown" |
| `ppp_involvement` | enum | PPP involvement: "yes", "no", "unknown" |

#### **Detailed Solution Information**
| Field | Type | Description |
|-------|------|-------------|
| `summary_description` | string | Paragraph summarizing the solution |
| `key_highlights` | array | Key highlights in bullet point format |
| `results_outcomes` | string | Results and outcomes if available |
| `solution_contact_info` | object | Contact information (organization, email, phone, website) |
| `source_links` | array | Links to source websites and documents |
| `source` | string | Source of information (Internet, World Bank, etc.) |

### **Repository Metadata Endpoints**

#### **Last Update Endpoint**
```http
GET /repository/last-update
```

**Response:**
```json
{
  "status": "success",
  "last_update": "2024-09-24T08:00:00Z",
  "update_type": "document_ingestion",
  "documents_updated": 15
}
```

#### **Solution Count Endpoint**
```http
GET /repository/solution-count
```

**Response:**
```json
{
  "status": "success",
  "total_solutions": 1247,
  "total_documents": 265,
  "last_counted": "2024-09-24T08:00:00Z",
  "breakdown": {
    "risk_reduction": 456,
    "insurance_penetration": 523,
    "risk_financing": 268
  }
}
```

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
- Example: `"flood insurance protection gap in Thailand government policy"` vs `"flood insurance Thailand policy"`

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

### **1. Basic Solution Discovery**
```json
{
  "query": "parametric insurance agricultural risk",
  "parameters": {
    "max_results": 10,
    "include_snippets": true
  }
}
```

### **2. Risk-Specific Solution Search**
```json
{
  "query": "drought insurance solutions smallholder farmers",
  "filters": {
    "solution_category": ["risk reduction", "insurance penetration"],
    "risk_type": ["drought", "agricultural"],
    "geographic_scope": ["ASEAN", "country"],
    "ppp_involvement": true
  },
  "options": {
    "include_facets": true
  }
}
```

### **3. Regional PPP Solution Analysis**
```json
{
  "query": "public private partnership flood insurance",
  "filters": {
    "geographic_scope": ["ASEAN+3"],
    "solution_category": ["risk financing"],
    "ppp_involvement": true,
    "implemented": "yes"
  },
  "parameters": {
    "relevance_threshold": 0.8,
    "snippet_length": 400
  }
}
```

### **4. Repository Metadata Queries**
```bash
# Get last update information
GET /repository/last-update

# Get solution count breakdown
GET /repository/solution-count
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
- **File**: `solve-global-gaip-kr-api.yaml`
- **Interactive docs**: Available upon request

### **Support Channels**
- **Technical Support**: api-support@solve.global
- **Account Management**: partnerships@solve.global
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

**Questions or need assistance with integration? Contact our technical support team at api-support@solve.global**
