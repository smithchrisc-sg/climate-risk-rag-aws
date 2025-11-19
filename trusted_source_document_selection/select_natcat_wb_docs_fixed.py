#!/usr/bin/env python3
"""
Natural Catastrophe World Bank Document Selection Script

Selects World Bank documents relevant to Natural Catastrophe solutions using:
- Vector similarity search via Qdrant
- Lexical filtering for NatCat + solution terms
- Per-query normalized relevance scoring

Outputs JSONL manifest for downstream ingestion as trusted source documents.
"""

import csv
import json
import sqlite3
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

# =============================================================================
# CONFIGURATION
# =============================================================================

# Input paths
CSV_PATHS = [
    "/Users/chris/climate-risk-rag-aws/solution_ingestion/input_data/natural_catastrophe_26-Sep-2025.csv",
    "/Users/chris/climate-risk-rag-aws/solution_ingestion/input_data/natural_catastrophe_original.csv"
]
TEXT_COLS_IN_CSV = ["Description", "Key Highlights", "Results"]

# SQLite database
SQLITE_DB_PATH = "/Volumes/G-RAID Photo 24TB/climate_risk_rag/db/corpus_document_ids.db"

# Qdrant configuration
QDRANT_URL = "http://localhost:6333"
QDRANT_COLLECTION = "document_chunks"
N_CHUNKS_PER_QUERY = 20

# Scoring thresholds
MIN_NORM_SCORE = 0.75
N_DOCS_PER_QUERY = 3

# Output
OUTPUT_MANIFEST = "wb_natcat_tsd_manifest_lexical.jsonl"

# Lexical filter terms
NATCAT_DOC_TERMS = [
    "flood", "flooding",
    "cyclone", "hurricane", "typhoon", 
    "storm surge",
    "drought",
    "wildfire", "bushfire",
    "landslide",
    "earthquake", 
    "tsunami",
    "disaster risk", "natural disaster", "natural hazard", "catastrophe",
]

SOLUTIONISH_TERMS = [
    "insurance", "financing", "risk transfer", "parametric",
    "index insurance", "catastrophe bond", "reinsurance", 
    "early warning", "contingent credit", "reserve fund",
    "risk pool", "sovereign risk", "premium subsidy",
]

# =============================================================================
# EMBEDDING FUNCTION
# =============================================================================

# Global model instance
_model = None

def embed(text: str) -> list[float]:
    """Create embedding for text using sentence-transformers."""
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Truncate to avoid huge inputs
    truncated_text = text[:3000]
    embedding = _model.encode(truncated_text)
    return embedding.tolist()

# =============================================================================
# DATA LOADING FUNCTIONS
# =============================================================================

def load_natcat_solution_texts(csv_paths: list[str], text_cols: list[str]) -> list[str]:
    """Load NatCat solution texts from CSVs."""
    query_texts = []
    
    for csv_path in csv_paths:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                text_parts = []
                for col in text_cols:
                    if col in row and row[col]:
                        text_parts.append(row[col].strip())
                
                if text_parts:
                    full_text = "\n\n".join(text_parts)
                    query_texts.append(full_text)
    
    return query_texts

def load_wb_docs(db_path: str) -> dict[str, dict]:
    """Load WB docs from SQLite database."""
    wb_docs = {}
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT doc_id, url, original_filename, text_path FROM documents")
    
    for row in cursor.fetchall():
        doc_id, url, original_filename, text_path = row
        
        # Read full text for lexical filtering
        full_text = ""
        if text_path:
            try:
                # Convert relative path to absolute
                abs_text_path = f"/Volumes/G-RAID Photo 24TB/climate_risk_rag/{text_path}"
                with open(abs_text_path, 'r', encoding='utf-8') as f:
                    full_text = f.read()
            except Exception:
                pass  # Use empty string if file can't be read
        
        wb_docs[doc_id] = {
            "doc_id": doc_id,
            "title": original_filename or "",
            "url": url or "",
            "text_excerpt": full_text
        }
    
    conn.close()
    return wb_docs

# =============================================================================
# SEARCH FUNCTIONS
# =============================================================================

def search_qdrant_for_text(text: str) -> dict[str, float]:
    """Search Qdrant and return {doc_id: best_similarity_score}."""
    client = QdrantClient(url=QDRANT_URL, check_compatibility=False)
    
    # Get embedding for query text
    query_vector = embed(text)
    
    # Search Qdrant
    search_results = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector,
        limit=N_CHUNKS_PER_QUERY,
        with_payload=True
    )
    
    # Aggregate by doc_id, keeping max similarity per doc
    doc_scores = {}
    for result in search_results.points:
        doc_id = result.payload.get("doc_id")
        if doc_id:
            score = result.score
            if doc_id not in doc_scores or score > doc_scores[doc_id]:
                doc_scores[doc_id] = score
    
    return doc_scores

# =============================================================================
# FILTERING FUNCTIONS
# =============================================================================

def doc_is_natcat_like(doc: dict) -> bool:
    """Check if doc contains NatCat and solution-ish terms."""
    text = doc.get("text_excerpt", "").lower()
    
    has_natcat = any(term in text for term in NATCAT_DOC_TERMS)
    has_solution = any(term in text for term in SOLUTIONISH_TERMS)
    
    return has_natcat and has_solution

