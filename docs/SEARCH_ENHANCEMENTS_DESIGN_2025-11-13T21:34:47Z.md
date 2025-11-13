# Search Enhancements Design Document
**Created:** 2025-11-13T21:34:47Z  
**Status:** Design Phase  
**Implementation Target:** Phase 2 - Trusted Document Search Integration

## Executive Summary

This document outlines the design for enhanced search capabilities in the GAIP Climate Risk RAG system, focusing on S3-based search session caching for stable pagination and multi-modal ranking fusion. The design builds upon the successfully implemented Phase 1 cursor-based pagination foundation.

## Current State (Phase 1 Complete ✅)

### Implemented Features
- **Cursor-based pagination API** - Frontend and backend support opaque cursor tokens
- **Neptune solution search** - 567 solutions searchable with comprehensive filters
- **Professional UI** - CloudFront-deployed interface with pagination controls
- **API v2 compliance** - Proper request/response format with query_id and cursor support

### Architecture Foundation
```
Frontend (Cursor UI) → API Gateway → Lambda (Cursor Handler) → Neptune KG + S3 → Response
```

### Current Limitations
- **No query-based ranking** - Search query ignored for solution relevance
- **Filter-only results** - Solutions ranked by Neptune order, not content relevance
- **No document search** - Only solutions available, no supporting documents
- **Sequential pagination** - Each page requires new Neptune query + S3 assembly

## Phase 2 Design: S3-Based Search Session Cache

### Overview
Implement S3-backed search sessions to enable:
1. **Stable pagination** across expensive multi-modal ranking
2. **Query-driven relevance** using BM25 + Vector + Knowledge Graph fusion
3. **Related document discovery** for each solution
4. **Performance optimization** through pre-computed rankings

### Architecture Design

#### High-Level Flow
```
Query → [Compute Full Ranking] → [Store S3 Session] → [Serve Page 1]
Cursor → [Load S3 Session] → [Slice Page N] → [Serve Page N]
```

#### Detailed Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Gateway    │    │   Search Lambda │
│                 │    │                  │    │                 │
│ Cursor UI       │◄──►│ /search endpoint │◄──►│ Cursor Handler  │
│ Page Controls   │    │ 29s timeout      │    │ 1024MB memory   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                       ┌─────────────────────────────────┼─────────────────────────────────┐
                       │                                 ▼                                 │
                       │                    ┌─────────────────────┐                       │
                       │                    │ Search Coordinator  │                       │
                       │                    │ - Session Manager   │                       │
                       │                    │ - Ranking Fusion    │                       │
                       │                    └─────────────────────┘                       │
                       │                                 │                                 │
              ┌────────▼────────┐              ┌────────▼────────┐              ┌────────▼────────┐
              │   Neptune KG    │              │  OpenSearch     │              │   S3 Sessions   │
              │                 │              │                 │              │                 │
              │ Filter Solutions│              │ BM25 + Vector   │              │ Cached Rankings │
              │ Extract Entities│              │ Document Search │              │ Session Metadata│
              └─────────────────┘              └─────────────────┘              └─────────────────┘
```

### S3 Session Cache Design

#### Session Storage Structure
```
Bucket: solve-global-kr-search-sessions-{account-id}-{region}
Key Pattern: search-sessions/{date}/{session_id}.json
Lifecycle: 24-hour auto-deletion
```

#### Session Schema
```json
{
  "session_id": "uuid-v4",
  "created_at": "2025-11-13T21:34:47Z",
  "expires_at": "2025-11-14T21:34:47Z",
  "page_size": 20,
  "total_results": 156,
  "query_metadata": {
    "query_hash": "sha256-of-query-and-filters",
    "original_query": "climate adaptation strategies",
    "applied_filters": {
      "solution_category": ["natural-catastrophe"],
      "countries": ["singapore", "thailand"]
    },
    "search_method": "bm25_vector_fusion",
    "computation_time_ms": 4250
  },
  "ranking_data": {
    "solution_ids": [
      "sol_123", "sol_456", "sol_789", ...
    ],
    "scores": {
      "sol_123": {
        "combined_score": 0.85,
        "bm25_score": 0.72,
        "vector_score": 0.91,
        "kg_score": 0.68,
        "document_count": 3
      }
    },
    "max_cached_results": 500,
    "truncated": false
  }
}
```

#### Cursor Token Format
```json
{
  "query_id": "search_session-uuid",
  "page": 3,
  "integrity_hash": "sha256(query_id + page + secret)[:8]"
}
```

### Multi-Modal Ranking Pipeline

#### Stage 1: Solution Filtering (Neptune)
```python
async def filter_solutions(filters: Dict[str, Any]) -> List[str]:
    """Get candidate solutions using existing Neptune logic"""
    # Use current solution_searcher.search_solutions() without pagination
    # Return all matching solution IDs (up to reasonable limit like 1000)
