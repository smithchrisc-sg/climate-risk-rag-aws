#!/usr/bin/env python3
"""
Entity Mapper for Solution Ingestion
Maps solution entities to standardized URIs using reference files.
"""

import logging
import re
from typing import Dict, Any, List
from pathlib import Path
from rdflib import Graph, Namespace, URIRef

logger = logging.getLogger(__name__)

# Define namespaces
SG = Namespace("http://solve.global/knowledge-commons/")
GN = Namespace("http://www.geonames.org/ontology#")

class EntityMapper:
    """Maps solution entities to standardized URIs using reference files."""
    
    def __init__(self):
        self.examples_dir = Path(__file__).parent.parent / "Examples"
        self.geography_mapping = {}
        self.organization_graph = None
        self.vocabulary_graph = None
        
        # Load reference data
        self._load_geography_mapping()
        self._load_organization_graph()
        self._load_vocabulary_graph()
        
    def _load_geography_mapping(self):
        """Load geography to GeoNames URI mapping."""
        geo_file = self.examples_dir / "partial_geonames_mapping.txt"
        if geo_file.exists():
            with open(geo_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if ':' in line and not line.startswith('#'):
                        # Parse format: 'Country Name': 'gn:123456'
                        parts = line.split(': ')
                        if len(parts) == 2:
                            country = parts[0].strip("'\"")
                            uri = parts[1].strip("'\"").split('#')[0].strip()  # Remove comments
                            self.geography_mapping[country] = uri
            logger.info(f"Loaded {len(self.geography_mapping)} geography mappings")
        else:
            logger.warning(f"Geography mapping file not found: {geo_file}")
    
    def _load_organization_graph(self):
        """Load organization RDF graph."""
        org_file = self.examples_dir / "organizations_complete.ttl"
        if org_file.exists():
            self.organization_graph = Graph()
            self.organization_graph.parse(org_file, format='turtle')
            logger.info(f"Loaded organization graph with {len(self.organization_graph)} triples")
        else:
            logger.warning(f"Organization file not found: {org_file}")
    
    def _load_vocabulary_graph(self):
        """Load vocabulary concepts RDF graph."""
        vocab_file = self.examples_dir / "vocabulary_concepts.ttl"
        if vocab_file.exists():
            self.vocabulary_graph = Graph()
            self.vocabulary_graph.parse(vocab_file, format='turtle')
            logger.info(f"Loaded vocabulary graph with {len(self.vocabulary_graph)} triples")
        else:
            logger.warning(f"Vocabulary file not found: {vocab_file}")
    
    def enhance_solution_metadata(self, solution) -> Dict[str, Any]:
        """Enhance solution with mapped entities."""
        
        # Start with solution as dict
        enhanced = solution.to_dict()
        
        # Map geography
        country = getattr(solution, 'country', '').strip()
        if country in self.geography_mapping:
            # Convert gn:123456 to proper URIRef
            gn_id = self.geography_mapping[country].replace('gn:', '')
            enhanced['mapped_geography'] = GN[gn_id]
            logger.debug(f"Mapped geography: {country} -> {enhanced['mapped_geography']}")
        else:
            enhanced['mapped_geography'] = country  # Fallback to string
            if country:
                logger.warning(f"No geography mapping for: '{country}'")
        
        # Extract and map organizations
        organizations = self._extract_organizations(solution)
        mapped_orgs = []
        for org_name in organizations:
            mapped_orgs.append({
                'name': org_name,
                'uri': self._generate_org_uri(org_name)
            })
        enhanced['mapped_organizations'] = mapped_orgs
        
        # Set primary publisher (first organization found)
        if mapped_orgs:
            enhanced['primary_publisher_uri'] = mapped_orgs[0]['uri']
            logger.debug(f"Primary publisher: {mapped_orgs[0]['name']} -> {enhanced['primary_publisher_uri']}")
        
        # Map vocabulary concepts
        enhanced['risk_type_uris'] = self._map_risk_types(getattr(solution, 'type_of_risk', ''))
        enhanced['solution_type_uris'] = self._map_solution_types(getattr(solution, 'type_of_solution', ''))
        enhanced['theme_uris'] = self._map_themes(getattr(solution, 'theme', ''))
        
        # Parse implementation years
        enhanced['implementation_years'] = self._parse_years(getattr(solution, 'year_of_implementation', ''))
        
        logger.info(f"Enhanced metadata: {len(mapped_orgs)} orgs, geography: {enhanced.get('mapped_geography', 'none')}")
        
        return enhanced
    
    def _extract_organizations(self, solution) -> List[str]:
        """Extract organization names from solution fields."""
        organizations = []
        
        for field_name in ['public_organisations', 'international_organisations', 'private_organisations']:
            field_value = getattr(solution, field_name, '')
            if field_value and field_value.strip() and field_value.strip().upper() != 'NIL':
                orgs = [org.strip() for org in field_value.split(',') if org.strip()]
                organizations.extend(orgs)
        
        return organizations
    
    def _generate_org_uri(self, org_name: str) -> URIRef:
        """Generate organization URI."""
        # Normalize organization name for URI
        normalized = re.sub(r'[^\w\s-]', '', org_name.lower())
        normalized = re.sub(r'\s+', '_', normalized.strip())
        normalized = normalized.replace('__', '_').strip('_')
        return SG[f"Org_{normalized}"]
    
    def _map_risk_types(self, risk_type_str: str) -> List[URIRef]:
        """Map risk types to vocabulary URIs."""
        if not risk_type_str or not risk_type_str.strip():
            return []
        
        # Simple mapping for common risk types
        risk_mapping = {
            'natural catastrophe': SG.RiskType_natural_catastrophe,
            'climate change': SG.RiskType_climate_change,
            'flooding': SG.RiskType_flooding,
            'drought': SG.RiskType_drought
        }
        
        risk_type = risk_type_str.lower().strip()
        if risk_type in risk_mapping:
            return [risk_mapping[risk_type]]
        
        # Fallback: generate URI from text
        normalized = re.sub(r'[^\w\s-]', '', risk_type)
        normalized = re.sub(r'\s+', '_', normalized.strip())
        return [SG[f"RiskType_{normalized}"]]
    
    def _map_solution_types(self, solution_type_str: str) -> List[URIRef]:
        """Map solution types to vocabulary URIs."""
        if not solution_type_str or not solution_type_str.strip():
            return []
        
        # Parse multiple solution types
        solution_types = [t.strip() for t in solution_type_str.split(',') if t.strip()]
        uris = []
        
        for solution_type in solution_types:
            normalized = re.sub(r'[^\w\s-]', '', solution_type.lower())
            normalized = re.sub(r'\s+', '_', normalized.strip())
            uris.append(SG[f"SolutionType_{normalized}"])
        
        return uris
    
    def _map_themes(self, theme_str: str) -> List[URIRef]:
        """Map themes to vocabulary URIs."""
        if not theme_str or not theme_str.strip():
            return []
        
        # Parse multiple themes
        themes = [t.strip() for t in theme_str.split(',') if t.strip()]
        uris = []
        
        for theme in themes:
            normalized = re.sub(r'[^\w\s-]', '', theme.lower())
            normalized = re.sub(r'\s+', '_', normalized.strip())
            uris.append(SG[f"Theme_{normalized}"])
        
        return uris
    
    def _parse_years(self, year_str: str) -> List[str]:
        """Parse implementation years."""
        if not year_str or not year_str.strip():
            return []
        
        logger.info(f"Parsing year string: '{year_str}'")
        
        all_years = set()
        
        # Extract 4-digit years first
        four_digit_years = re.findall(r'\b((19|20)\d{2})\b', year_str)
        # Extract just the full year from the tuple matches
        four_digit_years = [match[0] for match in four_digit_years]
        logger.info(f"Found 4-digit years: {four_digit_years}")
        all_years.update(four_digit_years)
        
        # Extract standalone 2-digit numbers that could be years
        two_digit_matches = re.findall(r'(?<!\d)\b(\d{2})\b(?!\d)', year_str)
        logger.info(f"Found 2-digit matches: {two_digit_matches}")
        
        # Process 2-digit years
        for year_2d in two_digit_matches:
            # Skip if this 2-digit year is part of any 4-digit year we found
            skip = False
            for four_digit in four_digit_years:
                if year_2d in four_digit:
                    skip = True
                    break
            
            if skip:
                logger.info(f"Skipping {year_2d} as it's part of 4-digit year")
                continue
                
            year_int = int(year_2d)
            # Only process if it looks like a reasonable year (not random 2-digit numbers)
            if 10 <= year_int <= 99:  # Valid 2-digit year range
                if year_int > 25:
                    full_year = f"19{year_2d}"
                else:
                    full_year = f"20{year_2d}"
                logger.info(f"Converting {year_2d} to {full_year}")
                all_years.add(full_year)
        
        result = list(all_years)
        logger.info(f"Final years: {result}")
        return result
