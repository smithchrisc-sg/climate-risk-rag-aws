#!/usr/bin/env python3
"""
Vocabulary Analysis Utility
Analyzes Type of Risk, Type of Solution, and Theme columns for controlled vocabularies.
"""

import csv
import logging
from pathlib import Path
from collections import Counter
from typing import Dict, List, Set

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VocabularyAnalyzer:
    """Analyzes controlled vocabularies from CSV columns."""
    
    def __init__(self, input_dir: str = "input_data"):
        self.input_dir = Path(input_dir)
        self.risk_types = Counter()
        self.solution_types = Counter()
        self.themes = Counter()
        
    def clean_value(self, value: str) -> str:
        """Clean and normalize vocabulary value."""
        if not value or value.upper() in ['NIL', 'N/A', 'NULL', '']:
            return None
        return value.strip()
    
    def process_csv_file(self, csv_file: Path):
        """Process a single CSV file and extract vocabularies."""
        logger.info(f"Processing CSV file: {csv_file}")
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row_num, row in enumerate(reader, 1):
                    # Extract vocabulary columns - check both with and without trailing space
                    risk_type = self.clean_value(row.get('Type of Risk', ''))
                    solution_type = self.clean_value(row.get('Type of Solution', '') or row.get('Type of Solution ', ''))
                    theme = self.clean_value(row.get('Theme', ''))
                    
                    # Count occurrences
                    if risk_type:
                        self.risk_types[risk_type] += 1
                    if solution_type:
                        self.solution_types[solution_type] += 1
                    if theme:
                        self.themes[theme] += 1
                        
        except Exception as e:
            logger.error(f"Error processing {csv_file}: {e}")
    
    def analyze_all_csv_files(self):
        """Process all CSV files in the input directory."""
        csv_files = list(self.input_dir.glob("*.csv"))
        
        if not csv_files:
            logger.warning(f"No CSV files found in {self.input_dir}")
            return
        
        logger.info(f"Found {len(csv_files)} CSV files to process")
        
        for csv_file in csv_files:
            self.process_csv_file(csv_file)
    
    def get_vocabulary_stats(self) -> Dict:
        """Get statistics about vocabularies."""
        return {
            'risk_types': {
                'count': len(self.risk_types),
                'total_mentions': sum(self.risk_types.values()),
                'most_common': self.risk_types.most_common()
            },
            'solution_types': {
                'count': len(self.solution_types),
                'total_mentions': sum(self.solution_types.values()),
                'most_common': self.solution_types.most_common()
            },
            'themes': {
                'count': len(self.themes),
                'total_mentions': sum(self.themes.values()),
                'most_common': self.themes.most_common()
            }
        }
    
    def save_vocabulary_analysis(self, output_file: str = "vocabulary_analysis.txt"):
        """Save vocabulary analysis to a file."""
        stats = self.get_vocabulary_stats()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("Vocabulary Analysis Report\n")
            f.write("=" * 50 + "\n\n")
            
            # Risk Types
            f.write("TYPE OF RISK:\n")
            f.write("-" * 20 + "\n")
            f.write(f"Unique values: {stats['risk_types']['count']}\n")
            f.write(f"Total mentions: {stats['risk_types']['total_mentions']}\n\n")
            
            f.write("All Risk Types (by frequency):\n")
            for risk_type, count in stats['risk_types']['most_common']:
                f.write(f"  {count:3d}x {risk_type}\n")
            f.write("\n")
            
            # Solution Types
            f.write("TYPE OF SOLUTION:\n")
            f.write("-" * 20 + "\n")
            f.write(f"Unique values: {stats['solution_types']['count']}\n")
            f.write(f"Total mentions: {stats['solution_types']['total_mentions']}\n\n")
            
            f.write("All Solution Types (by frequency):\n")
            for solution_type, count in stats['solution_types']['most_common']:
                f.write(f"  {count:3d}x {solution_type}\n")
            f.write("\n")
            
            # Themes
            f.write("THEMES:\n")
            f.write("-" * 20 + "\n")
            f.write(f"Unique values: {stats['themes']['count']}\n")
            f.write(f"Total mentions: {stats['themes']['total_mentions']}\n\n")
            
            f.write("All Themes (by frequency):\n")
            for theme, count in stats['themes']['most_common']:
                f.write(f"  {count:3d}x {theme}\n")
        
        logger.info(f"Vocabulary analysis saved to: {output_file}")

def main():
    """Main function to run vocabulary analysis."""
    print("Vocabulary Analysis for Type of Risk, Solution, and Theme")
    print("=" * 60)
    
    analyzer = VocabularyAnalyzer()
    
    # Process all CSV files
    analyzer.analyze_all_csv_files()
    
    # Get and display statistics
    stats = analyzer.get_vocabulary_stats()
    
    print(f"\nVocabulary Analysis Results:")
    print(f"  Type of Risk - Unique values: {stats['risk_types']['count']}, Total mentions: {stats['risk_types']['total_mentions']}")
    print(f"  Type of Solution - Unique values: {stats['solution_types']['count']}, Total mentions: {stats['solution_types']['total_mentions']}")
    print(f"  Themes - Unique values: {stats['themes']['count']}, Total mentions: {stats['themes']['total_mentions']}")
    
    print(f"\nMost Common Risk Types:")
    for risk_type, count in stats['risk_types']['most_common'][:10]:
        print(f"  {count:3d}x {risk_type}")
    
    print(f"\nMost Common Solution Types:")
    for solution_type, count in stats['solution_types']['most_common'][:10]:
        print(f"  {count:3d}x {solution_type}")
    
    print(f"\nMost Common Themes:")
    for theme, count in stats['themes']['most_common'][:10]:
        print(f"  {count:3d}x {theme}")
    
    # Save detailed analysis
    analyzer.save_vocabulary_analysis()
    
    print(f"\nDetailed analysis saved to: vocabulary_analysis.txt")

if __name__ == "__main__":
    main()
