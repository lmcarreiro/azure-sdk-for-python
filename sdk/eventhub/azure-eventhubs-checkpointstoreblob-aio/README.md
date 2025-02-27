# Azure EventHubs Checkpoint Store client library for Python using Storage Blobs

Azure EventHubs Checkpoint Store is used for storing checkpoints while processing events from Azure Event Hubs.
This Checkpoint Store package works as a plug-in package to `EventProcessor`. It uses Azure Storage Blob as the persistent store for maintaining checkpoints and partition ownership information.

[Source code](https://github.com/Azure/azure-sdk-for-python/tree/master/sdk/eventhub/azure-eventhubs-checkpointstoreblob-aio) | [Package (PyPi)](https://pypi.org/project/azure-eventhub-checkpointstoreblob-aio/) | [API reference documentation](https://azure.github.io/azure-sdk-for-python/ref/azure.eventhub.extensions.html) | [Azure Eventhubs documentation](https://docs.microsoft.com/en-us/azure/event-hubs/) | [Azure Storage documentation](https://docs.microsoft.com/en-us/azure/storage/)

## Getting started

### Install the package

```
$ pip install --pre azure-eventhub-checkpointstoreblob-aio
```

**Prerequisites**

- Python 3.5.3 or later.
- **Microsoft Azure Subscription:**  To use Azure services, including Azure Event Hubs, you'll need a subscription.  If you do not have an existing Azure account, you may sign up for a free trial or use your MSDN subscriber benefits when you [create an account](https://azure.microsoft.com/en-us/).

- **Event Hubs namespace with an Event Hub:** To interact with Azure Event Hubs, you'll also need to have a namespace and Event Hub  available.  If you are not familiar with creating Azure resources, you may wish to follow the step-by-step guide for [creating an Event Hub using the Azure portal](https://docs.microsoft.com/en-us/azure/event-hubs/event-hubs-create).  There, you can also find detailed instructions for using the Azure CLI, Azure PowerShell, or Azure Resource Manager (ARM) templates to create an Event Hub.

- **Azure Storage Account:** You'll need to have an Azure Storage Account and create a Azure Blob Storage Block Container to store the checkpoint data with blobs. You may follow the guide [creating an Azure Block Blob Storage Account](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-blob-create-account-block-blob).

## Key concepts

### Checkpointing

Checkpointing is a process by which readers mark or commit their position within a partition event sequence. 
Checkpointing is the responsibility of the consumer and occurs on a per-partition basis within a consumer group. 
This responsibility means that for each consumer group, each partition reader must keep track of its current position 
in the event stream, and can inform the service when it considers the data stream complete. If a reader disconnects from
a partition, when it reconnects it begins reading at the checkpoint that was previously submitted by the last reader of
that partition in that consumer group. When the reader connects, it passes the offset to the event hub to specify the 
location at which to start reading. In this way, you can use checkpointing to both mark events as "complete" by 
downstream applications, and to provide resiliency if a failover between readers running on different machines occurs. 
It is possible to return to older data by specifying a lower offset from this checkpointing process. Through this 
mechanism, checkpointing enables both failover resiliency and event stream replay.

### Offsets & sequence numbers
Both offset & sequence number refer to the position of an event within a partition. You can think of them as a 
client-side cursor. The offset is a byte numbering of the event. The offset/sequence number enables an event consumer 
(reader) to specify a point in the event stream from which they want to begin reading events. You can specify a 
timestamp such that you receive events enqueued only after the given timestamp. Consumers are responsible for 
storing their own offset values outside of the Event Hubs service. Within a partition, each event includes an offset, 
sequence number and the timestamp of when it was enqueued.

## Examples
- [Create an Azure Storage Blobs `ContainerClient`](#create-an-azure-storage-blobs-containerclient)
- [Create an Azure EventHubs `EventHubClient`](#create-an-eventhubclient)
- [Consume events using an `EventProessor` that uses a `BlobPartitionManager`](#consume-events-using-an-eventprocessor-that-uses-a-blobpartitionmanager-to-do-checkpointing)

### Create an Azure Storage Blobs `ContainerClient`
The easiest way to create a `ContainerClient` is to use a connection string.
```python
from azure.storage.blob.aio import ContainerClient
container_client = ContainerClient.from_connection_string("my_storageacount_connection_string", "mycontainer")
```
For other ways of creating a `ContainerClient`, go to [Blob Storage library](https://github.com/Azure/azure-sdk-for-python/tree/master/sdk/storage/azure-storage-blob) for more details.

### Create an `EventHubClient`
The easiest way to create a `EventHubClient` is to use a connection string.
```python
from azure.eventhub.aio import EventHubClient
eventhub_client = EventHubClient.from_connection_string("my_eventhub_namespace_connection_string", event_hub_path="myeventhub")
```
For other ways of creating a `EventHubClient`, refer to [EventHubs library](https://github.com/Azure/azure-sdk-for-python/tree/master/sdk/eventhub/azure-eventhubs) for more details.

### Consume events using an `EventProcessor` that uses a `BlobPartitionManager` to do checkpointing
```python
import asyncio

from azure.eventhub.aio import EventHubClient
from azure.eventhub.aio.eventprocessor import EventProcessor, PartitionProcessor
from azure.storage.blob.aio import ContainerClient
from azure.eventhub.extensions.checkpointstoreblobaio import BlobPartitionManager

eventhub_connection_str = '<< CONNECTION STRING FOR THE EVENT HUBS NAMESPACE >>'
storage_container_connection_str = '<< CONNECTION STRING OF THE STORAGE >>'
storage_container_name = '<< STORAGE CONTAINER NAME>>'

class MyPartitionProcessor(PartitionProcessor):
    async def process_events(self, events, partition_context):
        if events:
            # write your code here to process events
            # save checkpoint to the data store
            await partition_context.update_checkpoint(events[-1].offset, events[-1].sequence_number)

async def main():
    eventhub_client = EventHubClient.from_connection_string(eventhub_connection_str, receive_timeout=5, retry_total=3)
    storage_container_client = ContainerClient.from_connection_string(storage_container_connection_str, storage_container_name)
    partition_manager = BlobPartitionManager(storage_container_client)  # use the BlobPartitonManager to save
    event_processor = EventProcessor(eventhub_client, "$default", MyPartitionProcessor, partition_manager)    
    async with storage_container_client:
        asyncio.ensure_future(event_processor.start())
        await asyncio.sleep(60)  # run for a while
        await event_processor.stop()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
```

## Troubleshooting

### General
Enabling logging will be helpful to do trouble shooting.
Refer to [Logging](#logging) to enable loggers for related libraries.

## Next steps

### Examples
- [./examples/eventprocessor/event_processor_blob_storage_example.py](https://github.com/Azure/azure-sdk-for-python/blob/master/sdk/eventhub/azure-eventhubs-checkpointstoreblob-aio/examples/event_processor_blob_storage_example.py) - event processor with blob partition manager example

### Documentation

Reference documentation is available at https://azure.github.io/azure-sdk-for-python/ref/azure.eventhub.extensions.html.

### Logging

- Enable `azure.eventhub.extensions.checkpointstoreblobaio` logger to collect traces from the library.
- Enable `azure.eventhub.aio.eventprocessor` logger to collect traces from package eventprocessor of the azure-eventhub library.
- Enable `azure.eventhub` logger to collect traces from the main azure-eventhub library.
- Enable `azure.storage.blob` logger to collect traces from azure storage blob library.
- Enable `uamqp` logger to collect traces from the underlying uAMQP library.
- Enable AMQP frame level trace by setting `network_tracing=True` when creating the client.

### Provide Feedback

If you encounter any bugs or have suggestions, please file an issue in the [Issues](https://github.com/Azure/azure-sdk-for-python/issues) section of the project.

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

![Impressions](https://azure-sdk-impressions.azurewebsites.net/api/impressions/azure-sdk-for-python/sdk/eventhub/azure-eventhubs-checkpointstoreblob-aio/README.png)
