#!/usr/bin/env python3
"""
Search Method Diagnostic Tool
Tests each search method individually to identify issues
"""

import asyncio
import json
import sys
import os

# Add lambda search path
sys.path.append('/Users/chris/climate-risk-rag-aws/lambda/search/src')

from search.opensearch import OpenSearchProcessor
from search.neptune import NeptuneProcessor
from search.postgres import PostgresProcessor

async def test_keyword_search(query="climate risk"):
    """Test OpenSearch keyword search"""
    print("=" * 60)
    print("TESTING KEYWORD SEARCH (OpenSearch)")
    print("=" * 60)
    
    try:
        processor = OpenSearchProcessor()
        results = await processor.search_documents(query, {}, {"size": 5})
        
        print(f"✅ Keyword search successful")
        print(f"📊 Results count: {len(results)}")
        
        for i, result in enumerate(results[:3]):
            print(f"\n{i+1}. Score: {result.score:.4f}")
            print(f"   Doc ID: {result.doc_id}")
            print(f"   Title: {result.title[:80]}...")
            
        return results
        
    except Exception as e:
        print(f"❌ Keyword search failed: {e}")
        return []

async def test_vector_search(query="climate risk"):
    """Test OpenSearch vector search"""
    print("\n" + "=" * 60)
    print("TESTING VECTOR SEARCH (OpenSearch)")
    print("=" * 60)
    
    try:
        processor = OpenSearchProcessor()
        results = await processor.search_chunks_by_vector(query, {}, {"size": 5})
        
        print(f"✅ Vector search successful")
        print(f"📊 Results count: {len(results)}")
        
        for i, result in enumerate(results[:3]):
            print(f"\n{i+1}. Score: {result.score:.4f}")
            print(f"   Doc ID: {result.doc_id}")
            print(f"   Title: {result.title[:80]}...")
            
        return results
        
    except Exception as e:
        print(f"❌ Vector search failed: {e}")
        return []

async def test_graph_search(query="climate risk"):
    """Test Neptune graph search"""
    print("\n" + "=" * 60)
    print("TESTING GRAPH SEARCH (Neptune)")
    print("=" * 60)
    
    try:
        processor = NeptuneProcessor()
        results = await processor.search_by_entities(query, {}, {"size": 5})
        
        print(f"✅ Graph search successful")
        print(f"📊 Results count: {len(results)}")
        
        for i, result in enumerate(results[:3]):
            print(f"\n{i+1}. Score: {result.score:.4f}")
            print(f"   Doc ID: {result.doc_id}")
            print(f"   Title: {result.title[:80]}...")
            
        return results
        
    except Exception as e:
        print(f"❌ Graph search failed: {e}")
        return []

async def compare_score_ranges(keyword_results, vector_results, graph_results):
    """Compare score ranges across methods"""
    print("\n" + "=" * 60)
    print("SCORE RANGE ANALYSIS")
    print("=" * 60)
    
    def analyze_scores(results, method_name):
        if not results:
            print(f"{method_name}: No results")
            return
            
        scores = [r.score for r in results]
        print(f"{method_name}:")
        print(f"  Count: {len(scores)}")
        print(f"  Range: {min(scores):.4f} - {max(scores):.4f}")
        print(f"  Average: {sum(scores)/len(scores):.4f}")
    
    analyze_scores(keyword_results, "Keyword")
    analyze_scores(vector_results, "Vector")
    analyze_scores(graph_results, "Graph")

async def main():
    """Run diagnostic tests"""
    query = sys.argv[1] if len(sys.argv) > 1 else "climate risk"
    
    print(f"🔍 Diagnosing search methods with query: '{query}'")
    
    # Test each method
    keyword_results = await test_keyword_search(query)
    vector_results = await test_vector_search(query)
    graph_results = await test_graph_search(query)
    
    # Compare results
    await compare_score_ranges(keyword_results, vector_results, graph_results)
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
