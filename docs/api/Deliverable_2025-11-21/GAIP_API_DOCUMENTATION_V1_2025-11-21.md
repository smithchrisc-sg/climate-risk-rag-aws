# GAIP Knowledge Repository Search API - v1.0 Documentation (2025-11-21)

## Overview

The GAIP Knowledge Repository Search API v1.0 provides comprehensive search capabilities over climate risk solutions and trusted source documents with complete metadata and related document integration.

**Current Base URL**: `https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1`  
**Production Base URL**: `https://api.solve.global/gaip/v1` (Future)

## Authentication

**Current Status**: No authentication required for testing  
**Production**: JWT Bearer token authentication (see `GAIP_API_AUTHENTICATION_GUIDE_V1_2025-11-21.md`)

```bash
# Current - No authentication needed
curl -X POST https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search

# Future - Authentication required
Authorization: Bearer <your-jwt-token>
```

## Endpoints

### 1. POST /search

Search the knowledge repository with comprehensive results including related documents.

**Request Body:**

```json
{
  "query": "parametric flood insurance Southeast Asia",
  "filters": {
    "solution_category": ["natural-catastrophe"],
    "solution_type": ["risk-reduction"],
    "countries": ["thailand", "vietnam"],
    "ppp_involvement": true
  },
  "parameters": {
    "max_results": 20,
    "cursor": null
  }
}
```

**Complete Filter Options:**

| Filter | Type | Values | Description |
|--------|------|--------|-------------|
| `solution_category` | array | `natural-catastrophe`, `cyber`, `health`, `retirement`, `mortality` | Primary risk categories |
| `solution_type` | array | `risk-reduction`, `risk-financing`, `increase-penetration`, `raising-awareness`, `leveraging-technology`, `regulation` | Solution approaches |
| `countries` | array | `thailand`, `vietnam`, `philippines`, `indonesia`, `malaysia`, `singapore`, `cambodia`, `laos`, `myanmar`, `brunei`, `china`, `japan`, `south-korea`, `india`, `bangladesh`, `pakistan`, `nepal`, `sri-lanka`, `australia`, `new-zealand` | Country-specific filtering |
| `region` | array | `asean`, `asean-plus-3`, `asia-pacific` | Regional groupings |
| `ppp_involvement` | boolean | `true`, `false` | Public-Private Partnership involvement |

**Response Structure:**

