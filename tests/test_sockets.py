import pytest
import asyncio
from attrs import asdict

from src.iot_node.node import Node
from src.iot_node.message_classes import DirectMessage
from src.iot_node.message_classes import PublishMessage
from src.iot_node.commad_arg_classes import SubscribeToPublisher
from src.iot_node.commad_arg_classes import UnsubscribeFromTopic


@pytest.mark.asyncio
async def test_rep_router():
    n1 = Node(
        id="node_one",
        router_bind="tcp://127.0.0.1:20001",
        publisher_bind="tcp://127.0.0.1:21001",
    )

    n2 = Node(
        id="node_two",
        router_bind="tcp://127.0.0.1:20002",
        publisher_bind="tcp://127.0.0.1:21002",
    )

    n3 = Node(
        id="node_three",
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
        creator=n1.id,
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


@pytest.mark.asyncio
async def test_pub_sub():
    n1 = Node(
        id="node_one",
        router_bind="tcp://127.0.0.1:20001",
        publisher_bind="tcp://127.0.0.1:21001",
    )

    n2 = Node(
        id="node_two",
        router_bind="tcp://127.0.0.1:20002",
        publisher_bind="tcp://127.0.0.1:21002",
    )

    n3 = Node(
        id="node_three",
        router_bind="tcp://127.0.0.1:20003",
        publisher_bind="tcp://127.0.0.1:21003",
    )

    await n1.init_sockets()
    await n2.init_sockets()
    await n3.init_sockets()

    await n1.start()
    await n2.start()
    await n3.start()

    sub = SubscribeToPublisher("tcp://127.0.0.1:21001", "yolo")
    n2.command(sub)
    n3.command(sub)
    await asyncio.sleep(0.25)

    pub = PublishMessage(
        creator=n1.id, message="Hey bro", message_type="PublishMessage", topic="yolo"
    )

    n1.command(pub)
    await asyncio.sleep(0.25)

    assert hash(pub) in n2.received_messages
    assert hash(pub) in n3.received_messages

    # Test adding a new topic
    sub = SubscribeToPublisher("tcp://127.0.0.1:21001", "wumbo")
    n2.command(sub)
    n3.command(sub)
    await asyncio.sleep(0.25)

    pub = PublishMessage(
        creator=n1.id,
        message="Hey bro, WUMBO",
        message_type="PublishMessage",
        topic="wumbo",
    )

    n1.command(pub)
    await asyncio.sleep(0.25)

    assert hash(pub) in n2.received_messages
    assert hash(pub) in n3.received_messages

    # Make sure we don't get messages from an unsubscribed topic
    pub = PublishMessage(
        creator=n1.id,
        message="Hey bro, TUMBO",
        message_type="PublishMessage",
        topic="tumbo",
    )

    n1.command(pub)
    await asyncio.sleep(0.25)

    assert hash(pub) not in n2.received_messages
    assert hash(pub) not in n3.received_messages

    # Test topic unsubscribe
    unsub = UnsubscribeFromTopic("yolo")
    n2.command(unsub)
    n3.command(unsub)
    await asyncio.sleep(0.25)

    pub = PublishMessage(
        creator=n1.id,
        message="Hey bro, YOURE UNSUBBED",
        message_type="PublishMessage",
        topic="yolo",
    )

    n1.command(pub)
    await asyncio.sleep(0.25)

    assert hash(pub) not in n2.received_messages
    assert hash(pub) not in n3.received_messages

    n1.stop()
    n2.stop()
    n3.stop()
