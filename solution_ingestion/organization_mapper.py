#!/usr/bin/env python3
"""
Organization Mapping Utility
Provides fast lookup and mapping functions for organization RDF generation.
"""

import re
import json
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote
from analyze_organizations import OrganizationAnalyzer
from classify_organizations import OrganizationClassifier
from normalize_organizations import OrganizationNormalizer

class OrganizationMapper:
    """Fast lookup utility for organization mapping during RDF generation."""
    
    def __init__(self):
        self.classifier = OrganizationClassifier()
        self.normalizer = OrganizationNormalizer()
        self.namespace = "http://solve.global/knowledge-commons/"
        
        # Lookup tables (populated by build_lookup_tables)
        self.name_to_uri = {}
        self.name_to_classification = {}
        self.name_to_canonical = {}
        self.fuzzy_matches = {}
        
    def create_organization_uri(self, org_name: str) -> str:
        """Create a consistent URI for an organization."""
        # Extract base name and country
        base_name, country = self.normalizer.extract_base_name_and_country(org_name)
        
        # Normalize for URI
        normalized = re.sub(r'[^\w\s-]', '', base_name.lower())
        normalized = re.sub(r'\s+', '_', normalized.strip())
        normalized = re.sub(r'_+', '_', normalized).strip('_')
        
        # Add country suffix if present
        if country:
            country_normalized = re.sub(r'[^\w\s-]', '', country.lower())
            country_normalized = re.sub(r'\s+', '_', country_normalized.strip())
            normalized = f"{normalized}_{country_normalized}"
        
        return f"sg:Org_{normalized}"
    
    def build_lookup_tables(self, analyzer: OrganizationAnalyzer):
        """Build fast lookup tables for organization mapping."""
        print("Building organization lookup tables...")
        
        # Build basic mappings
        all_orgs = [
            (org, 'public') for org in analyzer.public_orgs
        ] + [
            (org, 'international') for org in analyzer.international_orgs
        ] + [
            (org, 'private') for org in analyzer.private_orgs
        ]
        
        for org_name, org_type in all_orgs:
            uri = self.create_organization_uri(org_name)
            classification = self.classifier.classify_organization(org_name, org_type)
            
            self.name_to_uri[org_name] = uri
            self.name_to_classification[org_name] = classification
            self.name_to_canonical[org_name] = org_name  # Default to self
        
        # Build normalization mappings
        org_types = {
            'public': list(analyzer.public_orgs),
            'international': list(analyzer.international_orgs),
            'private': list(analyzer.private_orgs)
        }
        
        for org_type, org_list in org_types.items():
            consider_country = org_type in ['public', 'private']
            similar_groups = self.normalizer.find_similar_organizations(org_list, consider_country)
            
            if similar_groups:
                suggestions = self.normalizer.suggest_canonical_names(similar_groups)
                
                for canonical, group in similar_groups.items():
                    canonical_name = suggestions[canonical]
                    for variant in group:
                        self.name_to_canonical[variant] = canonical_name
                        # Also create fuzzy match entries
                        self.fuzzy_matches[variant] = {
                            'canonical': canonical_name,
                            'uri': self.name_to_uri[canonical_name],
                            'classification': self.name_to_classification[canonical_name],
                            'variants': group
                        }
        
        print(f"Built lookup tables for {len(self.name_to_uri)} organizations")
        print(f"Found {len(self.fuzzy_matches)} fuzzy match groups")
    
    def lookup_organization(self, org_name: str) -> Optional[Dict]:
        """Fast lookup of organization information."""
        if not org_name or not org_name.strip():
            return None
        
        org_name = org_name.strip()
        
        # Direct match
        if org_name in self.name_to_uri:
            return {
                'name': org_name,
                'canonical_name': self.name_to_canonical.get(org_name, org_name),
                'uri': self.name_to_uri[org_name],
                'classification': self.name_to_classification[org_name],
                'match_type': 'exact'
            }
        
        # Fuzzy match
        if org_name in self.fuzzy_matches:
            match_info = self.fuzzy_matches[org_name]
            return {
                'name': org_name,
                'canonical_name': match_info['canonical'],
                'uri': match_info['uri'],
                'classification': match_info['classification'],
                'match_type': 'fuzzy',
                'variants': match_info['variants']
            }
        
        return None
    
    def parse_organization_field(self, field_value: str) -> List[Dict]:
        """Parse comma-separated organization field and return lookup results."""
        if not field_value or field_value.strip().upper() in ['NIL', 'N/A', 'NULL', '']:
            return []
        
        results = []
        orgs = [org.strip() for org in field_value.split(',') if org.strip()]
        
        for org in orgs:
            lookup_result = self.lookup_organization(org)
            if lookup_result:
                results.append(lookup_result)
            else:
                # Create a basic entry for unknown organizations
                results.append({
                    'name': org,
                    'canonical_name': org,
                    'uri': self.create_organization_uri(org),
                    'classification': 'org:Organization',
                    'match_type': 'unknown'
                })
        
        return results
    
    def save_lookup_cache(self, filename: str = "organization_lookup_cache.json"):
        """Save lookup tables to JSON for fast loading."""
        cache_data = {
            'name_to_uri': self.name_to_uri,
            'name_to_classification': self.name_to_classification,
            'name_to_canonical': self.name_to_canonical,
            'fuzzy_matches': self.fuzzy_matches
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        
        print(f"Lookup cache saved to: {filename}")
    
    def load_lookup_cache(self, filename: str = "organization_lookup_cache.json"):
        """Load lookup tables from JSON cache."""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            self.name_to_uri = cache_data['name_to_uri']
            self.name_to_classification = cache_data['name_to_classification']
            self.name_to_canonical = cache_data['name_to_canonical']
            self.fuzzy_matches = cache_data['fuzzy_matches']
            
            print(f"Loaded lookup cache from: {filename}")
            print(f"Cached {len(self.name_to_uri)} organizations")
            return True
        except FileNotFoundError:
            print(f"Cache file {filename} not found, will build from scratch")
            return False
    
    def get_organization_rdf_reference(self, org_name: str) -> str:
        """Get RDF reference (URI) for an organization name."""
        lookup_result = self.lookup_organization(org_name)
        if lookup_result:
            return lookup_result['uri']
        else:
            # Create URI for unknown organization
            return self.create_organization_uri(org_name)

def main():
    """Build and test organization mapping."""
    print("Organization Mapping Utility")
    print("=" * 30)
    
    # Load organizations
    analyzer = OrganizationAnalyzer()
    analyzer.analyze_all_csv_files()
    
    # Build mapper
    mapper = OrganizationMapper()
    mapper.build_lookup_tables(analyzer)
    
    # Save cache
    mapper.save_lookup_cache()
    
    # Test some lookups
    test_cases = [
        "Ministry of Health (Japan)",
        "World Bank",
        "Ministry of Health",  # Should not match without country
        "Asian Development Bank (ADB)",
        "Unknown Organization"
    ]
    
    print(f"\nTesting organization lookups:")
    for test_org in test_cases:
        result = mapper.lookup_organization(test_org)
        if result:
            print(f"  {test_org} -> {result['uri']} ({result['match_type']})")
        else:
            print(f"  {test_org} -> No match")
    
    # Test field parsing
    print(f"\nTesting field parsing:")
    test_field = "Ministry of Health (Japan), World Bank, Some Unknown Org"
    results = mapper.parse_organization_field(test_field)
    for result in results:
        print(f"  {result['name']} -> {result['uri']} ({result['match_type']})")
    
    print(f"\nOrganization mapper ready for RDF generation integration!")

if __name__ == "__main__":
    main()
