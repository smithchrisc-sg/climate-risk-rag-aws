#!/usr/bin/env python3
"""
Organization Analysis Utility for Ontology Normalization
Extracts and analyzes organizations from CSV files for entity RDF generation.
"""

import csv
import logging
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrganizationAnalyzer:
    """Analyzes organizations from CSV files for normalization and deduplication."""
    
    def __init__(self, input_dir: str = "input_data"):
        self.input_dir = Path(input_dir)
        self.public_orgs = set()
        self.international_orgs = set()
        self.private_orgs = set()
        
        # Track source information for each organization
        self.org_sources = defaultdict(list)  # org_name -> [(file, row, type)]
        
    def clean_organization_name(self, org_name: str) -> str:
        """Clean and normalize organization name."""
        if not org_name or org_name.upper() in ['NIL', 'N/A', 'NULL', '']:
            return None
            
        # Basic cleaning
        cleaned = org_name.strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize whitespace
        cleaned = cleaned.strip('.,;')  # Remove trailing punctuation
        
        return cleaned if cleaned else None
    
    def extract_organizations_from_cell(self, cell_value: str) -> List[str]:
        """Extract individual organization names from comma-separated cell."""
        if not cell_value:
            return []
            
        # Split by comma and clean each organization
        orgs = []
        for org in cell_value.split(','):
            cleaned = self.clean_organization_name(org)
            if cleaned:
                orgs.append(cleaned)
        
        return orgs
    
    def process_csv_file(self, csv_file: Path):
        """Process a single CSV file and extract organizations."""
        logger.info(f"Processing CSV file: {csv_file}")
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row_num, row in enumerate(reader, 1):
                    # Get country for context
                    country = row.get('Country', '').strip()
                    
                    # Extract organization columns
                    public_orgs = self.extract_organizations_from_cell(
                        row.get('Public Organisations', '')
                    )
                    international_orgs = self.extract_organizations_from_cell(
                        row.get('International Organisations', '')
                    )
                    private_orgs = self.extract_organizations_from_cell(
                        row.get('Private Organisations', '')
                    )
                    
                    # Add to sets and track sources with country context
                    for org in public_orgs:
                        # For public orgs, include country in the key
                        org_key = f"{org} ({country})" if country else org
                        self.public_orgs.add(org_key)
                        self.org_sources[org_key].append((csv_file.name, row_num, 'public', country))
                    
                    for org in international_orgs:
                        # International orgs don't need country context
                        self.international_orgs.add(org)
                        self.org_sources[org].append((csv_file.name, row_num, 'international', country))
                    
                    for org in private_orgs:
                        # Private orgs might need country context for disambiguation
                        org_key = f"{org} ({country})" if country and self._needs_country_context(org) else org
                        self.private_orgs.add(org_key)
                        self.org_sources[org_key].append((csv_file.name, row_num, 'private', country))
                        
        except Exception as e:
            logger.error(f"Error processing {csv_file}: {e}")
    
    def _needs_country_context(self, org_name: str) -> bool:
        """Determine if a private organization needs country context for disambiguation."""
        # Generic names that likely need country context
        generic_indicators = [
            'university', 'institute', 'foundation', 'association', 
            'company', 'corporation', 'group', 'consulting', 'research'
        ]
        
        org_lower = org_name.lower()
        return any(indicator in org_lower for indicator in generic_indicators)
    
    def analyze_all_csv_files(self):
        """Process all CSV files in the input directory."""
        csv_files = list(self.input_dir.glob("*.csv"))
        
        if not csv_files:
            logger.warning(f"No CSV files found in {self.input_dir}")
            return
        
        logger.info(f"Found {len(csv_files)} CSV files to process")
        
        for csv_file in csv_files:
            self.process_csv_file(csv_file)
    
    def get_organization_stats(self) -> Dict:
        """Get statistics about extracted organizations."""
        all_orgs = self.public_orgs | self.international_orgs | self.private_orgs
        
        # Count organizations by type
        type_counts = {
            'public': len(self.public_orgs),
            'international': len(self.international_orgs),
            'private': len(self.private_orgs),
            'total_unique': len(all_orgs)
        }
        
        # Find organizations that appear in multiple categories
        overlaps = {}
        overlaps['public_international'] = self.public_orgs & self.international_orgs
        overlaps['public_private'] = self.public_orgs & self.private_orgs
        overlaps['international_private'] = self.international_orgs & self.private_orgs
        overlaps['all_three'] = self.public_orgs & self.international_orgs & self.private_orgs
        
        return {
            'counts': type_counts,
            'overlaps': overlaps,
            'total_mentions': sum(len(sources) for sources in self.org_sources.values())
        }
    
    def get_most_frequent_organizations(self, limit: int = 20) -> Dict:
        """Get most frequently mentioned organizations by type."""
        # Count mentions by organization type
        public_counts = Counter()
        international_counts = Counter()
        private_counts = Counter()
        
        for org, sources in self.org_sources.items():
            for source_file, row_num, org_type, country in sources:
                if org_type == 'public':
                    public_counts[org] += 1
                elif org_type == 'international':
                    international_counts[org] += 1
                elif org_type == 'private':
                    private_counts[org] += 1
        
        return {
            'public': public_counts.most_common(limit),
            'international': international_counts.most_common(limit),
            'private': private_counts.most_common(limit)
        }
    
    def save_organization_lists(self, output_file: str = "organization_analysis.txt"):
        """Save organization lists to a file for review."""
        output_path = Path(output_file)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("Organization Analysis Report\n")
            f.write("=" * 50 + "\n\n")
            
            # Statistics
            stats = self.get_organization_stats()
            f.write("STATISTICS:\n")
            f.write(f"Public Organizations: {stats['counts']['public']}\n")
            f.write(f"International Organizations: {stats['counts']['international']}\n")
            f.write(f"Private Organizations: {stats['counts']['private']}\n")
            f.write(f"Total Unique Organizations: {stats['counts']['total_unique']}\n")
            f.write(f"Total Mentions: {stats['total_mentions']}\n\n")
            
            # Overlaps
            f.write("CATEGORY OVERLAPS:\n")
            for overlap_type, orgs in stats['overlaps'].items():
                if orgs:
                    f.write(f"{overlap_type}: {len(orgs)} organizations\n")
                    for org in sorted(orgs):
                        f.write(f"  - {org}\n")
                    f.write("\n")
            
            # Most frequent organizations
            frequent = self.get_most_frequent_organizations()
            
            f.write("MOST FREQUENT ORGANIZATIONS:\n\n")
            
            f.write("Public Organizations:\n")
            for org, count in frequent['public']:
                f.write(f"  {count:3d}x {org}\n")
            f.write("\n")
            
            f.write("International Organizations:\n")
            for org, count in frequent['international']:
                f.write(f"  {count:3d}x {org}\n")
            f.write("\n")
            
            f.write("Private Organizations:\n")
            for org, count in frequent['private']:
                f.write(f"  {count:3d}x {org}\n")
            f.write("\n")
            
            # Full lists
            f.write("COMPLETE ORGANIZATION LISTS:\n\n")
            
            f.write("All Public Organizations:\n")
            for org in sorted(self.public_orgs):
                f.write(f"  - {org}\n")
            f.write("\n")
            
            f.write("All International Organizations:\n")
            for org in sorted(self.international_orgs):
                f.write(f"  - {org}\n")
            f.write("\n")
            
            f.write("All Private Organizations:\n")
            for org in sorted(self.private_orgs):
                f.write(f"  - {org}\n")
        
        logger.info(f"Organization analysis saved to: {output_path}")

