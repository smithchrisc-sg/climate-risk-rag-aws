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


from botocore.exceptions import ClientError
import logging
from commons import current_milli_time
from config_provider import config_provider

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(config_provider.logging_level)


class DDBLeaseManager(object):

    """
    Manages lease needed to start Poller Worker for Stream.

    A Lease stores information about worker currently reading data from Stream and
    also keep track of the records that have already been processed from Stream using Checkpoint.
    A worker needs to take lease at beginning of the process and needs to evict lease at the
    end of process or system failure. Two simultaneous workers can not take lease for Same Application
    which is guaranteed by Conditional Check on Lease Owner.
    Currently, Lease Information is stored in Dynamo DB Table which makes it simpler to manage taking lease, evicting
    lease and updating lease process through Dynamo DB Conditional Check.

    Note: Neptune stream is single sharded and will be consumed by single worker.
    """

    def __init__(self, lease_table):
        self.table = lease_table

    def create_lease_if_not_exists(self, item_dict=None):

        """
        Creates a new lease. Conditional on a lease not already existing.
        """

        try:
            self.table.put_item(Item=item_dict,
                                ConditionExpression='attribute_not_exists(leaseKey)')
            logger.debug("Successfully Created Lease Entry - {}".format(str(item_dict)))
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') != 'ConditionalCheckFailedException':
                logger.error("Failed to put item in to {0} : error{1}".format(self.table, e))
                raise

    def get_lease(self, lease_key):

        """
        Returns lease for a given key.
        """

        try:
            response = self.table.get_item(Key={'leaseKey': lease_key}, ConsistentRead=True)
            return response['Item']
        except Exception as e:
            logger.error('{0} failed query items , error{1}'.format(self.table, e))
            return None

    def take_lease(self, item_dict=None):

        """
        Take a lease for the given owner update its owner field. Conditional on
        the leaseOwner is nobody in DynamoDB. Mutates the  owner of the
        passed-in lease object after updating DynamoDB.
        """

        try:
            response = self.table.update_item(
                Key={'leaseKey': item_dict['leaseKey']},
                UpdateExpression="SET leaseOwner = :leaseOwnerVal," +
                                 " lastUpdateTime= :lastUpdateTimeVal",
                ConditionExpression="leaseOwner = :NOBODY",
                ExpressionAttributeValues={':leaseOwnerVal': item_dict['leaseOwner'],
                                           ':lastUpdateTimeVal': current_milli_time(),
                                           ':NOBODY': 'nobody'
                                           },
                ReturnValues="ALL_NEW")
            logger.debug("Successfully Taken Lease for leaseKey - {}, leaseOwner - {}. Lease - {}"
                         .format(str(item_dict['leaseKey']), str(item_dict['leaseOwner']), str(response["Attributes"])))
            return response["Attributes"]
        except ClientError as e:
            if e.response['Error']['Code'] == "ConditionalCheckFailedException":
                logger.error(e.response['Error']['Message'])
            else:
                raise

    def update_lease(self, item_dict=None):

        """
        Update a lease by updating Checkpoint for Lease. Conditional on
        the leaseOwner same as Lease owner at the time of taking lease in DynamoDB .

        Checkpoint is the last processed event (Neptune Stream Checkpoint is consist of
        checkpoint and checkpointSubSequenceNumber)
        """

        try:
            response = self.table.update_item(
                Key={'leaseKey': item_dict['leaseKey']},
                UpdateExpression="SET checkpoint = :checkpointVal," +
                                 " checkpointSubSequenceNumber = :checkpointSubSequenceNumberVal," +
                                 " lastUpdateTime= :lastUpdateTimeVal",
                ConditionExpression="leaseOwner = :leaseOwnerVal ",
                ExpressionAttributeValues={':leaseOwnerVal': item_dict['leaseOwner'],
                                           ':checkpointVal': item_dict['checkpoint'],
                                           ':checkpointSubSequenceNumberVal': item_dict['checkpointSubSequenceNumber'],
                                           ':lastUpdateTimeVal': current_milli_time()
                                           },
                ReturnValues="ALL_NEW")
            logger.debug("Successfully Updated Lease - {}".format(str(response["Attributes"])))
            return response["Attributes"]
        except ClientError as e:
            if e.response['Error']['Code'] == "ConditionalCheckFailedException":
                logger.error(e.response['Error']['Message'])
            else:
                raise

    def evict_lease(self, item_dict=None):

        """
        Evict the current owner of lease by setting owner to nobody. Conditional on the owner in DynamoDB matching
        the owner of the input. Mutates the owner of the passed-in lease object after updating
        the record in DynamoDB.
        """

        try:
            response = self.table.update_item(
                Key={'leaseKey': item_dict['leaseKey']},
                UpdateExpression="SET leaseOwner = :NOBODY," +
                                 " lastUpdateTime= :lastUpdateTimeVal",
                ConditionExpression="leaseOwner = :leaseOwnerVal",
                ExpressionAttributeValues={':lastUpdateTimeVal': current_milli_time(),
                                           ':NOBODY': 'nobody',
                                           ':leaseOwnerVal': item_dict['leaseOwner']
                                           },
                ReturnValues="ALL_NEW")
            logger.debug("Successfully Evicted Lease - {}".format(str(response["Attributes"])))
            return response["Attributes"]
        except ClientError as e:
            if e.response['Error']['Code'] == "ConditionalCheckFailedException":
                logger.error(e.response['Error']['Message'])
            else:
                raise

    def delete_all_items_in_lease_table(self):

        """
        Delete all lease items in dynamo db table
        """

        response = self.table.scan()
        items = response['Items']
        number_of_items = len(items)
        if number_of_items == 0:  # no items to delete
            return

        for item in items:
            self.table.delete_item(Key={'leaseKey': item['leaseKey']})
