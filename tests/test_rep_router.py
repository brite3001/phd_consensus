import pytest
import asyncio

from src.iot_node.node import Node
from src.iot_node.message_classes import DirectMessage


@pytest.mark.asyncio
async def test_rep_router():
    n1 = Node(
        id="node_one",
        router_bind="tcp://127.0.0.1:20001",
        publisher_bind="tcp://127.0.0.1:21001",
    )

    n2 = Node(
        id="node_one",
        router_bind="tcp://127.0.0.1:20002",
        publisher_bind="tcp://127.0.0.1:21002",
    )

    n3 = Node(
        id="node_one",
        router_bind="tcp://127.0.0.1:20003",
        publisher_bind="tcp://127.0.0.1:21003",
    )

    await n1.init_sockets()
    await n2.init_sockets()
    await n3.init_sockets()

    await n1.start()
    await n2.start()
    await n3.start()

    dm = DirectMessage(
        sender=n1.id,
        message="Hello!!!",
        message_type="DirectMessage",
    )

    n1.command(dm, "tcp://127.0.0.1:20002")
    n1.command(dm, "tcp://127.0.0.1:20003")
    await asyncio.sleep(2)

    assert hash(dm) in n2.received_messages
    assert hash(dm) in n3.received_messages

    n1.stop()
    n2.stop()
    n3.stop()
