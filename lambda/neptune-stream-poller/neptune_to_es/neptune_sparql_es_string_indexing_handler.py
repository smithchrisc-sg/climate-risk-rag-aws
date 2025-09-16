#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2019 Amazon.com, Inc. or its affiliates.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#    http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file.
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.


from rdflib.term import BNode, Literal
from neptune_to_es.es_helper import *
from commons import parse_sparql_statement
from neptune_to_es.neptune_sparql_es_handler import ElasticSearchSparqlHandler
from config_provider import config_provider
from ontology_filter import get_ontology_filter

ENABLE_NON_STRING_INDEXING = config_provider.get_handler_additional_param('EnableNonStringIndexing') == 'true'

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(config_provider.logging_level)


def get_datatype_token(object_type):

    """
    Parse clean type string from datatype URI in format namespace#datatype.
    If no datatype can be retrieved then default to string datatype
    Ex. "<http://www.w3.org/2001/XMLSchema#integer>” -> "integer"

    :param object_type: Full datatype URI string from stream record object
    :return: Datatype string value
    """

    type = re.search(r"(?<=http://www.w3.org/2001/XMLSchema#)[^<]+", object_type)

    return type[0] if type else DataType.STRING.value


class ElasticSearchStringOnlySparqlHandler(ElasticSearchSparqlHandler):
    """
    Replicates Stream Records to a target Elastic Search Service.
    Stream Records are converted to appropriate Elastic Search documents and updated in
    Elastic Search Service using Bulk API. To minimize update requests sent to Elastic Search, this class sends
    a single update request for a bundle of Stream records.

    Note: This class will replicate only String data and non-string data would be dropped.

    This Class uses single index (amazon_neptune index) to store Sparql data. Elastic Search index stores
    Triples/ Quad data as object based document with all possible pairs of predicate & object for same
    Subject in a single document. Document id for Elastic Search document is created using md5 of (Subject) value
    from Sparql Statement.

    Object value corresponding to a predicate is Stored as a nested object in Elastic Search.
    Sample:
    {
        "value" : "propValue1",         // Value of Property
        "datatype" : ":propDatatypeURI",   // DataType URI corresponding to Neptune DB. Not present for String Literals
        "graph" : ":namedGraphURI", // Named Graph URI value. Present only if Predicate-Object pair belongs to a Named Graph.
        "language" : "en"  // Present only for rdf:langString
    }

    Below is the sample representations of Sparql Document.

    {
        "_index": "amazon_neptune",
        "_id": "723c31fc529b23952d1f21b165a8f437",
        "_version": 2,
        "_score": 1,
        "_source": {
            "entity_id" : ":subjectURI",
            "entity_type" : [ ":type1", ":type2"],  // Object value corresponding to :rdfType Predicate of Subject
            "document_type" : "rdf-resource",
            "predicates" : {
                ":fooPredicate" : [
                    {
                      "value" : "value1"
                    },
                    {
                      "value" : "value2",
                      "graph" : ":namedGraph1"      // Predicate-Object Pair belongs to a Named Graph(:namedGraph1)
                    }
                ],
                ":barProperty" : [
                    {
                      "value" : "value3",
                      "language" : "en"         //object is LangString Literal -> "value3"@en
                    }
                ]
            }
        }
    }

    """

    def __init__(self):
        super().__init__()

    def get_query_operation(self, record):
        return record[OPERATION_STR]

    def generate_es_field_value(self, record_data):

        """
        Generates Elastic Search document field Nested value from Stream Record data.

        :param record_data: Stream Record data
        :return: Elastic Search Document field value
        """

        statement_elements = record_data[ELEMENTS_STR]

        # For rdf:type Predicate directly return value instead of dictionary
        if statement_elements[PREDICATE].eq(RDF_TYPE):
            return str(statement_elements[OBJECT])

        value = {
            "value": str(statement_elements[OBJECT].value)
        }

        # Appending Graph information in case of Named Graph
        if GRAPH in statement_elements:
            value[GRAPH] = str(statement_elements[GRAPH])

        # Appending Language information in case of rdf:langString Literal
        if statement_elements[OBJECT].language:
            value[LANGUAGE] = str(statement_elements[OBJECT].language)

        return value

    def filter_records(self, records, client):

        """
        Filters records to be stored in Elastic Search.
        Enhanced with ontology positive filtering for cost optimization and precision.
        
        For Sparql Language, Stream Records are filtered out if:
        1) Subject is a Blank Node
        2) Object is not a String Literal(xsd:string, rdf:langString) for predicates other than rdf:type


        :param client: ElasticSearch client
        :param records: Stream records list
        :return: Filtered records list
        """

        # ONTOLOGY POSITIVE FILTERING - Apply first for maximum efficiency
        ontology_filter = get_ontology_filter()
        if ontology_filter.filtering_enabled:
            original_count = len(records)
            records = ontology_filter.filter_records(records)
            logger.info(f"Ontology positive filtering: {original_count} → {len(records)} records")
            
            # If no records remain after ontology filtering, return early
            if not records:
                logger.info("No records remaining after ontology positive filtering")
                return []

        # Valid String datatypes as URI
        langStringURI = URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#langString')
        stringURI = URIRef('http://www.w3.org/2001/XMLSchema#string')

        for record in records:
            record_data = record[DATA_STR]
            statement_elements = parse_sparql_statement(record_data)
            # Storing parsed SPARQL statement in-memory for further usage
            record_data[ELEMENTS_STR] = statement_elements
            if isinstance(statement_elements[SUBJECT], BNode):
                # case 1) Subject is a Blank Node
                logger.debug("Dropping Record : Rdf Resource is represented by Blank Node for record {}"
                             .format(str(record_data)))
            elif statement_elements[PREDICATE].neq(RDF_TYPE) and (not isinstance(statement_elements[OBJECT], Literal) or statement_elements[OBJECT].datatype):
                # case 2) Object is not a String Literal(xsd:string, rdf:langString) for predicates other than rdf:type
                if (statement_elements[OBJECT].datatype and (not (statement_elements[OBJECT].datatype.eq(stringURI)
                                                             or statement_elements[OBJECT].datatype.eq(langStringURI)))):
                    logger.debug("Dropping Record : Rdf Object value is not a String Literal for record {}"
                             .format(str(record_data)))
                # No Datatype or datatype is xsd:string or rdf:langString
                else:
                    yield record
            else:
                yield record