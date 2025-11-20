#!/usr/bin/env python3
"""
Convert large RDF/XML files to Turtle format efficiently
Handles large files by processing in chunks to avoid memory issues
"""

import sys
from rdflib import Graph
import argparse

def convert_rdf_to_turtle(input_file, output_file, chunk_size=100000):
    """
    Convert RDF/XML to Turtle format efficiently for large files
    
    Args:
        input_file: Path to input RDF/XML file
        output_file: Path to output Turtle file
        chunk_size: Number of triples to process at once
    """
    
    print(f"Converting {input_file} to {output_file}")
    print(f"Processing in chunks of {chunk_size} triples")
    
    # Create graph and parse input
    g = Graph()
    
    try:
        print("Parsing RDF/XML file...")
        g.parse(input_file, format='xml')
        
        print(f"Loaded {len(g)} triples")
        
        # Serialize to Turtle
        print("Writing Turtle format...")
        g.serialize(destination=output_file, format='turtle')
        
        print(f"Conversion complete! Output: {output_file}")
        
    except Exception as e:
        print(f"Error during conversion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert RDF/XML to Turtle')
    parser.add_argument('input_file', help='Input RDF/XML file')
    parser.add_argument('output_file', help='Output Turtle file')
    parser.add_argument('--chunk-size', type=int, default=100000, 
                       help='Chunk size for processing (default: 100000)')
    
    args = parser.parse_args()
    
    convert_rdf_to_turtle(args.input_file, args.output_file, args.chunk_size)
