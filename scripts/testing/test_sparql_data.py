#!/usr/bin/env python3
"""
Test script to check what data is actually returned by SPARQL queries
"""
import sys
import os
sys.path.append('/Users/chris/climate-risk-rag-aws/lambda/search/src')

from utils.KnowledgeGraphManager import KnowledgeGraphManager

def test_sparql_data():
    """Test what data is returned by enhanced SPARQL queries"""
    
    kg_manager = KnowledgeGraphManager()
    
    # Test query to see what solutions have spatial data
    test_query = """
    PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>
    PREFIX sg: <http://solve.global/knowledge-commons/>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX gno: <http://www.geonames.org/ontology#>
    
    SELECT ?solution ?title ?spatial ?country_name ?riskType ?risk_label ?solutionType ?solution_label
    WHERE {
        ?solution a sgd:Solution ;
                  dcterms:title ?title .
        
        OPTIONAL { ?solution dcterms:spatial ?spatial }
        
        OPTIONAL {
          ?solution dcterms:spatial ?geo .
          FILTER(STRSTARTS(STR(?geo), "https://sws.geonames.org/"))
          GRAPH <http://www.geonames.org/ontology/data> {
            ?geo gno:name ?country_name
          }
        }
        
        OPTIONAL { 
          ?solution sg:riskType ?riskType .
          ?riskType rdfs:label ?risk_label 
        }
        
        OPTIONAL { 
          ?solution sg:solutionType ?solutionType .
          ?solutionType rdfs:label ?solution_label 
        }
    }
    LIMIT 5
    """
    
    print("Testing SPARQL query for enhanced data...")
    try:
        results = kg_manager.execute_sparql_query(test_query)
        print("Found " + str(len(results)) + " results")
        
        for i, result in enumerate(results):
            print("\nResult " + str(i+1) + ":")
            print("  Solution: " + str(result.get('solution', 'N/A')))
            print("  Title: " + str(result.get('title', 'N/A')))
            print("  Spatial: " + str(result.get('spatial', 'N/A')))
            print("  Country name: " + str(result.get('country_name', 'N/A')))
            print("  Risk type: " + str(result.get('riskType', 'N/A')))
            print("  Risk label: " + str(result.get('risk_label', 'N/A')))
            print("  Solution type: " + str(result.get('solutionType', 'N/A')))
            print("  Solution label: " + str(result.get('solution_label', 'N/A')))
            
    except Exception as e:
        print("Error executing query: " + str(e))

if __name__ == "__main__":
    test_sparql_data()
