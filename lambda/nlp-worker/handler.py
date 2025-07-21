#!/usr/bin/env python3
"""
NLP Worker Lambda Handler
Entry point for NLP results processing
"""
import sys
import os

# Add lambda layer paths
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from nlp_worker import NLPWorker

def lambda_handler(event, context):
    """Lambda entry point for NLP results processing"""
    worker = NLPWorker()
    return worker.process_event(event, context)