```

#### Stage 2: Content-Based Ranking (OpenSearch)
```python
async def rank_solutions_by_content(query: str, solution_ids: List[str]) -> Dict[str, float]:
    """Rank solutions by query relevance using OpenSearch"""
    
    # BM25 Keyword Search
    bm25_scores = await opensearch.search_solutions_keyword(
        query=query,
        solution_ids=solution_ids,
        index="documents_keyword"
    )
    
    # Vector Semantic Search  
    vector_scores = await opensearch.search_solutions_vector(
        query=query,
        solution_ids=solution_ids,
        index="chunks_vector"
    )
    
    # Score Fusion using Reciprocal Rank Fusion (RRF)
    combined_scores = {}
    for sol_id in solution_ids:
        bm25_rank = get_rank(sol_id, bm25_scores)
        vector_rank = get_rank(sol_id, vector_scores)
        
        # RRF Formula: 1/(k + rank) where k=60 (standard)
        rrf_score = (1/(60 + bm25_rank)) + (1/(60 + vector_rank))
        combined_scores[sol_id] = rrf_score
    
    return combined_scores
```

#### Stage 3: Knowledge Graph Enhancement (Optional)
```python
async def enhance_with_kg_relationships(solution_ids: List[str], query: str) -> Dict[str, float]:
    """Boost scores based on KG relationships and entity matches"""
    
    # Extract entities from query
    query_entities = extract_entities(query)
    
    # Find solutions with matching entities
    kg_boosts = {}
    for sol_id in solution_ids:
        entity_matches = count_entity_matches(sol_id, query_entities)
        relationship_strength = calculate_relationship_strength(sol_id, query_entities)
        kg_boosts[sol_id] = (entity_matches * 0.1) + (relationship_strength * 0.2)
    
    return kg_boosts
```

#### Stage 4: Related Document Discovery
```python
async def find_related_documents(solution_ids: List[str], query: str) -> Dict[str, List[Dict]]:
    """Find documents related to each solution"""
    
    related_docs = {}
    
    # Process solutions in parallel batches
    for batch in batch_solutions(solution_ids, batch_size=5):
        batch_tasks = []
        for sol_id in batch:
            task = find_documents_for_solution(sol_id, query)
            batch_tasks.append(task)
        
        batch_results = await asyncio.gather(*batch_tasks)
        
        for sol_id, docs in zip(batch, batch_results):
            related_docs[sol_id] = docs[:3]  # Top 3 documents per solution
    
    return related_docs

async def find_documents_for_solution(solution_id: str, query: str) -> List[Dict]:
    """Find documents related to a specific solution"""
    
    # Get solution content for context
    solution_content = await get_solution_content(solution_id)
    
    # Search documents using solution content + user query
    search_query = f"{query} {solution_content['title']} {solution_content['summary']}"
    
    # Parallel document search
    keyword_docs = await opensearch.search_documents_keyword(
        query=search_query,
        content_type="trusted_source_document",
        max_results=10
    )
    
    vector_docs = await opensearch.search_documents_vector(
        query=search_query,
        content_type="trusted_source_document", 
        max_results=10
    )
    
    # Combine and deduplicate
    combined_docs = merge_and_rank_documents(keyword_docs, vector_docs)
    
    return combined_docs[:5]  # Top 5 candidates
```

### Session Management Implementation

#### Session Creation (New Search)
```python
async def handle_new_search(query: str, filters: Dict, parameters: Dict) -> Dict:
    """Handle new search with full ranking computation"""
    
    start_time = time.time()
    
    # Stage 1: Filter solutions
    candidate_solutions = await filter_solutions(filters)
    
    if not query.strip():
        # No query = no ranking needed, use existing logic
        return await handle_filter_only_search(candidate_solutions, parameters)
    
    # Stage 2: Rank by content relevance
    content_scores = await rank_solutions_by_content(query, candidate_solutions)
    
    # Stage 3: Enhance with KG (optional)
    kg_scores = await enhance_with_kg_relationships(candidate_solutions, query)
    
    # Stage 4: Find related documents
    related_documents = await find_related_documents(candidate_solutions, query)
    
    # Combine scores and rank
    final_ranking = []
    for sol_id in candidate_solutions:
        combined_score = (
            content_scores.get(sol_id, 0.0) * 0.7 +  # Content relevance weight
            kg_scores.get(sol_id, 0.0) * 0.3           # KG relationship weight
        )
        
        final_ranking.append({
            'solution_id': sol_id,
            'combined_score': combined_score,
            'content_score': content_scores.get(sol_id, 0.0),
            'kg_score': kg_scores.get(sol_id, 0.0),
            'related_documents': related_documents.get(sol_id, [])
        })
    
    # Sort by combined score
    final_ranking.sort(key=lambda x: x['combined_score'], reverse=True)
    
    # Create session
    session_id = str(uuid.uuid4())
    session_data = create_session_data(
        session_id=session_id,
        query=query,
        filters=filters,
        ranking=final_ranking,
        computation_time=time.time() - start_time
    )
    
    # Store in S3
    await store_session(session_id, session_data)
    
    # Return first page
    return await serve_page_from_session(session_id, page=1, parameters=parameters)
