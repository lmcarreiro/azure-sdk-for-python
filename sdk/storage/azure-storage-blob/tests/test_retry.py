# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import unittest
import pytest

from azure.core.exceptions import (
    HttpResponseError,
    ResourceExistsError,
    ServiceResponseError,
    ClientAuthenticationError
)
from azure.core.pipeline.transport import(
    RequestsTransport
)
from devtools_testutils import ResourceGroupPreparer, StorageAccountPreparer
from azure.storage.blob import (
    BlobServiceClient,
    ContainerClient,
    BlobClient,
    LocationMode,
    LinearRetry,
    ExponentialRetry,
)

from testcase import (
    StorageTestCase,
    ResponseCallback,
    RetryCounter,
    GlobalStorageAccountPreparer
)


# --Test Class -----------------------------------------------------------------
class StorageRetryTest(StorageTestCase):
    # --Test Cases --------------------------------------------
    @GlobalStorageAccountPreparer()
    def test_retry_on_server_error(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        service = self._create_storage_service(BlobServiceClient, storage_account, storage_account_key)

        # Force the create call to 'timeout' with a 408
        callback = ResponseCallback(status=201, new_status=500).override_status

        # Act
        try:
            # The initial create will return 201, but we overwrite it and retry.
            # The retry will then get a 409 and return false.
            with self.assertRaises(ResourceExistsError):
                service.create_container(container_name, raw_response_hook=callback)
        finally:
            service.delete_container(container_name)

        # Assert

    @GlobalStorageAccountPreparer()
    def test_retry_on_timeout(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        retry = ExponentialRetry(initial_backoff=1, increment_base=2)
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry)

        callback = ResponseCallback(status=201, new_status=408).override_status

        # Act
        try:
            # The initial create will return 201, but we overwrite it and retry.
            # The retry will then get a 409 and return false.
            with self.assertRaises(ResourceExistsError):
                service.create_container(container_name, raw_response_hook=callback)
        finally:
            service.delete_container(container_name)

        # Assert

    @GlobalStorageAccountPreparer()
    def test_retry_callback_and_retry_context(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        retry = LinearRetry(backoff=1)
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry)

        # Force the create call to 'timeout' with a 408
        callback = ResponseCallback(status=201, new_status=408).override_status

        def assert_exception_is_present_on_retry_context(**kwargs):
            self.assertIsNotNone(kwargs.get('response'))
            self.assertEqual(kwargs['response'].status_code, 408)


        # Act
        try:
            # The initial create will return 201, but we overwrite it and retry.
            # The retry will then get a 409 and return false.
            with self.assertRaises(ResourceExistsError):
                service.create_container(
                    container_name, raw_response_hook=callback,
                    retry_hook=assert_exception_is_present_on_retry_context)
        finally:
            service.delete_container(container_name)

    @GlobalStorageAccountPreparer()
    def test_retry_on_socket_timeout(self, resource_group, location, storage_account, storage_account_key):
        if not self.is_live:
            pytest.skip("live only")
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        retry = LinearRetry(backoff=1)

        # make the connect timeout reasonable, but packet timeout truly small, to make sure the request always times out
        socket_timeout = (11, 0.000000000001)
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry, connection_timeout=socket_timeout)

        assert service._client._client._pipeline._transport.connection_config.timeout == socket_timeout

        # Act
        try:
            with self.assertRaises(ServiceResponseError) as error:
                service.create_container(container_name)
            # Assert
            # This call should succeed on the server side, but fail on the client side due to socket timeout
            self.assertTrue('read timeout' in str(error.exception), 'Expected socket timeout but got different exception.')

        finally:
            # we must make the timeout normal again to let the delete operation succeed
            service.delete_container(container_name, connection_timeout=(11, 11))

    @GlobalStorageAccountPreparer()
    def test_no_retry(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_total=0)


        # Force the create call to 'timeout' with a 408
        callback = ResponseCallback(status=201, new_status=408).override_status

        # Act
        try:
            with self.assertRaises(HttpResponseError) as error:
                service.create_container(container_name, raw_response_hook=callback)
            self.assertEqual(error.exception.response.status_code, 408)
            self.assertEqual(error.exception.reason, 'Created')

        finally:
            service.delete_container(container_name)

    @GlobalStorageAccountPreparer()
    def test_linear_retry(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        retry = LinearRetry(backoff=1)
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry)

        # Force the create call to 'timeout' with a 408
        callback = ResponseCallback(status=201, new_status=408).override_status

        # Act
        try:
            # The initial create will return 201, but we overwrite it and retry.
            # The retry will then get a 409 and return false.
            with self.assertRaises(ResourceExistsError):
                service.create_container(container_name, raw_response_hook=callback)
        finally:
            service.delete_container(container_name)

        # Assert

    @GlobalStorageAccountPreparer()
    def test_exponential_retry(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        retry = ExponentialRetry(initial_backoff=1, increment_base=3, retry_total=3)
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry)

        try:
            container = service.create_container(container_name)

            # Force the create call to 'timeout' with a 408
            callback = ResponseCallback(status=200, new_status=408)

            # Act
            with self.assertRaises(HttpResponseError):
                container.get_container_properties(raw_response_hook=callback.override_status)

            # Assert the response was called the right number of times (1 initial request + 3 retries)
            self.assertEqual(callback.count, 1+3)
        finally:
            # Clean up
            service.delete_container(container_name)

    @GlobalStorageAccountPreparer()
    def test_exponential_retry_interval(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        retry_policy = ExponentialRetry(initial_backoff=1, increment_base=3, random_jitter_range=3)
        context_stub = {}

        for i in range(10):
            # Act
            context_stub['count'] = 0
            backoff = retry_policy.get_backoff_time(context_stub)

            # Assert backoff interval is within +/- 3 of 1
            self.assertTrue(0 <= backoff <= 4)

            # Act
            context_stub['count'] = 1
            backoff = retry_policy.get_backoff_time(context_stub)

            # Assert backoff interval is within +/- 3 of 4(1+3^1)
            self.assertTrue(1 <= backoff <= 7)

            # Act
            context_stub['count'] = 2
            backoff = retry_policy.get_backoff_time(context_stub)

            # Assert backoff interval is within +/- 3 of 10(1+3^2)
            self.assertTrue(7 <= backoff <= 13)

            # Act
            context_stub['count'] = 3
            backoff = retry_policy.get_backoff_time(context_stub)

            # Assert backoff interval is within +/- 3 of 28(1+3^3)
            self.assertTrue(25 <= backoff <= 31)

    @GlobalStorageAccountPreparer()
    def test_linear_retry_interval(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        context_stub = {}

        for i in range(10):
            # Act
            retry_policy = LinearRetry(backoff=1, random_jitter_range=3)
            backoff = retry_policy.get_backoff_time(context_stub)

            # Assert backoff interval is within +/- 3 of 1
            self.assertTrue(0 <= backoff <= 4)

            # Act
            retry_policy = LinearRetry(backoff=5, random_jitter_range=3)
            backoff = retry_policy.get_backoff_time(context_stub)

            # Assert backoff interval is within +/- 3 of 5
            self.assertTrue(2 <= backoff <= 8)

            # Act
            retry_policy = LinearRetry(backoff=15, random_jitter_range=3)
            backoff = retry_policy.get_backoff_time(context_stub)

            # Assert backoff interval is within +/- 3 of 15
            self.assertTrue(12 <= backoff <= 18)

    @GlobalStorageAccountPreparer()
    def test_invalid_retry(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        retry = ExponentialRetry(initial_backoff=1, increment_base=2)
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry)

        # Force the create call to fail by pretending it's a teapot
        callback = ResponseCallback(status=201, new_status=418).override_status

        # Act
        try:
            with self.assertRaises(HttpResponseError) as error:
                service.create_container(container_name, raw_response_hook=callback)
            self.assertEqual(error.exception.response.status_code, 418)
            self.assertEqual(error.exception.reason, 'Created')
        finally:
            service.delete_container(container_name)

    @GlobalStorageAccountPreparer()
    def test_retry_with_deserialization(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('retry')
        retry = ExponentialRetry(initial_backoff=1, increment_base=2)
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry)

        try:
            created = service.create_container(container_name)

            # Act
            callback = ResponseCallback(status=200, new_status=408).override_first_status
            containers = service.list_containers(name_starts_with='retry', raw_response_hook=callback)

            # Assert
            containers = list(containers)
            self.assertTrue(len(containers) >= 1)
        finally:
            service.delete_container(container_name)

    @GlobalStorageAccountPreparer()
    def test_retry_secondary(self, resource_group, location, storage_account, storage_account_key):
        """Secondary location test.

        This test is special, since in pratical term, we don't have time to wait
        for the georeplication to be done (can take a loooooong time).
        So for the purpose of this test, we fake a 408 on the primary request,
        and then we check we do a 408. AND DONE.
        It's not really perfect, since we didn't tested it would work on
        a real geo-location.

        Might be changed to live only as loooooong test with a polling on
        the current geo-replication status.
        """
        # Arrange
        # Fail the first request and set the retry policy to retry to secondary
        # The given test account must be GRS
        class MockTransport(RequestsTransport):
            CALL_NUMBER = 1
            ENABLE = False
            def send(self, request, **kwargs):
                if MockTransport.ENABLE:
                    if MockTransport.CALL_NUMBER == 2:
                        if request.method != 'PUT':
                            assert '-secondary' in request.url
                        # Here's our hack
                        # Replace with primary so the test works even
                        # if secondary is not ready
                        request.url = request.url.replace('-secondary', '')

                response = super(MockTransport, self).send(request, **kwargs)

                if MockTransport.ENABLE:
                    assert response.status_code in [200, 201, 409]
                    if MockTransport.CALL_NUMBER == 1:
                        response.status_code = 408
                    elif MockTransport.CALL_NUMBER == 2:
                        if response.status_code == 409:  # We can't really retry on PUT
                            response.status_code = 201
                    else:
                        pytest.fail("This test is not supposed to do more calls")
                    MockTransport.CALL_NUMBER += 1
                return response

        retry = ExponentialRetry(retry_to_secondary=True, initial_backoff=1, increment_base=2)
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry,
            transport=MockTransport()
        )

        # Act
        MockTransport.ENABLE = True

        # Assert

        # Try put
        def put_retry_callback(retry_count=None, location_mode=None, **kwargs):
            # This call should be called once, with the decision to try secondary
            put_retry_callback.called = True
            if MockTransport.CALL_NUMBER == 1:
                self.assertEqual(LocationMode.PRIMARY, location_mode)
            elif MockTransport.CALL_NUMBER == 2:
                self.assertEqual(LocationMode.PRIMARY, location_mode)
            else:
                pytest.fail("This test is not supposed to retry more than once")
        put_retry_callback.called = False

        container = service.get_container_client('containername')
        created = container.create_container(retry_hook=put_retry_callback)
        assert put_retry_callback.called

        def retry_callback(retry_count=None, location_mode=None, **kwargs):
            # This call should be called once, with the decision to try secondary
            retry_callback.called = True
            if MockTransport.CALL_NUMBER == 1:
                self.assertEqual(LocationMode.SECONDARY, location_mode)
            elif MockTransport.CALL_NUMBER == 2:
                self.assertEqual(LocationMode.SECONDARY, location_mode)
            else:
                pytest.fail("This test is not supposed to retry more than once")
        retry_callback.called = False

        # Try list
        MockTransport.CALL_NUMBER = 1
        retry_callback.called = False
        containers = service.list_containers(
            results_per_page=1, retry_hook=retry_callback)
        next(containers)
        assert retry_callback.called

        # Try get
        MockTransport.CALL_NUMBER = 1
        retry_callback.called = False
        container.get_container_properties(retry_hook=retry_callback)
        assert retry_callback.called

    @GlobalStorageAccountPreparer()
    def test_invalid_account_key(self, resource_group, location, storage_account, storage_account_key):
        # Arrange
        container_name = self.get_resource_name('utcontainer')
        retry = ExponentialRetry(initial_backoff=1, increment_base=3, retry_total=3)
        service = self._create_storage_service(
            BlobServiceClient, storage_account, storage_account_key, retry_policy=retry)
        service.credential.account_name = "dummy_account_name"
        service.credential.account_key = "dummy_account_key"

        # Shorten retries and add counter
        retry_counter = RetryCounter()
        retry_callback = retry_counter.simple_count

        # Act
        with self.assertRaises(ClientAuthenticationError):
            service.create_container(container_name, retry_callback=retry_callback)

        # Assert
        # No retry should be performed since the signing error is fatal
        self.assertEqual(retry_counter.count, 0)


# ------------------------------------------------------------------------------

