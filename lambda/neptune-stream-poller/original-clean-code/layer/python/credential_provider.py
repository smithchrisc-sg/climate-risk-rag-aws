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
import os


@six.add_metaclass(abc.ABCMeta)
class CredentialProvider:

    """
    Abstract class for accessing Credentials.
    Implementation of this class must ensure credentials are refreshed on expiry.
    """

    @abc.abstractmethod
    def get_access_key(self):
        pass

    @abc.abstractmethod
    def get_secret_key(self):
        pass

    @abc.abstractmethod
    def get_security_token(self):
        pass


class EnvCredentialProvider(CredentialProvider):

    """
    Implementation of Credential Provider. This class reads credential values from environment variables.
    EnvCredentialProvider is suited for scenerios (Lambda Function) where Environment variables are always
    refreshed with valid Credentials.
    """

    def get_access_key(self):
        return os.getenv('AWS_ACCESS_KEY_ID', '')

    def get_secret_key(self):
        return os.getenv('AWS_SECRET_ACCESS_KEY', '')

    def get_security_token(self):
        return os.getenv('AWS_SESSION_TOKEN', '')


# Global variable to access credential_provider. By default EnvCredentialProvider is used.
# Credential Provider can be changed by using set_credential_provider Method
credential_provider = EnvCredentialProvider()


def set_credential_provider(provider):

    """
    Sets global Credential Provider Instance which can be used across the module.

    :param provider:
    """
    global credential_provider
    credential_provider = provider
