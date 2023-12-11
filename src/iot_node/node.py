from attrs import define, field, asdict
from py_ecc.bls import G2ProofOfPossession as bls_pop
import asyncio
import aiozmq
import zmq
import json
import secrets

from .message_classes import DirectMessage
from .message_classes import PublishMessage
from .message_classes import MessageSignatures
from .commad_arg_classes import SubscribeToPublisher
from .commad_arg_classes import UnsubscribeFromTopic


@define
class Node:
    id: str
    router_bind: str
    publisher_bind: str

    _subscriber: aiozmq.stream.ZmqStream = field(init=False)
    _publisher: aiozmq.stream.ZmqStream = field(init=False)
    _router: aiozmq.stream.ZmqStream = field(init=False)
    _private_key: int = field(init=False)
    _public_key: int = field(init=False)

    received_messages: dict = field(factory=dict)
    running: bool = True

    ####################
    # Inbox            #
    ####################
    async def inbox(self, message):
        print(f"[{self.id}] Received Message")
        print(f"[{self.id}] {message}")
        self.received_messages[hash(message)] = message

    ####################
    # Listeners        #
    ####################
    async def router_listener(self):
        print(f"[{self.id}] Starting Router")

        while True:
            if not self.running:
                break

            recv = await self._router.read()

            message = json.loads(recv[2].decode())
            meta_data = json.loads(recv[3].decode())

            if message["message_type"] == "DirectMessage":
                message = DirectMessage(**message)
            else:
                print("Couldnt find matching class for message!!")

            asyncio.create_task(self.inbox(message, meta_data))

    async def subscriber_listener(self):
        print(f"[{self.id}] Starting Subscriber")

        while True:
            if not self.running:
                break

            recv = await self._subscriber.read()

            topic, message, meta_data = recv
            message = json.loads(message.decode())
            meta_data = json.loads(meta_data.decode())

            if message["message_type"] == "PublishMessage":
                message = PublishMessage(**message)
            else:
                print("Couldnt find matching class for message!!")

            asyncio.create_task(self.inbox(message, meta_data))

    ####################
    # Message Sending  #
    ####################
    async def publish(self, pub: PublishMessage):
        message = json.dumps(asdict(pub)).encode()

        self._publisher.write([pub.topic.encode(), message])
        print(f"[{self.id}] Published Message {hash(pub)}")

    async def direct_message(self, message: DirectMessage, receiver: str):
        if receiver is None:
            raise Exception("Missing receiver in direct_message call!!!")

        req = await aiozmq.create_zmq_stream(zmq.REQ)
        await req.transport.connect(receiver)
        message = json.dumps(asdict(message)).encode()

        req.write([message])

    ####################
    # Node 'API'       #
    ####################
    def command(self, command_obj, meta_data=None, receiver=None):
        if isinstance(command_obj, DirectMessage):
            asyncio.create_task(self.direct_message(command_obj, meta_data, receiver))
        if isinstance(command_obj, SubscribeToPublisher):
            asyncio.create_task(self.subscribe(command_obj))
        if isinstance(command_obj, PublishMessage):
            asyncio.create_task(self.publish(command_obj, meta_data))
        if isinstance(command_obj, UnsubscribeFromTopic):
            asyncio.create_task(self.unsubscribe(command_obj))

    ####################
    # Helper Functions #
    ####################
    async def subscribe(self, s2p: SubscribeToPublisher):
        self._subscriber.transport.connect(s2p.publisher)
        self._subscriber.transport.subscribe(s2p.topic)

        print(f"[{self.id}] Successfully subscribed to {s2p.publisher}")

    async def unsubscribe(self, unsub: UnsubscribeFromTopic):
        self._subscriber.transport.unsubscribe(unsub.topic)

    async def init_sockets(self):
        self._subscriber = await aiozmq.create_zmq_stream(zmq.SUB)
        self._publisher = await aiozmq.create_zmq_stream(
            zmq.PUB, bind=self.publisher_bind
        )
        self._router = await aiozmq.create_zmq_stream(zmq.ROUTER, bind=self.router_bind)

        self._private_key = secrets.randbits(128)
        self._public_key = bls_pop.SkToPk(self._private_key)

        print(f"[{self.id}] Started PUB/SUB Sockets")

    def stop(self):
        self.running = False
        self._publisher.close()
        self._subscriber.close()
        self._router.close()

    async def start(self):
        asyncio.create_task(self.router_listener())
        asyncio.create_task(self.subscriber_listener())