```

#### Session Retrieval (Cursor Navigation)
```python
async def handle_cursor_search(cursor: str, parameters: Dict) -> Dict:
    """Handle cursor-based pagination using cached session"""
    
    # Decode cursor
    cursor_data = decode_cursor(cursor)
    session_id = cursor_data['query_id'].replace('search_', '')
    target_page = cursor_data['page']
    
    # Validate integrity (optional)
    if not validate_cursor_integrity(cursor_data):
        raise ValueError("Invalid cursor")
    
    # Load session from S3
    try:
        session_data = await load_session(session_id)
    except SessionNotFoundError:
        # Session expired - could recompute or return error
        return {"error": "Search session expired, please start a new search"}
    
    # Serve requested page
    return await serve_page_from_session(session_id, target_page, parameters)

async def serve_page_from_session(session_id: str, page: int, parameters: Dict) -> Dict:
    """Serve a specific page from cached session data"""
    
    session_data = await load_session(session_id)
    
    page_size = parameters.get('max_results', session_data['page_size'])
    total_results = len(session_data['ranking_data']['solution_ids'])
    total_pages = (total_results + page_size - 1) // page_size
    
    # Validate page bounds
    if page < 1 or page > total_pages:
        raise ValueError(f"Page {page} out of bounds (1-{total_pages})")
    
    # Calculate slice
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_results)
    
    # Get solution IDs for this page
    page_solution_ids = session_data['ranking_data']['solution_ids'][start_idx:end_idx]
    
    # Assemble full solution data (reuse existing S3 logic)
    solutions = []
    for sol_id in page_solution_ids:
        solution_data = await assemble_solution_data(sol_id)
        
        # Add ranking metadata
        if sol_id in session_data['ranking_data']['scores']:
            score_data = session_data['ranking_data']['scores'][sol_id]
            solution_data['relevance_score'] = score_data['combined_score']
            solution_data['related_documents'] = score_data.get('related_documents', [])
        
        solutions.append(solution_data)
    
    # Build pagination metadata
    next_cursor = None
    if page < total_pages:
        next_cursor = encode_cursor({
            'query_id': f"search_{session_id}",
            'page': page + 1
        })
    
    pagination = {
        'current_page': page,
        'total_pages': total_pages,
        'total_results': total_results,
        'page_size': page_size,
        'has_next': page < total_pages,
        'has_previous': page > 1,
        'next_cursor': next_cursor
    }
    
    return format_search_response(solutions, session_data, pagination)
```

### Performance Optimization Strategies

#### Computation Time Targets
- **New Search (with ranking):** < 15 seconds (within 29s API Gateway limit)
- **Cursor Navigation:** < 2 seconds (S3 lookup + solution assembly)
- **Parallel Processing:** 5 solutions per batch for document search

#### Caching Strategy
```python
# Multi-level caching approach
CACHE_LAYERS = {
    'session_metadata': 'S3 (24h TTL)',
    'solution_content': 'Lambda memory (request scope)',
    'opensearch_results': 'No caching (real-time)',
    'neptune_filters': 'Lambda memory (5min TTL)'
}
```

#### Resource Scaling
```python
LAMBDA_CONFIG = {
    'search_lambda': {
        'memory': 2048,  # Increased for parallel processing
        'timeout': 29,   # API Gateway limit
        'concurrent_executions': 10
    },
    'document_search_lambda': {  # Optional separate lambda
        'memory': 3008,  # Max CPU for parallel document search
        'timeout': 20,
        'concurrent_executions': 20
    }
}
```

### Error Handling & Resilience

#### Graceful Degradation Strategy
```python
async def search_with_fallbacks(query: str, filters: Dict, parameters: Dict) -> Dict:
    """Search with multiple fallback levels"""
    
    try:
        # Level 1: Full multi-modal search
        return await full_multimodal_search(query, filters, parameters)
    
    except OpenSearchError:
        # Level 2: Neptune + basic ranking
        return await neptune_search_with_basic_ranking(query, filters, parameters)
    
    except Exception:
        # Level 3: Filter-only search (current Phase 1 behavior)
        return await filter_only_search(filters, parameters)
