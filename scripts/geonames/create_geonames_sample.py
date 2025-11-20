#!/usr/bin/env python3
"""
Create a sample of geonames individuals for testing
Extract first N entries from the concatenated RDF file and create a proper RDF/XML file
"""

import sys
import xml.dom.minidom

def create_geonames_sample(input_file, output_file, max_entries=10000):
    """
    Create a sample RDF file with the first N geonames entries
    
    Args:
        input_file: Path to concatenated RDF file
        output_file: Path to output RDF file
        max_entries: Maximum number of entries to include
    """
    
    print(f"Creating sample of {max_entries} entries from {input_file}")
    
    # RDF/XML header
    rdf_header = '''<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF 
    xmlns:cc="http://creativecommons.org/ns#" 
    xmlns:dcterms="http://purl.org/dc/terms/" 
    xmlns:foaf="http://xmlns.com/foaf/0.1/" 
    xmlns:gn="http://www.geonames.org/ontology#" 
    xmlns:owl="http://www.w3.org/2002/07/owl#" 
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" 
    xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#" 
    xmlns:wgs84_pos="http://www.w3.org/2003/01/geo/wgs84_pos#">

'''
    
    rdf_footer = '</rdf:RDF>\n'
    
    entry_count = 0
    current_entry = []
    in_rdf_block = False
    
    try:
        with open(output_file, 'w', encoding='utf-8') as out_f:
            out_f.write(rdf_header)
            
            with open(input_file, 'r', encoding='utf-8') as in_f:
                for line_num, line in enumerate(in_f, 1):
                    line = line.strip()
                    
                    if not line:
                        continue
                    
                    # Check if this is a URL line (start of new entry)
                    if line.startswith('https://sws.geonames.org/') and line.endswith('/'):
                        # Process previous entry if we have one
                        if current_entry and in_rdf_block:
                            try:
                                # Extract the gn:Feature element from the RDF
                                rdf_content = '\n'.join(current_entry)
                                
                                # Find the gn:Feature element
                                start_idx = rdf_content.find('<gn:Feature')
                                end_idx = rdf_content.find('</gn:Feature>') + len('</gn:Feature>')
                                
                                if start_idx != -1 and end_idx != -1:
                                    feature_element = rdf_content[start_idx:end_idx]
                                    
                                    # Pretty print and write
                                    out_f.write('    ' + feature_element + '\n\n')
                                    
                                    entry_count += 1
                                    if entry_count % 1000 == 0:
                                        print(f"Processed {entry_count} entries...")
                                    
                                    # Check if we've hit our limit
                                    if entry_count >= max_entries:
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
            
            # Process the last entry if we haven't reached the limit
            if current_entry and in_rdf_block and entry_count < max_entries:
                try:
                    rdf_content = '\n'.join(current_entry)
                    start_idx = rdf_content.find('<gn:Feature')
                    end_idx = rdf_content.find('</gn:Feature>') + len('</gn:Feature>')
                    
                    if start_idx != -1 and end_idx != -1:
                        feature_element = rdf_content[start_idx:end_idx]
                        out_f.write('    ' + feature_element + '\n\n')
                        entry_count += 1
                        
                except Exception as e:
                    print(f"Error processing final entry: {e}")
            
            out_f.write(rdf_footer)
        
        print(f"Sample created successfully!")
        print(f"Total entries: {entry_count}")
        print(f"Output file: {output_file}")
        
    except Exception as e:
        print(f"Error creating sample: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 create_geonames_sample.py <input_file> <output_file> [max_entries]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    max_entries = int(sys.argv[3]) if len(sys.argv) > 3 else 10000
    
    create_geonames_sample(input_file, output_file, max_entries)
