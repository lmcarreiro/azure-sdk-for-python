# coding: utf-8

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os

class QueueHelloWorldSamples(object):

    connection_string = os.getenv("CONNECTION_STRING")

    def create_client_with_connection_string(self):
        # Instantiate the QueueServiceClient from a connection string
        from azure.storage.queue import QueueServiceClient
        queue_service = QueueServiceClient.from_connection_string(conn_str=self.connection_string)

        # Get queue service properties
        properties = queue_service.get_service_properties()

    def queue_and_messages_example(self):
        # Instantiate the QueueClient from a connection string
        from azure.storage.queue import QueueClient
        queue = QueueClient.from_connection_string(conn_str=self.connection_string, queue_name="my_queue")

        # Create the queue
        # [START create_queue]
        queue.create_queue()
        # [END create_queue]

        try:
            # Send messages
            queue.send_message(u"I'm using queues!")
            queue.send_message(u"This is my second message")

            # Receive the messages
            response = queue.receive_messages(messages_per_page=2)

            # Print the content of the messages
            for message in response:
                print(message.content)

        finally:
            # [START delete_queue]
            queue.delete_queue()
            # [END delete_queue]