```

#### Session Recovery
```python
async def handle_session_expiry(cursor: str, original_request: Dict) -> Dict:
    """Handle expired sessions gracefully"""
    
    # Option A: Recompute and serve requested page
    new_session_response = await handle_new_search(
        query=original_request['query'],
        filters=original_request['filters'],
        parameters=original_request['parameters']
    )
    
    # Adjust to requested page if possible
    cursor_data = decode_cursor(cursor)
    if cursor_data['page'] > 1:
        # Navigate to requested page using new session
        return await handle_cursor_search(
            new_session_response['pagination']['next_cursor'],
            {'page': cursor_data['page']}
        )
    
    return new_session_response
```

### Security Considerations

#### Cursor Integrity
```python
def encode_cursor(payload: Dict) -> str:
    """Encode cursor with integrity check"""
    
    # Add timestamp and hash for integrity
    payload['timestamp'] = int(time.time())
    payload['hash'] = hmac.sha256(
        f"{payload['query_id']}{payload['page']}{SECRET_KEY}".encode()
    ).hexdigest()[:8]
    
    return base64.b64encode(json.dumps(payload).encode()).decode()

def validate_cursor_integrity(cursor_data: Dict) -> bool:
    """Validate cursor hasn't been tampered with"""
    
    expected_hash = hmac.sha256(
        f"{cursor_data['query_id']}{cursor_data['page']}{SECRET_KEY}".encode()
    ).hexdigest()[:8]
    
    return cursor_data.get('hash') == expected_hash
```

#### Session Access Control
```python
# Session isolation by user context
SESSION_KEY_PATTERN = "search-sessions/{user_id}/{date}/{session_id}.json"

# Rate limiting per user
RATE_LIMITS = {
    'new_searches_per_hour': 100,
    'cursor_requests_per_minute': 60,
    'max_concurrent_sessions': 5
}
```

### Monitoring & Observability

#### Key Metrics
```python
CLOUDWATCH_METRICS = {
    'search_performance': [
        'NewSearchLatency',
        'CursorNavigationLatency', 
        'RankingComputationTime',
        'DocumentSearchTime'
    ],
    'session_management': [
        'SessionCreationRate',
        'SessionHitRate',
        'SessionMissRate',
        'SessionExpiryRate'
    ],
    'search_quality': [
        'ResultsPerPage',
        'ZeroResultsRate',
        'UserEngagementRate'
    ]
}
```

#### Logging Strategy
```python
STRUCTURED_LOGGING = {
    'new_search': {
        'query_hash': 'sha256',
        'filter_count': 'int',
        'candidate_solutions': 'int',
        'final_results': 'int',
        'computation_stages': 'dict',
        'performance_breakdown': 'dict'
    },
    'cursor_navigation': {
        'session_id': 'uuid',
        'page_requested': 'int',
        'cache_hit': 'bool',
        'response_time': 'float'
    }
}
```

## Implementation Phases

### Phase 2.1: Basic S3 Session Cache (Week 1)
- [ ] Implement S3 session storage and retrieval
- [ ] Update cursor handling to use sessions
- [ ] Add basic query-based ranking (OpenSearch keyword only)
- [ ] Test with existing UI

### Phase 2.2: Multi-Modal Ranking (Week 2)
- [ ] Implement BM25 + Vector search integration
- [ ] Add Reciprocal Rank Fusion (RRF) scoring
- [ ] Enhance with Knowledge Graph relationships
- [ ] Performance optimization and parallel processing

### Phase 2.3: Related Document Discovery (Week 3)
- [ ] Implement document search for each solution
- [ ] Add document result display to frontend
- [ ] Optimize document search performance
- [ ] Add document-solution relationship scoring

### Phase 2.4: Production Optimization (Week 4)
- [ ] Add comprehensive error handling and fallbacks
- [ ] Implement monitoring and alerting
- [ ] Performance tuning and cost optimization
- [ ] Security hardening and rate limiting

## Success Criteria

### Performance Targets
- **New search response time:** < 15 seconds (95th percentile)
- **Cursor navigation:** < 2 seconds (95th percentile)
- **Search quality:** Improved relevance over filter-only results
- **System reliability:** 99.9% uptime, graceful degradation

### User Experience Goals
- **Stable pagination:** Consistent results across page navigation
- **Relevant ranking:** Query-driven result ordering
- **Rich context:** Related documents for each solution
- **Responsive UI:** No perceived performance degradation

### Technical Excellence
- **Cost efficiency:** Optimized S3 and Lambda usage
- **Scalability:** Support for 100+ concurrent users
- **Maintainability:** Clean, documented, testable code
- **Observability:** Comprehensive monitoring and debugging

---

**Next Steps:** Review and approve design, then proceed with Phase 2.1 implementation.
