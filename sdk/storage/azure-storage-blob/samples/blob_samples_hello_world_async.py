# coding: utf-8

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import asyncio

# set up
DEST_FILE = 'BlockDestination.txt'
SOURCE_FILE = 'SampleSource.txt'

class BlobSamplesAsync(object):

    connection_string = os.getenv("CONNECTION_STRING")

    #--Begin Blob Samples-----------------------------------------------------------------

    async def create_container_sample_async(self):
        # Instantiate a new BlobServiceClient using a connection string
        from azure.storage.blob.aio import BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)

        # Instantiate a new ContainerClient
        container_client = blob_service_client.get_container_client("mycontainerasync")

        try:
            # Create new container in the service
            await container_client.create_container()

            # List containers in the storage account
            my_containers = []
            async for container in blob_service_client.list_containers():
                my_containers.append(container)

        finally:
            # Delete the container
            await container_client.delete_container()

    async def block_blob_sample_async(self):
        # Instantiate a new BlobServiceClient using a connection string
        from azure.storage.blob.aio import BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)

        # Instantiate a new ContainerClient
        container_client = blob_service_client.get_container_client("myblockcontainerasync")

        try:
            # Create new Container in the service
            await container_client.create_container()

            # Instantiate a new BlobClient
            blob_client = container_client.get_blob_client("myblockblob")

            # [START upload_a_blob]
            # Upload content to block blob
            with open(SOURCE_FILE, "rb") as data:
                await blob_client.upload_blob(data, blob_type="BlockBlob")
            # [END upload_a_blob]

            # [START download_a_blob]
            with open(DEST_FILE, "wb") as my_blob:
                stream = await blob_client.download_blob()
                data = await stream.readall()
                my_blob.write(data)
            # [END download_a_blob]

            # [START delete_blob]
            await blob_client.delete_blob()
            # [END delete_blob]

        finally:
            # Delete the container
            await container_client.delete_container()

    async def page_blob_sample_async(self):
        # Instantiate a new BlobServiceClient using a connection string
        from azure.storage.blob.aio import BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)

        # Instantiate a new ContainerClient
        container_client = blob_service_client.get_container_client("mypagecontainerasync")

        try:
            # Create new Container in the Service
            await container_client.create_container()

            # Instantiate a new BlobClient
            blob_client = container_client.get_blob_client("mypageblob")

            # Upload content to the Page Blob
            data = self.get_random_bytes(512)
            await blob_client.upload_blob(data, blob_type="PageBlob")

            # Download Page Blob
            with open(DEST_FILE, "wb") as my_blob:
                stream = await blob_client.download_blob()
                data = await stream.readall()
                my_blob.write(data)

            # Delete Page Blob
            await blob_client.delete_blob()

        finally:
            # Delete container
            await container_client.delete_container()

    async def append_blob_sample_async(self):
        # Instantiate a new BlobServiceClient using a connection string
        from azure.storage.blob.aio import BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)

        # Instantiate a new ContainerClient
        container_client = blob_service_client.get_container_client("myappendcontainerasync")

        try:
            # Create new Container in the Service
            await container_client.create_container()

            # Get the BlobClient
            blob_client = container_client.get_blob_client("myappendblob")

            # Upload content to the append blob
            with open(SOURCE_FILE, "rb") as data:
                await blob_client.upload_blob(data, blob_type="AppendBlob")

            # Download append blob
            with open(DEST_FILE, "wb") as my_blob:
                stream = await blob_client.download_blob()
                data = await stream.readall()
                my_blob.write(data)

            # Delete append blob
            await blob_client.delete_blob()

        finally:
            # Delete container
            await container_client.delete_container()
