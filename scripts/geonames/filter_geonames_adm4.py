#!/usr/bin/env python3
"""
Filter geonames data to include only administrative divisions up to ADM4 level
Extracts countries, states, counties, districts, and municipalities from the concatenated RDF file
"""

import re
import sys
from collections import Counter

def filter_geonames_adm4(input_file, output_file, max_entries=None):
    """
    Filter geonames data to include only ADM4 level administrative divisions
    
    Args:
        input_file: Path to concatenated geonames RDF file
        output_file: Path to output RDF file
        max_entries: Maximum number of entries to process (None for all)
    """
    
    # Define ADM4 level feature codes to include
    adm4_codes = {
        # Countries
        'A.PCLI',   # Independent political entity
        'A.PCLF',   # Freely associated state
        'A.PCLD',   # Dependent political entity
        'A.PCLS',   # Semi-independent political entity
        
        # Administrative divisions
        'A.ADM1',   # First-order administrative division (states, provinces)
        'A.ADM1H',  # Historical first-order administrative division
        'A.ADM2',   # Second-order administrative division (counties)
        'A.ADM2H',  # Historical second-order administrative division
        'A.ADM3',   # Third-order administrative division (districts)
        'A.ADM3H',  # Historical third-order administrative division
        'A.ADM4',   # Fourth-order administrative division (municipalities)
        'A.ADM4H',  # Historical fourth-order administrative division
        'A.ADMD',   # Administrative division (general)
        'A.ADMDH',  # Historical administrative division (general)
        
        # Capital cities (important administrative centers)
        'P.PPLC',   # Capital of a political entity
        'P.PPLA',   # Seat of a first-order administrative division
        'P.PPLA2',  # Seat of a second-order administrative division
        'P.PPLA3',  # Seat of a third-order administrative division
        'P.PPLA4',  # Seat of a fourth-order administrative division
    }
    
    print(f"Filtering {input_file} for ADM4 level administrative divisions")
    print(f"Target feature codes: {sorted(adm4_codes)}")
    
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
    filtered_count = 0
    current_entry = []
    in_rdf_block = False
    feature_code_stats = Counter()
    
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
                                # Extract the feature code to determine if we should include this entry
                                rdf_content = '\n'.join(current_entry)
                                
                                feature_code_match = re.search(r'gn:featureCode rdf:resource="https://www\.geonames\.org/ontology#([^"]+)"', rdf_content)
                                
                                if feature_code_match:
                                    feature_code = feature_code_match.group(1)
                                    feature_code_stats[feature_code] += 1
                                    
                                    # Check if this feature code should be included
                                    if feature_code in adm4_codes:
                                        # Extract the gn:Feature element from the RDF
                                        start_idx = rdf_content.find('<gn:Feature')
                                        end_idx = rdf_content.find('</gn:Feature>') + len('</gn:Feature>')
                                        
                                        if start_idx != -1 and end_idx != -1:
                                            feature_element = rdf_content[start_idx:end_idx]
                                            
                                            # Write to output file with proper indentation
                                            out_f.write('    ' + feature_element + '\n\n')
                                            filtered_count += 1
                                            
                                            if filtered_count % 1000 == 0:
                                                print(f"Included {filtered_count} entries (processed {entry_count})...")
                                
                                entry_count += 1
                                
                                # Progress indicator
                                if entry_count % 100000 == 0:
                                    print(f"Processed {entry_count:,} entries, included {filtered_count:,} ({(filtered_count/entry_count)*100:.2f}%)")
                                
                                # Check if we've hit our limit
                                if max_entries and entry_count >= max_entries:
                                    print(f"Reached maximum entries limit: {max_entries:,}")
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
            if current_entry and in_rdf_block and (not max_entries or entry_count < max_entries):
                try:
                    rdf_content = '\n'.join(current_entry)
                    feature_code_match = re.search(r'gn:featureCode rdf:resource="https://www\.geonames\.org/ontology#([^"]+)"', rdf_content)
                    
                    if feature_code_match:
                        feature_code = feature_code_match.group(1)
                        feature_code_stats[feature_code] += 1
                        
                        if feature_code in adm4_codes:
                            start_idx = rdf_content.find('<gn:Feature')
                            end_idx = rdf_content.find('</gn:Feature>') + len('</gn:Feature>')
                            
                            if start_idx != -1 and end_idx != -1:
                                feature_element = rdf_content[start_idx:end_idx]
                                out_f.write('    ' + feature_element + '\n\n')
                                filtered_count += 1
                    
                    entry_count += 1
                        
                except Exception as e:
                    print(f"Error processing final entry: {e}")
            
            out_f.write(rdf_footer)
        
        # Print final statistics
        print(f"\n=== FILTERING COMPLETE ===")
        print(f"Total entries processed: {entry_count:,}")
        print(f"Entries included: {filtered_count:,}")
        print(f"Filter rate: {(filtered_count/entry_count)*100:.2f}%")
        print(f"Output file: {output_file}")
        
        # Print feature code breakdown for included entries
        print(f"\n=== INCLUDED FEATURE CODES ===")
        included_codes = {code: count for code, count in feature_code_stats.items() if code in adm4_codes}
        for code in sorted(included_codes.keys()):
            count = included_codes[code]
            percentage = (count / filtered_count) * 100 if filtered_count > 0 else 0
            print(f"{code:10} {count:8,} ({percentage:5.1f}%)")
        
        # Estimate full dataset impact
        if entry_count > 0:
            estimated_total = 4_600_000_000
            estimated_filtered = int(estimated_total * (filtered_count / entry_count))
            estimated_size_mb = estimated_filtered * 4 / 1024  # Rough estimate: 4KB per entry
            
            print(f"\n=== ESTIMATED FULL DATASET IMPACT ===")
            print(f"Estimated total entries in full dataset: {estimated_total:,}")
            print(f"Estimated filtered entries: {estimated_filtered:,}")
            print(f"Estimated file size: {estimated_size_mb:.0f}MB")
            print(f"Size reduction: {((estimated_total - estimated_filtered) / estimated_total) * 100:.1f}%")
        
    except Exception as e:
        print(f"Error during filtering: {e}")
        sys.exit(1)

