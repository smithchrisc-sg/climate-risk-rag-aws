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

import abc
import six
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@six.add_metaclass(abc.ABCMeta)
class Aggregator:

    """
    Abstract class for Aggregator. Aggregation of records can help in optimizing number of requests sent
    to downstream systems. Changes from Aggregated records bundle can be inferred as one unit and
    thus can be sent to downstream system through single request.
    """
    @abc.abstractmethod
    def aggregate_records(self, records):
        pass
