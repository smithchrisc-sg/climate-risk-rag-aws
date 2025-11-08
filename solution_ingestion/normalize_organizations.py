#!/usr/bin/env python3
"""
Organization Normalization Utility using Fuzzy Matching
Normalizes and deduplicates organizations for entity RDF generation.
"""

import logging
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Set
import re
from difflib import SequenceMatcher

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrganizationNormalizer:
    """Normalizes organizations using fuzzy matching and rule-based approaches."""
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.normalization_rules = self._create_normalization_rules()
        self.acronym_expansions = self._create_acronym_expansions()
        
    def _create_normalization_rules(self) -> Dict[str, str]:
        """Create rules for common organization name variations."""
        return {
            # Common abbreviations and variations
            r'\bGov\b': 'Government',
            r'\bDept\b': 'Department',
            r'\bMin\b': 'Ministry',
            r'\bUniv\b': 'University',
            r'\bIntl\b': 'International',
            r'\bNatl\b': 'National',
            r'\bAssoc\b': 'Association',
            r'\bOrg\b': 'Organization',
            r'\bCorp\b': 'Corporation',
            r'\bLtd\b': 'Limited',
            r'\bInc\b': 'Incorporated',
            r'\bCo\b': 'Company',
            
            # Remove common suffixes that don't add meaning
            r'\s*\([^)]*\)\s*$': '',  # Remove trailing parentheses
            r'\s*,\s*$': '',  # Remove trailing commas
            r'\s+': ' ',  # Normalize whitespace
        }
    
    def _create_acronym_expansions(self) -> Dict[str, str]:
        """Create mappings for common acronyms."""
        return {
            'WHO': 'World Health Organization',
            'ADB': 'Asian Development Bank',
            'UNDP': 'United Nations Development Programme',
            'GFDRR': 'Global Facility for Disaster Reduction and Recovery',
            'JICA': 'Japan International Cooperation Agency',
            'MOH': 'Ministry of Health',
            'MOHW': 'Ministry of Health and Welfare',
            'USAID': 'United States Agency for International Development',
            'EU': 'European Union',
            'UN': 'United Nations',
            'IMF': 'International Monetary Fund',
            'WTO': 'World Trade Organization',
            'OECD': 'Organisation for Economic Co-operation and Development',
        }
    
    def normalize_organization_name(self, org_name: str) -> str:
        """Apply normalization rules to an organization name."""
        if not org_name:
            return org_name
            
        normalized = org_name.strip()
        
        # Apply normalization rules
        for pattern, replacement in self.normalization_rules.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two organization names."""
        # Extract base names if they have country context
        base1, _ = self.extract_base_name_and_country(name1)
        base2, _ = self.extract_base_name_and_country(name2)
        
        # Normalize both names first
        norm1 = self.normalize_organization_name(base1.lower())
        norm2 = self.normalize_organization_name(base2.lower())
        
        # Use SequenceMatcher for similarity
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def extract_base_name_and_country(self, org_name: str) -> Tuple[str, str]:
        """Extract base organization name and country from formatted name."""
        # Check if name has country context in parentheses at the end
        match = re.match(r'^(.+?)\s*\(([^)]+)\)$', org_name)
        if match:
            base_name = match.group(1).strip()
            country = match.group(2).strip()
            return base_name, country
        return org_name, ""
    
    def find_similar_organizations(self, org_list: List[str], consider_country: bool = True) -> Dict[str, List[str]]:
        """Find groups of similar organizations using fuzzy matching."""
        groups = {}
        processed = set()
        
        for i, org1 in enumerate(org_list):
            if org1 in processed:
                continue
                
            base1, country1 = self.extract_base_name_and_country(org1)
            
            # Find all similar organizations
            similar_group = [org1]
            processed.add(org1)
            
            for j, org2 in enumerate(org_list[i+1:], i+1):
                if org2 in processed:
                    continue
                    
                base2, country2 = self.extract_base_name_and_country(org2)
                
                # For organizations with country context, only compare within same country
                if consider_country and country1 and country2 and country1 != country2:
                    continue
                
                similarity = self.calculate_similarity(base1, base2)
                if similarity >= self.similarity_threshold:
                    similar_group.append(org2)
                    processed.add(org2)
            
            # Only keep groups with more than one member
            if len(similar_group) > 1:
                # Use the shortest base name as the canonical form
                canonical = min(similar_group, key=lambda x: len(self.extract_base_name_and_country(x)[0]))
                groups[canonical] = similar_group
        
        return groups
    
    def suggest_canonical_names(self, similar_groups: Dict[str, List[str]]) -> Dict[str, str]:
        """Suggest canonical names for groups of similar organizations."""
        suggestions = {}
        
        for canonical, group in similar_groups.items():
            # Try to find the most complete/official name
            best_name = canonical
            
            # Prefer names without abbreviations
            for name in group:
                # Check if this name has fewer abbreviations
                abbrev_count = len(re.findall(r'\b[A-Z]{2,}\b', name))
                best_abbrev_count = len(re.findall(r'\b[A-Z]{2,}\b', best_name))
                
                if abbrev_count < best_abbrev_count:
                    best_name = name
                elif abbrev_count == best_abbrev_count and len(name) > len(best_name):
                    # If same abbreviation count, prefer longer name
                    best_name = name
            
            suggestions[canonical] = best_name
        
        return suggestions
    
    def analyze_organization_type(self, org_name: str) -> str:
        """Analyze organization name to suggest type classification."""
        name_lower = org_name.lower()
        
        # Government/Public indicators
        gov_indicators = ['government', 'ministry', 'department', 'agency', 'bureau', 
                         'commission', 'authority', 'council', 'administration']
        
        # International indicators
        intl_indicators = ['united nations', 'world bank', 'international', 'global',
                          'regional', 'asian development', 'european', 'african development']
        
        # Private indicators
        private_indicators = ['corporation', 'company', 'ltd', 'inc', 'llc', 'university',
                            'institute', 'foundation', 'consulting', 'group']
        
        if any(indicator in name_lower for indicator in intl_indicators):
            return 'international'
        elif any(indicator in name_lower for indicator in gov_indicators):
            return 'public'
        elif any(indicator in name_lower for indicator in private_indicators):
            return 'private'
        else:
            return 'unknown'

def main():
    """Main function to run organization normalization."""
    print("Organization Normalization using Fuzzy Matching")
    print("=" * 50)
    
    # First, we need to load the organizations from our analyzer
    from analyze_organizations import OrganizationAnalyzer
    
    analyzer = OrganizationAnalyzer()
    analyzer.analyze_all_csv_files()
    
    normalizer = OrganizationNormalizer()
    
    # Process each organization type
    org_types = {
        'public': list(analyzer.public_orgs),
        'international': list(analyzer.international_orgs),
        'private': list(analyzer.private_orgs)
    }
    
    print(f"\nFinding similar organizations (threshold: {normalizer.similarity_threshold})...")
    
    all_suggestions = {}
    
    for org_type, org_list in org_types.items():
        print(f"\nProcessing {org_type} organizations ({len(org_list)} total)...")
        
        # Find similar groups - consider country context for public/private orgs
        consider_country = org_type in ['public', 'private']
        similar_groups = normalizer.find_similar_organizations(org_list, consider_country)
        
        if similar_groups:
            print(f"Found {len(similar_groups)} groups of similar organizations:")
            
            # Get canonical name suggestions
            suggestions = normalizer.suggest_canonical_names(similar_groups)
            all_suggestions[org_type] = (suggestions, similar_groups)
            
            # Show top 10 groups
            for i, (canonical, group) in enumerate(list(similar_groups.items())[:10]):
                suggested_name = suggestions[canonical]
                print(f"  Group {i+1}: {suggested_name}")
                for name in group:
                    if name != suggested_name:
                        print(f"    -> {name}")
                print()
        else:
            print("  No similar groups found with current threshold")
    
    # Save normalization suggestions
    output_file = "organization_normalization_suggestions.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("Organization Normalization Suggestions\n")
        f.write("=" * 50 + "\n\n")
        
        for org_type, data in all_suggestions.items():
            if isinstance(data, tuple):
                suggestions, similar_groups = data
            else:
                # Fallback for old format
                suggestions = data
                similar_groups = {}
            
            f.write(f"{org_type.upper()} ORGANIZATIONS:\n")
            f.write("-" * 30 + "\n")
            
            for canonical, suggested in suggestions.items():
                group = similar_groups.get(canonical, [canonical])
                
                f.write(f"Canonical: {suggested}\n")
                f.write("Variants:\n")
                for variant in group:
                    if variant != suggested:
                        f.write(f"  - {variant}\n")
                f.write("\n")
            f.write("\n")
    
    print(f"\nNormalization suggestions saved to: {output_file}")
    print("Review the suggestions and adjust the similarity threshold if needed.")

if __name__ == "__main__":
    main()
