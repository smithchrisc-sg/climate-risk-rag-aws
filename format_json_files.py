#!/usr/bin/env python3
"""
Format all JSON files in the data directory with proper indentation (indent=4)
to make them readable in text editors.
"""

import json
import os
import glob

def format_json_file(file_path):
    """Format a single JSON file with indent=4"""
    try:
        # Read the original JSON
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Write it back with proper formatting
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
        
        return True
    except Exception as e:
        print("Error formatting {}: {}".format(file_path, e))
        return False

def find_json_files(directory):
    """Find all JSON files in directory and subdirectories"""
    json_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    return json_files

def main():
    # Find all JSON files in the data directory
    json_files = find_json_files("data")
    
    print("Found {} JSON files to format...".format(len(json_files)))
    
    formatted_count = 0
    error_count = 0
    
    for json_file in json_files:
        print("Formatting: {}".format(json_file))
        if format_json_file(json_file):
            formatted_count += 1
        else:
            error_count += 1
    
    print("\nFormatting complete!")
    print("Successfully formatted: {} files".format(formatted_count))
    print("Errors: {} files".format(error_count))

if __name__ == "__main__":
    main()
