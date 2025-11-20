#!/usr/bin/env python3
"""
Analyze geonames feature codes to understand filtering potential
Extract feature codes from the sample and estimate size reduction
"""

import re
from collections import Counter, defaultdict

def analyze_feature_codes(ttl_file):
    """Analyze feature codes in the turtle file"""
    
    print(f"Analyzing feature codes in {ttl_file}")
    
    feature_codes = Counter()
    feature_classes = Counter()
    names_by_feature = defaultdict(list)
    
    current_subject = None
    current_feature_code = None
    current_feature_class = None
    current_name = None
    
    with open(ttl_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # Skip prefixes and empty lines
            if line.startswith('@prefix') or not line:
                continue
            
            # New subject (place)
            if line.startswith('<https://sws.geonames.org/'):
                current_subject = line.split('>')[0] + '>'
                current_feature_code = None
                current_feature_class = None
                current_name = None
                continue
            
            # Extract feature code
            if 'gn:featureCode' in line:
                match = re.search(r'gn:featureCode <https://www\.geonames\.org/ontology#([^>]+)>', line)
                if match:
                    current_feature_code = match.group(1)
                    feature_codes[current_feature_code] += 1
            
            # Extract feature class
            if 'gn:featureClass' in line:
                match = re.search(r'gn:featureClass <https://www\.geonames\.org/ontology#([^>]+)>', line)
                if match:
                    current_feature_class = match.group(1)
                    feature_classes[current_feature_class] += 1
            
            # Extract name
            if 'gn:name' in line and not 'alternateName' in line:
                match = re.search(r'gn:name "([^"]+)"', line)
                if match:
                    current_name = match.group(1)
            
            # Store example when we have all info
            if current_feature_code and current_name and len(names_by_feature[current_feature_code]) < 5:
                names_by_feature[current_feature_code].append(current_name)
    
    return feature_codes, feature_classes, names_by_feature

def analyze_concatenated_file(rdf_file, sample_size=100000):
    """Analyze feature codes directly from the concatenated RDF file"""
    
    print(f"Analyzing feature codes in {rdf_file} (sampling {sample_size} entries)")
    
    feature_codes = Counter()
    feature_classes = Counter()
    names_by_feature = defaultdict(list)
    
    entry_count = 0
    current_entry = []
    in_rdf_block = False
    
    with open(rdf_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            if not line:
                continue
            
            # Check if this is a URL line (start of new entry)
            if line.startswith('https://sws.geonames.org/') and line.endswith('/'):
                # Process previous entry if we have one
                if current_entry and in_rdf_block:
                    try:
                        rdf_content = ' '.join(current_entry)
                        
                        # Extract feature code
                        feature_code_match = re.search(r'gn:featureCode rdf:resource="https://www\.geonames\.org/ontology#([^"]+)"', rdf_content)
                        if feature_code_match:
                            feature_code = feature_code_match.group(1)
                            feature_codes[feature_code] += 1
                        
                        # Extract feature class
                        feature_class_match = re.search(r'gn:featureClass rdf:resource="https://www\.geonames\.org/ontology#([^"]+)"', rdf_content)
                        if feature_class_match:
                            feature_class = feature_class_match.group(1)
                            feature_classes[feature_class] += 1
                        
                        # Extract name
                        name_match = re.search(r'<gn:name>([^<]+)</gn:name>', rdf_content)
                        if name_match and feature_code_match:
                            name = name_match.group(1)
                            feature_code = feature_code_match.group(1)
                            if len(names_by_feature[feature_code]) < 5:
                                names_by_feature[feature_code].append(name)
                        
                        entry_count += 1
                        if entry_count % 10000 == 0:
                            print(f"Processed {entry_count} entries...")
                        
                        # Check if we've hit our sample limit
                        if entry_count >= sample_size:
                            print(f"Reached sample limit: {sample_size}")
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
    
    return feature_codes, feature_classes, names_by_feature, entry_count

def print_analysis(feature_codes, feature_classes, names_by_feature, total_entries):
    """Print the analysis results"""
    
    print(f"\n=== GEONAMES FEATURE ANALYSIS ===")
    print(f"Total entries analyzed: {total_entries:,}")
    print(f"Unique feature codes: {len(feature_codes)}")
    print(f"Unique feature classes: {len(feature_classes)}")
    
    print(f"\n=== FEATURE CLASSES ===")
    for feature_class, count in feature_classes.most_common():
        percentage = (count / total_entries) * 100
        print(f"{feature_class:10} {count:8,} ({percentage:5.1f}%)")
    
    print(f"\n=== TOP FEATURE CODES ===")
    for feature_code, count in feature_codes.most_common(20):
        percentage = (count / total_entries) * 100
        examples = ', '.join(names_by_feature[feature_code][:3])
        print(f"{feature_code:15} {count:8,} ({percentage:5.1f}%) - {examples}")
    
    # Calculate filtering scenarios
    print(f"\n=== FILTERING SCENARIOS ===")
    
    # Scenario 1: Countries, states, major cities
    admin_codes = ['A.PCLI', 'A.ADM1', 'A.ADM2', 'P.PPLC', 'P.PPLA', 'P.PPLA2']
    admin_count = sum(feature_codes[code] for code in admin_codes if code in feature_codes)
    admin_percentage = (admin_count / total_entries) * 100
    print(f"Countries + States + Major Cities: {admin_count:,} ({admin_percentage:.1f}%)")
    
    # Scenario 2: Add ADM3 (counties/districts)
    admin3_codes = admin_codes + ['A.ADM3', 'P.PPLA3']
    admin3_count = sum(feature_codes[code] for code in admin3_codes if code in feature_codes)
    admin3_percentage = (admin3_count / total_entries) * 100
    print(f"+ ADM3 (Counties/Districts): {admin3_count:,} ({admin3_percentage:.1f}%)")
    
    # Scenario 3: Add ADM4 (municipalities)
    admin4_codes = admin3_codes + ['A.ADM4', 'P.PPLA4']
    admin4_count = sum(feature_codes[code] for code in admin4_codes if code in feature_codes)
    admin4_percentage = (admin4_count / total_entries) * 100
    print(f"+ ADM4 (Municipalities): {admin4_count:,} ({admin4_percentage:.1f}%)")
    
    # Scenario 4: All populated places
    populated_codes = [code for code in feature_codes.keys() if code.startswith('P.PPL')]
    populated_count = sum(feature_codes[code] for code in populated_codes)
    populated_percentage = (populated_count / total_entries) * 100
    print(f"All Populated Places (P.PPL*): {populated_count:,} ({populated_percentage:.1f}%)")
    
    # Estimate full dataset impact
    estimated_total = 4_600_000_000  # From our earlier estimate
    print(f"\n=== ESTIMATED FULL DATASET IMPACT ===")
    print(f"Estimated total entries: {estimated_total:,}")
    print(f"Countries + States + Major Cities: {int(estimated_total * admin_percentage / 100):,}")
    print(f"+ ADM3: {int(estimated_total * admin3_percentage / 100):,}")
    print(f"+ ADM4: {int(estimated_total * admin4_percentage / 100):,}")
    print(f"All Populated Places: {int(estimated_total * populated_percentage / 100):,}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_geonames_features.py <file> [sample_size]")
        print("  file: either .ttl file or .rdf file")
        print("  sample_size: for .rdf files, number of entries to sample (default: 100000)")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if input_file.endswith('.ttl'):
        feature_codes, feature_classes, names_by_feature = analyze_feature_codes(input_file)
        total_entries = sum(feature_codes.values())
    else:
        sample_size = int(sys.argv[2]) if len(sys.argv) > 2 else 100000
        feature_codes, feature_classes, names_by_feature, total_entries = analyze_concatenated_file(input_file, sample_size)
    
    print_analysis(feature_codes, feature_classes, names_by_feature, total_entries)
