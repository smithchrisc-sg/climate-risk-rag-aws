#!/usr/bin/env python3
"""
CSV Parser for Solution Ingestion
Loads and parses standardized CSV files into solution objects.
"""

import pandas as pd
from pathlib import Path
from typing import List, Iterator
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.solution import Solution

logger = logging.getLogger(__name__)

class CSVParser:
    """Parses standardized CSV files containing solution data."""
    
    def __init__(self, input_dir: str = None):
        self.input_dir = Path(input_dir) if input_dir else Path(__file__).parent.parent / 'input_data'
    
    def load_csv_files(self) -> List[Path]:
        """Load all CSV files from input directory."""
        csv_files = list(self.input_dir.glob('*.csv'))
        # Exclude backup files
        csv_files = [f for f in csv_files if not f.name.endswith('.backup')]
        logger.info(f"Found {len(csv_files)} CSV files: {[f.name for f in csv_files]}")
        return csv_files
    
    def parse_csv_file(self, csv_path: Path) -> Iterator[Solution]:
        """Parse single CSV file and yield Solution objects."""
        logger.info(f"Parsing {csv_path.name}")
        
        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
            logger.info(f"Loaded {len(df)} solutions from {csv_path.name}")
            
            for idx, row in df.iterrows():
                solution_dict = self._row_to_dict(row, csv_path.stem, idx + 1)
                if solution_dict:
                    try:
                        solution = Solution.from_dict(solution_dict)
                        yield solution
                    except Exception as e:
                        logger.warning(f"Skipping invalid solution at row {idx + 1}: {e}")
                        continue
                    
        except Exception as e:
            logger.error(f"Error parsing {csv_path.name}: {e}")
            raise
    
    def _row_to_dict(self, row: pd.Series, file_source: str, row_num: int) -> dict:
        """Convert CSV row to solution dictionary."""
        # Skip empty rows
        if pd.isna(row.get('Name')) or str(row.get('Name')).strip() == '':
            return None
        
        return {
            'id': f"{file_source}_{row_num}",
            'source_file': file_source,
            'row_number': row_num,
            'number': self._clean_value(row.get('No.')),
            'name': self._clean_value(row.get('Name')),
            'country': self._clean_value(row.get('Country')),
            'public_organisations': self._clean_value(row.get('Public Organisations')),
            'international_organisations': self._clean_value(row.get('International Organisations')),
            'private_organisations': self._clean_value(row.get('Private Organisations')),
            'type_of_risk': self._clean_value(row.get('Type of Risk')),
            'type_of_solution': self._clean_value(row.get('Type of Solution ')),  # Note trailing space
            'ppp': self._clean_value(row.get('PPP?')),
            'theme': self._clean_value(row.get('Theme')),
            'year_of_implementation': self._clean_value(row.get('Year of Implementation')),
            'description': self._clean_value(row.get('Description')),
            'key_highlights': self._clean_value(row.get('Key Highlights')),
            'results': self._clean_value(row.get('Results')),
            'organization_sources': self._clean_value(row.get('Organization Sources')),
            'other_sources': self._clean_value(row.get('Other Sources')),
            'contact_information': self._clean_value(row.get('Contact Information')),
            'date_added': self._clean_value(row.get('Date Added')),
            'last_updated': self._clean_value(row.get('Last Updated')),
            'most_recent_changes': self._clean_value(row.get('Most Recent Changes'))
        }
    
    def _clean_value(self, value) -> str:
        """Clean and normalize field values."""
        if pd.isna(value):
            return ''
        
        # Convert to string and clean
        cleaned = str(value).strip()
        
        # Remove common artifacts
        if cleaned.lower() in ['nan', 'none', 'null', '']:
            return ''
        
        return cleaned
    
    def parse_all_files(self) -> Iterator[Solution]:
        """Parse all CSV files and yield all Solution objects."""
        csv_files = self.load_csv_files()
        total_solutions = 0
        
        for csv_file in csv_files:
            file_count = 0
            for solution in self.parse_csv_file(csv_file):
                yield solution
                file_count += 1
                total_solutions += 1
            
            logger.info(f"Parsed {file_count} solutions from {csv_file.name}")
        
        logger.info(f"Total solutions parsed: {total_solutions}")

def main():
    """Test CSV parsing functionality."""
    parser = CSVParser()
    
    print("CSV Parser Test")
    print("=" * 50)
    
    # Parse first few solutions from each file
    solutions = list(parser.parse_all_files())
    
    print(f"\nTotal solutions loaded: {len(solutions)}")
    print("\nFirst 5 solutions:")
    
    for i, solution in enumerate(solutions[:5]):
        print(f"\n{i+1}. {solution}")
        print(f"   Doc ID: {solution.doc_id}")
        print(f"   Country: {solution.country}")
        print(f"   Risk Type: {solution.type_of_risk}")
        print(f"   Full text length: {len(solution.get_full_text())} chars")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
