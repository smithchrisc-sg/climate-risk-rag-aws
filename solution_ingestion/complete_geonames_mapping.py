#!/usr/bin/env python3

# Complete GeoNames mapping for unmapped countries
ADDITIONAL_MAPPINGS = {
    "Laos PDR": "gn:1655842",
    "People's Republic of China": "gn:1814991", 
    "Republic of Fiji": "gn:2205218",
    "Republic of Korea (South Korea)": "gn:1835841",
    "Republic of the Philippines": "gn:1694008",
    "Chinese Taipei": "gn:1668284",  # Taiwan
    "Aotearoa New Zealand": "gn:2186224",
    "Chinese Hong Kong": "gn:1819730",
    "Brunei Darussalam": "gn:1820814",
    "Japan": "gn:1861060",
    "Kingdom of Cambodia": "gn:1831722",
    "Maldives": "gn:1282028",
    "Republic of Maldives": "gn:1282028",
    "Belize": "gn:3582678",
    "Vietnam": "gn:1562822",
    "Viet Nam": "gn:1562822",
    "Cambodia": "gn:1831722",
    "Indonesia": "gn:1643084",
    "Philippines": "gn:1694008",
    "Singapore": "gn:1880251",
    "Lao PDR": "gn:1655842",
    "Lao People's Democratic Republic": "gn:1655842",
    "China (Hong Kong Special Administrative Region)": "gn:1819730",
    "People's Republic of China (PRC)": "gn:1814991",
    "Pakistan (Punjab Province)": "gn:1168579",  # Punjab Province
    "Taiwan": "gn:1668284",
    "Taiwan (Republic of China, R.O.C.)": "gn:1668284",
    "Republic of Korea": "gn:1835841",
    "Australia (Victoria)": "gn:2145234",  # Victoria state
    "Australia (State of Queensland)": "gn:2152274",
    "Australia (State of New South Wales)": "gn:2155400",
    "Nepal": "gn:1282988",
    "Bangladesh": "gn:1210997"
}

def update_geography_file():
    with open('geography_entities.ttl', 'r') as f:
        content = f.read()
    
    for country, geonames_uri in ADDITIONAL_MAPPINGS.items():
        # Replace NEEDS MAPPING with actual URI
        old_text = country + " -> NEEDS MAPPING"
        new_text = country + " -> " + geonames_uri
        content = content.replace(old_text, new_text)
    
    with open('geography_entities.ttl', 'w') as f:
        f.write(content)
    
    print("Updated " + str(len(ADDITIONAL_MAPPINGS)) + " country mappings")

if __name__ == "__main__":
    update_geography_file()
