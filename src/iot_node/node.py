from attrs import define, field, asdict, frozen, validators
from py_ecc.bls import G2ProofOfPossession as bls_pop
from fastecdsa import curve, keys, point
from typing import Union, Type
import base64
import asyncio
import aiozmq
import zmq
import json
import secrets
from queue import Queue

from .message_classes import DirectMessage
from .message_classes import PublishMessage
from .message_classes import BatchedMessages
from .message_classes import BatchedMessageBuilder
from .message_classes import Gossip
from .message_classes import PeerDiscovery
from .commad_arg_classes import SubscribeToPublisher
from .commad_arg_classes import UnsubscribeFromTopic


@frozen
class CryptoKeys:
    ecdsa_private_key: int = field(validator=[validators.instance_of(int)])
    ecdsa_public_key: point.Point = field(
        validator=[validators.instance_of(point.Point)]
    )
    ecdsa_public_key_dict: dict = field(validator=[validators.instance_of(dict)])

    bls_private_key: int = field(validator=[validators.instance_of(int)])
    bls_public_key: bytes = field(validator=[validators.instance_of(bytes)])
    bls_public_key_string: str = field(validator=[validators.instance_of(str)])

    def ecdsa_dict_to_point(self, ecdsa_dict: dict) -> point.Point:
        return point.Point(ecdsa_dict["x"], ecdsa_dict["y"])

    def ecdsa_dict_to_id(self, ecdsa_dict: dict) -> str:
        return str(hash(json.dumps(ecdsa_dict)))[:3]

    def bls_bytes_to_base64(self, bls_bytes: bytes) -> base64:
        base64.b64encode(bls_bytes).decode("utf-8")

    def bls_base64_to_bytes(self, bls_base64: base64) -> bytes:
        return base64.b64decode(bls_base64)

    def bls_bytes_to_id(self, bls_bytes: bytes) -> str:
        return str(hash(bls_bytes))[:3]


@frozen
class PeerInformation:
    bls_public_key: bytes = field(validator=[validators.instance_of(bytes)])
    ecdsa_public_key: point.Point = field(
        validator=[validators.instance_of(point.Point)]
    )
    router_address: str = field(validator=[validators.instance_of(str)])
    publisher_address: str = field(validator=[validators.instance_of(str)])


