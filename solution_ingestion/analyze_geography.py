#!/usr/bin/env python3
"""
Geographic Entity Analysis and Mapping
Maps countries to GeoNames URIs and handles regional organizations.
"""

import csv
from pathlib import Path
from collections import Counter
from typing import Dict, List, Optional

class GeographicMapper:
    """Maps geographic entities to GeoNames URIs and regional organizations."""
    
    def __init__(self):
        self.country_counts = Counter()
        self.geonames_mapping = self._create_geonames_mapping()
        self.regional_organizations = self._create_regional_organizations()
        
    def _create_geonames_mapping(self) -> Dict[str, str]:
        """Create mapping from country names to GeoNames URIs."""
        return {
            # Major countries from the data
            'Australia': 'gn:2077456',
            'Japan': 'gn:1861060', 
            'Singapore': 'gn:1880251',
            'New Zealand': 'gn:2186224',
            'Thailand': 'gn:1605651',
            'Malaysia': 'gn:1733045',
            'Philippines': 'gn:1694008',
            'Indonesia': 'gn:1643084',
            'South Korea': 'gn:1835841',
            'Republic of Korea': 'gn:1835841',  # Same as South Korea
            'Taiwan': 'gn:1668284',
            'Taiwan (China)': 'gn:1668284',
            'China': 'gn:1814991',
            "People's Republic of China": 'gn:1814991',
            'India': 'gn:1269750',
            'Bangladesh': 'gn:1210997',
            'Pakistan': 'gn:1168579',
            'Nepal': 'gn:1282988',
            'Sri Lanka': 'gn:1227603',
            'Myanmar': 'gn:1327865',
            'Cambodia': 'gn:1831722',
            'Vietnam': 'gn:1562822',
            'Laos': 'gn:1655842',
            'Brunei': 'gn:1820814',
            'United States': 'gn:6252001',
            'Canada': 'gn:6251999',
            'United Kingdom': 'gn:2635167',
            'Germany': 'gn:2921044',
            'France': 'gn:3017382',
            'Italy': 'gn:3175395',
            'Spain': 'gn:2510769',
            'Netherlands': 'gn:2750405',
            'Switzerland': 'gn:2658434',
            'Norway': 'gn:3144096',
            'Sweden': 'gn:2661886',
            'Denmark': 'gn:2623032',
            'Finland': 'gn:660013',
            'Brazil': 'gn:3469034',
            'Mexico': 'gn:3996063',
            'Chile': 'gn:3895114',
            'Argentina': 'gn:3865483',
            'South Africa': 'gn:953987',
            'Kenya': 'gn:192950',
            'Nigeria': 'gn:2328926',
            'Egypt': 'gn:357994',
            'Turkey': 'gn:298795',
            'Russia': 'gn:2017370',
            'Israel': 'gn:294640',
            'Saudi Arabia': 'gn:102358',
            'UAE': 'gn:290557',
            'United Arab Emirates': 'gn:290557',
            'Qatar': 'gn:289688',
            'Kuwait': 'gn:285570',
            'Oman': 'gn:286963',
            'Bahrain': 'gn:290291',
            'Jordan': 'gn:248816',
            'Lebanon': 'gn:272103',
            'Iran': 'gn:130758',
            'Iraq': 'gn:99237',
            'Afghanistan': 'gn:1149361',
            'Uzbekistan': 'gn:1512440',
            'Kazakhstan': 'gn:1522867',
            'Mongolia': 'gn:2029969',
            'Fiji': 'gn:2205218',
            'Papua New Guinea': 'gn:2088628',
            'Solomon Islands': 'gn:2103350',
            'Vanuatu': 'gn:2134431',
            'Samoa': 'gn:4034894',
            'Tonga': 'gn:4032283',
            'Palau': 'gn:1559582',
            'Marshall Islands': 'gn:2080185',
            'Micronesia': 'gn:2081918',
            'Kiribati': 'gn:4030945',
            'Tuvalu': 'gn:2110297',
            'Nauru': 'gn:2110425',
        }
    
    def _create_regional_organizations(self) -> Dict[str, Dict]:
        """Create regional organization definitions."""
        return {
            'ASEAN': {
                'uri': 'sg:RegionalOrg_asean',
                'label': 'Association of Southeast Asian Nations',
                'type': 'RegionalOrganization',
                'members': ['gn:1643084', 'gn:1733045', 'gn:1694008', 'gn:1880251', 
                           'gn:1605651', 'gn:1562822', 'gn:1327865', 'gn:1655842', 
                           'gn:1831722', 'gn:1820814']  # Indonesia, Malaysia, Philippines, etc.
            },
            'APEC': {
                'uri': 'sg:RegionalOrg_apec',
                'label': 'Asia-Pacific Economic Cooperation',
                'type': 'RegionalOrganization',
                'members': ['gn:2077456', 'gn:1861060', 'gn:1835841', 'gn:1814991',
                           'gn:6252001', 'gn:6251999', 'gn:2186224']  # Australia, Japan, etc.
            },
            'EU': {
                'uri': 'sg:RegionalOrg_eu',
                'label': 'European Union',
                'type': 'RegionalOrganization',
                'members': ['gn:2921044', 'gn:3017382', 'gn:3175395', 'gn:2510769',
                           'gn:2750405', 'gn:2658434']  # Germany, France, Italy, etc.
            },
            'Pacific Islands': {
                'uri': 'sg:RegionalOrg_pacific_islands',
                'label': 'Pacific Island Nations',
                'type': 'RegionalOrganization',
                'members': ['gn:2205218', 'gn:2088628', 'gn:2103350', 'gn:2134431',
                           'gn:4034894', 'gn:4032283']  # Fiji, PNG, Solomon Islands, etc.
            }
        }
    
    def analyze_countries_from_csv(self, input_dir: str = "input_data"):
        """Analyze countries from CSV files."""
        input_path = Path(input_dir)
        csv_files = list(input_path.glob("*.csv"))
        
        for csv_file in csv_files:
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        country = row.get('Country', '').strip()
                        if country and country.upper() not in ['NIL', 'N/A', 'NULL', '']:
                            self.country_counts[country] += 1
            except Exception as e:
                print(f"Error processing {csv_file}: {e}")
    
    def get_geonames_uri(self, country_name: str) -> Optional[str]:
        """Get GeoNames URI for a country."""
        return self.geonames_mapping.get(country_name.strip())
    
    def generate_geography_rdf(self) -> str:
        """Generate RDF for geographic entities and regional organizations."""
        rdf_lines = [
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
            "@prefix gn: <http://www.geonames.org/ontology#> .",
            "@prefix sg: <http://solve.global/knowledge-commons/> .",
            "@prefix geo: <http://www.w3.org/2003/01/geo/wgs84_pos#> .",
            "",
            "# Regional Organization Class",
            "",
            "sg:RegionalOrganization rdfs:subClassOf gn:Feature ;",
            '    rdfs:label "Regional Organization" ;',
            '    skos:prefLabel "Regional Organization" .',
            "",
            "# Regional Organizations",
            ""
        ]
        
        # Generate regional organizations
        for org_key, org_info in self.regional_organizations.items():
            rdf_lines.extend([
                f"{org_info['uri']} a sg:RegionalOrganization ;",
                f'    rdfs:label "{org_info["label"]}" ;',
                f'    skos:prefLabel "{org_key}" ;',
                f'    gn:name "{org_info["label"]}" .'
            ])
            
            # Add member relationships
            if org_info['members']:
                member_list = ', '.join(org_info['members'])
                rdf_lines.append(f"    # Members: {member_list}")
            
            rdf_lines.append("")
        
        # Add country usage statistics as comments
        rdf_lines.extend([
            "# Country Usage Statistics (from CSV data)",
            "# Countries found in data with GeoNames mappings:",
            ""
        ])
        
        mapped_countries = 0
        unmapped_countries = []
        
        for country, count in self.country_counts.most_common():
            geonames_uri = self.get_geonames_uri(country)
            if geonames_uri:
                rdf_lines.append(f"# {count:3d}x {country} -> {geonames_uri}")
                mapped_countries += 1
            else:
                unmapped_countries.append((country, count))
        
        if unmapped_countries:
            rdf_lines.extend([
                "",
                "# Unmapped countries (need GeoNames URIs):",
                ""
            ])
            for country, count in unmapped_countries:
                rdf_lines.append(f"# {count:3d}x {country} -> NEEDS MAPPING")
        
        rdf_lines.extend([
            "",
            f"# Summary: {mapped_countries} countries mapped, {len(unmapped_countries)} need mapping",
            ""
        ])
        
        return '\n'.join(rdf_lines)
    
    def get_country_stats(self) -> Dict:
        """Get statistics about countries in the data."""
        mapped = sum(1 for country in self.country_counts.keys() 
                    if self.get_geonames_uri(country))
        unmapped = len(self.country_counts) - mapped
        
        return {
            'total_countries': len(self.country_counts),
            'mapped_countries': mapped,
            'unmapped_countries': unmapped,
            'total_mentions': sum(self.country_counts.values()),
            'most_common': self.country_counts.most_common(10)
        }

def main():
    """Analyze geographic entities and generate RDF."""
    print("Geographic Entity Analysis and Mapping")
    print("=" * 40)
    
    mapper = GeographicMapper()
    mapper.analyze_countries_from_csv()
    
    # Show statistics
    stats = mapper.get_country_stats()
    print(f"\nGeographic Analysis Results:")
    print(f"  Total countries: {stats['total_countries']}")
    print(f"  Mapped to GeoNames: {stats['mapped_countries']}")
    print(f"  Need mapping: {stats['unmapped_countries']}")
    print(f"  Total mentions: {stats['total_mentions']}")
    
    print(f"\nMost Common Countries:")
    for country, count in stats['most_common']:
        geonames_uri = mapper.get_geonames_uri(country)
        status = "✅" if geonames_uri else "❌"
        print(f"  {status} {count:3d}x {country}")
    
    # Generate RDF
    rdf_content = mapper.generate_geography_rdf()
    
    # Save to file
    output_file = "geography_entities.ttl"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(rdf_content)
    
    print(f"\nGeographic RDF saved to: {output_file}")
    print("Includes GeoNames mappings and regional organizations!")

if __name__ == "__main__":
    main()
