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
import boto3, traceback, logging
from botocore.client import Config
from config_provider import config_provider


# Global Instances
config = Config(connect_timeout=5, retries={'max_attempts': 3})
cloudwatch_client = boto3.client('cloudwatch', region_name=config_provider.region, config=config)
logger = logging.getLogger(__name__)
logger.setLevel(config_provider.logging_level)

class MetricsPublisher:

    """
    Generate and publish Cloud Watch metrics for Neptune Stream Poller.
    Metrics are data about the performance of systems which in turn help in detailed monitoring.
    For Stream Poller, system is publishing data for two key metrics:

    Number of Records Processed - This metric capture how many records from Neptune Stream are
                                  successfully processed per unit of time. This Metric can
                                  be used to analyse Throughput.
    Lag Time for Stream Poller - This metric capture by how many milliseconds Stream poller is lagging  behind
                                 the latest commit on Neptune Source Instance.

    Both the Metrics are Published to AWS Cloud Watch using Metrics Publisher Class.
    """

    def __init__(self):
        self.nameSpace = 'AWS/Neptune'

    def __generate_metrics__(self, metric_name, dimension_name, dimension_value, unit, value):

        """
        Generates metrics json object which will be used to publish metrics

        :param metric_name: Name of Cloud watch Metrics
        :param dimension_name:  Dimension  name associated with cloud watch metrics
        :param dimension_value: Dimension value associated with cloud watch metrics
        :param unit: Unit of data published to cloud watch
        :param value:  Value of data published to cloud watch
        :return: Json object to create Metrics
        """

        return {
                 'MetricName': metric_name,
                 'Dimensions': [
                     {
                         'Name': dimension_name,
                         'Value': dimension_value
                     },
                 ],
                 'Unit': unit,
                 'Value': value
        }

    def publish_metrics(self, metrics):

        """
        Publishes Metrics on cloudwatch using cloudwatch client.

        :param metrics: Lists of Metrics to be published
        """
        try:
            cloudwatch_client.put_metric_data(MetricData=metrics, Namespace=self.nameSpace)
        except Exception as e:
            # Logs the error appropriately.
            logger.error(traceback.format_exc())
            logger.error(f"Error occurred while publishing metrics {metrics} in namespace {self.nameSpace}")


    def generate_record_processed_metrics(self, count):

        """
        Generates metrics for number of records processed by stream
        :param count: Count of number of records processed
        :return: Cloud watch Metrics object
        """

        return self.__generate_metrics__(str(config_provider.application_name) + ' - Stream Records Processed',
                                         'Neptune Stream', config_provider.neptune_stream_endpoint, 'Count', int(count))

    def generate_stream_lag_metrics(self, time_in_millis):

        """
        Generates metrics for lag time of stream poller
        :param time_in_millis: Lag time in Milliseconds
        :return: Cloud watch Metrics object
        """
        return self.__generate_metrics__(str(config_provider.application_name) + ' - Stream Lag from Neptune DB',
                                         'Neptune Stream', config_provider.neptune_stream_endpoint, 'Milliseconds',
                                         time_in_millis)
