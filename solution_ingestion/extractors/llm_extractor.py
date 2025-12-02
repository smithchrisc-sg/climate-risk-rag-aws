"""
LLM Extractor for Ontology Concepts
Uses Bedrock Claude to extract granular ontology concepts from solution text.
"""

import json
import logging
from typing import Dict, List

import boto3

logger = logging.getLogger(__name__)


class LLMExtractor:
    """Extract ontology concepts using Bedrock Claude."""
    
    def __init__(self, kg_manager):
        self.kg_manager = kg_manager
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.model_id = 'anthropic.claude-3-haiku-20240307-v1:0'
        
        # Load ontology taxonomy from KG (cached)
        self.ontology_taxonomy = self._load_ontology_taxonomy()
    
    def _load_ontology_taxonomy(self) -> Dict:
        """Load ontology taxonomy from Neptune KG."""
        # Query for risk hierarchy
        risks_query = """
        PREFIX sg: <http://solve.global/knowledge-commons/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?risk ?label WHERE {
            ?risk a sg:Risk ;
                  rdfs:label ?label .
        }
        """
        
        # Query for mechanisms
        mechanisms_query = """
        PREFIX sg: <http://solve.global/knowledge-commons/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?mechanism ?label WHERE {
            ?mechanism a sg:Mechanism ;
                       rdfs:label ?label .
        }
        """
        
        # Query for impacts
        impacts_query = """
        PREFIX sg: <http://solve.global/knowledge-commons/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?impact ?label WHERE {
            ?impact a sg:Impact ;
                    rdfs:label ?label .
        }
        """
        
        try:
            risks = self.kg_manager.execute_sparql_query(risks_query)
            mechanisms = self.kg_manager.execute_sparql_query(mechanisms_query)
            impacts = self.kg_manager.execute_sparql_query(impacts_query)
            
            return {
                'risks': [{'uri': r['risk'], 'label': r['label']} for r in risks],
                'mechanisms': [{'uri': m['mechanism'], 'label': m['label']} for m in mechanisms],
                'impacts': [{'uri': i['impact'], 'label': i['label']} for i in impacts]
            }
        except Exception as e:
            logger.warning(f"Failed to load ontology taxonomy from KG: {e}")
            # Return minimal taxonomy as fallback
            return self._get_fallback_taxonomy()
    
    def _get_fallback_taxonomy(self) -> Dict:
        """Fallback taxonomy if KG query fails."""
        return {
            'risks': [
                {'uri': 'sg:FloodRisk', 'label': 'Flood Risk'},
                {'uri': 'sg:EarthquakeRisk', 'label': 'Earthquake Risk'},
                {'uri': 'sg:TyphoonRisk', 'label': 'Typhoon Risk'},
                {'uri': 'sg:DroughtRisk', 'label': 'Drought Risk'},
                {'uri': 'sg:PandemicRisk', 'label': 'Pandemic Risk'},
                {'uri': 'sg:CyberRisk', 'label': 'Cyber Risk'}
            ],
            'mechanisms': [
                {'uri': 'sg:ParametricInsurance', 'label': 'Parametric Insurance'},
                {'uri': 'sg:IndexBasedInsurance', 'label': 'Index-Based Insurance'},
                {'uri': 'sg:MicroinsuranceProduct', 'label': 'Microinsurance Product'},
                {'uri': 'sg:EarlyWarningSystem', 'label': 'Early Warning System'},
                {'uri': 'sg:RiskPooling', 'label': 'Risk Pooling'},
                {'uri': 'sg:PublicPrivatePartnership', 'label': 'Public-Private Partnership'}
            ],
            'impacts': [
                {'uri': 'sg:EconomicLossReduction', 'label': 'Economic Loss Reduction'},
                {'uri': 'sg:MortalityReduction', 'label': 'Mortality Reduction'},
                {'uri': 'sg:InsurancePenetrationIncrease', 'label': 'Insurance Penetration Increase'},
                {'uri': 'sg:RecoveryTimeReduction', 'label': 'Recovery Time Reduction'}
            ]
        }
    
    def extract(self, doc_id: str, chunks_by_section: Dict, kg_metadata: Dict) -> Dict:
        """Extract ontology concepts from solution text."""
        # Combine all chunk text
        solution_text = self._combine_chunks(chunks_by_section)
        
        # Build prompt
        prompt = self._build_prompt(solution_text, kg_metadata)
        
        # Call Bedrock Claude
        try:
            response = self._call_bedrock(prompt)
            extraction = self._parse_response(response)
            
            # Map extractions to chunk URIs
            extraction = self._map_to_chunks(extraction, chunks_by_section)
            
            return extraction
        except Exception as e:
            logger.error(f"LLM extraction failed for {doc_id}: {e}")
            return {'risks': [], 'mechanisms': [], 'impacts': [], 'countries': []}
    
    def _combine_chunks(self, chunks_by_section: Dict) -> str:
        """Combine chunks into single text with section markers."""
        text_parts = []
        
        for section, chunks in chunks_by_section.items():
            text_parts.append(f"\n{section}:")
            for chunk in chunks:
                text_parts.append(chunk['text'])
        
        return '\n'.join(text_parts)
    
    def _build_prompt(self, solution_text: str, kg_metadata: Dict) -> str:
        """Build Claude prompt for extraction."""
        # Format ontology taxonomy
        risks_list = '\n'.join([f"- {r['label']}" for r in self.ontology_taxonomy['risks'][:20]])
        mechanisms_list = '\n'.join([f"- {m['label']}" for m in self.ontology_taxonomy['mechanisms'][:20]])
        impacts_list = '\n'.join([f"- {i['label']}" for i in self.ontology_taxonomy['impacts'][:20]])
        
        prompt = f"""You are an expert in climate risk and insurance solutions. Extract specific ontology concepts from the solution description.

EXISTING METADATA (from knowledge graph):
- Risk Types: {kg_metadata.get('riskTypes', 'N/A')}
- Solution Types: {kg_metadata.get('solutionTypes', 'N/A')}

ONTOLOGY TAXONOMY (extract from these categories):

RISKS (extract most specific):
{risks_list}

MECHANISMS (how solution works):
{mechanisms_list}

IMPACTS (what solution achieves):
{impacts_list}

SOLUTION TEXT:
{solution_text[:3000]}

INSTRUCTIONS:
1. Extract SPECIFIC risks mentioned (e.g., "Flood Risk" not just "Natural Catastrophe")
2. Identify MECHANISMS used (e.g., "Parametric Insurance", "Early Warning System")
3. Identify IMPACTS achieved (e.g., "Economic Loss Reduction")
4. For each extraction, provide:
   - Label (e.g., "Flood Risk")
   - Confidence (0.0-1.0)
   - Evidence (quote from solution text, max 100 chars)
   - Section (Description/Key Highlights/Results)

OUTPUT FORMAT (JSON only, no other text):
{{
  "risks": [
    {{"label": "Flood Risk", "confidence": 0.95, "evidence": "parametric flood insurance", "section": "Description"}}
  ],
  "mechanisms": [
    {{"label": "Parametric Insurance", "confidence": 0.98, "evidence": "automated payouts based on rainfall", "section": "Key Highlights"}}
  ],
  "impacts": [
    {{"label": "Economic Loss Reduction", "confidence": 0.90, "evidence": "reduced financial losses", "section": "Results"}}
  ]
}}

Extract concepts now (JSON only):"""
        
        return prompt
    
    def _call_bedrock(self, prompt: str) -> str:
        """Call Bedrock Claude API."""
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "temperature": 0.0,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        response = self.bedrock.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
    
    def _parse_response(self, response: str) -> Dict:
        """Parse Claude JSON response."""
        try:
            # Extract JSON from response (may have extra text)
            start = response.find('{')
            end = response.rfind('}') + 1
            json_str = response[start:end]
            
            extraction = json.loads(json_str)
            
            # Map labels to URIs
            for category in ['risks', 'mechanisms', 'impacts']:
                for item in extraction.get(category, []):
                    item['uri'] = self._label_to_uri(item['label'], category)
            
            return extraction
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Response: {response}")
            return {'risks': [], 'mechanisms': [], 'impacts': [], 'countries': []}
    
    def _label_to_uri(self, label: str, category: str) -> str:
        """Map label to URI using taxonomy."""
        taxonomy_key = category  # 'risks', 'mechanisms', 'impacts'
        
        for item in self.ontology_taxonomy.get(taxonomy_key, []):
            if item['label'].lower() == label.lower():
                return item['uri']
        
        # Fallback: construct URI from label
        uri_suffix = label.replace(' ', '').replace('-', '')
        return f"sg:{uri_suffix}"
    
    def _map_to_chunks(self, extraction: Dict, chunks_by_section: Dict) -> Dict:
        """Map each extraction to specific chunk URIs."""
        for category in ['risks', 'mechanisms', 'impacts']:
            for item in extraction.get(category, []):
                section = item.get('section', 'Description')
                evidence = item.get('evidence', '').lower()
                
                # Get chunks for this section
                section_chunks = chunks_by_section.get(section, [])
                
                # Find chunks containing evidence
                matching_chunks = [
                    c['uri'] for c in section_chunks
                    if evidence in c['text'].lower()
                ]
                
                # Use matching chunks or all section chunks
                item['chunk_uris'] = matching_chunks if matching_chunks else [c['uri'] for c in section_chunks]
        
        return extraction