```json
{
  "status": "success",
  "query_id": "search_12345_67890",
  "execution_time_ms": 285,
  "total_results": 156,
  "returned_results": 20,
  "results": {
    "solutions": [
      {
        "document_id": "sol_001",
        "content_type": "solution",
        "solution_name": "Parametric Flood Insurance Program",
        "title": "Protection Gap Analysis: Flood Insurance in Southeast Asia 2024",
        "relevance_score": 0.95,
        "publication_date": "2024-03-15",
        "implemented": true,
        "ppp_involvement": "yes",
        "last_update_date": "2025-04-22",
        "country_regions_covered": ["Thailand", "Vietnam", "Philippines"],
        "risk_types_addressed": ["Natural Catastrophe", "Flood", "Agricultural"],
        "solution_categories": [],
        "solution_types": ["Risk Reduction", "Risk Financing"],
        "key_highlights": [
          "Automated payout system reduces claim processing time to 48 hours",
          "Covers 50,000+ smallholder farmers across three countries",
          "95% payout accuracy achieved in pilot program"
        ],
        "summary_description": "This parametric insurance solution provides rapid payouts to rice farmers affected by flooding, using satellite data and weather indices.",
        "source": "https://documents.worldbank.org/example",
        "related_documents": [
          {
            "doc_id": "tsd_002",
            "content_type": "trusted_source_document",
            "title": "Flood Risk Assessment Methodology for Southeast Asian Rice Production",
            "summary": "Comprehensive methodology for assessing flood risks in rice-producing regions",
            "rank": 1,
            "source_name": "World Bank",
            "source_url": "https://documents.worldbank.org/flood-assessment"
          },
          {
            "doc_id": "tsd_003",
            "content_type": "trusted_source_document",
            "title": "Parametric Insurance Technical Implementation Guide",
            "summary": "Technical guidelines for implementing parametric insurance products",
            "rank": 2,
            "source_name": "International Finance Corporation",
            "source_url": "https://www.ifc.org/parametric-guide"
          }
        ],
        "snippets": [
          {
            "text": "Protection gap analysis reveals significant underinsurance in flood-prone regions...",
            "page_number": 12,
            "section": "Regional Assessment"
          }
        ],
        "metadata": {
          "document_type": "solution",
          "categories": ["Natural Catastrophe", "Flood"],
          "regions": ["Thailand", "Vietnam", "Philippines"],
          "publication_year": 2024,
          "source": "https://documents.worldbank.org/example"
        }
      }
    ]
  },
  "pagination": {
    "current_page": 1,
    "page_size": 20,
    "total_pages": 8,
    "has_next": true,
    "has_previous": false,
    "next_cursor": "eyJza2lwIjoyMH0="
  }
}
```

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `document_id` | string | Unique solution identifier |
| `solution_name` | string | Primary solution name |
| `implemented` | boolean | True if solution is currently active/implemented |
| `ppp_involvement` | string | "yes", "no", or "unknown" for Public-Private Partnership |
| `last_update_date` | string | ISO8601 date when solution was last updated (YYYY-MM-DD) |
| `key_highlights` | array | Individual highlight strings from solution documentation |
| `risk_types_addressed` | array | Human-readable risk type labels |
| `solution_types` | array | Human-readable solution approach labels |
| `country_regions_covered` | array | Country names where solution is applicable |
| `related_documents` | array | 3-5 relevant trusted source documents per solution |

### 2. GET /repository/last-update

Returns the last repository update timestamp.

**Response:**

```json
{
  "last_update": "2025-11-21T10:30:00Z",
  "update_type": "incremental",
  "documents_updated": 15
}
```

### 3. GET /repository/solution-count

Returns statistics about repository content.

**Response:**

```json
{
  "total_documents": 967,
  "solutions": 567,
  "trusted_source_documents": 400,
  "last_updated": "2025-11-21T10:30:00Z"
}
```

---

## Pagination

Uses cursor-based pagination for efficient large result sets.

**First Request:**
```json
{
  "query": "climate risk",
  "parameters": {
    "max_results": 20,
    "cursor": null
  }
}
```

**Subsequent Requests:**
```json
{
  "query": "climate risk",
  "parameters": {
    "max_results": 20,
    "cursor": "eyJza2lwIjoyMH0="
  }
}
```

---

## Error Responses

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid/missing token (production only) |
| 403 | Forbidden - Insufficient permissions (production only) |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |

**Error Format:**

```json
{
  "error": {
    "code": "INVALID_FILTER",
    "message": "Invalid solution_category value",
    "details": "Allowed values: natural-catastrophe, cyber, health, retirement, mortality"
  }
}
```

---

## Usage Examples

### Search for Natural Catastrophe Solutions

```bash
curl -X POST https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "earthquake insurance",
    "filters": {
      "solution_category": ["natural-catastrophe"],
      "countries": ["japan", "philippines"]
    },
    "parameters": {
      "max_results": 10
    }
  }'
```

### Search with PPP Filter

```bash
curl -X POST https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "parametric insurance",
    "filters": {
      "solution_category": ["natural-catastrophe"],
      "ppp_involvement": true
    },
    "parameters": {
      "max_results": 15
    }
  }'
```

### Browse by Region

```bash
curl -X POST https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "",
    "filters": {
      "region": ["asean"],
      "solution_type": ["risk-financing"]
    },
    "parameters": {
      "max_results": 25
    }
  }'
```

