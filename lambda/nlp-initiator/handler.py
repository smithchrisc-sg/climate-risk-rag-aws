#!/usr/bin/env python3
"""
NLP Processor Lambda Handler (renamed from initiator for compatibility)
Entry point for NLP processing pipeline
"""
import sys
import os

# Add lambda layer paths
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from nlp_initiator import NLPInitiator

def lambda_handler(event, context):
    """Lambda entry point for NLP processing initiation"""
    initiator = NLPInitiator()
    return initiator.process_event(event, context)
