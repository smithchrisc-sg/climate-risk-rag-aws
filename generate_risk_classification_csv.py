#!/usr/bin/env python3
"""
Generate CSV for manual risk concept classification.
Shows current taxonomy hierarchy + irrelevant concepts to classify.
"""

import sys
import re
import csv
from collections import defaultdict
from boto3 import Session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests

NEPTUNE_ENDPOINT = "https://solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182/sparql"
REGION = "us-east-1"

def run_query(query):
    """Execute SPARQL query against Neptune."""
    session = Session()
    creds = session.get_credentials().get_frozen_credentials()
    
    r = AWSRequest(method="POST", url=NEPTUNE_ENDPOINT, data={"query": query})
    SigV4Auth(creds, "neptune-db", REGION).add_auth(r)
    
    resp = requests.post(NEPTUNE_ENDPOINT, headers=dict(r.headers.items()), data={"query": query})
    
    if resp.status_code != 200:
        raise Exception(f"SPARQL query failed: {resp.text}")
    
    return resp.json().get('results', {}).get('bindings', [])

def get_risk_taxonomy():
    """Get current risk taxonomy hierarchy from Neptune."""
    query = """
    PREFIX sg: <http://solve.global/knowledge-commons/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?child ?parent ?label
    WHERE {
      ?child rdfs:subClassOf ?parent .
      ?child rdfs:label ?label .
      FILTER(STRSTARTS(STR(?child), "http://solve.global/knowledge-commons/"))
      FILTER(STRSTARTS(STR(?parent), "http://solve.global/knowledge-commons/"))
      FILTER(CONTAINS(STR(?child), "Risk"))
    }
    ORDER BY ?parent ?child
    """
    
    results = run_query(query)
    
    # Build hierarchy
    children = defaultdict(list)
    labels = {}
    
    for row in results:
        child = row['child']['value'].split('/')[-1]
        parent = row['parent']['value'].split('/')[-1]
        label = row['label']['value']
        
        children[parent].append(child)
        labels[child] = label
    
    return children, labels

def get_unclassified_risks():
    """Get risk concepts used in solutions but not in taxonomy hierarchy."""
    query = """
    PREFIX sg: <http://solve.global/knowledge-commons/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT DISTINCT ?risk
    WHERE {
      # Risks that are used in solutions
      ?solution sg:addressesRisk ?risk .
      FILTER(STRSTARTS(STR(?risk), "http://solve.global/knowledge-commons/"))
      
      # But are NOT in the taxonomy (no subClassOf relationship)
      FILTER NOT EXISTS {
        ?risk rdfs:subClassOf+ sg:Risk .
      }
    }
    ORDER BY ?risk
    """
    
    results = run_query(query)
    
    risks = []
    for row in results:
        risk = row['risk']['value'].split('/')[-1]
        risks.append(risk)
    
    return risks

def get_usage_counts(concepts):
    """Get usage count for each concept."""
    filter_list = ', '.join([f'sg:{c}' for c in concepts])
    
    query = f"""
    PREFIX sg: <http://solve.global/knowledge-commons/>
    
    SELECT ?risk (COUNT(DISTINCT ?solution) AS ?count)
    WHERE {{
      ?solution sg:addressesRisk ?risk .
      FILTER(?risk IN ({filter_list}))
    }}
    GROUP BY ?risk
    ORDER BY DESC(?count)
    """
    
    results = run_query(query)
    
    counts = {}
    for row in results:
        concept = row['risk']['value'].split('/')[-1]
        counts[concept] = int(row['count']['value'])
    
    return counts

def build_hierarchy_rows(children, labels, parent='Risk', level=0, max_level=8):
    """Recursively build hierarchy rows."""
    rows = []
    
    if parent not in children:
        return rows
    
    for child in sorted(children[parent]):
        row = [''] * max_level
        row[level] = child
        rows.append(row)
        
        # Recurse for children
        child_rows = build_hierarchy_rows(children, labels, child, level + 1, max_level)
        rows.extend(child_rows)
    
    return rows

def main():
    output_file = "risk_classification_worksheet.csv"
    
    print("🔍 Fetching current risk taxonomy from Neptune...")
    children, labels = get_risk_taxonomy()
    
    print("📋 Finding unclassified risk concepts...")
    irrelevant = get_unclassified_risks()
    
    print("📊 Getting usage counts...")
    counts = get_usage_counts(irrelevant)
    
    print(f"✍️  Writing CSV to {output_file}...")
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow(['Level 1', 'Level 2', 'Level 3', 'Level 4', 'Level 5', 'Level 6', 'Level 7', 'Level 8', 'Action', 'Usage Count', 'Notes'])
        writer.writerow(['', '', '', '', '', '', '', '', '', '', ''])
        
        # Instructions
        writer.writerow(['=== INSTRUCTIONS ===', '', '', '', '', '', '', '', '', '', ''])
        writer.writerow(['1. Current taxonomy shown below', '', '', '', '', '', '', '', '', '', ''])
        writer.writerow(['2. Irrelevant concepts listed at bottom', '', '', '', '', '', '', '', '', '', ''])
        writer.writerow(['3. Move irrelevant concepts to correct position in hierarchy', '', '', '', '', '', '', '', '', '', ''])
        writer.writerow(['4. Use Action column:', '', '', '', '', '', '', '', '', '', ''])
        writer.writerow(['   - EQUIV→TargetConcept (remap to existing)', '', '', '', '', '', '', '', '', '', ''])
        writer.writerow(['   - ADD (add as new subclass)', '', '', '', '', '', '', '', '', '', ''])
        writer.writerow(['   - DELETE (truly irrelevant)', '', '', '', '', '', '', '', '', '', ''])
        writer.writerow(['', '', '', '', '', '', '', '', '', '', ''])
        
        # Current taxonomy
        writer.writerow(['=== CURRENT RISK TAXONOMY ===', '', '', '', '', '', '', '', '', '', ''])
        writer.writerow(['Risk', '', '', '', '', '', '', '', 'EXISTING', '', 'Top-level risk class'])
        
        hierarchy_rows = build_hierarchy_rows(children, labels)
        for row in hierarchy_rows:
            row.extend(['EXISTING', '', ''])
            writer.writerow(row)
        
        writer.writerow(['', '', '', '', '', '', '', '', '', '', ''])
        writer.writerow(['=== IRRELEVANT CONCEPTS TO CLASSIFY ===', '', '', '', '', '', '', '', '', '', ''])
        writer.writerow(['(Move these to correct position above)', '', '', '', '', '', '', '', '', '', ''])
        writer.writerow(['', '', '', '', '', '', '', '', '', '', ''])
        
        # Irrelevant concepts
        for concept in irrelevant:
            count = counts.get(concept, 0)
            writer.writerow([concept, '', '', '', '', '', '', '', 'TODO', count, 'Move to correct position or mark action'])
    
    print(f"✅ Done! Edit {output_file} and classify concepts.")
    print(f"   Total irrelevant concepts: {len(irrelevant)}")
    print(f"   Current taxonomy concepts: {len(labels)}")

if __name__ == '__main__':
    main()
