#!/usr/bin/env python3
"""Debug version with lower thresholds and debug output"""

import csv
import json
import sqlite3
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

# Lower thresholds for debugging
MIN_NORM_SCORE = 0.5  # Lower threshold
N_DOCS_PER_QUERY = 5
N_CHUNKS_PER_QUERY = 20

# Paths
CSV_PATHS = [
    "/Users/chris/climate-risk-rag-aws/solution_ingestion/input_data/natural_catastrophe_26-Sep-2025.csv",
    "/Users/chris/climate-risk-rag-aws/solution_ingestion/input_data/natural_catastrophe_original.csv"
]
TEXT_COLS_IN_CSV = ["Description", "Key Highlights", "Results"]
SQLITE_DB_PATH = "/Volumes/G-RAID Photo 24TB/climate_risk_rag/db/corpus_document_ids.db"
QDRANT_URL = "http://localhost:6333"
QDRANT_COLLECTION = "document_chunks"

# Terms
NATCAT_DOC_TERMS = [
    "flood", "flooding", "cyclone", "hurricane", "typhoon", "storm surge",
    "drought", "wildfire", "bushfire", "landslide", "earthquake", "tsunami",
    "disaster risk", "natural disaster", "natural hazard", "catastrophe",
]

SOLUTIONISH_TERMS = [
    "insurance", "financing", "risk transfer", "parametric", "index insurance", 
    "catastrophe bond", "reinsurance", "early warning", "contingent credit", 
    "reserve fund", "risk pool", "sovereign risk", "premium subsidy",
]

_model = None

def embed(text: str) -> list[float]:
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    truncated_text = text[:3000]
    embedding = _model.encode(truncated_text)
    return embedding.tolist()

def load_natcat_solution_texts(csv_paths: list[str], text_cols: list[str]) -> list[str]:
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

def search_qdrant_for_text(text: str) -> dict[str, float]:
    client = QdrantClient(url=QDRANT_URL, check_compatibility=False)
    query_vector = embed(text)
    
    search_results = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector,
        limit=N_CHUNKS_PER_QUERY,
        with_payload=True
    )
    
    doc_scores = {}
    for result in search_results.points:
        doc_id = result.payload.get("doc_id")
        if doc_id:
            score = result.score
            if doc_id not in doc_scores or score > doc_scores[doc_id]:
                doc_scores[doc_id] = score
    
    return doc_scores

def doc_is_natcat_like(doc: dict) -> bool:
    text = doc.get("text_excerpt", "").lower()
    has_natcat = any(term in text for term in NATCAT_DOC_TERMS)
    has_solution = any(term in text for term in SOLUTIONISH_TERMS)
    return has_natcat and has_solution

def main():
    print("Debug run with lower thresholds...")
    
    # Load first few queries only
    query_texts = load_natcat_solution_texts(CSV_PATHS, TEXT_COLS_IN_CSV)[:5]
    print(f"Testing with {len(query_texts)} queries")
    
    # Load WB docs
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT doc_id, url, original_filename, text_path FROM documents LIMIT 100")
    
    wb_docs_by_id = {}
    for row in cursor.fetchall():
        doc_id, url, original_filename, text_path = row
        full_text = ""
        if text_path:
            try:
                with open(text_path, 'r', encoding='utf-8') as f:
                    full_text = f.read()[:5000]  # Limit text for debug
            except Exception:
                pass
        
        wb_docs_by_id[doc_id] = {
            "doc_id": doc_id,
            "title": original_filename or "",
            "url": url or "",
            "text_excerpt": full_text
        }
    
    conn.close()
    print(f"Loaded {len(wb_docs_by_id)} WB docs for testing")
    
    # Test first query
    if query_texts:
        print(f"\nTesting first query: {query_texts[0][:200]}...")
        doc_scores = search_qdrant_for_text(query_texts[0])
        print(f"Found {len(doc_scores)} docs from vector search")
        
        if doc_scores:
            max_score = max(doc_scores.values())
            print(f"Max score: {max_score}")
            
            # Check lexical filtering
            natcat_count = 0
            solution_count = 0
            both_count = 0
            
            for doc_id, score in list(doc_scores.items())[:10]:
                doc = wb_docs_by_id.get(doc_id)
                if doc:
                    text = doc.get("text_excerpt", "").lower()
                    has_natcat = any(term in text for term in NATCAT_DOC_TERMS)
                    has_solution = any(term in text for term in SOLUTIONISH_TERMS)
                    
                    if has_natcat:
                        natcat_count += 1
                    if has_solution:
                        solution_count += 1
                    if has_natcat and has_solution:
                        both_count += 1
                        
                    norm_score = score / max_score
                    print(f"  {doc_id}: score={score:.3f}, norm={norm_score:.3f}, natcat={has_natcat}, solution={has_solution}")
            
            print(f"\nLexical filter results:")
            print(f"  Docs with NatCat terms: {natcat_count}")
            print(f"  Docs with solution terms: {solution_count}")
            print(f"  Docs with both: {both_count}")

if __name__ == "__main__":
    main()
