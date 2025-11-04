#!/usr/bin/env python3
"""
CSV Preprocessor for Solution Ingestion
Standardizes CSV files to match the reference format with consistent columns and ordering.
"""

import pandas as pd
import os
from pathlib import Path

# Standard column order based on natural_catastrophe_26-Sep-2025.csv
STANDARD_COLUMNS = [
    'No.', 'Name', 'Country', 'Public Organisations', 'International Organisations', 
    'Private Organisations', 'Type of Risk', 'Type of Solution ', 'PPP?', 'Theme', 
    'Year of Implementation', 'Description', 'Key Highlights', 'Results', 
    'Organization Sources', 'Other Sources', 'Contact Information', 
    'Date Added', 'Last Updated', 'Most Recent Changes'
]

DEFAULT_DATE_ADDED = "28 July 2024"
DEFAULT_MOST_RECENT_CHANGES = ""

def preprocess_csv(input_path, output_path):
    """Standardize CSV file to match reference format."""
    df = pd.read_csv(input_path, encoding='utf-8-sig')
    
    # Add missing columns with defaults
    if 'Date Added' not in df.columns:
        df['Date Added'] = DEFAULT_DATE_ADDED
    if 'Most Recent Changes' not in df.columns:
        df['Most Recent Changes'] = DEFAULT_MOST_RECENT_CHANGES
    
    # Reorder columns to match standard
    df = df.reindex(columns=STANDARD_COLUMNS, fill_value='')
    
    # Save standardized file
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    return len(df)

def validate_csv(file_path):
    """Validate CSV structure and data integrity."""
    df = pd.read_csv(file_path, encoding='utf-8-sig')
    
    issues = []
    
    # Check column count and names
    if len(df.columns) != len(STANDARD_COLUMNS):
        issues.append(f"Column count mismatch: {len(df.columns)} vs {len(STANDARD_COLUMNS)}")
    
    missing_cols = set(STANDARD_COLUMNS) - set(df.columns)
    if missing_cols:
        issues.append(f"Missing columns: {missing_cols}")
    
    # Check for empty required fields
    required_fields = ['No.', 'Name', 'Description']
    for field in required_fields:
        if field in df.columns:
            empty_count = df[field].isna().sum() + (df[field] == '').sum()
            if empty_count > 0:
                issues.append(f"{field}: {empty_count} empty values")
    
    return issues, len(df)

def main():
    """Process all CSV files in input_data directory."""
    input_dir = Path(__file__).parent.parent / 'input_data'
    
    print("CSV Preprocessing Report")
    print("=" * 50)
    
    total_solutions = 0
    
    for csv_file in input_dir.glob('*.csv'):
        print(f"\nProcessing: {csv_file.name}")
        
        # Create backup
        backup_path = csv_file.with_suffix('.csv.backup')
        if not backup_path.exists():
            csv_file.rename(backup_path)
            print(f"  Backup created: {backup_path.name}")
        
        # Preprocess
        try:
            row_count = preprocess_csv(backup_path, csv_file)
            print(f"  Standardized: {row_count} solutions")
            
            # Validate
            issues, validated_count = validate_csv(csv_file)
            if issues:
                print(f"  Issues found: {'; '.join(issues)}")
            else:
                print(f"  Validation: PASSED ({validated_count} solutions)")
            
            total_solutions += validated_count
            
        except Exception as e:
            print(f"  ERROR: {e}")
    
    print(f"\nTotal solutions across all files: {total_solutions}")
    print("Preprocessing complete!")

if __name__ == "__main__":
    main()
