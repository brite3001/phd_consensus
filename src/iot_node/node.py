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
import random
from queue import Queue

from .message_classes import DirectMessage
from .message_classes import PublishMessage
from .message_classes import BatchedMessages
from .message_classes import BatchedMessageBuilder
from .message_classes import Gossip
from .message_classes import PeerDiscovery
from .commad_arg_classes import SubscribeToPublisher
from .commad_arg_classes import UnsubscribeFromTopic
from logs import get_logger


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
class PeerSocket:
    router_address: str = field(validator=[validators.instance_of(str)])
    bls_id: str = field(validator=[validators.instance_of(str)])
    socket: aiozmq.ZmqStream = field(
        validator=[validators.instance_of(aiozmq.ZmqStream)]
    )


@define
class Node:
    router_bind: str = field(validator=[validators.instance_of(str)])
    publisher_bind: str = field(validator=[validators.instance_of(str)])
    id: str = field(init=False)
    my_logger = field(init=False)

    peers: dict[str, PeerInformation] = field(factory=dict)
    sockets: list[PeerSocket] = field(factory=list)

    _subscriber: aiozmq.stream.ZmqStream = field(init=False)
    _publisher: aiozmq.stream.ZmqStream = field(init=False)
    _router: aiozmq.stream.ZmqStream = field(init=False)
    _crypto_keys: CryptoKeys = field(init=False)

    gossip_queue: Queue = field(factory=Queue)
    received_messages: dict = field(factory=dict)
    running: bool = field(factory=bool)

    # Tuneable Values
    minimum_transactions_to_batch: int = field(factory=int)

    ####################
    # Inbox            #
    ####################
    async def inbox(self, message):
        # print(f"[{self.id}] Received Message")

        if isinstance(message, Gossip):
            self.my_logger.info(message)
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

            req = await aiozmq.create_zmq_stream(zmq.REQ)
            await req.transport.connect(message.router_address)

            self.sockets.append(PeerSocket(message.router_address, bls_id, req))
        elif isinstance(message, DirectMessage):
            print("aaa")
            self.my_logger.info(message)

    ####################
    # Listeners        #
    ####################
    async def router_listener(self):
        self.my_logger.info("Starting Router")

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
                    sender = self._crypto_keys.ecdsa_dict_to_point(
                        bm.sender_info.sender
                    )
                    sender_bls_id = "Unknown"

                    # Find peers BLS ID based off their ECDSA key
                    for peer in self.peers.values():
                        if sender == peer.ecdsa_public_key:
                            sender_bls_id = self._crypto_keys.bls_bytes_to_id(
                                peer.bls_public_key
                            )
                    creator = self._crypto_keys.bls_bytes_to_id(bm.creator)
                    self.my_logger.info(
                        f"Received BatchedMessage from: {sender_bls_id} created by {creator}"
                    )

                    for message in bm.messages:
                        asyncio.create_task(self.inbox(message))
            elif msg["message_type"] == "PeerDiscovery":
                key_ex = PeerDiscovery(**msg)
                self.my_logger.info(
                    f"Received Peer Discovery Message from {self._crypto_keys.bls_bytes_to_id(key_ex.bls_public_key)}"
                )
                asyncio.create_task(self.inbox(key_ex))
            else:
                self.my_logger.info(f"Received unrecognised message: {msg}")

            self._router.write([recv[0], b"", b"OK"])

    async def subscriber_listener(self):
        self.my_logger.info("Starting Subscriber")

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
                self.my_logger.warning("Couldnt find matching class for message!!")

            asyncio.create_task(self.inbox(message, meta_data))

    ####################
    # Message Sending  #
    ####################
    async def publish(self, pub: PublishMessage):
        message = json.dumps(asdict(pub)).encode()

        self._publisher.write([pub.topic.encode(), message])
        self.my_logger.info(f"Published Message {hash(pub)}")

    async def direct_message(self, message: Type[DirectMessage], receiver=""):
        assert issubclass(type(message), DirectMessage)

        if len(receiver) == 0:
            peer_socket = random.choice(self.sockets)
            req = peer_socket.socket
        else:
            req = await aiozmq.create_zmq_stream(zmq.REQ)
            await req.transport.connect(receiver)

        message = json.dumps(asdict(message)).encode()
        req.write([message])

    async def gossip(self, gossip: Gossip):
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
            asyncio.create_task(self.direct_message(bmb))

            # setup variables
            """
            Subscribing and sample sizes
            echo_subscribe / echo_sample_size
            ready_subscribe / ready_sample_size / delivery_sample_size

            Thresholds
            ready_threshold
            feedback_threshold
            delivery_threshold

            
            Echo responses
            replies_echo
            replies_ready
            replies_deliery

            Message index    
            """

            # Algorithm (Sender)
            """
            Setup
            1) Create an echo_subscribe group of size echo_sample_size
            2) Subscribe to the publisher of all nodes in echo_subscribe
            3) Send all nodes in echo_subscribe an EchoSubscribe message

            3) Create a ready_subscribe group of size ready_sample_size
            4) Subscribe to the publisher of all nodes in ready_subscribe
            5) Send all nodes in ready_subscribe a ReadySubscribe message

            6) Increment the message index
            7) Send the message to all nodes in echo_subscribe group

            8) Send a READY message if either:
            8a) you receive at least ready_threshold Echo messages from your echo_subscribe group
            8b) you receive at least feed_back threshold Ready messages from your ready_subscribe group

            9) once you receive at least delivery_sample_size Ready messages, the message is considered Delivered
            """

            # Algorithm (Gossiper)
            """
            Basically same as above, except a little check is added which may avoid sending the message again.
            When sending an EchoSubscribe message and a ReadySubscribe message, if the nodes in your echo_subscribe
            and ready_subscribe groups have already reached the
            ready_threshold and the feedback_threshold, the node will again broadcast an Echo or Ready message.

            Node receives lots of Ready Messages
            If the gossiping node receives feedback_threshold number of Ready messages, they'll also send out a
            Ready message. If they receive delivery_threshold number of messages, the node will just immediately
            Deliver the message to the application.

            Node receives few Ready messages
            If the node doesn't hit the feedback threshold for their ready_subscribe group when sending a 
            ReadySubscribe message, the node will send the orginal message and gossip it. The gossiper
            will not increment the message index, they'll maintain the index chosen by the creator

            """

    ####################
    # Node 'API'       #
    ####################
    def command(self, command_obj, receiver=""):
        if isinstance(command_obj, SubscribeToPublisher):
            asyncio.create_task(self.subscribe(command_obj))
        elif isinstance(command_obj, Gossip):
            asyncio.create_task(self.gossip(command_obj))
        elif isinstance(command_obj, PublishMessage):
            asyncio.create_task(self.publish(command_obj))
        elif isinstance(command_obj, UnsubscribeFromTopic):
            asyncio.create_task(self.unsubscribe(command_obj))
        elif issubclass(type(command_obj), DirectMessage):
            asyncio.create_task(self.direct_message(command_obj, receiver))
        else:
            self.my_logger.warning(f"Unrecognised command object: {command_obj}")

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

        self.my_logger.info(
            "Successfully Subscribed", extra={"published": s2p.publisher}
        )

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

        self.my_logger = get_logger(self.id)

        self.my_logger.info("Started PUB/SUB Sockets", extra={"published": "aaaa"})

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
