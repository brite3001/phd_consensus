from attrs import define, field, asdict
import asyncio
import aiozmq
import zmq
import json

from .message_classes import DirectMessage
from .message_classes import PublishMessage
from .commad_arg_classes import SubscribeToPublisher


@define
class Node:
    id: str
    router_bind: str
    publisher_bind: str

    _subscriber: aiozmq.stream.ZmqStream = field(init=False)
    _publisher: aiozmq.stream.ZmqStream = field(init=False)
    _router: aiozmq.stream.ZmqStream = field(init=False)

    received_messages: dict = field(factory=dict)
    running: bool = True

    ####################
    # Inbox            #
    ####################
    async def inbox(self, message):
        print("Received Message")
        print(message)
        self.received_messages[hash(message)] = message

    ####################
    # Listeners        #
    ####################
    async def router_listener(self):
        print(f"[{self.id}] Starting Router")

        while True:
            if self.running == False:
                break

            message = await self._router.read()
            message = json.loads(message[2].decode())

            if message["message_type"] == "DirectMessage":
                message = DirectMessage(**message)
            else:
                print("Couldnt find matching class for message!!")

            asyncio.create_task(self.inbox(message))

    async def subscriber_listener(self):
        print(f"[{self.id}] Starting Subscriber")

        while True:
            if self.running == False:
                break

            message = await self._subscriber.read()
            _, message = message
            message = json.loads(message.decode())

            if message["message_type"] == "PublishMessage":
                message = PublishMessage(**message)
            else:
                print("Couldnt find matching class for message!!")

            asyncio.create_task(self.inbox(message))

    ####################
    # Message Sending  #
    ####################
    async def publish(self, pm: PublishMessage):
        message = json.dumps(asdict(pm)).encode()
        self._publisher.write([pm.topic.encode(), message])

    async def direct_message(self, dm: DirectMessage, receiver: str):
        if receiver is None:
            raise Exception("Missing receiver in direct_message call!!!")

        req = await aiozmq.create_zmq_stream(zmq.REQ)
        await req.transport.connect(receiver)
        message = json.dumps(asdict(dm)).encode()

        req.write([message])

    ####################
    # Helper Functions #
    ####################
    async def subscribe(self, s2p: SubscribeToPublisher):
        self._subscriber.transport.connect(s2p.publisher)
        self._subscriber.transport.subscribe(s2p.topic)

        print(f"[{self.id}] Successfully subscribed to {s2p.publisher}")

    async def init_sockets(self):
        self._subscriber = await aiozmq.create_zmq_stream(zmq.SUB)
        self._publisher = await aiozmq.create_zmq_stream(
            zmq.PUB, bind=self.publisher_bind
        )
        self._router = await aiozmq.create_zmq_stream(zmq.ROUTER, bind=self.router_bind)

        print(f"[{self.id}] Started PUB/SUB Sockets")

    def command(self, command_obj, receiver=None):
        if isinstance(command_obj, DirectMessage):
            asyncio.create_task(self.direct_message(command_obj, receiver))
        if isinstance(command_obj, SubscribeToPublisher):
            asyncio.create_task(self.subscribe(command_obj))
        if type(command_obj) == PublishMessage:
            asyncio.create_task(self.publish(command_obj))

    def stop(self):
        self.running = False
        self._publisher.close()
        self._subscriber.close()
        self._router.close()

    async def start(self):
        asyncio.create_task(self.router_listener())
        asyncio.create_task(self.subscriber_listener())
