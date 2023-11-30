from attrs import define, field
import asyncio
import aiozmq
import zmq
import json

from .commad_arg_classes import DirectMessage
from .commad_arg_classes import PublishMessage
from .commad_arg_classes import SubscribeToPublisher


@define
class Node:
    id: str
    router_bind: str
    publisher_bind: str

    _subscriber: aiozmq.stream.ZmqStream = field(init=False)
    _publisher: aiozmq.stream.ZmqStream = field(init=False)

    async def init_pub_sub(self):
        self._subscriber = await aiozmq.create_zmq_stream(zmq.SUB)
        self._publisher = await aiozmq.create_zmq_stream(
            zmq.PUB, bind=self.publisher_bind
        )

        print(f"[{self.id}] Started PUB/SUB Sockets")

    async def inbox(self):
        pass
        # deal with received messages from gossip and router here...

    async def router_event_loop(self):
        print(f"{[self.id]} Starting Router")
        router = await aiozmq.create_zmq_stream(zmq.ROUTER, bind=self.router_bind)

        while True:
            msg = await router.read()
            msg = json.loads(msg[2].decode())
            print(f"Received message {msg}")

    async def subscriber_event_loop(self):
        print(f"[{id}] Starting Subscriber")

        while True:
            msg = await self._subscriber.read()
            print(f"Received message from publisher: {msg}")

    async def publish(self, command_obj: PublishMessage):
        message = json.dumps(command_obj.message).encode("utf-8")
        self._publisher.write([command_obj.topic, message])

    async def direct_message(self, command_obj: DirectMessage):
        req = await aiozmq.create_zmq_stream(zmq.REQ)
        await req.transport.connect(command_obj.receiver)
        message = json.dumps(command_obj.message).encode("utf-8")

        req.write([message])

    async def subscribe(self, command_obj: SubscribeToPublisher):
        self._subscriber.transport.connect(command_obj.publisher)
        self._subscriber.transport.subscribe(command_obj.topic)

        print(f"Successfully subscribed to {command_obj.publisher}")

    def command(self, command_obj):
        if type(command_obj) == DirectMessage:
            asyncio.create_task(self.direct_message(command_obj))
        if type(command_obj) == SubscribeToPublisher:
            asyncio.create_task(self.subscribe(command_obj))
        if type(command_obj) == PublishMessage:
            asyncio.create_task(self.publish(command_obj))

    async def start(self):
        asyncio.create_task(self.router_event_loop())
        asyncio.create_task(self.subscriber_event_loop())
