"""
Rule-Based Enhancer for Ontology Extraction
Supplements LLM extraction with keyword-based rules.
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class RuleEnhancer:
    """Enhance LLM extraction with rule-based patterns."""
    
    def __init__(self):
        # Keyword patterns for high-confidence concepts
        self.patterns = {
            'risks': {
                'sg:FloodRisk': ['flood', 'flooding', 'inundation', 'deluge'],
                'sg:EarthquakeRisk': ['earthquake', 'seismic', 'tremor'],
                'sg:TyphoonRisk': ['typhoon', 'hurricane', 'cyclone'],
                'sg:DroughtRisk': ['drought', 'water scarcity', 'arid'],
                'sg:PandemicRisk': ['pandemic', 'epidemic', 'outbreak', 'covid'],
                'sg:CyberRisk': ['cyber', 'ransomware', 'data breach', 'hacking']
            },
            'mechanisms': {
                'sg:ParametricInsurance': ['parametric', 'index-based', 'weather index', 'trigger-based'],
                'sg:MicroinsuranceProduct': ['microinsurance', 'micro-insurance', 'micro insurance'],
                'sg:EarlyWarningSystem': ['early warning', 'alert system', 'warning system'],
                'sg:RiskPooling': ['risk pool', 'pooling', 'risk sharing'],
                'sg:PublicPrivatePartnership': ['PPP', 'public-private', 'government partnership', 'public private']
            },
            'impacts': {
                'sg:EconomicLossReduction': ['economic loss', 'financial loss', 'reduced losses', 'loss reduction'],
                'sg:MortalityReduction': ['mortality', 'death', 'fatalities', 'lives saved'],
                'sg:InsurancePenetrationIncrease': ['penetration', 'coverage increase', 'insurance uptake'],
                'sg:RecoveryTimeReduction': ['recovery time', 'rapid recovery', 'faster recovery']
            }
        }
    
    def enhance(self, extraction: Dict, chunks_by_section: Dict) -> Dict:
        """Enhance LLM extraction with rule-based patterns."""
        # Combine all text for pattern matching
        all_text = self._combine_text(chunks_by_section)
        
        # Track enhancements
        enhancements = {'risks_added': 0, 'mechanisms_added': 0, 'impacts_added': 0}
        
        # Apply patterns for each category
        for category in ['risks', 'mechanisms', 'impacts']:
            for concept_uri, keywords in self.patterns.get(category, {}).items():
                # Check if LLM already extracted this concept
                if self._already_extracted(concept_uri, extraction.get(category, [])):
                    continue
                
                # Check if any keyword matches
                if self._keyword_match(keywords, all_text):
                    # Add rule-based extraction
                    extraction.setdefault(category, []).append({
                        'uri': concept_uri,
                        'label': self._uri_to_label(concept_uri),
                        'confidence': 0.85,
                        'evidence': f"Keyword match: {keywords[0]}",
                        'section': 'Description',
                        'source': 'rule',
                        'chunk_uris': self._get_all_chunk_uris(chunks_by_section)
                    })
                    enhancements[f"{category}_added"] += 1
        
        # Add enhancement metadata
        extraction['enhancements'] = enhancements
        
        logger.info(f"Rule enhancements: {enhancements}")
        return extraction
    
    def _combine_text(self, chunks_by_section: Dict) -> str:
        """Combine all chunk text into single string."""
        text_parts = []
        for chunks in chunks_by_section.values():
            for chunk in chunks:
                text_parts.append(chunk['text'])
        return ' '.join(text_parts).lower()
    
    def _already_extracted(self, concept_uri: str, extractions: List[Dict]) -> bool:
        """Check if concept already extracted by LLM."""
        return any(e['uri'] == concept_uri for e in extractions)
    
    def _keyword_match(self, keywords: List[str], text: str) -> bool:
        """Check if any keyword appears in text."""
        return any(kw.lower() in text for kw in keywords)
    
    def _uri_to_label(self, uri: str) -> str:
        """Convert URI to human-readable label."""
        # Extract suffix after 'sg:'
        suffix = uri.split(':')[1] if ':' in uri else uri
        
        # Add spaces before capitals
        import re
        label = re.sub(r'([A-Z])', r' \1', suffix).strip()
        
        return label
    
    def _get_all_chunk_uris(self, chunks_by_section: Dict) -> List[str]:
        """Get all chunk URIs from all sections."""
        uris = []
        for chunks in chunks_by_section.values():
            uris.extend([c['uri'] for c in chunks])
        return uris