---

## Advanced Features

### Related Documents
Each solution includes 3-5 related trusted source documents:
- **World Bank reports** and policy papers
- **IMF studies** and economic analyses  
- **Academic research** and technical guides
- **Government policy** documents
- **Industry best practices** and case studies

### Hybrid Search
The API combines three search approaches:
1. **Keyword Search (BM25)**: Exact term matching with field boosting
2. **Semantic Search (Vector)**: Conceptual similarity using AI embeddings
3. **Knowledge Graph**: Structured relationship filtering

### Smart Filtering
- **Automatic categorization** based on content analysis
- **Geographic intelligence** using GeoNames integration
- **Organization analysis** for PPP involvement detection
- **Implementation status** based on publication dates

---

## Performance & Limits

### Response Times
- **Simple queries**: 200-500ms
- **Complex filtered searches**: 300-800ms
- **With related documents**: 500-1000ms

### Rate Limits
- **100 requests per minute** per client
- **1000 requests per hour** per client

### Content Statistics
- **567+ solutions** across all risk categories
- **400+ trusted source documents** from major institutions
- **Coverage**: Asia-Pacific focus with global best practices
- **Languages**: Primarily English with some multilingual content

---

## Best Practices

### Query Construction
1. **Use natural language** - "flood insurance for farmers" works better than "flood+insurance+farmers"
2. **Combine text and filters** - Search "insurance" + filter by "natural-catastrophe" + "thailand"
3. **Start broad, then narrow** - Begin with category filters, then add geographic or type filters
4. **Leverage related documents** - Use them to discover additional relevant content

### Filter Strategy
1. **solution_category** first for broad categorization
2. **countries** or **region** for geographic focus
3. **solution_type** for specific approaches
4. **ppp_involvement** for partnership-based solutions

### Pagination
1. **Use cursor-based pagination** for consistent results
2. **Cache cursors** for back/forward navigation
3. **Limit page sizes** to 50 or fewer for optimal performance

### Error Handling
1. **Implement retry logic** for 5xx errors
2. **Validate filters** before sending requests
3. **Handle empty results** gracefully
4. **Cache successful responses** when appropriate

---

## Integration Patterns

### Frontend Integration
```javascript
class GaipSearchClient {
  constructor(baseUrl = 'https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1') {
    this.baseUrl = baseUrl;
  }
  
  async search(query, filters = {}, maxResults = 20, cursor = null) {
    const response = await fetch(`${this.baseUrl}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        filters,
        parameters: { max_results: maxResults, cursor }
      })
    });
    
    return response.json();
  }
  
  async getStats() {
    const response = await fetch(`${this.baseUrl}/repository/solution-count`);
    return response.json();
  }
}
```

### Backend Integration
```python
import requests
from typing import Dict, List, Optional

class GaipSearchClient:
    def __init__(self, base_url: str = "https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1"):
        self.base_url = base_url
    
    def search(self, query: str, filters: Dict = None, max_results: int = 20, cursor: str = None) -> Dict:
        payload = {
            "query": query,
            "filters": filters or {},
            "parameters": {"max_results": max_results, "cursor": cursor}
        }
        
        response = requests.post(f"{self.base_url}/search", json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_solution_count(self) -> Dict:
        response = requests.get(f"{self.base_url}/repository/solution-count")
        response.raise_for_status()
        return response.json()
```

---

## Support

For questions about this API:
- **Email**: api-support@solve.global
- **Current API Documentation**: This document
- **Authentication Guide**: `GAIP_API_AUTHENTICATION_GUIDE_V1_2025-11-21.md`
- **Implementation Guide**: `GAIP_API_IMPLEMENTATION_GUIDE_2025-11-21.md`

---

**Document Version**: v1.0 (2025-11-21)  
**API Status**: Production Ready - All Features Implemented  
**Last Updated**: November 21, 2025