@define
class Node:
    router_bind: str = field(validator=[validators.instance_of(str)])
    publisher_bind: str = field(validator=[validators.instance_of(str)])
    id: str = field(init=False)

    # {'bls_id': PeerInformation}
    peers: dict = field(factory=dict)

    _subscriber: aiozmq.stream.ZmqStream = field(init=False)
    _publisher: aiozmq.stream.ZmqStream = field(init=False)
    _router: aiozmq.stream.ZmqStream = field(init=False)
    _crypto_keys: CryptoKeys = field(init=False)

    minimum_transactions_to_batch: int = field(factory=int)
    gossip_queue: Queue = field(factory=Queue)
    received_messages: dict = field(factory=dict)
    running: bool = field(factory=bool)

    ####################
    # Inbox            #
    ####################
    async def inbox(self, message):
        # print(f"[{self.id}] Received Message")

        if isinstance(message, Gossip):
            print(f"[{self.id}] {message}")
            self.received_messages[hash(message)] = message
        elif isinstance(message, PeerDiscovery):
            bls_id = self._crypto_keys.bls_bytes_to_id(message.bls_public_key)
            ecdsa_point = self._crypto_keys.ecdsa_dict_to_point(
                message.ecdsa_public_key
            )
            self.peers[bls_id] = PeerInformation(
                message.bls_public_key,
                ecdsa_point,
                message.router_address,
                message.publisher_address,
            )

    ####################
    # Listeners        #
    ####################
    async def router_listener(self):
        print(f"[{self.id}] Starting Router")

        while True:
            if not self.running:
                break

            recv = await self._router.read()

            msg = json.loads(recv[2].decode())

            if msg["message_type"] == "DirectMessage":
                dm = DirectMessage(**msg)
                asyncio.create_task(self.inbox(dm))
            elif msg["message_type"] == "BatchedMessageBuilder":
                bm = BatchedMessages(**msg)
                msg_sig_check, sender_sig_check = bm.verify_signatures()

                if msg_sig_check and sender_sig_check:
                    sender = self._crypto_keys.ecdsa_dict_to_id(bm.sender_info.sender)
                    creator = self._crypto_keys.bls_bytes_to_id(bm.creator)
                    print(
                        f"[{self.id}] Received BatchedMessage from: {sender} created by {creator}"
                    )

                    for message in bm.messages:
                        asyncio.create_task(self.inbox(message))
            elif msg["message_type"] == "PeerDiscovery":
                print("Received Peer Discovery Message")
                key_ex = PeerDiscovery(**msg)
                asyncio.create_task(self.inbox(key_ex))
            else:
                print(f"Received unrecognised message: {msg}")

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

    async def direct_message(self, message: Type[DirectMessage], receiver: str):
        assert issubclass(type(message), DirectMessage)

        req = await aiozmq.create_zmq_stream(zmq.REQ)
        await req.transport.connect(receiver)
        message = json.dumps(asdict(message)).encode()

        req.write([message])

    async def gossip(self, gossip: Gossip, receiver: str):
        self.gossip_queue.put(gossip)

        if self.gossip_queue.qsize() >= self.minimum_transactions_to_batch:
            bmb = BatchedMessageBuilder(
                message_type="BatchedMessageBuilder",
                creator=self._crypto_keys.bls_public_key,
            )

            while not self.gossip_queue.empty():
                bmb.messages.append(self.gossip_queue.get())

            bmb.sign_messages(self._crypto_keys)
            bmb.sign_sender(self._crypto_keys)

            """
            TODO: replace with proper AT2 Gossip...
            """
            asyncio.create_task(self.direct_message(bmb, receiver))

    ####################
    # Node 'API'       #
    ####################
    def command(self, command_obj, receiver=None):
        if isinstance(command_obj, SubscribeToPublisher):
            asyncio.create_task(self.subscribe(command_obj))
        elif isinstance(command_obj, Gossip):
            asyncio.create_task(self.gossip(command_obj, receiver))
        elif isinstance(command_obj, PublishMessage):
            asyncio.create_task(self.publish(command_obj))
        elif isinstance(command_obj, UnsubscribeFromTopic):
            asyncio.create_task(self.unsubscribe(command_obj))
        elif issubclass(type(command_obj), DirectMessage):
            asyncio.create_task(self.direct_message(command_obj, receiver))
        else:
            print(f"Unrecognised command object: {command_obj}")

    ####################
    # Helper Functions #
    ####################

    async def peer_discovery(self, routers: list):
        pd = PeerDiscovery(
            message_type="PeerDiscovery",
            bls_public_key=self._crypto_keys.bls_public_key,
            ecdsa_public_key=self._crypto_keys.ecdsa_public_key_dict,
            router_address=self.router_bind,
            publisher_address=self.publisher_bind,
        )

        routers.remove(self.router_bind)

        for ip in routers:
            asyncio.create_task(self.direct_message(pd, ip))

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

        ecdsa_private_key = keys.gen_private_key(curve.P256)
        ecdsa_public_key = keys.get_public_key(ecdsa_private_key, curve.P256)
        ecdsa_public_key_dict = {}
        ecdsa_public_key_dict["x"] = ecdsa_public_key.x
        ecdsa_public_key_dict["y"] = ecdsa_public_key.y

        bls_private_key = secrets.randbits(128)
        bls_public_key = bls_pop.SkToPk(bls_private_key)
        bls_public_key_string = base64.b64encode(bls_public_key).decode("utf-8")

        self._crypto_keys = CryptoKeys(
            ecdsa_private_key,
            ecdsa_public_key,
            ecdsa_public_key_dict,
            bls_private_key,
            bls_public_key,
            bls_public_key_string,
        )

        self.id = self._crypto_keys.bls_bytes_to_id(self._crypto_keys.bls_public_key)

        print(f"[{self.id}] Started PUB/SUB Sockets")

    def stop(self):
        self.running = False
        self._publisher.close()
        self._subscriber.close()
        self._router.close()

    async def start(self):
        self.running = True
        self.minimum_transactions_to_batch = 5
        asyncio.create_task(self.router_listener())
        asyncio.create_task(self.subscriber_listener())
