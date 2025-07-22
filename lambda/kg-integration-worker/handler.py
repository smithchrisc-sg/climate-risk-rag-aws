#!/usr/bin/env python3
"""
KG Integration Worker Lambda Handler
Entry point for knowledge graph integration processing
"""
import sys
import os

# Add lambda layer paths
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from kg_integration_worker import KGIntegrationWorker

def lambda_handler(event, context):
    """Lambda entry point for KG integration processing"""
    worker = KGIntegrationWorker()
    return worker.lambda_handler(event, context)
