# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import asyncio

from datetime import datetime, timedelta
from azure.core.exceptions import HttpResponseError
from azure.core.pipeline.transport import AioHttpTransport
from multidict import CIMultiDict, CIMultiDictProxy

from azure.storage.blob import StorageErrorCode, BlobSasPermissions, generate_blob_sas

from azure.storage.blob.aio import (
    BlobServiceClient,
    ContainerClient,
    BlobClient,
)

from azure.storage.blob._shared.policies import StorageContentValidation
from devtools_testutils import ResourceGroupPreparer, StorageAccountPreparer
from testcase import GlobalStorageAccountPreparer
from asyncblobtestcase import (
    AsyncBlobTestCase,
)

# ------------------------------------------------------------------------------
SOURCE_BLOB_SIZE = 8 * 1024


# ------------------------------------------------------------------------------

class AiohttpTestTransport(AioHttpTransport):
    """Workaround to vcrpy bug: https://github.com/kevin1024/vcrpy/pull/461
    """
    async def send(self, request, **config):
        response = await super(AiohttpTestTransport, self).send(request, **config)
        if not isinstance(response.headers, CIMultiDictProxy):
            response.headers = CIMultiDictProxy(CIMultiDict(response.internal_response.headers))
            response.content_type = response.headers.get("content-type")
        return response


class StorageBlockBlobTestAsync(AsyncBlobTestCase):
    async def _setup(self, name, key):
        # test chunking functionality by reducing the size of each chunk,
        # otherwise the tests would take too long to execute
        self.bsc = BlobServiceClient(
            self._account_url(name),
            credential=key,
            connection_data_block_size=4 * 1024,
            max_single_put_size=32 * 1024,
            max_block_size=4 * 1024,
            transport=AiohttpTestTransport())
        self.config = self.bsc._config
        self.container_name = self.get_resource_name('utcontainer')

        # create source blob to be copied from
        self.source_blob_name = self.get_resource_name('srcblob')
        self.source_blob_data = self.get_random_bytes(SOURCE_BLOB_SIZE)

        blob = self.bsc.get_blob_client(self.container_name, self.source_blob_name)

        if self.is_live:
            try:
                await self.bsc.create_container(self.container_name)
            except:
                pass
            await blob.upload_blob(self.source_blob_data, overwrite=True)

        # generate a SAS so that it is accessible with a URL
        sas_token = generate_blob_sas(
            blob.account_name,
            blob.container_name,
            blob.blob_name,
            snapshot=blob.snapshot,
            account_key=blob.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=1),
        )
        self.source_blob_url = BlobClient.from_blob_url(blob.url, credential=sas_token).url

    @GlobalStorageAccountPreparer()
    @AsyncBlobTestCase.await_prepared_test
    async def test_put_block_from_url_and_commit_async(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        await self._setup(storage_account.name, storage_account_key)
        dest_blob_name = self.get_resource_name('destblob')
        dest_blob = self.bsc.get_blob_client(self.container_name, dest_blob_name)

        # Act part 1: make put block from url calls
        split = 4 * 1024
        futures = [
            dest_blob.stage_block_from_url(
                block_id=1,
                source_url=self.source_blob_url,
                source_offset=0,
                source_length=split),
            dest_blob.stage_block_from_url(
                block_id=2,
                source_url=self.source_blob_url,
                source_offset=split,
                source_length=split)]
        await asyncio.gather(*futures)

        # Assert blocks
        committed, uncommitted = await dest_blob.get_block_list('all')
        self.assertEqual(len(uncommitted), 2)
        self.assertEqual(len(committed), 0)

        # Act part 2: commit the blocks
        await dest_blob.commit_block_list(['1', '2'])

        # Assert destination blob has right content
        content = await (await dest_blob.download_blob()).readall()
        self.assertEqual(content, self.source_blob_data)
        self.assertEqual(len(content), 8 * 1024)

    @GlobalStorageAccountPreparer()
    @AsyncBlobTestCase.await_prepared_test
    async def test_put_block_from_url_and_vldte_content_md5(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        await self._setup(storage_account.name, storage_account_key)
        dest_blob_name = self.get_resource_name('destblob')
        dest_blob = self.bsc.get_blob_client(self.container_name, dest_blob_name)
        src_md5 = StorageContentValidation.get_content_md5(self.source_blob_data)

        # Act part 1: put block from url with md5 validation
        await dest_blob.stage_block_from_url(
            block_id=1,
            source_url=self.source_blob_url,
            source_content_md5=src_md5,
            source_offset=0,
            source_length=8 * 1024)

        # Assert block was staged
        committed, uncommitted = await dest_blob.get_block_list('all')
        self.assertEqual(len(uncommitted), 1)
        self.assertEqual(len(committed), 0)

        # Act part 2: put block from url with wrong md5
        fake_md5 = StorageContentValidation.get_content_md5(b"POTATO")
        with self.assertRaises(HttpResponseError) as error:
            await dest_blob.stage_block_from_url(
                block_id=2,
                source_url=self.source_blob_url,
                source_content_md5=fake_md5,
                source_offset=0,
                source_length=8 * 1024)
        self.assertEqual(error.exception.error_code, StorageErrorCode.md5_mismatch)

        # Assert block was not staged
        committed, uncommitted = await dest_blob.get_block_list('all')
        self.assertEqual(len(uncommitted), 1)
        self.assertEqual(len(committed), 0)

    @GlobalStorageAccountPreparer()
    @AsyncBlobTestCase.await_prepared_test
    async def test_copy_blob_sync_async(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        await self._setup(storage_account.name, storage_account_key)
        dest_blob_name = self.get_resource_name('destblob')
        dest_blob = self.bsc.get_blob_client(self.container_name, dest_blob_name)

        # Act
        copy_props = await dest_blob.start_copy_from_url(self.source_blob_url, requires_sync=True)

        # Assert
        self.assertIsNotNone(copy_props)
        self.assertIsNotNone(copy_props['copy_id'])
        self.assertEqual('success', copy_props['copy_status'])

        # Verify content
        content = await (await dest_blob.download_blob()).readall()
        self.assertEqual(self.source_blob_data, content)