def convert_to_turtle(rdf_file, ttl_file):
    """Convert the filtered RDF file to Turtle format"""
    
    print(f"Converting {rdf_file} to Turtle format...")
    
    try:
        import subprocess
        result = subprocess.run([
            'rapper', '-i', 'rdfxml', '-o', 'turtle', rdf_file
        ], capture_output=True, text=True, check=True)
        
        with open(ttl_file, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
        
        print(f"Conversion complete: {ttl_file}")
        
        # Get triple count
        lines = result.stderr.split('\n')
        for line in lines:
            if 'returned' in line and 'triples' in line:
                print(f"Triple count: {line}")
                break
        
    except subprocess.CalledProcessError as e:
        print(f"Error converting to Turtle: {e}")
        print("You can convert manually with: rapper -i rdfxml -o turtle input.rdf > output.ttl")
    except ImportError:
        print("subprocess not available, skipping Turtle conversion")
        print("You can convert manually with: rapper -i rdfxml -o turtle input.rdf > output.ttl")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Filter geonames data for ADM4 level administrative divisions')
    parser.add_argument('input_file', help='Input concatenated geonames RDF file')
    parser.add_argument('output_file', help='Output filtered RDF file')
    parser.add_argument('--max-entries', '-m', type=int, 
                       help='Maximum number of entries to process (for testing)')
    parser.add_argument('--convert-turtle', '-t', action='store_true',
                       help='Also convert output to Turtle format')
    
    args = parser.parse_args()
    
    # Run the filtering
    filter_geonames_adm4(args.input_file, args.output_file, args.max_entries)
    
    # Convert to Turtle if requested
    if args.convert_turtle:
        ttl_file = args.output_file.replace('.rdf', '.ttl')
        convert_to_turtle(args.output_file, ttl_file)
