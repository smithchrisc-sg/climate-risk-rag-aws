#!/usr/bin/env python3
"""
Debug RDF content before Neptune loading
"""

import sys
import os
import logging
from pathlib import Path

# Add current directory to path
sys.path.append('.')

from parsers.csv_parser import CSVParser
from generators.pseudo_document_generator import PseudoDocumentGenerator
from generators.integrated_rdf_chunk_generator import IntegratedRDFChunkGenerator
from config.environment import Environment

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def debug_rdf_generation():
    """Debug RDF generation for first solution."""
    
    # Initialize components
    env = Environment()
    csv_parser = CSVParser()
    doc_generator = PseudoDocumentGenerator()
    integrated_generator = IntegratedRDFChunkGenerator()
    
    # Parse first solution
    csv_file = Path("input_data/natural_catastrophe_26-Sep-2025.csv")
    solutions = list(csv_parser.parse_csv_file(csv_file))
    
    # Process first solution
    test_solution = solutions[0]
    logger.info(f"Testing solution: {test_solution.name[:50]}...")
    
    # Generate pseudo-document
    processed_solutions = doc_generator.process_solutions([test_solution])
    processed_solution = processed_solutions[0]
    
    # Generate RDF
    logger.info("Generating RDF...")
    rdf_content, chunks = integrated_generator.generate_document_rdf_and_chunks(processed_solution)
    
    # Debug RDF content
    logger.info(f"RDF length: {len(rdf_content)} characters")
    logger.info(f"Generated chunks: {len(chunks)}")
    
    # Check for common RDF syntax issues
    lines = rdf_content.split('\n')
    logger.info(f"RDF has {len(lines)} lines")
    
    # Show first 20 lines
    logger.info("First 20 lines of RDF:")
    for i, line in enumerate(lines[:20], 1):
        logger.info(f"{i:2d}: {line}")
    
    # Check for syntax issues
    issues = []
    
    # Check for unescaped quotes in literals
    for i, line in enumerate(lines, 1):
        if '"' in line and not line.strip().startswith('@'):
            # Count quotes - should be even for proper literals
            quote_count = line.count('"')
            if quote_count % 2 != 0:
                issues.append(f"Line {i}: Odd number of quotes: {line}")
    
    # Check for missing prefixes
    used_prefixes = set()
    declared_prefixes = set()
    
    for line in lines:
        if line.startswith('@prefix'):
            prefix = line.split(':')[0].replace('@prefix ', '')
            declared_prefixes.add(prefix)
        elif ':' in line and not line.startswith('@'):
            # Find prefixes used in triples
            parts = line.split()
            for part in parts:
                if ':' in part and not part.startswith('http'):
                    prefix = part.split(':')[0]
                    used_prefixes.add(prefix)
    
    missing_prefixes = used_prefixes - declared_prefixes
    if missing_prefixes:
        issues.append(f"Missing prefix declarations: {missing_prefixes}")
    
    # Check for malformed URIs
    for i, line in enumerate(lines, 1):
        if '<' in line and '>' in line:
            # Extract URIs
            import re
            uris = re.findall(r'<([^>]+)>', line)
            for uri in uris:
                if ' ' in uri:
                    issues.append(f"Line {i}: URI contains spaces: <{uri}>")
    
    if issues:
        logger.error("RDF Syntax Issues Found:")
        for issue in issues[:10]:  # Show first 10 issues
            logger.error(f"  {issue}")
    else:
        logger.info("No obvious RDF syntax issues found")
    
    # Try to parse with rdflib
    try:
        from rdflib import Graph
        g = Graph()
        g.parse(data=rdf_content, format='turtle')
        logger.info(f"✅ RDFLib parsing successful: {len(g)} triples")
    except Exception as e:
        logger.error(f"❌ RDFLib parsing failed: {e}")
        
        # Show the problematic area
        error_str = str(e)
        if "line" in error_str.lower():
            import re
            line_match = re.search(r'line (\d+)', error_str)
            if line_match:
                error_line = int(line_match.group(1))
                logger.error(f"Error around line {error_line}:")
                start = max(0, error_line - 3)
                end = min(len(lines), error_line + 3)
                for i in range(start, end):
                    marker = ">>> " if i == error_line - 1 else "    "
                    logger.error(f"{marker}{i+1:3d}: {lines[i]}")
    
    # Save RDF to file for manual inspection
    debug_file = Path("debug_rdf_output.ttl")
    with open(debug_file, 'w', encoding='utf-8') as f:
        f.write(rdf_content)
    logger.info(f"RDF content saved to: {debug_file}")

if __name__ == "__main__":
    debug_rdf_generation()
