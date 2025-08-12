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


from __future__ import print_function  # Python 2/3 compatibility

import logging
import boto3
import sys
import time
import _thread

from config_provider import config_provider
from commons import *
from stream_records_processor import StreamRecordsProcessor
from metrics_publisher import MetricsPublisher
from ddb_helper import DDBLeaseManager
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Event

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(config_provider.logging_level)

# global variables
metrics_publisher_client = MetricsPublisher()
stream_records_processor = StreamRecordsProcessor()
dynamodb = boto3.resource('dynamodb', region_name=config_provider.region)
lease_manager = DDBLeaseManager(dynamodb.Table(config_provider.lease_table_name))

WAITING_TIME = 60000

def get_or_create_lease():

    """
    Get or create Lease in Lease Table.
    :return: Lease Object from Dynamo DB Table
    """
    starting_checkpoint = config_provider.starting_checkpoint.split(':')
    
    lease_manager.create_lease_if_not_exists(
        {
            'leaseKey': config_provider.application_name,
            'checkpointSubSequenceNumber': starting_checkpoint[1],
            'checkpoint': starting_checkpoint[0],
            'leaseOwner': 'nobody',
            'lastUpdateTime': current_milli_time()
        }
    )

    return lease_manager.get_lease(config_provider.application_name)

def fetch_stream_records(query_queue, lease, execution_end_time, event):
    # Fetch from lease table
    checkpoint = lease['checkpoint']
    checkpoint_sub_sequence_number = lease['checkpointSubSequenceNumber']
    wait_time = 0

    try:
         while current_milli_time() < execution_end_time:
            # Stop execution of fetch_stream_records() thread when parent default_handler_replication() thread is stopped
            if event.is_set():
                return
            results = stream_records_processor.fetch_stream_records(config_provider.stream_records_batch_size,
                                checkpoint, checkpoint_sub_sequence_number, query_queue)

            if results is None:
                # No records in Stream
                logger.info("No more stream records to process.")
                # Wait exponentially till max polling wait time
                wait_time = get_wait_time(config_provider.max_polling_wait_time, wait_time)
                time.sleep(wait_time)
            else:
                # When Stream records are processed in small chunks by handler, handle_records method returns
                # series of results one-by-one on Demand using Python Generators.
                # Each iteration will compute result object lazily which can further be used to update checkpoint.
                for result in results:
                    checkpoint_sub_sequence_number = result.last_op_num
                    checkpoint = result.last_commit_num
                    logger.info("Last read event ({}, {})".format(checkpoint, checkpoint_sub_sequence_number))
                wait_time = 0

    except Exception as e:
        logger.error("Error Occurred while processing records - {}.".format(str(e)))
        # Interrupt main writer thread if poller thread gets an exception
        _thread.interrupt_main()
        raise e

def default_handler_replication(lease, wait_time, execution_end_time):
    waiting_end_time = current_milli_time() + WAITING_TIME
    try:
        query_queue = Queue(maxsize = 0)
        executor = ThreadPoolExecutor(1)
        event = Event()
        executor.submit(fetch_stream_records, query_queue, lease, execution_end_time, event)
        while current_milli_time() < execution_end_time:
            # case when no more records are present in query_queue from stream records
            if not stream_records_processor.write_with_metrics(query_queue, lease, lease_manager, metrics_publisher_client):
                logger.info("No more stream records to write.")
                wait_time = get_wait_time(config_provider.max_polling_wait_time, wait_time)
                # wait_time can be zero when set to do continuous polling. For continuous polling no need to wait.
                if wait_time > 0:
                    if current_milli_time() > waiting_end_time:
                        logger.info("Waiting for {} seconds before next Polling.".format(str(wait_time)))
                        # stop execution of fetch_stream_records() thread
                        event.set()
                        break
                    else:
                        time.sleep(wait_time)
            else:
                # case when there are more batch queries present in query_queue from stream records. No need to wait.
                wait_time = 0

    except Exception as e:
        logger.error("Error Occurred while processing records - {}.".format(str(e)))
        raise e
    finally:
        logger.info("Evicting lease - {}".format(str(lease)))
        lease_manager.evict_lease(lease)

def custom_handler_replication(lease, wait_time, execution_end_time):
    try:
        while current_milli_time() < execution_end_time:
            # case when no more records are present in stream
            if not stream_records_processor.process_with_metrics(lease, lease_manager, metrics_publisher_client):
                wait_time = get_wait_time(config_provider.max_polling_wait_time, wait_time)
                # wait_time can be zero when set to do continuous polling. For continuous polling no need to wait.
                if wait_time > 0:
                    logger.info("Waiting for {} seconds before next Polling.".format(str(wait_time)))
                    break
            else:
                # case when there are more records present in stream. No need to wait.
                wait_time = 0

    except Exception as e:
        logger.error("Error Occurred while processing records - {}.".format(str(e)))
        raise e
    finally:
        logger.info("Evicting lease - {}".format(str(lease)))
        lease_manager.evict_lease(lease)

def lambda_handler(event, context):

    """
    Main Lambda handler
    This is invoked when Lambda is called.
    This lambda function do below steps sequentially:
    1. Take Lease
    2. Poll for records from Stream until no records or 90% of Lambda Execution time is reached
    3. Stream records are passed to appropriate handlers. If no records are found lambda exists &
     pass wait_time to state machine
    4. Metrics are published to Cloud watch
    """

    lease = get_or_create_lease()
    lease['leaseOwner'] = config_provider.application_name
    logger.info("Taking lease for {} ....".format(lease['leaseOwner']))
    lease = lease_manager.take_lease(lease)

    # Time to stop Continuous polling from Stream if not otherwise stopped
    execution_end_time = current_milli_time() + int(round(0.9 * config_provider.max_polling_interval * 1000))
    wait_time = event['iterator']['wait_time']
    handler_name = config_provider.stream_records_handler_name
    sys.setrecursionlimit(5000) # Increase recursion limit for calling dfs

    # Default handler will use the updated logic for polling and writing in different threads
    if handler_name in [NEPTUNE_TO_NEPTUNE_GREMLIN, NEPTUNE_TO_NEPTUNE_SPARQL, NEPTUNE_TO_ES_GREMLIN, NEPTUNE_TO_ES_SPARQL]:
        default_handler_replication(lease, wait_time, execution_end_time)
    else:
        custom_handler_replication(lease, wait_time, execution_end_time)

    index = event['iterator']['index'] + 1
    response = {
        'index': index,
        'continue': index < event['iterator']['count'],
        'count': event['iterator']['count'],
        'wait_time': wait_time
    }

    logger.info("Finished running Lambda function handler. Passing Response to next step - {}".format(response))
    return response