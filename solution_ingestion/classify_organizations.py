#!/usr/bin/env python3
"""
Organization Classification Utility for Subclass Hierarchy
Analyzes organization names to suggest functional classifications for RDF subclassing.
"""

import re
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple
from analyze_organizations import OrganizationAnalyzer

class OrganizationClassifier:
    """Classifies organizations into functional hierarchies for subclassing."""
    
    def __init__(self):
        self.classification_patterns = self._create_classification_patterns()
        self.hierarchy = self._create_hierarchy_structure()
        
    def _create_classification_patterns(self) -> Dict[str, List[str]]:
        """Create patterns for identifying organization types."""
        return {
            # Health sector
            'HealthMinistry': [
                r'ministry.*health', r'health.*ministry', r'department.*health',
                r'health.*department', r'health.*welfare', r'moh\b', r'mohw\b'
            ],
            
            # Environment sector
            'EnvironmentMinistry': [
                r'ministry.*environment', r'environment.*ministry', 
                r'department.*environment', r'environment.*department',
                r'environmental.*protection', r'climate.*ministry'
            ],
            
            # Transportation sector
            'TransportationMinistry': [
                r'transport.*agency', r'transport.*ministry', r'ministry.*transport',
                r'department.*transport', r'roads.*department', r'aviation.*authority',
                r'maritime.*authority', r'transport.*authority'
            ],
            
            # Statistics/Data
            'StatisticalOffice': [
                r'bureau.*statistics', r'statistics.*bureau', r'statistics.*office',
                r'national.*statistics', r'statistical.*office', r'census.*bureau'
            ],
            
            # Emergency Management
            'EmergencyManagementAgency': [
                r'emergency.*management', r'disaster.*management', r'civil.*defense',
                r'emergency.*services', r'disaster.*prevention', r'crisis.*management'
            ],
            
            # Development Banks (International)
            'DevelopmentBank': [
                r'development.*bank', r'world.*bank', r'asian.*development',
                r'african.*development', r'inter.*american.*development'
            ],
            
            # UN Agencies (International)
            'UNAgency': [
                r'united.*nations', r'\bun\b', r'undp\b', r'unicef\b', r'who\b',
                r'unesco\b', r'unep\b', r'unhcr\b'
            ],
            
            # Insurance Companies (Private)
            'InsuranceCompany': [
                r'insurance', r'reinsurance', r're-insurance', r'insurer',
                r'mutual.*insurance', r'insurance.*company'
            ],
            
            # Universities (Private/Public)
            'University': [
                r'university', r'college', r'institute.*technology',
                r'school.*medicine', r'academic.*institution'
            ],
            
            # Consulting Firms (Private)
            'ConsultingFirm': [
                r'consulting', r'consultancy', r'advisory', r'solutions',
                r'consulting.*group', r'consulting.*firm'
            ]
        }
    
    def _create_hierarchy_structure(self) -> Dict[str, str]:
        """Define the subclass hierarchy."""
        return {
            # Public organization subtypes
            'HealthMinistry': 'Ministry',
            'EnvironmentMinistry': 'Ministry', 
            'TransportationMinistry': 'Ministry',
            'Ministry': 'PublicOrganization',
            'StatisticalOffice': 'PublicOrganization',
            'EmergencyManagementAgency': 'PublicOrganization',
            
            # International organization subtypes
            'DevelopmentBank': 'InternationalOrganization',
            'UNAgency': 'InternationalOrganization',
            
            # Private organization subtypes
            'InsuranceCompany': 'PrivateOrganization',
            'University': 'PrivateOrganization',
            'ConsultingFirm': 'PrivateOrganization',
            
            # Top level
            'PublicOrganization': 'org:Organization',
            'InternationalOrganization': 'org:Organization',
            'PrivateOrganization': 'org:Organization'
        }
    
    def classify_organization(self, org_name: str, org_type: str) -> str:
        """Classify an organization based on its name and type."""
        # Extract base name (remove country context)
        base_name = re.sub(r'\s*\([^)]+\)\s*$', '', org_name).lower()
        
        # Try to match against patterns
        for class_name, patterns in self.classification_patterns.items():
            for pattern in patterns:
                if re.search(pattern, base_name, re.IGNORECASE):
                    return class_name
        
        # Fallback to basic type
        if org_type == 'public':
            return 'PublicOrganization'
        elif org_type == 'international':
            return 'InternationalOrganization'
        elif org_type == 'private':
            return 'PrivateOrganization'
        
        return 'org:Organization'
    
    def analyze_classifications(self, analyzer: OrganizationAnalyzer) -> Dict:
        """Analyze all organizations and suggest classifications."""
        classifications = defaultdict(list)
        class_counts = Counter()
        
        # Classify public organizations
        for org in analyzer.public_orgs:
            classification = self.classify_organization(org, 'public')
            classifications[classification].append(org)
            class_counts[classification] += 1
        
        # Classify international organizations
        for org in analyzer.international_orgs:
            classification = self.classify_organization(org, 'international')
            classifications[classification].append(org)
            class_counts[classification] += 1
        
        # Classify private organizations
        for org in analyzer.private_orgs:
            classification = self.classify_organization(org, 'private')
            classifications[classification].append(org)
            class_counts[classification] += 1
        
        return {
            'classifications': dict(classifications),
            'counts': class_counts,
            'hierarchy': self.hierarchy
        }
    
    def generate_ontology_ttl(self, analysis: Dict) -> str:
        """Generate Turtle RDF for the organization ontology."""
        ttl_lines = [
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix org: <http://www.w3.org/ns/org#> .",
            "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
            "@prefix sg: <http://solve.global/knowledge-commons/> .",
            "",
            "# Organization Type Hierarchy",
            ""
        ]
        
        # Generate subclass declarations
        for subclass, superclass in analysis['hierarchy'].items():
            if superclass.startswith('org:'):
                ttl_lines.append(f"sg:{subclass} rdfs:subClassOf {superclass} ;")
            else:
                ttl_lines.append(f"sg:{subclass} rdfs:subClassOf sg:{superclass} ;")
            
            # Add labels
            label = re.sub(r'([A-Z])', r' \1', subclass).strip()
            ttl_lines.append(f'    rdfs:label "{label}" ;')
            ttl_lines.append(f'    skos:prefLabel "{label}" .')
            ttl_lines.append("")
        
        return '\n'.join(ttl_lines)
    
    def save_classification_analysis(self, analysis: Dict, filename: str = "organization_classification_analysis.txt"):
        """Save detailed classification analysis."""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("Organization Classification Analysis\n")
            f.write("=" * 50 + "\n\n")
            
            # Summary statistics
            f.write("CLASSIFICATION SUMMARY:\n")
            f.write("-" * 30 + "\n")
            for class_name, count in analysis['counts'].most_common():
                f.write(f"{class_name}: {count} organizations\n")
            f.write(f"\nTotal Classified: {sum(analysis['counts'].values())}\n\n")
            
            # Hierarchy structure
            f.write("HIERARCHY STRUCTURE:\n")
            f.write("-" * 30 + "\n")
            for subclass, superclass in analysis['hierarchy'].items():
                f.write(f"{subclass} -> {superclass}\n")
            f.write("\n")
            
            # Detailed classifications
            f.write("DETAILED CLASSIFICATIONS:\n")
            f.write("-" * 30 + "\n")
            
            for class_name, orgs in analysis['classifications'].items():
                f.write(f"\n{class_name} ({len(orgs)} organizations):\n")
                for org in sorted(orgs)[:20]:  # Show first 20
                    f.write(f"  - {org}\n")
                if len(orgs) > 20:
                    f.write(f"  ... and {len(orgs) - 20} more\n")
                f.write("\n")

