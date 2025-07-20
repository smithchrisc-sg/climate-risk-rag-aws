#!/usr/bin/env python3
"""
Script to update DocumentIDManager to use new DatabaseManager context manager pattern
"""

import re

def update_database_patterns(file_path):
    """Update old database connection patterns to new context manager pattern"""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern to match the old connection pattern
    old_pattern = r'(\s+)try:\s*\n(\s+)conn = self\.db_manager\.get_connection\(\)\s*\n(\s+)try:\s*\n(.*?)\n(\s+)finally:\s*\n(\s+)self\.db_manager\.return_connection\(conn\)'
    
    def replace_pattern(match):
        indent = match.group(1)
        inner_indent = match.group(2)
        try_indent = match.group(3)
        inner_code = match.group(4)
        
        # Extract the inner code and adjust indentation
        lines = inner_code.split('\n')
        adjusted_lines = []
        for line in lines:
            if line.strip():
                # Remove one level of indentation
                if line.startswith(try_indent + '    '):
                    adjusted_lines.append(inner_indent + '    ' + line[len(try_indent + '    '):])
                elif line.startswith(try_indent):
                    adjusted_lines.append(inner_indent + line[len(try_indent):])
                else:
                    adjusted_lines.append(line)
            else:
                adjusted_lines.append(line)
        
        new_inner_code = '\n'.join(adjusted_lines)
        
        return f'{indent}try:\n{inner_indent}    with self.db_manager.get_connection() as conn:\n{new_inner_code}'
    
    # Apply the replacement
    updated_content = re.sub(old_pattern, replace_pattern, content, flags=re.DOTALL)
    
    # Write back the updated content
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    print(f"Updated database patterns in {file_path}")

if __name__ == "__main__":
    file_path = "/Users/chris/climate-risk-rag-aws/layers/database-core-layer/python/utils/DocumentIDManager.py"
    update_database_patterns(file_path)
