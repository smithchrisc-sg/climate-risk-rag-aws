#!/usr/bin/env python3

import json
import re
from typing import Dict, List, Optional

class IntegratedEntityMapper:
    """Maps entities to RDF URIs using organization, vocabulary, and geography mappings."""
    
    def __init__(self):
        self.org_cache = self._load_organization_cache()
        self.vocab_mappings = self._load_vocabulary_mappings()
        self.geo_mappings = self._load_geography_mappings()
    
    def _load_organization_cache(self) -> Dict:
        try:
            with open('organization_lookup_cache.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _load_vocabulary_mappings(self) -> Dict:
        """Extract vocabulary concept mappings from TTL file."""
        mappings = {}
        try:
            with open('vocabulary_concepts.ttl', 'r') as f:
                content = f.read()
                # Extract concept URIs and labels
                for line in content.split('\n'):
                    if 'skos:prefLabel' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            uri = parts[0]
                            label = ' '.join(parts[2:]).strip('".; ')
                            mappings[label.lower()] = uri
        except FileNotFoundError:
            pass
        return mappings
    
    def _load_geography_mappings(self) -> Dict:
        """Load geography mappings from CSV file."""
        mappings = {}
        try:
            import csv
            with open('country_mappings.csv', 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    country = row['country_name'].strip()
                    geonames_uri = row['geonames_uri'].strip()
                    mappings[country.lower()] = geonames_uri
        except FileNotFoundError:
            pass
        return mappings
    
    def map_organization(self, org_name: str) -> Optional[str]:
        """Map organization name to canonical URI."""
        if not org_name:
            return None
        
        org_name = org_name.strip()
        
        # Direct lookup in name_to_uri cache
        if 'name_to_uri' in self.org_cache and org_name in self.org_cache['name_to_uri']:
            return self.org_cache['name_to_uri'][org_name]
        
        # Simple fuzzy matching - just check if any cached name contains our search term
        if 'name_to_uri' in self.org_cache:
            org_lower = org_name.lower()
            for cached_name, uri in self.org_cache['name_to_uri'].items():
                if org_lower in cached_name.lower() or cached_name.lower() in org_lower:
                    return uri
        
        return None
    
    def map_vocabulary_concept(self, concept: str) -> Optional[str]:
        """Map vocabulary term to SKOS concept URI."""
        if not concept:
            return None
        
        concept_lower = concept.lower().strip()
        return self.vocab_mappings.get(concept_lower)
    
    def map_geography(self, location: str) -> Optional[str]:
        """Map geographic location to GeoNames URI."""
        if not location:
            return None
        
        location_lower = location.lower().strip()
        return self.geo_mappings.get(location_lower)
    
    def enhance_solution_metadata(self, solution) -> Dict:
        """Enhance solution with mapped entity URIs."""
        # Convert solution to dict for enhancement
        enhanced = {
            'doc_id': getattr(solution, 'doc_id', solution.id),
            'name': solution.name,
            'country': solution.country,
            'date_added': getattr(solution, 'date_added', ''),
            'source_url': getattr(solution, 'source_url', ''),
            'public_organisations': solution.public_organisations,
            'international_organisations': solution.international_organisations,
            'private_organisations': solution.private_organisations,
            'type_of_risk': solution.type_of_risk,
            'type_of_solution': solution.type_of_solution,
            'theme': solution.theme
        }
        
        # Map organizations (prioritize: public -> international -> private)
        organization_uris = []
        primary_publisher_uri = None
        
        for org_field in ['public_organisations', 'international_organisations', 'private_organisations']:
            if hasattr(solution, org_field) and getattr(solution, org_field):
                org_text = getattr(solution, org_field).strip()
                if org_text:
                    # Split by common delimiters and get first org for publisher
                    orgs = [org.strip() for org in org_text.replace('\n', ',').split(',') if org.strip()]
                    for org in orgs:
                        org_uri = self.map_organization(org)
                        if org_uri:
                            if primary_publisher_uri is None:
                                primary_publisher_uri = org_uri
                            organization_uris.append(org_uri)
        
        if organization_uris:
            enhanced['organization_uris'] = organization_uris
            enhanced['primary_publisher_uri'] = primary_publisher_uri
        
        # Map geography
        if solution.country:
            geo_uri = self.map_geography(solution.country)
            if geo_uri:
                enhanced['country_uri'] = geo_uri
        
        # Map vocabulary concepts
        for field in ['type_of_risk', 'type_of_solution', 'theme']:
            if hasattr(solution, field) and getattr(solution, field):
                concepts = [c.strip() for c in str(getattr(solution, field)).split(',')]
                mapped_concepts = []
                for concept in concepts:
                    concept_uri = self.map_vocabulary_concept(concept)
                    if concept_uri:
                        mapped_concepts.append(concept_uri)
                if mapped_concepts:
                    enhanced[f"{field}_uris"] = mapped_concepts
        
        return enhanced
