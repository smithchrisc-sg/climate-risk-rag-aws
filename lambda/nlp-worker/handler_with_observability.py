#!/usr/bin/env python3
"""
NLP Worker Lambda Handler with Observability
Entry point for NLP results processing with comprehensive metrics tracking
"""
import sys
import os

# Add lambda layer paths
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from nlp_worker_with_observability import NLPWorkerWithObservability

def lambda_handler(event, context):
    """Lambda entry point for NLP results processing with observability"""
    worker = NLPWorkerWithObservability()
    return worker.process_event(event, context)
