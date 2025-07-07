#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test vector embeddings cost estimation and model comparison
"""
import sys
import os
sys.path.append('./lambda/vector_embeddings_worker')

from embeddings_interface import EmbeddingsFactory

def test_cost_estimation():
    """Test cost estimation for both models"""
    
    # Sample texts (typical chunk sizes)
    sample_texts = [
        "Climate change represents one of the most significant challenges facing humanity in the 21st century. The scientific consensus is clear that human activities, particularly the emission of greenhouse gases, are driving unprecedented changes in Earth's climate system.",
        "The Paris Agreement, adopted in 2015, established a global framework for addressing climate change by limiting global temperature rise to well below 2 degrees Celsius above pre-industrial levels, with efforts to limit the increase to 1.5 degrees Celsius.",
        "Renewable energy technologies, including solar, wind, and hydroelectric power, have experienced dramatic cost reductions and efficiency improvements over the past decade, making them increasingly competitive with fossil fuel alternatives.",
        "Climate risk assessment involves evaluating the potential impacts of climate change on various sectors, including agriculture, water resources, coastal areas, and human health, to inform adaptation and mitigation strategies.",
        "Carbon pricing mechanisms, such as carbon taxes and cap-and-trade systems, are policy tools designed to internalize the environmental costs of greenhouse gas emissions and incentivize low-carbon alternatives."
    ]
    
    print("Testing Vector Embeddings Cost Estimation")
    print("=" * 60)
    
    # Test SentenceTransformers (free model)
    print("\nSentenceTransformers Model:")
    try:
        st_embeddings = EmbeddingsFactory.create_embeddings('sentence_transformers')
        st_cost = st_embeddings.estimate_cost(sample_texts)
        st_info = st_embeddings.get_model_info()
        
        print("  Model: {}".format(st_info['model_name']))
        print("  Dimension: {}".format(st_info['dimension']))
        print("  Cost for {} chunks: ${:.6f}".format(len(sample_texts), st_cost))
        print("  Cost per chunk: ${:.6f}".format(st_cost/len(sample_texts)))
        print("  Cost per 1000 docs (18 chunks avg): ${:.2f}".format(st_cost/len(sample_texts)*18*1000))
        
    except Exception as e:
        print("  Error: {}".format(str(e)))
    
    # Test Titan (paid model)
    print("\nAmazon Titan Model:")
    try:
        titan_embeddings = EmbeddingsFactory.create_embeddings('titan')
        titan_cost = titan_embeddings.estimate_cost(sample_texts)
        titan_info = titan_embeddings.get_model_info()
        
        print("  Model: {}".format(titan_info['model_id']))
        print("  Dimension: {}".format(titan_info['dimension']))
        print("  Cost for {} chunks: ${:.6f}".format(len(sample_texts), titan_cost))
        print("  Cost per chunk: ${:.6f}".format(titan_cost/len(sample_texts)))
        print("  Cost per 1000 docs (18 chunks avg): ${:.2f}".format(titan_cost/len(sample_texts)*18*1000))
        
    except Exception as e:
        print("  Error: {}".format(str(e)))
    
    # Cost comparison
    print("\nCost Comparison:")
    try:
        st_cost_per_doc = st_cost/len(sample_texts) * 18  # 18 chunks average
        titan_cost_per_doc = titan_cost/len(sample_texts) * 18
        
        print("  SentenceTransformers per document: ${:.6f}".format(st_cost_per_doc))
        print("  Titan per document: ${:.6f}".format(titan_cost_per_doc))
        print("  Titan is {:.1f}x more expensive".format(titan_cost_per_doc/st_cost_per_doc))
        
        # Decision threshold
        threshold = 0.50  # $0.50 per document
        print("\nDecision (threshold: ${:.2f}/doc):".format(threshold))
        
        if titan_cost_per_doc <= threshold:
            print("  Titan cost ${:.6f} is acceptable".format(titan_cost_per_doc))
            print("  Recommendation: Use Titan for better quality")
        else:
            print("  Titan cost ${:.6f} exceeds threshold".format(titan_cost_per_doc))
            print("  Recommendation: Use SentenceTransformers")
            
    except:
        print("  Unable to compare costs")
    
    print("\n" + "=" * 60)

def test_embeddings_generation():
    """Test actual embeddings generation (if models are available)"""
    
    print("\nTesting Embeddings Generation")
    print("=" * 60)
    
    test_text = ["Climate change is a global challenge requiring immediate action."]
    
    # Test SentenceTransformers
    print("\nSentenceTransformers Generation:")
    try:
        st_embeddings = EmbeddingsFactory.create_embeddings('sentence_transformers')
        embeddings = st_embeddings.create_embeddings_batch(test_text)
        print("  Generated embedding with shape: {}".format(embeddings[0].shape))
        print("  Sample values: {}".format(embeddings[0][:5]))
        
    except Exception as e:
        print("  Error: {}".format(str(e)))
    
    # Test Titan (will fail without AWS credentials/permissions)
    print("\nAmazon Titan Generation:")
    try:
        titan_embeddings = EmbeddingsFactory.create_embeddings('titan')
        embeddings = titan_embeddings.create_embeddings_batch(test_text)
        print("  Generated embedding with shape: {}".format(embeddings[0].shape))
        print("  Sample values: {}".format(embeddings[0][:5]))
        
    except Exception as e:
        print("  Error (expected without AWS setup): {}".format(str(e)))

if __name__ == "__main__":
    test_cost_estimation()
    test_embeddings_generation()
