#!/usr/bin/env python3
"""
Test SPARQL parser without executing queries.
"""

def parse_sparql_file(filepath):
    """Parse SPARQL file and return list of queries."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Extract PREFIX declarations
    prefixes = []
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if line.startswith('PREFIX'):
            prefixes.append(line)
    
    prefix_block = '\n'.join(prefixes)
    
    # Split queries by semicolon
    queries = []
    current_query = []
    in_query = False
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and comments outside queries
        if not line or (line.startswith('#') and not in_query):
            continue
        
        # Skip PREFIX lines (already extracted)
        if line.startswith('PREFIX'):
            continue
        
        # Start of a query (DELETE, INSERT, or comment before query)
        if line.startswith(('DELETE', 'INSERT', '#')):
            in_query = True
        
        if in_query:
            current_query.append(line)
            
            # Query ends with semicolon
            if line.endswith(';'):
                query_text = '\n'.join(current_query)
                # Add prefixes to each query
                queries.append(f"{prefix_block}\n\n{query_text}")
                current_query = []
                in_query = False
    
    return queries

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 test_sparql_parser.py <sparql_file>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    print(f"Parsing {filepath}...")
    queries = parse_sparql_file(filepath)
    
    print(f"\nFound {len(queries)} queries\n")
    print("=" * 80)
    
    for i, query in enumerate(queries, 1):
        print(f"\nQUERY {i}:")
        print("-" * 80)
        print(query)
        print("-" * 80)
        
        if i >= 3:  # Only show first 3 queries
            print(f"\n... and {len(queries) - 3} more queries")
            break
