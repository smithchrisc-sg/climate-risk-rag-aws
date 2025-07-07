#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple cost calculation for vector embeddings
"""

def calculate_costs():
    # Sample text lengths (typical climate risk document chunks)
    sample_texts = [
        "Climate change represents one of the most significant challenges facing humanity in the 21st century. The scientific consensus is clear that human activities, particularly the emission of greenhouse gases, are driving unprecedented changes in Earth's climate system.",
        "The Paris Agreement, adopted in 2015, established a global framework for addressing climate change by limiting global temperature rise to well below 2 degrees Celsius above pre-industrial levels, with efforts to limit the increase to 1.5 degrees Celsius.",
        "Renewable energy technologies, including solar, wind, and hydroelectric power, have experienced dramatic cost reductions and efficiency improvements over the past decade, making them increasingly competitive with fossil fuel alternatives.",
        "Climate risk assessment involves evaluating the potential impacts of climate change on various sectors, including agriculture, water resources, coastal areas, and human health, to inform adaptation and mitigation strategies.",
        "Carbon pricing mechanisms, such as carbon taxes and cap-and-trade systems, are policy tools designed to internalize the environmental costs of greenhouse gas emissions and incentivize low-carbon alternatives."
    ]
    
    print("Vector Embeddings Cost Analysis")
    print("=" * 50)
    
    # Calculate text statistics
    total_chars = sum(len(text) for text in sample_texts)
    avg_chars_per_chunk = total_chars / len(sample_texts)
    
    # More realistic token estimation for climate documents
    # Climate documents tend to have more technical terms, longer words
    estimated_tokens_per_chunk = avg_chars_per_chunk / 3.5  # More conservative estimate
    
    print("Sample Data:")
    print("  Chunks: {}".format(len(sample_texts)))
    print("  Total characters: {}".format(total_chars))
    print("  Avg chars per chunk: {:.0f}".format(avg_chars_per_chunk))
    print("  Estimated tokens per chunk: {:.0f}".format(estimated_tokens_per_chunk))
    
    # Titan cost calculation
    titan_cost_per_1k_tokens = 0.0004
    titan_cost_per_chunk = (estimated_tokens_per_chunk / 1000) * titan_cost_per_1k_tokens
    
    print("\nAmazon Titan Costs:")
    print("  Cost per 1K tokens: ${:.4f}".format(titan_cost_per_1k_tokens))
    print("  Tokens per chunk: {:.0f}".format(estimated_tokens_per_chunk))
    print("  Cost per chunk: ${:.6f}".format(titan_cost_per_chunk))
    
    # SentenceTransformers cost (Lambda only)
    # Assume 2GB Lambda, ~1ms per chunk processing
    lambda_cost_per_gb_second = 0.0000166667
    processing_time_per_chunk = 0.001  # 1ms
    lambda_memory_gb = 2
    st_cost_per_chunk = processing_time_per_chunk * lambda_memory_gb * lambda_cost_per_gb_second
    
    print("\nSentenceTransformers Costs (Lambda only):")
    print("  Lambda cost per GB-second: ${:.10f}".format(lambda_cost_per_gb_second))
    print("  Processing time per chunk: {:.3f}s".format(processing_time_per_chunk))
    print("  Lambda memory: {}GB".format(lambda_memory_gb))
    print("  Cost per chunk: ${:.10f}".format(st_cost_per_chunk))
    
    # Document-level costs (assuming 18 chunks per document average)
    chunks_per_doc = 18
    titan_cost_per_doc = titan_cost_per_chunk * chunks_per_doc
    st_cost_per_doc = st_cost_per_chunk * chunks_per_doc
    
    print("\nPer Document Costs (18 chunks avg):")
    print("  Titan per document: ${:.6f}".format(titan_cost_per_doc))
    print("  SentenceTransformers per document: ${:.6f}".format(st_cost_per_doc))
    print("  Titan is {:.0f}x more expensive".format(titan_cost_per_doc / st_cost_per_doc))
    
    # 1000 document costs
    docs_1k = 1000
    titan_cost_1k = titan_cost_per_doc * docs_1k
    st_cost_1k = st_cost_per_doc * docs_1k
    
    print("\n1000 Document Processing Costs:")
    print("  Titan for 1K docs: ${:.2f}".format(titan_cost_1k))
    print("  SentenceTransformers for 1K docs: ${:.2f}".format(st_cost_1k))
    print("  Savings with SentenceTransformers: ${:.2f}".format(titan_cost_1k - st_cost_1k))
    
    # Decision threshold
    threshold = 0.50
    print("\nDecision Analysis (threshold: ${:.2f}/doc):".format(threshold))
    
    if titan_cost_per_doc <= threshold:
        print("  OK Titan cost ${:.6f} is acceptable".format(titan_cost_per_doc))
        print("  Recommendation: Use Titan for better quality")
    else:
        print("  WARN Titan cost ${:.6f} exceeds threshold".format(titan_cost_per_doc))
        print("  Recommendation: Use SentenceTransformers")
        
    print("\nConclusion:")
    if titan_cost_per_doc > threshold:
        print("  -> Start with SentenceTransformers (free)")
        print("  -> Architecture supports easy model swapping")
        print("  -> Can upgrade to Titan later if quality improvement justifies cost")
    else:
        print("  -> Titan cost is acceptable")
        print("  -> Can start with Titan for best quality")

if __name__ == "__main__":
    calculate_costs()
