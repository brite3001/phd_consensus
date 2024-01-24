from attrs import define, field, asdict, frozen, validators
from py_ecc.bls import G2ProofOfPossession as bls_pop
from fastecdsa import curve, keys, point
from typing import Type, Tuple, Union
from merkly.mtree import MerkleTree
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
from .message_classes import Gossip
from .message_classes import PeerDiscovery
from .message_classes import EchoSubscribe
from .commad_arg_classes import SubscribeToPublisher
from .commad_arg_classes import UnsubscribeFromTopic
from .at2_classes import AT2Configuration
from logs import get_logger


@frozen
class CryptoKeys:
    ecdsa_private_key: int = field(validator=[validators.instance_of(int)])
    ecdsa_public_key: point.Point = field(
        validator=[validators.instance_of(point.Point)]
    )
    ecdsa_public_key_tuple: tuple = field(validator=[validators.instance_of(tuple)])

    bls_private_key: int = field(validator=[validators.instance_of(int)])
    bls_public_key: bytes = field(validator=[validators.instance_of(bytes)])
    bls_public_key_string: str = field(validator=[validators.instance_of(str)])

    def ecdsa_tuple_to_point(self, ecdsa_tuple: tuple) -> point.Point:
        return point.Point(ecdsa_tuple[0], ecdsa_tuple[1])

    def ecdsa_tuple_or_list_to_id(self, ecdsa: Union[Tuple, dict]) -> str:
        return str(hash(tuple(ecdsa)))[:3]

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
    ecdsa_id: str = field(validator=[validators.instance_of(str)])
    socket: aiozmq.ZmqStream = field(
        validator=[validators.instance_of(aiozmq.ZmqStream)]
    )