# =============================================================================
# SELECTION AND RANKING FUNCTIONS
# =============================================================================

def select_docs_per_query(query_texts: list[str], wb_docs_by_id: dict[str, dict]) -> list[tuple[int, str, float]]:
    """Select docs per query with normalized scoring."""
    solution_docs = []
    
    for query_idx, text in enumerate(query_texts):
        print(f"Processing query {query_idx + 1}/{len(query_texts)}")
        
        # Search Qdrant
        doc_scores = search_qdrant_for_text(text)
        if not doc_scores:
            continue
        
        # Normalize scores for this query
        max_score = max(doc_scores.values())
        if max_score == 0:
            continue
        
        query_candidates = []
        for doc_id, score in doc_scores.items():
            norm_score = score / max_score
            
            # Apply threshold
            if norm_score < MIN_NORM_SCORE:
                continue
            
            # Check if doc exists and passes lexical filter
            doc = wb_docs_by_id.get(doc_id)
            if not doc or not doc_is_natcat_like(doc):
                continue
            
            query_candidates.append((doc_id, norm_score))
        
        # Sort by normalized score and take top N
        query_candidates.sort(key=lambda x: x[1], reverse=True)
        for doc_id, norm_score in query_candidates[:N_DOCS_PER_QUERY]:
            solution_docs.append((query_idx, doc_id, norm_score))
    
    return solution_docs

def aggregate_doc_scores(solution_docs: list[tuple[int, str, float]]) -> tuple[dict[str, float], dict[str, int]]:
    """Aggregate doc scores across queries."""
    doc_max_score = {}
    doc_hit_count = {}
    
    for query_idx, doc_id, norm_score in solution_docs:
        # Track best score
        if doc_id not in doc_max_score or norm_score > doc_max_score[doc_id]:
            doc_max_score[doc_id] = norm_score
        
        # Track hit count
        doc_hit_count[doc_id] = doc_hit_count.get(doc_id, 0) + 1
    
    return doc_max_score, doc_hit_count

def rank_docs(doc_max_score: dict[str, float], doc_hit_count: dict[str, int]) -> list[tuple[str, float, int]]:
    """Rank docs by best score, then hit count."""
    ranked = []
    for doc_id in doc_max_score:
        ranked.append((doc_id, doc_max_score[doc_id], doc_hit_count[doc_id]))
    
    # Sort by best_norm_score desc, then hit_count desc
    ranked.sort(key=lambda x: (x[1], x[2]), reverse=True)
    return ranked

# =============================================================================
# OUTPUT FUNCTION
# =============================================================================

def write_manifest(ranked_docs: list[tuple[str, float, int]], wb_docs_by_id: dict[str, dict], output_path: str) -> None:
    """Write JSONL manifest file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        for doc_id, best_norm_score, hit_count in ranked_docs:
            doc = wb_docs_by_id[doc_id]
            
            manifest_entry = {
                "doc_id": doc_id,
                "title": doc["title"],
                "url": doc["url"],
                "best_norm_score": best_norm_score,
                "num_solution_queries_hit": hit_count,
                "source": "wb_poc_local",
                "content_type": "tsd"
            }
            
            f.write(json.dumps(manifest_entry) + '\n')

# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main():
    """Main execution function."""
    print("Starting NatCat WB document selection...")
    
    # Load NatCat solution texts
    print("Loading NatCat solution texts...")
    query_texts = load_natcat_solution_texts(CSV_PATHS, TEXT_COLS_IN_CSV)
    print(f"Loaded {len(query_texts)} NatCat solution texts")
    
    # Load WB docs
    print("Loading WB docs from SQLite...")
    wb_docs_by_id = load_wb_docs(SQLITE_DB_PATH)
    print(f"Loaded {len(wb_docs_by_id)} WB docs")
    
    # Run per-query selection
    print("Running per-query selection...")
    solution_docs = select_docs_per_query(query_texts, wb_docs_by_id)
    print(f"Selected {len(solution_docs)} doc-query pairs")
    
    # Aggregate and rank
    print("Aggregating and ranking docs...")
    doc_max_score, doc_hit_count = aggregate_doc_scores(solution_docs)
    ranked_docs = rank_docs(doc_max_score, doc_hit_count)
    print(f"Final selection: {len(ranked_docs)} unique WB docs")
    
    # Write manifest
    print(f"Writing manifest to {OUTPUT_MANIFEST}...")
    write_manifest(ranked_docs, wb_docs_by_id, OUTPUT_MANIFEST)
    
    # Print stats
    print("\n=== FINAL STATS ===")
    print(f"Loaded {len(query_texts)} NatCat solution texts")
    print(f"Loaded {len(wb_docs_by_id)} WB docs")
    print(f"Selected {len(ranked_docs)} WB docs as NatCat TSDs")
    print(f"Manifest written to: {OUTPUT_MANIFEST}")
    
    if ranked_docs:
        print(f"Top doc: {ranked_docs[0][0]} (score: {ranked_docs[0][1]:.3f}, hits: {ranked_docs[0][2]})")

if __name__ == "__main__":
    main()
