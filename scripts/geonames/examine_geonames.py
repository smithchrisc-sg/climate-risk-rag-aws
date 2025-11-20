#!/usr/bin/env python3
"""
Simple script to examine the structure of the concatenated geonames RDF file
No external dependencies required
"""

import sys

def examine_file_structure(input_file, num_entries=5):
    """Examine the file structure to understand the format"""
    
    print(f"Examining structure of {input_file}")
    
    entry_count = 0
    current_entry = []
    in_rdf_block = False
    line_count = 0
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line_count += 1
                line = line.strip()
                
                if not line:
                    continue
                
                # Check if this is a URL line
                if line.startswith('https://sws.geonames.org/') and line.endswith('/'):
                    if current_entry:
                        print(f"\n--- Entry {entry_count + 1} ---")
                        print(f"URL: {line}")
                        print("RDF Content (first 5 lines):")
                        for i, content_line in enumerate(current_entry[:5]):
                            print(f"  {content_line}")
                        if len(current_entry) > 5:
                            print(f"  ... ({len(current_entry) - 5} more lines)")
                        print(f"Total lines in this entry: {len(current_entry)}")
                        
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
                
                # Progress indicator for large files
                if line_count % 100000 == 0:
                    print(f"Processed {line_count} lines, found {entry_count} entries so far...")
    
    except Exception as e:
        print(f"Error examining file: {e}")
        return
    
    print(f"\nSummary:")
    print(f"Total lines processed: {line_count}")
    print(f"Total entries found: {entry_count}")

def count_entries_estimate(input_file, sample_lines=1000000):
    """Get a rough estimate of total entries by sampling"""
    
    print(f"Estimating total entries in {input_file} (sampling first {sample_lines} lines)")
    
    entry_count = 0
    line_count = 0
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line_count += 1
                line = line.strip()
                
                if line.startswith('https://sws.geonames.org/') and line.endswith('/'):
                    entry_count += 1
                
                if line_count >= sample_lines:
                    break
        
        # Estimate total
        if line_count > 0:
            entries_per_line = entry_count / line_count
            
            # Get total file size estimate
            import os
            file_size = os.path.getsize(input_file)
            
            print(f"Sample results:")
            print(f"  Lines sampled: {line_count}")
            print(f"  Entries found: {entry_count}")
            print(f"  Entries per line: {entries_per_line:.6f}")
            print(f"  File size: {file_size:,} bytes ({file_size/1024/1024/1024:.1f} GB)")
            
            # Very rough estimate - this is just for planning
            if entries_per_line > 0:
                estimated_total_entries = int(file_size / (line_count / entry_count) * entries_per_line)
                print(f"  Estimated total entries: {estimated_total_entries:,}")
    
    except Exception as e:
        print(f"Error estimating entries: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 examine_geonames.py <input_file> [--estimate]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if len(sys.argv) > 2 and sys.argv[2] == '--estimate':
        count_entries_estimate(input_file)
    else:
        examine_file_structure(input_file)
