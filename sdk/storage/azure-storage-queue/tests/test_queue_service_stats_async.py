# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import unittest
import asyncio
from devtools_testutils import ResourceGroupPreparer, StorageAccountPreparer
from azure.storage.queue.aio import QueueServiceClient
from azure.core.pipeline.transport import AioHttpTransport
from multidict import CIMultiDict, CIMultiDictProxy

from asyncqueuetestcase import (
    AsyncQueueTestCase
)

SERVICE_UNAVAILABLE_RESP_BODY = '<?xml version="1.0" encoding="utf-8"?><StorageServiceStats><GeoReplication><Status' \
                                '>unavailable</Status><LastSyncTime></LastSyncTime></GeoReplication' \
                                '></StorageServiceStats> '

SERVICE_LIVE_RESP_BODY = '<?xml version="1.0" encoding="utf-8"?><StorageServiceStats><GeoReplication><Status' \
                                '>live</Status><LastSyncTime>Wed, 19 Jan 2021 22:28:43 GMT</LastSyncTime></GeoReplication' \
                                '></StorageServiceStats> '


class AiohttpTestTransport(AioHttpTransport):
    """Workaround to vcrpy bug: https://github.com/kevin1024/vcrpy/pull/461
    """
    async def send(self, request, **config):
        response = await super(AiohttpTestTransport, self).send(request, **config)
        if not isinstance(response.headers, CIMultiDictProxy):
            response.headers = CIMultiDictProxy(CIMultiDict(response.internal_response.headers))
            response.content_type = response.headers.get("content-type")
        return response


# --Test Class -----------------------------------------------------------------
class QueueServiceStatsTestAsync(AsyncQueueTestCase):
    # --Helpers-----------------------------------------------------------------
    def _assert_stats_default(self, stats):
        self.assertIsNotNone(stats)
        self.assertIsNotNone(stats['geo_replication'])

        self.assertEqual(stats['geo_replication']['status'], 'live')
        self.assertIsNotNone(stats['geo_replication']['last_sync_time'])

    def _assert_stats_unavailable(self, stats):
        self.assertIsNotNone(stats)
        self.assertIsNotNone(stats['geo_replication'])

        self.assertEqual(stats['geo_replication']['status'], 'unavailable')
        self.assertIsNone(stats['geo_replication']['last_sync_time'])

    @staticmethod
    def override_response_body_with_unavailable_status(response):
        response.http_response.text = lambda: SERVICE_UNAVAILABLE_RESP_BODY

    @staticmethod
    def override_response_body_with_live_status(response):
        response.http_response.text = lambda: SERVICE_LIVE_RESP_BODY

    # --Test cases per service ---------------------------------------
    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage', sku='Standard_RAGRS')
    @AsyncQueueTestCase.await_prepared_test
    async def test_queue_service_stats_f(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        qsc = QueueServiceClient(self._account_url(storage_account.name), storage_account_key, transport=AiohttpTestTransport())
        # Act
        stats = await qsc.get_service_stats(raw_response_hook=self.override_response_body_with_live_status)

        # Assert
        self._assert_stats_default(stats)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage', sku='Standard_RAGRS')
    @AsyncQueueTestCase.await_prepared_test
    async def test_queue_service_stats_when_unavailable(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        qsc = QueueServiceClient(self._account_url(storage_account.name), storage_account_key, transport=AiohttpTestTransport())

        # Act
        stats = await qsc.get_service_stats(
            raw_response_hook=self.override_response_body_with_unavailable_status)

        # Assert
        self._assert_stats_unavailable(stats)

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()
