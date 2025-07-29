#!/usr/bin/env python3
"""
KG Triple Loader Lambda Handler
Entry point for loading TTL triples into Neptune from multiple sources
"""
import sys
import os

# Add lambda layer paths
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from kg_triple_loader import KGTripleLoader

def lambda_handler(event, context):
    """Lambda entry point for KG triple loading processing"""
    loader = KGTripleLoader()
    return loader.lambda_handler(event, context)
