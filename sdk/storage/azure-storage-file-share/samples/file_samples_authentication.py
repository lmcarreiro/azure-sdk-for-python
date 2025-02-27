# coding: utf-8

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""
FILE: file_samples_authentication.py

DESCRIPTION:
    These samples demonstrate authenticating a client via a connection string,
    shared access key, or by generating a sas token with which the returned signature
    can be used with the credential parameter of any ShareServiceClient,
    ShareClient, ShareDirectoryClient, or ShareFileClient.

USAGE:
    python file_samples_authentication.py
    Set the environment variables with your own values before running the sample.
"""

import os
from datetime import datetime, timedelta


class FileAuthSamples(object):

    connection_string = os.getenv('CONNECTION_STRING')
    shared_access_key = os.getenv('STORAGE_ACCOUNT_KEY')
    account_url = "{}://{}.blob.core.windows.net".format(
        os.getenv('PROTOCOL'),
        os.getenv('STORAGE_ACCOUNT_NAME')
    )

    def authentication_connection_string(self):
        # Instantiate the ShareServiceClient from a connection string
        # [START create_share_service_client_from_conn_string]
        from azure.storage.fileshare import ShareServiceClient
        share_service_client = ShareServiceClient.from_connection_string(self.connection_string)
        # [END create_share_service_client_from_conn_string]

    def authentication_shared_access_key(self):
        # Instantiate a ShareServiceClient using a shared access key
        # [START create_share_service_client]
        from azure.storage.fileshare import ShareServiceClient
        share_service_client = ShareServiceClient(
            account_url=self.account_url,
            credential=self.shared_access_key
        )
        # [END create_share_service_client]

    def authentication_shared_access_signature(self):
        # Instantiate a ShareServiceClient using a connection string
        # [START generate_sas_token]
        from azure.storage.fileshare import ShareServiceClient
        share_service_client = ShareServiceClient.from_connection_string(self.connection_string)

        # Create a SAS token to use to authenticate a new client
        from azure.storage.fileshare import generate_account_sas

        sas_token = generate_account_sas(
            share_service_client.account_name,
            share_service_client.credential.account_key,
            resource_types="object",
            permission="read",
            expiry=datetime.utcnow() + timedelta(hours=1)
        )
        # [END generate_sas_token]


if __name__ == '__main__':
    sample = FileAuthSamples()
    sample.authentication_connection_string()
    sample.authentication_shared_access_key()
    sample.authentication_shared_access_signature()

