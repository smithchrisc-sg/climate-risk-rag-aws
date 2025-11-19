#!/usr/bin/env python3
"""Simplified version using only vector similarity"""

import csv
import json
import sqlite3
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

# Configuration
MIN_NORM_SCORE = 0.6  # Lower threshold
N_DOCS_PER_QUERY = 5
N_CHUNKS_PER_QUERY = 20

CSV_PATHS = [
    "/Users/chris/climate-risk-rag-aws/solution_ingestion/input_data/natural_catastrophe_26-Sep-2025.csv",
    "/Users/chris/climate-risk-rag-aws/solution_ingestion/input_data/natural_catastrophe_original.csv"
]
TEXT_COLS_IN_CSV = ["Description", "Key Highlights", "Results"]
SQLITE_DB_PATH = "/Volumes/G-RAID Photo 24TB/climate_risk_rag/db/corpus_document_ids.db"
QDRANT_URL = "http://localhost:6333"
QDRANT_COLLECTION = "document_chunks"
OUTPUT_MANIFEST = "wb_natcat_tsd_simple.jsonl"

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

def load_wb_docs(db_path: str) -> dict[str, dict]:
    wb_docs = {}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT doc_id, url, original_filename FROM documents")
    
    for row in cursor.fetchall():
        doc_id, url, original_filename = row
        wb_docs[doc_id] = {
            "doc_id": doc_id,
            "title": original_filename or "",
            "url": url or ""
        }
    
    conn.close()
    return wb_docs

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

def main():
    print("Simple vector-only selection...")
    
    # Load NatCat solution texts
    query_texts = load_natcat_solution_texts(CSV_PATHS, TEXT_COLS_IN_CSV)
    print(f"Loaded {len(query_texts)} NatCat solution texts")
    
    # Load WB docs
    wb_docs_by_id = load_wb_docs(SQLITE_DB_PATH)
    print(f"Loaded {len(wb_docs_by_id)} WB docs")
    
    # Collect all selected docs
    all_selected = {}  # doc_id -> (best_score, hit_count)
    
    for query_idx, text in enumerate(query_texts):
        if query_idx % 50 == 0:
            print(f"Processing query {query_idx + 1}/{len(query_texts)}")
        
        doc_scores = search_qdrant_for_text(text)
        if not doc_scores:
            continue
        
        max_score = max(doc_scores.values())
        if max_score == 0:
            continue
        
        # Select top docs for this query
        query_candidates = []
        for doc_id, score in doc_scores.items():
            norm_score = score / max_score
            if norm_score >= MIN_NORM_SCORE and doc_id in wb_docs_by_id:
                query_candidates.append((doc_id, norm_score))
        
        # Take top N for this query
        query_candidates.sort(key=lambda x: x[1], reverse=True)
        for doc_id, norm_score in query_candidates[:N_DOCS_PER_QUERY]:
            if doc_id not in all_selected:
                all_selected[doc_id] = [norm_score, 1]
            else:
                all_selected[doc_id][0] = max(all_selected[doc_id][0], norm_score)
                all_selected[doc_id][1] += 1
    
    # Sort by best score, then hit count
    ranked_docs = [(doc_id, scores[0], scores[1]) for doc_id, scores in all_selected.items()]
    ranked_docs.sort(key=lambda x: (x[1], x[2]), reverse=True)
    
    print(f"Selected {len(ranked_docs)} unique WB docs")
    
    # Write manifest
    with open(OUTPUT_MANIFEST, 'w', encoding='utf-8') as f:
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
    
    print(f"Manifest written to: {OUTPUT_MANIFEST}")
    if ranked_docs:
        print(f"Top doc: {ranked_docs[0][0]} (score: {ranked_docs[0][1]:.3f}, hits: {ranked_docs[0][2]})")

if __name__ == "__main__":
    main()
