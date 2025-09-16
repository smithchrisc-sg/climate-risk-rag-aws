# Updated filtering rules for named graph approach
default_rules = {
    # Geonames ontology schema - if we load the ontology definitions
    'http://www.geonames.org/ontology': {
        'http://www.w3.org/2000/01/rdf-schema#label',
        'http://www.w3.org/2000/01/rdf-schema#comment',
        'http://www.w3.org/2004/02/skos/core#prefLabel',
        'http://www.w3.org/2004/02/skos/core#altLabel',
    },
    
    # Geonames data - the actual place names for FTS
    'http://www.geonames.org/ontology/data': {
        'http://www.geonames.org/ontology#name',
        'http://www.geonames.org/ontology#alternateName',
        'http://www.geonames.org/ontology#officialName',
        'http://www.geonames.org/ontology#shortName'
    },
    
    # Climate risk ontology - labels and descriptions for concept lookup
    'http://climate-risk-ontology': {
        'http://www.w3.org/2000/01/rdf-schema#label',
        'http://www.w3.org/2000/01/rdf-schema#comment',
        'http://www.w3.org/2004/02/skos/core#prefLabel',
        'http://www.w3.org/2004/02/skos/core#altLabel',
        'http://www.w3.org/2004/02/skos/core#definition',
        'http://www.w3.org/2004/02/skos/core#note',
        'http://climate-risk-ontology#description'
    },
    
    # RDFS/SKOS core - standard semantic web predicates
    'http://www.w3.org/2000/01/rdf-schema': {
        'http://www.w3.org/2000/01/rdf-schema#label',
        'http://www.w3.org/2000/01/rdf-schema#comment'
    },
    
    'http://www.w3.org/2004/02/skos/core': {
        'http://www.w3.org/2004/02/skos/core#prefLabel',
        'http://www.w3.org/2004/02/skos/core#altLabel',
        'http://www.w3.org/2004/02/skos/core#definition',
        'http://www.w3.org/2004/02/skos/core#note'
    }
}