def main():
    """Main function to run organization classification."""
    print("Organization Classification for Subclass Hierarchy")
    print("=" * 50)
    
    # Load organizations
    analyzer = OrganizationAnalyzer()
    analyzer.analyze_all_csv_files()
    
    # Classify organizations
    classifier = OrganizationClassifier()
    analysis = classifier.analyze_classifications(analyzer)
    
    # Display summary
    print(f"\nClassification Results:")
    print(f"Total organizations classified: {sum(analysis['counts'].values())}")
    print(f"Number of classification types: {len(analysis['counts'])}")
    
    print(f"\nTop Classifications:")
    for class_name, count in analysis['counts'].most_common(10):
        print(f"  {class_name}: {count}")
    
    # Show some examples
    print(f"\nExample Classifications:")
    for class_name, orgs in list(analysis['classifications'].items())[:5]:
        if orgs:
            print(f"\n{class_name}:")
            for org in orgs[:3]:
                print(f"  - {org}")
            if len(orgs) > 3:
                print(f"  ... and {len(orgs) - 3} more")
    
    # Save detailed analysis
    classifier.save_classification_analysis(analysis)
    print(f"\nDetailed analysis saved to: organization_classification_analysis.txt")
    
    # Generate and save ontology
    ontology_ttl = classifier.generate_ontology_ttl(analysis)
    with open("organization_ontology.ttl", 'w', encoding='utf-8') as f:
        f.write(ontology_ttl)
    print(f"Organization ontology saved to: organization_ontology.ttl")
    
    print("\nReady for RDF generation with subclass hierarchy!")

if __name__ == "__main__":
    main()
