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


class HandlerResponse:

    """
    Model for Storing Handler Response.

    This Class has three attributes:
    last_op_num - Op_num for last stream record processed
    last_commit_num - Commit number for last stream record processed
    records_processed - Number of Stream Records Processed
    last_transaction_time_stamp - Time stamp of last transaction (Optional parameter)
    """

    def __init__(self, last_op_num, last_commit_num, records_processed, last_transaction_time_stamp=0):
        self.last_op_num = last_op_num
        self.last_commit_num = last_commit_num
        self.records_processed = records_processed
        self.last_transaction_time_stamp = last_transaction_time_stamp

@six.add_metaclass(abc.ABCMeta)
class AbstractHandler:

    """
    Abstract class for  Handler
    """

    @abc.abstractmethod
    def handle_records(self, stream_log):

        """
        Abstract Method for Processing Stream Records. This method should return a Python Generator Object
        wrapped around HandlerResponse using Python yield statement { yield HandlerResponse(......) }

        :param stream_log:
        :return: Returns Python Generator object wrapped around HandlerResponse using yield statement
        """
        pass