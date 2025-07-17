# Climate Risk RAG API Documentation

## Overview

The Climate Risk RAG system provides several APIs for document processing, search, and analysis. This document describes the available APIs and how to use them.

## Document Processing API

### Upload Document

Upload a document to the system for processing.

**Endpoint:** `POST /api/documents`

**Request:**
```json
{
  "document_name": "climate_risk_report_2025.pdf",
  "document_type": "pdf",
  "metadata": {
    "author": "Climate Research Institute",
    "publication_date": "2025-01-15",
    "tags": ["climate", "risk", "report"]
  }
}
```

**Response:**
```json
{
  "doc_id": "01dd077eebd99666",
  "status": "processing",
  "upload_url": "https://s3.amazonaws.com/bucket/upload-url"
}
```

### Get Document Status

Get the processing status of a document.

**Endpoint:** `GET /api/documents/{doc_id}/status`

**Response:**
```json
{
  "doc_id": "01dd077eebd99666",
  "status": "completed",
  "processing_stages": {
    "text_extraction": "completed",
    "chunking": "completed",
    "keyword_indexing": "completed",
    "vector_embeddings": "completed",
    "knowledge_graph": "completed"
  },
  "error": null
}
```

## Search API

### Search Documents

Search for documents using keywords and/or semantic search.

**Endpoint:** `POST /api/search`

**Request:**
```json
{
  "query": "climate change impact on coastal cities",
  "search_type": "hybrid",
  "filters": {
    "document_type": ["pdf", "docx"],
    "date_range": {
      "start": "2020-01-01",
      "end": "2025-12-31"
    },
    "tags": ["climate", "risk"]
  },
  "limit": 10,
  "offset": 0
}
```

**Response:**
```json
{
  "results": [
    {
      "doc_id": "01dd077eebd99666",
      "document_name": "climate_risk_report_2025.pdf",
      "relevance_score": 0.92,
      "snippet": "Climate change is expected to have significant impacts on coastal cities...",
      "metadata": {
        "author": "Climate Research Institute",
        "publication_date": "2025-01-15",
        "tags": ["climate", "risk", "report"]
      }
    },
    {
      "doc_id": "02ee088ffc00777",
      "document_name": "coastal_adaptation_strategies.pdf",
      "relevance_score": 0.85,
      "snippet": "Coastal cities must implement adaptation strategies to mitigate climate risks...",
      "metadata": {
        "author": "Urban Planning Institute",
        "publication_date": "2024-11-20",
        "tags": ["climate", "adaptation", "urban"]
      }
    }
  ],
  "total_results": 42,
  "page": 1,
  "total_pages": 5
}
```

## Knowledge Graph API

### Get Entity Information

Get information about an entity in the knowledge graph.

**Endpoint:** `GET /api/knowledge-graph/entities/{entity_id}`

**Response:**
```json
{
  "entity_id": "ent_123456",
  "name": "Sea Level Rise",
  "type": "climate_risk_factor",
  "description": "The increase in the level of the world's oceans due to climate change effects",
  "related_entities": [
    {
      "entity_id": "ent_789012",
      "name": "Coastal Flooding",
      "type": "climate_risk_impact",
      "relationship": "causes"
    },
    {
      "entity_id": "ent_345678",
      "name": "Glacier Melting",
      "type": "climate_phenomenon",
      "relationship": "caused_by"
    }
  ],
  "mentioned_in": [
    {
      "doc_id": "01dd077eebd99666",
      "document_name": "climate_risk_report_2025.pdf",
      "mention_count": 15
    }
  ]
}
```

### Query Knowledge Graph

Run a custom query on the knowledge graph.

**Endpoint:** `POST /api/knowledge-graph/query`

**Request:**
```json
{
  "query": "MATCH (r:RiskFactor)-[:IMPACTS]->(c:City) WHERE c.name = 'Miami' RETURN r.name, r.severity",
  "parameters": {
    "city_name": "Miami"
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "risk_factor": "Sea Level Rise",
      "severity": "High"
    },
    {
      "risk_factor": "Hurricane Frequency",
      "severity": "High"
    },
    {
      "risk_factor": "Extreme Heat",
      "severity": "Medium"
    }
  ]
}
```

## Error Handling

All API endpoints return standard HTTP status codes:

- 200: Success
- 400: Bad Request (invalid parameters)
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 500: Internal Server Error

Error responses include a JSON body with error details:

```json
{
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "Invalid date range specified",
    "details": {
      "parameter": "filters.date_range.start",
      "reason": "Date must be in ISO format (YYYY-MM-DD)"
    }
  }
}
```

## Authentication

All API endpoints require authentication using an API key or JWT token.

**API Key Authentication:**
```
Authorization: ApiKey YOUR_API_KEY
```

**JWT Authentication:**
```
Authorization: Bearer YOUR_JWT_TOKEN
```

## Rate Limiting

API requests are rate-limited to 100 requests per minute per API key. Rate limit information is included in the response headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1625097600
```
