#!/usr/bin/env python3
"""
Process the concatenated geonames RDF file
The all-geonames-rdf.rdf file contains multiple RDF/XML documents concatenated together,
each with its own XML declaration. We need to extract and process them properly.
"""

import re
import sys
from rdflib import Graph, Namespace
from rdflib.namespace import RDF, RDFS
import argparse

def process_concatenated_geonames_rdf(input_file, output_file, max_entries=None):
    """
    Process concatenated geonames RDF file and convert to turtle
    
    Args:
        input_file: Path to concatenated RDF file
        output_file: Path to output turtle file
        max_entries: Maximum number of entries to process (for testing)
    """
    
    print(f"Processing {input_file}")
    
    # Create combined graph
    combined_graph = Graph()
    
    # Define namespaces
    gn = Namespace("http://www.geonames.org/ontology#")
    combined_graph.bind("gn", gn)
    combined_graph.bind("rdfs", RDFS)
    
    entry_count = 0
    current_entry = []
    in_rdf_block = False
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Check if this is a URL line (geonames ID)
                if line.startswith('https://sws.geonames.org/') and line.endswith('/'):
                    # Process previous entry if we have one
                    if current_entry and in_rdf_block:
                        try:
                            rdf_content = '\n'.join(current_entry)
                            temp_graph = Graph()
                            temp_graph.parse(data=rdf_content, format='xml')
                            
                            # Add to combined graph
                            for triple in temp_graph:
                                combined_graph.add(triple)
                            
                            entry_count += 1
                            if entry_count % 10000 == 0:
                                print(f"Processed {entry_count} entries...")
                            
                            # Check if we've hit our limit
                            if max_entries and entry_count >= max_entries:
                                print(f"Reached maximum entries limit: {max_entries}")
                                break
                                
                        except Exception as e:
                            print(f"Error processing entry {entry_count}: {e}")
                    
                    # Start new entry
                    current_entry = []
                    in_rdf_block = False
                    continue
                
                # Check if this starts an RDF block
                if line.startswith('<?xml') or line.startswith('<rdf:RDF'):
                    in_rdf_block = True
                
                # Add line to current entry if we're in an RDF block
                if in_rdf_block:
                    current_entry.append(line)
        
        # Process the last entry
        if current_entry and in_rdf_block:
            try:
                rdf_content = '\n'.join(current_entry)
                temp_graph = Graph()
                temp_graph.parse(data=rdf_content, format='xml')
                
                for triple in temp_graph:
                    combined_graph.add(triple)
                
                entry_count += 1
            except Exception as e:
                print(f"Error processing final entry: {e}")
        
        print(f"Total entries processed: {entry_count}")
        print(f"Total triples: {len(combined_graph)}")
        
        # Write to turtle format
        print(f"Writing turtle format to {output_file}")
        combined_graph.serialize(destination=output_file, format='turtle')
        
        print("Conversion complete!")
        
    except Exception as e:
        print(f"Error processing file: {e}")
        sys.exit(1)

def sample_file_structure(input_file, num_entries=5):
    """Sample the file structure to understand the format"""
    
    print(f"Sampling structure of {input_file}")
    
    entry_count = 0
    current_entry = []
    in_rdf_block = False
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            if not line:
                continue
            
            # Check if this is a URL line
            if line.startswith('https://sws.geonames.org/') and line.endswith('/'):
                if current_entry:
                    print(f"\n--- Entry {entry_count + 1} ---")
                    print(f"URL: {line}")
                    print("RDF Content (first 3 lines):")
                    for i, content_line in enumerate(current_entry[:3]):
                        print(f"  {content_line}")
                    if len(current_entry) > 3:
                        print(f"  ... ({len(current_entry) - 3} more lines)")
                    
                    entry_count += 1
                    if entry_count >= num_entries:
                        break
                
                current_entry = []
                in_rdf_block = False
                continue
            
            if line.startswith('<?xml') or line.startswith('<rdf:RDF'):
                in_rdf_block = True
            
            if in_rdf_block:
                current_entry.append(line)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process concatenated geonames RDF file')
    parser.add_argument('input_file', help='Input concatenated RDF file')
    parser.add_argument('--output', '-o', help='Output turtle file')
    parser.add_argument('--sample', '-s', action='store_true', 
                       help='Just sample the file structure')
    parser.add_argument('--max-entries', '-m', type=int, 
                       help='Maximum number of entries to process')
    
    args = parser.parse_args()
    
    if args.sample:
        sample_file_structure(args.input_file)
    else:
        if not args.output:
            args.output = args.input_file.replace('.rdf', '.ttl')
        
        process_concatenated_geonames_rdf(args.input_file, args.output, args.max_entries)
