#!/usr/bin/env python3
"""
Organization RDF Generator
Creates complete Turtle RDF for all organizations with proper hierarchy and metadata.
"""

import re
from urllib.parse import quote
from analyze_organizations import OrganizationAnalyzer
from classify_organizations import OrganizationClassifier
from normalize_organizations import OrganizationNormalizer

class OrganizationRDFGenerator:
    """Generates complete RDF for organizations with hierarchy and normalization."""
    
    def __init__(self):
        self.classifier = OrganizationClassifier()
        self.normalizer = OrganizationNormalizer()
        self.namespace = "http://solve.global/knowledge-commons/"
        
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
    
    def escape_literal(self, text: str) -> str:
        """Escape text for RDF literal."""
        if not text:
            return ""
        return text.replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
    
    def generate_organization_rdf(self, org_name: str, org_type: str, sources: list) -> str:
        """Generate RDF for a single organization."""
        # Get classification
        classification = self.classifier.classify_organization(org_name, org_type)
        
        # Create URI
        org_uri = self.create_organization_uri(org_name)
        
        # Extract base name and country for metadata
        base_name, country = self.normalizer.extract_base_name_and_country(org_name)
        
        rdf_lines = [
            f"{org_uri} a sg:{classification} ;",
            f'    skos:prefLabel "{self.escape_literal(org_name)}" ;',
            f'    rdfs:label "{self.escape_literal(base_name)}" ;'
        ]
        
        # Add country information if present
        if country:
            rdf_lines.append(f'    schema:addressCountry "{self.escape_literal(country)}" ;')
        
        # Add source information
        source_files = list(set(source[0] for source in sources))
        if source_files:
            source_list = ', '.join(f'"{file}"' for file in source_files)
            rdf_lines.append(f'    sgm:sourceFiles {source_list} ;')
        
        # Add mention count
        mention_count = len(sources)
        rdf_lines.append(f'    sgm:mentionCount {mention_count} ;')
        
        # Add organization type classification
        if org_type:
            rdf_lines.append(f'    org:classification sg:{org_type.title()}Sector ;')
        
        # Close the statement
        rdf_lines[-1] = rdf_lines[-1].rstrip(' ;') + ' .'
        
        return '\n'.join(rdf_lines)
    
    def generate_complete_rdf(self, analyzer: OrganizationAnalyzer) -> str:
        """Generate complete RDF for all organizations."""
        # Get classification analysis
        analysis = self.classifier.analyze_classifications(analyzer)
        
        rdf_lines = [
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
            "@prefix org: <http://www.w3.org/ns/org#> .",
            "@prefix schema: <http://schema.org/> .",
            "@prefix sg: <http://solve.global/knowledge-commons/> .",
            "@prefix sgm: <http://solve.global/knowledge-commons/process-metadata#> .",
            "",
            "# Organization Type Hierarchy",
            ""
        ]
        
        # Add class hierarchy
        for subclass, superclass in analysis['hierarchy'].items():
            if superclass.startswith('org:'):
                rdf_lines.append(f"sg:{subclass} rdfs:subClassOf {superclass} ;")
            else:
                rdf_lines.append(f"sg:{subclass} rdfs:subClassOf sg:{superclass} ;")
            
            # Add labels
            label = re.sub(r'([A-Z])', r' \1', subclass).strip()
            rdf_lines.append(f'    rdfs:label "{label}" ;')
            rdf_lines.append(f'    skos:prefLabel "{label}" .')
            rdf_lines.append("")
        
        # Add sector classifications
        rdf_lines.extend([
            "# Sector Classifications",
            "",
            "sg:PublicSector a skos:Concept ;",
            '    skos:prefLabel "Public Sector" .',
            "",
            "sg:InternationalSector a skos:Concept ;",
            '    skos:prefLabel "International Sector" .',
            "",
            "sg:PrivateSector a skos:Concept ;",
            '    skos:prefLabel "Private Sector" .',
            "",
            "# Organization Instances",
            ""
        ])
        
        # Generate RDF for all organizations
        all_orgs = [
            (org, 'public', analyzer.org_sources[org]) for org in analyzer.public_orgs
        ] + [
            (org, 'international', analyzer.org_sources[org]) for org in analyzer.international_orgs
        ] + [
            (org, 'private', analyzer.org_sources[org]) for org in analyzer.private_orgs
        ]
        
        # Sort by organization name for consistent output
        all_orgs.sort(key=lambda x: x[0])
        
        for org_name, org_type, sources in all_orgs:
            org_rdf = self.generate_organization_rdf(org_name, org_type, sources)
            rdf_lines.append(org_rdf)
            rdf_lines.append("")
        
        return '\n'.join(rdf_lines)

def main():
    """Generate complete organization RDF."""
    print("Generating Complete Organization RDF")
    print("=" * 40)
    
    # Load and analyze organizations
    analyzer = OrganizationAnalyzer()
    analyzer.analyze_all_csv_files()
    
    # Generate RDF
    generator = OrganizationRDFGenerator()
    rdf_content = generator.generate_complete_rdf(analyzer)
    
    # Save to file
    output_file = "organizations_complete.ttl"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(rdf_content)
    
    print(f"Complete organization RDF saved to: {output_file}")
    print(f"Generated RDF for {len(analyzer.org_sources)} organizations")
    
    # Show some statistics
    stats = analyzer.get_organization_stats()
    print(f"\nStatistics:")
    print(f"  Public Organizations: {stats['counts']['public']}")
    print(f"  International Organizations: {stats['counts']['international']}")
    print(f"  Private Organizations: {stats['counts']['private']}")
    print(f"  Total Unique: {stats['counts']['total_unique']}")
    
    print(f"\nRDF file ready for manual loading into Neptune!")

if __name__ == "__main__":
    main()
