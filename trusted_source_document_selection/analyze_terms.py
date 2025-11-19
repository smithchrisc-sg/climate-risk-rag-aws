#!/usr/bin/env python3
"""Analyze what terms are actually in WB documents"""

import sqlite3
from collections import Counter

SQLITE_DB_PATH = "/Volumes/G-RAID Photo 24TB/climate_risk_rag/db/corpus_document_ids.db"

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

def main():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT doc_id, text_path FROM documents LIMIT 1000")
    
    natcat_counts = Counter()
    solution_counts = Counter()
    docs_with_natcat = 0
    docs_with_solution = 0
    docs_with_both = 0
    total_docs = 0
    
    for row in cursor.fetchall():
        doc_id, text_path = row
        if not text_path:
            continue
            
        try:
            with open(text_path, 'r', encoding='utf-8') as f:
                text = f.read().lower()
        except Exception:
            continue
        
        total_docs += 1
        
        # Check NatCat terms
        found_natcat = []
        for term in NATCAT_DOC_TERMS:
            if term in text:
                natcat_counts[term] += 1
                found_natcat.append(term)
        
        # Check solution terms
        found_solution = []
        for term in SOLUTIONISH_TERMS:
            if term in text:
                solution_counts[term] += 1
                found_solution.append(term)
        
        if found_natcat:
            docs_with_natcat += 1
        if found_solution:
            docs_with_solution += 1
        if found_natcat and found_solution:
            docs_with_both += 1
            print(f"Doc {doc_id}: natcat={found_natcat[:3]}, solution={found_solution[:3]}")
    
    conn.close()
    
    print(f"\n=== ANALYSIS OF {total_docs} WB DOCUMENTS ===")
    print(f"Docs with NatCat terms: {docs_with_natcat} ({docs_with_natcat/total_docs*100:.1f}%)")
    print(f"Docs with solution terms: {docs_with_solution} ({docs_with_solution/total_docs*100:.1f}%)")
    print(f"Docs with BOTH: {docs_with_both} ({docs_with_both/total_docs*100:.1f}%)")
    
    print(f"\nTop NatCat terms:")
    for term, count in natcat_counts.most_common(10):
        print(f"  {term}: {count}")
    
    print(f"\nTop solution terms:")
    for term, count in solution_counts.most_common(10):
        print(f"  {term}: {count}")

if __name__ == "__main__":
    main()
