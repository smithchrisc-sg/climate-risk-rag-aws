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

import time
from rdflib.util import from_n3
from rdflib.term import URIRef
import re

# Stream Json Field Literals
LABEL_STR = 'label'
ID_STR = 'id'
EVENT_ID_STR = 'eventId'
COMMIT_NUM_STR = 'commitNum'
OP_NUM_STR = 'opNum'
OPERATION_STR = 'op'
FROM_VERTEX_STR = 'from'
TO_VERTEX_STR = 'to'
PROPERTY_KEY_STR = 'key'
PROPERTY_VALUE_STR = 'value'
PROPERTY_VALUE_TYPE_STR = 'dataType'
TYPE_STR = 'type'
RECORDS_STR = 'records'
LAST_TXN_TIMESTAMP_STR = 'lastTrxTimestamp'
DATA_STR = 'data'
ELEMENTS_STR = 'elements'
ES_TYPE_STR = 'es_type'
LAST_EVENT_ID = 'lastEventId'
TOTAL_RECORDS = 'totalRecords'
STATEMENT_STR = 'stmt'
ADD_OPERATION = 'ADD'
REMOVE_OPERATION = 'REMOVE'

# Aggregator Literals
CURRENT_INDEX_STR = "currentIndex"
CURRENT_OP_STR = "currentOperation"
RECORDS_SET_STR = "recordsSet"

# Sparql Literals
SUBJECT = "subject"
PREDICATE = "predicate"
OBJECT = "object"
GRAPH = "graph"
LANGUAGE = "language"

# QUERY Language
GREMLIN = "gremlin"
PROPERTY_GRAPH = "propertygraph"
PROPERTY_GRAPH_ALIAS = "pg"
SPARQL = "sparql"

# Sparql Prefixes
_XSD_PFX = 'http://www.w3.org/2001/XMLSchema#'
_RDF_PFX = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'

RDF_TYPE = URIRef(_RDF_PFX + 'type')

# Gremlin Operations
ADD_VL = 'ADD_vl'
ADD_VP = 'ADD_vp'
ADD_E = 'ADD_e'
ADD_EP = 'ADD_ep'
REMOVE_VL = 'REMOVE_vl'
REMOVE_VP = 'REMOVE_vp'
REMOVE_E = 'REMOVE_e'
REMOVE_EP = 'REMOVE_ep'

# Handlers
NEPTUNE_TO_NEPTUNE_GREMLIN = 'neptune_to_neptune.neptune_to_neptune_gremlin_handler.NeptuneGremlinHandler'
NEPTUNE_TO_NEPTUNE_SPARQL = 'neptune_to_neptune.neptune_to_neptune_sparql_handler.NeptuneSparqlHandler'
NEPTUNE_TO_ES_GREMLIN = 'neptune_to_es.neptune_gremlin_es_handler.ElasticSearchGremlinHandler'
NEPTUNE_TO_ES_SPARQL = 'neptune_to_es.neptune_sparql_es_handler.ElasticSearchSparqlHandler'

def current_milli_time():

    """
    Returns current time in milliseconds rounded to integer
    :return: Current time in milliseconds
    """

    return int(round(time.time() * 1000))


def split_list(ref_list, chunk_size):

    """
    Split a given list to multiple sub-lists of given chunk size.

    :param ref_list: Reference list to be Split
    :param chunk_size: Size for sub-list
    :return: List of sub-lists
    """

    return [ref_list[i:i + chunk_size] for i in range(0, len(ref_list), chunk_size)]


def get_wait_time(max_wait_time, last_wait_time=0):

    """
    Returns time to wait in seconds using last wait time. Wait time is used to pause
    Stream polling in case no more records are present on Stream. New wait time is calculated using exponential factor.
    First time when no records are found on stream i.e. no last wait time, method returns 1 sec as wait time.
    If max_wait_time is zero, method returns 0 sec as wait time.

    :param max_wait_time:  Maximum waiting time(in seconds) between two Stream Polls
    :param last_wait_time: Waiting time(in seconds) between last two Stream Polls
    :return: Return time to wait before next Stream Poll
    """

    if max_wait_time == 0:
        return max_wait_time

    wait_time = 1
    if last_wait_time != 0:
        wait_time = 2 * last_wait_time if (2 * last_wait_time) < max_wait_time \
            else max_wait_time
    return wait_time

from rdflib.plugins.parsers.ntriples import W3CNTriplesParser
from rdflib.plugins.parsers.ntriples import ParseError
from rdflib.plugins.parsers.ntriples import r_tail
from rdflib.plugins.parsers.ntriples import r_wspace

class NeptuneNQuadsLineParser(W3CNTriplesParser):
    """
    This class reuses some of the methods in W3CNTriplesParser to
    parse a sparql statement in nquad format.
    
    Why not use NQuadsParser?
    The rdflib provide a NQuadsParser class meant to be used to parse nquads files.
    Unfortunately, the interface of that class doesn't lend itself well to single line 
    parsing. 

    """
    def parseline(self, stmt):
        self.line = stmt
        self.eat(r_wspace)
        if not self.line:
            return
        subject = self.subject()
        self.eat(r_wspace)
        predicate = self.predicate()
        self.eat(r_wspace)
        obj = self.object()
        self.eat(r_wspace)
        graph = self.uriref() or self.nodeid()
        self.eat(r_tail)
        if self.line:
            raise ParseError("Trailing garbage: %s" % self.line)
        record = {
            SUBJECT: subject,
            PREDICATE: predicate,
            OBJECT: obj
        }
        if graph:
            record[GRAPH] = graph
        return record

def parse_sparql_statement(record_data):

    """
    Parse Sparql Statement from Stream Record Data to RDF term. This method return a
    Dict object with subject, predicate, object, graph as keys and corresponding RDF terms as values.

    :param record_data:  Stream Record Data
    :return: Return a Dictionary Object with subject, predicate, object, graph as keys
    """
    record_statement = record_data[STATEMENT_STR].strip()
    parser = NeptuneNQuadsLineParser()
    return parser.parseline(record_statement)
