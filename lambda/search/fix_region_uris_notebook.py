# Jupyter notebook cell to fix region member URIs in Neptune
# Run this in your notebook environment

import json, os, requests
from botocore.session import Session
from botocore.awsrequest import AWSRequest
from botocore.auth import SigV4Auth

region = "us-east-1"
host   = "solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
endpoint = f"https://{host}:8182/sparql"

session = Session()
creds = session.get_credentials().get_frozen_credentials()

# First, check current state
check_query = """
PREFIX sg: <http://solve.global/knowledge-commons/>

SELECT ?region ?member WHERE {
  ?region sg:hasMember ?member .
}
ORDER BY ?region
"""

print("CURRENT STATE:")
print("=" * 60)
r = AWSRequest(method="POST", url=endpoint, data={"query": check_query})
SigV4Auth(creds, "neptune-db", region).add_auth(r)
resp = requests.post(endpoint, headers=dict(r.headers.items()), data={"query": check_query})

if resp.status_code == 200:
    results = resp.json()
    bindings = results.get('results', {}).get('bindings', [])
    print(f"Found {len(bindings)} region member relationships")
    for b in bindings[:5]:
        print(f"  {b['region']['value']} -> {b['member']['value']}")
    if len(bindings) > 5:
        print(f"  ... and {len(bindings) - 5} more")
else:
    print(f"Error: {resp.text}")

print("\n" + "=" * 60)
print("FIXING URIs...")
print("=" * 60)

# Fix the URIs
update_query = """
PREFIX sg: <http://solve.global/knowledge-commons/>

DELETE {
  ?region sg:hasMember ?oldCountry .
}
INSERT {
  ?region sg:hasMember ?newCountry .
}
WHERE {
  ?region sg:hasMember ?oldCountry .
  FILTER(STRSTARTS(STR(?oldCountry), "http://www.geonames.org/ontology#"))
  
  # Extract the ID and construct correct URI
  BIND(STRAFTER(STR(?oldCountry), "http://www.geonames.org/ontology#") AS ?id)
  BIND(IRI(CONCAT("https://sws.geonames.org/", ?id, "/")) AS ?newCountry)
}
"""

r2 = AWSRequest(method="POST", url=endpoint, data={"update": update_query})
SigV4Auth(creds, "neptune-db", region).add_auth(r2)
resp2 = requests.post(endpoint, headers=dict(r2.headers.items()), data={"update": update_query})

print(f"Update Status: {resp2.status_code}")
if resp2.status_code == 200:
    print("✅ URIs updated successfully")
else:
    print(f"❌ Error: {resp2.text}")

print("\n" + "=" * 60)
print("VERIFICATION:")
print("=" * 60)

# Verify the fix
r3 = AWSRequest(method="POST", url=endpoint, data={"query": check_query})
SigV4Auth(creds, "neptune-db", region).add_auth(r3)
resp3 = requests.post(endpoint, headers=dict(r3.headers.items()), data={"query": check_query})

if resp3.status_code == 200:
    results3 = resp3.json()
    bindings3 = results3.get('results', {}).get('bindings', [])
    print(f"After fix: {len(bindings3)} region member relationships")
    
    old_format = 0
    new_format = 0
    for b in bindings3:
        member_uri = b['member']['value']
        if member_uri.startswith("http://www.geonames.org/ontology#"):
            old_format += 1
        elif member_uri.startswith("https://sws.geonames.org/"):
            new_format += 1
    
    print(f"  Old format (http://www.geonames.org/ontology#): {old_format}")
    print(f"  New format (https://sws.geonames.org/): {new_format}")
    
    if old_format == 0:
        print("✅ All URIs successfully updated!")
    else:
        print(f"⚠️  Still have {old_format} URIs in old format")
    
    # Show sample
    print("\nSample after fix:")
    for b in bindings3[:3]:
        print(f"  {b['region']['value']} -> {b['member']['value']}")
else:
    print(f"Error: {resp3.text}")
