#!/usr/bin/env python3
"""
Analyze all ADM (Administrative Division) levels in geonames data
"""

import re
from collections import Counter, defaultdict

def analyze_adm_levels(rdf_file, sample_size=500000):
    """Analyze all ADM levels in the concatenated RDF file"""
    
    print(f"Analyzing ADM levels in {rdf_file} (sampling {sample_size} entries)")
    
    feature_codes = Counter()
    adm_codes = Counter()
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
                            
                            # Track ADM codes specifically
                            if feature_code.startswith('A.ADM') or feature_code in ['A.PCLI', 'A.PCLF', 'A.PCLD', 'A.PCLS']:
                                adm_codes[feature_code] += 1
                        
                        # Extract name for examples
                        name_match = re.search(r'<gn:name>([^<]+)</gn:name>', rdf_content)
                        if name_match and feature_code_match:
                            name = name_match.group(1)
                            feature_code = feature_code_match.group(1)
                            if len(names_by_feature[feature_code]) < 5:
                                names_by_feature[feature_code].append(name)
                        
                        entry_count += 1
                        if entry_count % 50000 == 0:
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
    
    return feature_codes, adm_codes, names_by_feature, entry_count

def print_adm_analysis(feature_codes, adm_codes, names_by_feature, total_entries):
    """Print detailed ADM analysis"""
    
    print(f"\n=== ADM LEVELS ANALYSIS ===")
    print(f"Total entries analyzed: {total_entries:,}")
    
    # All ADM-related codes
    print(f"\n=== ALL ADMINISTRATIVE DIVISION CODES ===")
    for feature_code in sorted(adm_codes.keys()):
        count = adm_codes[feature_code]
        percentage = (count / total_entries) * 100
        examples = ', '.join(names_by_feature[feature_code][:3])
        print(f"{feature_code:12} {count:8,} ({percentage:5.2f}%) - {examples}")
    
    # Cumulative analysis
    print(f"\n=== CUMULATIVE ADM FILTERING SCENARIOS ===")
    
    # Define ADM hierarchy
    adm_hierarchy = [
        (['A.PCLI'], 'Countries only'),
        (['A.PCLI', 'A.ADM1'], 'Countries + States/Provinces'),
        (['A.PCLI', 'A.ADM1', 'A.ADM2'], 'Countries + States + Counties'),
        (['A.PCLI', 'A.ADM1', 'A.ADM2', 'A.ADM3'], 'Countries + States + Counties + Districts'),
        (['A.PCLI', 'A.ADM1', 'A.ADM2', 'A.ADM3', 'A.ADM4'], 'Countries + States + Counties + Districts + Municipalities'),
        (['A.PCLI', 'A.ADM1', 'A.ADM2', 'A.ADM3', 'A.ADM4', 'A.ADM5'], 'Countries + States + Counties + Districts + Municipalities + Neighborhoods'),
    ]
    
    # Add other country codes
    other_country_codes = ['A.PCLF', 'A.PCLD', 'A.PCLS', 'A.ADMD']
    
    estimated_total = 4_600_000_000
    
    for codes, description in adm_hierarchy:
        # Include other administrative codes
        all_codes = codes + other_country_codes
        count = sum(adm_codes.get(code, 0) for code in all_codes)
        percentage = (count / total_entries) * 100 if total_entries > 0 else 0
        estimated_full = int(estimated_total * percentage / 100)
        estimated_size_mb = estimated_full * 4 / 1024  # Rough estimate: 4KB per entry
        
        print(f"{description:60} {count:6,} ({percentage:5.2f}%) -> Est: {estimated_full:10,} entries ({estimated_size_mb:6.0f}MB)")
    
    # Check if ADM5 exists
    if 'A.ADM5' not in adm_codes:
        print(f"\n⚠️  A.ADM5 not found in sample of {total_entries:,} entries")
        print("   This suggests A.ADM5 is either very rare or doesn't exist in geonames")
    
    # Popular places analysis
    print(f"\n=== POPULATED PLACES FOR COMPARISON ===")
    populated_codes = ['P.PPLC', 'P.PPLA', 'P.PPLA2', 'P.PPLA3', 'P.PPLA4', 'P.PPL']
    for code in populated_codes:
        if code in feature_codes:
            count = feature_codes[code]
            percentage = (count / total_entries) * 100
            examples = ', '.join(names_by_feature[code][:3])
            print(f"{code:12} {count:8,} ({percentage:5.2f}%) - {examples}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_adm_levels.py <rdf_file> [sample_size]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    sample_size = int(sys.argv[2]) if len(sys.argv) > 2 else 500000
    
    feature_codes, adm_codes, names_by_feature, total_entries = analyze_adm_levels(input_file, sample_size)
    print_adm_analysis(feature_codes, adm_codes, names_by_feature, total_entries)