def main():
    """Main function to run organization analysis."""
    print("Organization Analysis for Ontology Normalization")
    print("=" * 50)
    
    analyzer = OrganizationAnalyzer()
    
    # Process all CSV files
    analyzer.analyze_all_csv_files()
    
    # Get and display statistics
    stats = analyzer.get_organization_stats()
    
    print(f"\nOrganization Extraction Results:")
    print(f"  Public Organizations: {stats['counts']['public']}")
    print(f"  International Organizations: {stats['counts']['international']}")
    print(f"  Private Organizations: {stats['counts']['private']}")
    print(f"  Total Unique Organizations: {stats['counts']['total_unique']}")
    print(f"  Total Mentions: {stats['total_mentions']}")
    
    # Show overlaps
    print(f"\nCategory Overlaps:")
    for overlap_type, orgs in stats['overlaps'].items():
        if orgs:
            print(f"  {overlap_type}: {len(orgs)} organizations")
    
    # Show most frequent
    print(f"\nMost Frequent Organizations (Top 10):")
    frequent = analyzer.get_most_frequent_organizations(10)
    
    print("  Public:")
    for org, count in frequent['public'][:5]:
        print(f"    {count}x {org}")
    
    print("  International:")
    for org, count in frequent['international'][:5]:
        print(f"    {count}x {org}")
    
    print("  Private:")
    for org, count in frequent['private'][:5]:
        print(f"    {count}x {org}")
    
    # Save detailed analysis
    analyzer.save_organization_lists()
    
    print(f"\nDetailed analysis saved to: organization_analysis.txt")
    print("Ready for fuzzy matching and normalization!")

if __name__ == "__main__":
    main()
