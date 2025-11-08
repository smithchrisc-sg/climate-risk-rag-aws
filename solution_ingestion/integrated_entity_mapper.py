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
        """Extract geography mappings from TTL file."""
        mappings = {}
        try:
            with open('geography_entities.ttl', 'r') as f:
                content = f.read()
                # Extract country name -> GeoNames mappings from comments
                for line in content.split('\n'):
                    if ' -> gn:' in line and not line.strip().startswith('#'):
                        parts = line.split(' -> ')
                        if len(parts) == 2:
                            country = parts[0].strip()
                            geonames_uri = parts[1].strip()
                            mappings[country.lower()] = geonames_uri
        except FileNotFoundError:
            pass
        return mappings
    
    def map_organization(self, org_name: str) -> Optional[str]:
        """Map organization name to canonical URI."""
        if not org_name:
            return None
        
        # Direct lookup in cache
        if org_name in self.org_cache:
            org_data = self.org_cache[org_name]
            return f"sg:Organization_{org_data.get('id', org_name.replace(' ', '_'))}"
        
        # Fuzzy matching fallback
        org_lower = org_name.lower()
        for cached_name, org_data in self.org_cache.items():
            if org_lower in cached_name.lower() or cached_name.lower() in org_lower:
                return f"sg:Organization_{org_data.get('id', cached_name.replace(' ', '_'))}"
        
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
        
        # Map organizations (try all org fields)
        for org_field in ['public_organisations', 'international_organisations', 'private_organisations']:
            if hasattr(solution, org_field) and getattr(solution, org_field):
                org_uri = self.map_organization(getattr(solution, org_field))
                if org_uri:
                    enhanced['organization_uri'] = org_uri
                    break
        
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