@define
class Node:
    router_bind: str = field(validator=[validators.instance_of(str)])
    publisher_bind: str = field(validator=[validators.instance_of(str)])
    at2_config: AT2Configuration = field(
        validator=[validators.instance_of(AT2Configuration)]
    )
    id: str = field(init=False)
    my_logger = field(init=False)

    peers: dict[str, PeerInformation] = field(factory=dict)
    sockets: dict[PeerSocket] = field(factory=dict)

    _subscriber: aiozmq.stream.ZmqStream = field(init=False)
    _publisher: aiozmq.stream.ZmqStream = field(init=False)
    _router: aiozmq.stream.ZmqStream = field(init=False)
    _crypto_keys: CryptoKeys = field(init=False)

    gossip_queue: Queue = field(factory=Queue)
    received_messages: dict = field(factory=dict)
    running: bool = field(factory=bool)

    # Tuneable Values
    minimum_transactions_to_batch: int = field(factory=int)

    # SBRB Specific Variables
    _echo_replies: dict[
        str, str
    ] = {}  # {message_hash: [node_ids that have send an echo reply]}

    ####################
    # Inbox            #
    ####################
    async def inbox(self, message):
        # print(f"[{self.id}] Received Message")

        if isinstance(message, BatchedMessages):
            self.my_logger.info(message)
            # self.received_messages[hash(message)] = message
        elif isinstance(message, EchoSubscribe):
            print(message)
        elif isinstance(message, PeerDiscovery):
            ecdsa_id = self._crypto_keys.ecdsa_tuple_or_list_to_id(
                message.ecdsa_public_key
            )

            self.peers[ecdsa_id] = message

            req = await aiozmq.create_zmq_stream(zmq.REQ)
            await req.transport.connect(message.router_address)

            self.sockets[ecdsa_id] = PeerSocket(message.router_address, ecdsa_id, req)
        elif isinstance(message, DirectMessage):
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

            if len(recv) == 3:
                self.my_logger.info("Received unsigned message")
            elif len(recv) == 5:
                self.my_logger.info("Received signed message (creator signature only)")
            elif len(recv) == 7:
                self.my_logger.info(
                    "Received signed message (creator + sender) signatures"
                )
            else:
                self.my_logger.warning(f"Received message of unknown length! {recv}")

            msg = json.loads(recv[2].decode())

            if msg["message_type"] == "DirectMessage":
                dm = DirectMessage(**msg)
                asyncio.create_task(self.inbox(dm))
            elif msg["message_type"] == "BatchedMessage":
                creator_signature = json.loads(recv[4].decode())
                sender_signature = json.loads(recv[6].decode())
                bm = BatchedMessages(**msg)

                creator_sig_check = bm.verify_creator_and_sender(
                    creator_signature, "creator"
                )
                sender_sig_check = bm.verify_creator_and_sender(
                    sender_signature, "sender"
                )

                creator_id = self._crypto_keys.ecdsa_tuple_or_list_to_id(
                    bm.creator_ecdsa
                )
                sender_id = self._crypto_keys.ecdsa_tuple_or_list_to_id(bm.sender_ecdsa)

                if creator_sig_check and sender_sig_check:
                    self.my_logger.info(
                        f"Received BatchedMessage from: {sender_id} created by {creator_id}"
                    )

                    for message in bm.messages:
                        asyncio.create_task(self.inbox(message))
                else:
                    self.my_logger.warning(
                        f"Signature verification failed for {bm} | creator {creator_id} | sender {sender_id}"
                    )
            elif msg["message_type"] == "PeerDiscovery":
                pd = PeerDiscovery(**msg)
                self.my_logger.info(
                    f"Received Peer Discovery Message from {self._crypto_keys.ecdsa_tuple_or_list_to_id(pd.bls_public_key)}"
                )
                asyncio.create_task(self.inbox(pd))
            elif msg["message_type"] == "EchoSubscribe":
                creator_signature = json.loads(recv[5].decode())
                es = EchoSubscribe(**msg)
                msg_sig_check = es.verify_echo(creator_signature)
                print(msg_sig_check)
                asyncio.create_task(self.inbox(es))
            else:
                self.my_logger.info(f"Received unrecognised message: {msg}")

            self._router.write([recv[0], b"", b"OK"])

    async def subscriber_listener(self):
        self.my_logger.info("Starting Subscriber")

        while True:
            if not self.running:
                break

            recv = await self._subscriber.read()

            topic, message = recv
            message = json.loads(message.decode())

            if message["message_type"] == "PublishMessage":
                message = PublishMessage(**message)
            else:
                self.my_logger.warning("Couldnt find matching class for message!!")

            asyncio.create_task(self.inbox(message))

    ####################
    # Message Sending  #
    ####################
    async def publish(self, pub: PublishMessage):
        message = json.dumps(asdict(pub)).encode()

        self._publisher.write([pub.topic.encode(), message])
        self.my_logger.info(f"Published Message {hash(pub)}")

    async def unsigned_direct_message(self, message: Type[DirectMessage], receiver=""):
        assert issubclass(type(message), DirectMessage)

        if len(receiver) == 0:
            peer_socket = random.choice(self.sockets)
            req = peer_socket.socket
        else:
            req = await aiozmq.create_zmq_stream(zmq.REQ)
            await req.transport.connect(receiver)

        message = json.dumps(asdict(message)).encode()
        req.write([message])

    async def signed_batched_message(
        self,
        bm: BatchedMessages,
        receiver="",
    ):
        if len(receiver) == 0:
            peer_socket = random.choice(self.sockets)
            req = peer_socket.socket
        else:
            req = await aiozmq.create_zmq_stream(zmq.REQ)
            await req.transport.connect(receiver)

        creator_sig = json.dumps(bm.sign_as_creator(self._crypto_keys)).encode()
        sender_sig = json.dumps(bm.sign_as_sender(self._crypto_keys)).encode()

        message = json.dumps(asdict(bm)).encode()
        req.write([message, b"", creator_sig, b"", sender_sig])

    async def signed_echo(self, echo: EchoSubscribe, receiver: str):
        # the receiver is a key for a peer in the self.peers dict
        echo_sig = echo.sign_echo(self._crypto_keys)

        message = json.dumps(asdict(echo)).encode()

    ####################
    # AT2 Consensus    #
    ####################
    async def gossip(self, gossip: Gossip):
        self.gossip_queue.put(gossip)

        if self.gossip_queue.qsize() >= self.minimum_transactions_to_batch:
            messages = []

            while not self.gossip_queue.empty():
                messages.append(self.gossip_queue.get())

            # Batched Message Setup
            mtree = MerkleTree([str(hash(x)) for x in messages])

            bm = BatchedMessages(
                message_type="BatchedMessage",
                creator_bls=self._crypto_keys.bls_public_key_string,
                creator_ecdsa=self._crypto_keys.ecdsa_public_key_tuple,
                sender_ecdsa=self._crypto_keys.ecdsa_public_key_tuple,
                messages=tuple(messages),
                messages_agg_sig=self.sign_messages_with_BLS(messages),
                merkle_root=mtree.root,
            )

            batched_message_hash = hash(bm)

            # # Part 1
            echo_subscribe = random.sample(
                list(self.sockets), self.at2_config.echo_sample_size
            )

            es = EchoSubscribe(
                "EchoSubscribe",
                batched_message_hash,
                self._crypto_keys.ecdsa_public_key_tuple,
            )

            for peer_socket in echo_subscribe:
                self.command(es, peer_socket)

            # for node in echo_subscribe:
            #     asyncio.create_task(
            #         self.direct_message(es, self.peers[node].router_address)
            #     )

            # Part 2
            # for peer_id in echo_subscribe:
            #     await self.subscribe(self.peers[peer_id], batched_message_bytes)

            # ready_subscribe = random.sample(
            #     list(self.peers), self.at2_config.ready_sample_size
            # )

            # print(echo_subscribe)
            # print(ready_subscribe)

            # for peer in echo_subscribe:
            #     self.subscribe(peer, batched_message_hash.encode())

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
            echo_replies
            ready_replies
            delivery_replies

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
            8b) you receive at least feedback threshold Ready messages from your ready_subscribe group

            10) once you receive at least delivery_sample_size Ready messages, the message is considered Delivered
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
    # Node Message Bus #
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
        elif issubclass(type(command_obj), BatchedMessages):
            asyncio.create_task(self.signed_batched_message(command_obj, receiver))
        elif issubclass(type(command_obj), EchoSubscribe):
            asyncio.create_task(self.signed_echo(command_obj, receiver))
        elif issubclass(type(command_obj), DirectMessage):
            asyncio.create_task(self.unsigned_direct_message(command_obj, receiver))
        else:
            self.my_logger.warning(f"Unrecognised command object: {command_obj}")

    ####################
    # Helper Functions #
    ####################

    def sign_messages_with_BLS(self, messages):
        # Messages are signed with the BLS private key
        messages_as_bytes = [json.dumps(asdict(x)).encode() for x in messages]
        sigs = []
        agg_sig = None

        for msg_byte in messages_as_bytes:
            sigs.append(bls_pop.Sign(self._crypto_keys.bls_private_key, msg_byte))

        # Don't aggregate if we only have 1 signature
        if len(sigs) > 1:
            agg_sig = bls_pop.Aggregate(sigs)
        else:
            agg_sig = sigs[0]

        # return as base64 for easier serialisation
        return base64.b64encode(agg_sig).decode("utf-8")

    async def peer_discovery(self, routers: list):
        pd = PeerDiscovery(
            message_type="PeerDiscovery",
            bls_public_key=self._crypto_keys.bls_public_key,
            ecdsa_public_key=self._crypto_keys.ecdsa_public_key_tuple,
            router_address=self.router_bind,
            publisher_address=self.publisher_bind,
        )

        routers.remove(self.router_bind)

        for ip in routers:
            self.command(pd, ip)

    async def subscribe(self, peer_info: PeerInformation, topic: bytes):
        assert isinstance(peer_info, PeerInformation)
        assert isinstance(topic, bytes)
        self._subscriber.transport.connect(peer_info.publisher_address)
        self._subscriber.transport.subscribe(topic)

        self.my_logger.info(
            f"Successfully Subscribed to {peer_info.publisher_address}/{topic}"
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
        ecdsa_public_key_tuple = (ecdsa_public_key.x, ecdsa_public_key.y)

        bls_private_key = secrets.randbits(128)
        bls_public_key = bls_pop.SkToPk(bls_private_key)
        bls_public_key_string = base64.b64encode(bls_public_key).decode("utf-8")

        self._crypto_keys = CryptoKeys(
            ecdsa_private_key,
            ecdsa_public_key,
            ecdsa_public_key_tuple,
            bls_private_key,
            bls_public_key,
            bls_public_key_string,
        )

        self.id = str(hash(self._crypto_keys.ecdsa_public_key_tuple))[:3]

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
