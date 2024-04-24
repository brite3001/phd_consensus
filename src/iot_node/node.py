from attrs import define, field, asdict, frozen, validators
from py_ecc.bls import G2ProofOfPossession as bls_pop
from fastecdsa import curve, keys, point
from merkly.mtree import MerkleTree
from collections import defaultdict
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from talipp.indicators import ZLEMA, RSI, SMA, EMA, KAMA, TEMA, TSI
from scipy.stats import poisson, norm
from typing import Union
from sortedcontainers import SortedSet
import base64
import asyncio
import aiozmq
import zmq
import json
import secrets
import random
import time
import math

from .message_classes import DirectMessage
from .message_classes import PublishMessage
from .message_classes import BatchedMessages
from .message_classes import Gossip
from .message_classes import PeerDiscovery
from .message_classes import Echo
from .message_classes import Response
from .commad_arg_classes import SubscribeToPublisher
from .commad_arg_classes import UnsubscribeFromTopic
from .at2_classes import AT2Configuration
from .kalman import kalman_filter
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

    def ecdsa_tuple_to_id(self, ecdsa: tuple) -> str:
        assert isinstance(ecdsa, tuple)
        return str(hash(ecdsa))[:3]

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

    # Info about our peers
    peers: dict[str, PeerInformation] = field(factory=dict)  # str == ECDSA ID
    sockets: dict[str, PeerSocket] = field(factory=dict)  # str == ECDSA ID

    # AIOZMQ Sockets
    _subscriber: aiozmq.stream.ZmqStream = field(init=False)
    _publisher: aiozmq.stream.ZmqStream = field(init=False)
    _router: aiozmq.stream.ZmqStream = field(init=False)
    connected_subscribers: set = field(factory=set)  # stores peer_ids
    subscribed_topics: set = field(factory=set)  # stores topics as bytes
    rep_lock = field(factory=lambda: asyncio.Lock())

    _crypto_keys: CryptoKeys = field(init=False)
    running: bool = field(factory=bool)

    # Tuneable Values
    target_latency: int = 10
    current_latency: int = field(factory=int)
    max_gossip_timeout_time = 60
    node_selection_type = "normal"
    random_seed = 2929

    # Congestion control
    scheduler = field(init=False)
    pending_gossips: list[Gossip] = field(factory=list)
    pending_responses: list[Response] = field(factory=list)
    batched_message_job_id = field(init=False)
    increase_job_id = field(init=False)
    decrease_job_id = field(init=False)
    block_times: list = field(factory=list)
    job_time_change_flag: bool = field(factory=bool)

    # SBRB Specific Variables #
    received_messages: dict[str, BatchedMessages] = field(factory=dict)
    already_received: defaultdict[str, set] = field(factory=lambda: defaultdict(set))

    # str == msg_hash, set() of peer_ids
    echo_replies: defaultdict[str, set] = field(factory=lambda: defaultdict(set))
    ready_replies: defaultdict[str, set] = field(factory=lambda: defaultdict(set))

    # Sequencing
    # str == node_id
    vector_clock: defaultdict[str, int] = field(factory=lambda: defaultdict(int))
    sequenced_messages = field(factory=lambda: SortedSet())

    # Statistics
    sent_gossips: int = field(factory=int)
    received_gossips: int = field(factory=int)
    delivered_gossips: int = field(factory=int)
    sent_msg_metadata: list = field(factory=list)
    received_msg_metadata: list = field(factory=list)

    ####################
    # Inbox            #
    ####################
    async def inbox(self, message):
        # print(f"[{self.id}] Received Message")

        if isinstance(message, BatchedMessages):
            self.received_gossips += 1
            bm_hash = str(hash(message))
            if bm_hash not in self.received_messages:
                bm_creator = self._crypto_keys.ecdsa_tuple_to_id(message.creator_ecdsa)
                self.received_messages[bm_hash] = message
                self.vector_clock[bm_creator] += 1

                # vc_int = sum(list(self.vector_clock.values()))
                # if vc_int % self.call_committee_meeting_every_n_messages == 0:
                #     round_num = int(
                #         vc_int / self.call_committee_meeting_every_n_messages
                #     )
                #     await self.rank_nodes(round_num)

                es = Response(
                    "EchoResponse",
                    str(bm_hash),
                    self._crypto_keys.ecdsa_public_key_tuple,
                )
                self.command(es)

                bm = message.become_sender(self._crypto_keys)
                # regossip the message from the original creator, now with you as sender
                asyncio.create_task(self.gossip(bm))

        elif isinstance(message, Echo):
            if message.message_type == "EchoSubscribe":
                if message.batched_messages_hash in self.received_messages:
                    # publish an echo_reply for that particular message hash
                    es = Response(
                        "EchoResponse",
                        message.batched_messages_hash,
                        self._crypto_keys.ecdsa_public_key_tuple,
                    )
                    self.command(es)
                else:
                    # if you haven't received the message yet, ignore
                    pass
            if message.message_type == "ReadySubscribe":
                if (
                    len(self.ready_replies[message.batched_messages_hash])
                    >= self.at2_config.feedback_threshold
                ):
                    ready = Response(
                        "ReadyResponse",
                        message.batched_messages_hash,
                        self._crypto_keys.ecdsa_public_key_tuple,
                    )
                    self.command(ready)
        elif isinstance(message, PeerDiscovery):
            ecdsa_id = self._crypto_keys.ecdsa_tuple_to_id(message.ecdsa_public_key)

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
        self.my_logger.debug("Starting Router")

        while True:
            if not self.running:
                break

            recv = await self._router.read()

            # if len(recv) == 3:
            #     self.my_logger.info("Received unsigned message")
            #     pass
            # elif len(recv) == 5:
            #     self.my_logger.info("Received signed message (creator)")
            # elif len(recv) == 7:
            #     self.my_logger.info("Received signed message (creator + sender)")
            # else:
            #     self.my_logger.warning(f"Received message of unknown length! {recv}")

            msg = json.loads(recv[2].decode())
            router_response = b"OK"

            if msg["message_type"] == "DirectMessage":
                dm = DirectMessage(**msg)
                asyncio.create_task(self.inbox(dm))
            if msg["message_type"] == "BatchedMessage":
                msg["messages"] = tuple([Gossip(**x) for x in msg["messages"]])
                bm = BatchedMessages(**msg)
                bm_hash = str(hash(bm))

                if bm_hash not in self.received_messages:
                    creator_signature = json.loads(recv[4].decode())
                    sender_signature = json.loads(recv[6].decode())

                    creator_sig_check = bm.verify_creator_and_sender(
                        creator_signature, "creator"
                    )
                    sender_sig_check = bm.verify_creator_and_sender(
                        sender_signature, "sender"
                    )
                    # agg_msg_sig_check = bm.verify_aggregated_bls_signature()
                    agg_msg_sig_check = True

                    # bm_vector_clock_int = sum(value for key, value in bm.vector_clock)
                    # our_vector_clock_int = sum(
                    #     value for key, value in self.vector_clock.items()
                    # )

                    # acceptable_lag = (
                    #     True
                    #     if bm_vector_clock_int
                    #     >= our_vector_clock_int - self.vector_clock_lag
                    #     else False
                    # )

                    creator_id = self._crypto_keys.ecdsa_tuple_to_id(bm.creator_ecdsa)
                    sender_id = self._crypto_keys.ecdsa_tuple_to_id(bm.sender_ecdsa)

                    if creator_sig_check and sender_sig_check and agg_msg_sig_check:
                        self.my_logger.info(
                            f"Received BatchedMessage {bm_hash} from: {sender_id} created by {creator_id}"
                        )

                        asyncio.create_task(self.inbox(bm))
                    else:
                        self.my_logger.error(
                            f"Signature verification failed for {bm} | creator {creator_id} | sender {sender_id}"
                        )
                else:
                    self.my_logger.debug(f"Already received BM: {bm_hash}")
            elif msg["message_type"] == "PeerDiscovery":
                pd = PeerDiscovery(**msg)
                creator_id = self._crypto_keys.ecdsa_tuple_to_id(pd.ecdsa_public_key)
                # self.my_logger.info(
                #     f"Received Peer Discovery Message from {creator_id}"
                # )
                asyncio.create_task(self.inbox(pd))
            elif msg["message_type"] in ["EchoSubscribe", "ReadySubscribe"]:
                echo_type = msg["message_type"]
                creator_signature = json.loads(recv[4].decode())
                es = Echo(**msg)
                msg_sig_check = es.verify_message(creator_signature)

                creator_id = self._crypto_keys.ecdsa_tuple_to_id(es.creator)

                # self.my_logger.info(
                #     f"Received {echo_type} from {creator_id} for BatchedMessage {es.batched_messages_hash}"
                # )

                # Tells the sender not to send this BatchedMessage to us again. We already have it.
                if es.batched_messages_hash in self.received_messages:
                    router_response = b"ALREADY_RECEIVED"

                if msg_sig_check:
                    asyncio.create_task(self.inbox(es))
                else:
                    self.my_logger.warning(
                        f"Signature verification on {echo_type} from {creator_id} failed {es}"
                    )
            else:
                self.my_logger.error(f"Received unrecognised message: {msg}")

            self._router.write([recv[0], b"", router_response])

    async def subscriber_listener(self):
        self.my_logger.debug("Starting Subscriber")
        while True:
            if not self.running:
                break
            recv = await self._subscriber.read()
            # if len(recv) == 2:
            #     self.my_logger.info("Received unsigned published message")
            # elif len(recv) == 3:
            #     self.my_logger.info("Received signed published message")
            # topic is recv[0]
            message = recv[1]
            message = json.loads(message.decode())
            if message["message_type"] == "EchoResponse":
                message = Response(**message)
                echo_sig = json.loads(recv[2].decode())
                sig_check = message.verify_echo_response(echo_sig)
                publisher = self._crypto_keys.ecdsa_tuple_to_id(message.creator)
                self.my_logger.debug(
                    f"Received EchoResponse for {message.topic} from {publisher}"
                )
                if sig_check:
                    self.echo_replies[message.topic].add(publisher)
                else:
                    self.my_logger.warning(
                        f"Signature check for message {message.topic} from {publisher} failed!!"
                    )
            elif message["message_type"] == "ReadyResponse":
                message = Response(**message)
                echo_sig = json.loads(recv[2].decode())
                sig_check = message.verify_echo_response(echo_sig)
                publisher = self._crypto_keys.ecdsa_tuple_to_id(message.creator)
                self.my_logger.debug(
                    f"Received ReadyResponse for {message.topic} from {publisher}"
                )
                if sig_check:
                    self.ready_replies[message.topic].add(publisher)
                else:
                    self.my_logger.warning(
                        f"Signature check for message {message.topic} from {publisher} failed!!"
                    )

    ####################
    # Message Sending  #
    ####################
    async def unsigned_publish(self, pub: PublishMessage):
        message = json.dumps(asdict(pub)).encode()

        self._publisher.write([pub.topic.encode(), message])
        self.my_logger.info(f"Published Message {hash(pub)}")

    async def unsigned_direct_message(self, message: DirectMessage, receiver=""):
        assert issubclass(type(message), DirectMessage)

        if len(receiver) == 0:
            peer_socket = random.choice(self.sockets)
            req = peer_socket.socket
        else:
            req = await aiozmq.create_zmq_stream(zmq.REQ)
            await req.transport.connect(receiver)

        message = json.dumps(asdict(message)).encode()

        async with self.rep_lock:
            req.write([message])
            await req.read()

    async def send_signed_batched_message(
        self,
        bm: BatchedMessages,
        receiver="",
    ):
        creator_sig = json.dumps(bm.sign_as_creator(self._crypto_keys)).encode()
        sender_sig = json.dumps(bm.sign_as_sender(self._crypto_keys)).encode()

        message = json.dumps(asdict(bm)).encode()

        req_socket = self.sockets[receiver].socket

        # Allow access to this socket one message at a time
        async with self.rep_lock:
            req_socket.write([message, b"", creator_sig, b"", sender_sig])
            await req_socket.read()

    async def send_signed_message(self, message: Echo, receiver: str):
        # the receiver is an ECDSA ID
        message_sig = json.dumps(message.sign_message(self._crypto_keys)).encode()

        message = json.dumps(asdict(message)).encode()

        req_socket = self.sockets[receiver].socket

        async with self.rep_lock:
            req_socket.write([message, b"", message_sig])
            resp = await req_socket.read()

            if resp[0] == b"ALREADY_RECEIVED" and isinstance(message, Echo):
                self.already_received[message.batched_messages_hash].add(receiver)

    async def publish_signed_echo_response(self, to_publish: Response):
        message = json.dumps(asdict(to_publish)).encode()
        echo_sig = json.dumps(to_publish.sign(self._crypto_keys)).encode()
        self._publisher.write([to_publish.topic.encode(), message, echo_sig])

    ######################
    # Congestion Control #
    ######################

    async def ready_response_queue(self, response: Response):
        if response not in self.pending_responses:
            self.pending_responses.append(response)

    async def batched_message_queue(self, gossip: Gossip):
        self.pending_gossips.append(gossip)

    async def batch_message_builder_job(self):
        if len(self.pending_gossips) >= 1:
            mtree = MerkleTree([str(hash(x)) for x in self.pending_gossips])

            bm = BatchedMessages(
                message_type="BatchedMessage",
                creator_bls=self._crypto_keys.bls_public_key_string,
                creator_ecdsa=self._crypto_keys.ecdsa_public_key_tuple,
                sender_ecdsa=self._crypto_keys.ecdsa_public_key_tuple,
                messages=tuple(self.pending_gossips),
                # aggregated_bls_signature=self.sign_messages_with_BLS(messages),
                aggregated_bls_signature="111",
                merkle_root=mtree.root.hex(),
                vector_clock=self.vector_clock.items(),
            )

            asyncio.create_task(self.gossip(bm))

            self.sent_gossips += 1
            self.sent_msg_metadata.append(
                (len(self.pending_gossips), time.time(), self.id)
            )
            self.pending_gossips.clear()

        if self.job_time_change_flag:
            self.scheduler.remove_job(self.batched_message_job_id)
            updated_job = self.scheduler.add_job(
                self.batch_message_builder_job,
                trigger="interval",
                seconds=self.current_latency,
            )
            self.batched_message_job_id = updated_job.id
            self.job_time_change_flag = False

    async def increasing_congestion_monitoring_job(self):
        from scipy.signal import savgol_filter

        # mee = [random.uniform(1.01, 1.1) for _ in range(45)]
        # mee = SMA(21, mee)
        # print(mee)
        # print(len(mee))
        # tsi = TSI(9, 15, mee)
        # print(tsi)
        # print(tsi[-1])

        await asyncio.sleep(random.uniform(0.1, 2.5))
        # Increase the block time if we start overshooting the target
        if len(self.block_times) >= 20:
            # filtered_zlema = kalman_filter(ZLEMA(14, self.block_times))
            # filtered_zlema = savgol_filter(self.block_times, 14, 1)
            # filtered_zlema = [x for x in SMA(14, self.block_times) if x]
            # filtered_zlema = [x for x in EMA(14, self.block_times) if x]
            filtered_zlema = [x for x in KAMA(14, 2, 30, self.block_times) if x]

            if len(filtered_zlema) >= 15:
                # rsi = int(RSI(14, filtered_zlema)[-1])
                rsi = TSI(3, 6, filtered_zlema)[-1]

                increase = random.uniform(1.01, 1.1)

                dont_exceed_max_target = (
                    self.current_latency * increase < self.max_gossip_timeout_time
                )

                # Stops current_latency increase when network has low latency.
                network_not_slow = (
                    False if filtered_zlema[-1] < self.target_latency else True
                )

                # TSI +30
                if rsi > 30 and dont_exceed_max_target and network_not_slow:
                    self.current_latency = round(self.current_latency * increase, 3)
                    self.my_logger.error(
                        f"Congestion Control [{round(filtered_zlema[-1], 3)}] - [{rsi}] (/\) - New Target: {self.current_latency}"
                    )
                    self.job_time_change_flag = True

    async def decrease_congestion_monitoring_job(self):
        from scipy.signal import savgol_filter

        # Increase the block time if we start overshooting the target
        if len(self.block_times) >= 45:
            # filtered_zlema = kalman_filter(ZLEMA(21, self.block_times))
            # filtered_zlema = savgol_filter(self.block_times, 21, 1)
            # filtered_zlema = [x for x in SMA(22, self.block_times) if x]
            # filtered_zlema = [x for x in EMA(21, self.block_times) if x]
            filtered_zlema = [x for x in KAMA(21, 2, 30, self.block_times) if x]

            if len(filtered_zlema) >= 21:
                # rsi = int(RSI(21, filtered_zlema)[-1])
                rsi = TSI(9, 15, filtered_zlema)[-1]

                decrease = random.uniform(0.9, 0.99)

                # dont_go_below_target = (
                #     self.current_latency * decrease >= self.target_latency
                # )

                # TSI -30
                if rsi < -30:
                    self.current_latency = round(self.current_latency * decrease, 3)

                    self.my_logger.error(
                        f"Congestion Control [{round(filtered_zlema[-1], 3)}] - [{rsi}] (\/) - New Target: {self.current_latency}"
                    )
                    self.job_time_change_flag = True

    ####################
    # AT2 Consensus    #
    ####################

    # AT2 starts here
    async def gossip(self, bm: BatchedMessages):
        batched_message_hash = str(hash(bm))
        i_am_message_creator = (
            True
            if self._crypto_keys.ecdsa_tuple_to_id(bm.creator_ecdsa) == self.id
            else False
        )

        # Step 1
        echo_subscribe = self.select_nodes(
            self.node_selection_type, self.at2_config.echo_sample_size
        )

        # Step 2
        for peer_id in echo_subscribe:
            s2p = SubscribeToPublisher(peer_id, batched_message_hash.encode())
            self.command(s2p)

        # Step 3
        es = Echo(
            "EchoSubscribe",
            batched_message_hash,
            self._crypto_keys.ecdsa_public_key_tuple,
        )

        for peer_id in echo_subscribe:
            self.command(es, peer_id)

        # Step 4
        ready_subscribe = self.select_nodes(
            self.node_selection_type, self.at2_config.ready_sample_size
        )

        # Step 5
        for peer_id in ready_subscribe:
            s2p = SubscribeToPublisher(peer_id, batched_message_hash.encode())
            self.command(s2p)

        # Step 6
        rs = Echo(
            "ReadySubscribe",
            batched_message_hash,
            self._crypto_keys.ecdsa_public_key_tuple,
        )

        for peer_id in ready_subscribe:
            self.command(rs, peer_id)

        # Step 7
        if i_am_message_creator:
            self.vector_clock[self.id] += 1

        # step 8
        if (
            len(ready_subscribe.intersection(self.ready_replies[batched_message_hash]))
            < self.at2_config.feedback_threshold
        ):
            # If the message doesn't have enough ready_replies, assume it hasn't been propagated
            # enough, send the message to our echo_subscribe group
            self.received_messages[batched_message_hash] = bm
            for peer_id in echo_subscribe:
                if peer_id not in self.already_received[batched_message_hash]:
                    self.command(bm, peer_id)

        # Step 9
        # Using intersection to only count echos from nodes in our echo_subscribe set() we defined earlier
        retry_time_echo = 0
        while (
            len(echo_subscribe.intersection(self.echo_replies[batched_message_hash]))
            < self.at2_config.ready_threshold
        ):
            if retry_time_echo == self.max_gossip_timeout_time:
                break
            await asyncio.sleep(0.25)

            retry_time_echo += 0.25

        if (
            len(echo_subscribe.intersection(self.echo_replies[batched_message_hash]))
            >= self.at2_config.ready_threshold
        ):
            ready = Response(
                "ReadyResponse",
                batched_message_hash,
                self._crypto_keys.ecdsa_public_key_tuple,
            )

            self.command(ready)
            self.my_logger.warning(f"Ready for: {batched_message_hash}")
        else:
            self.my_logger.error(
                f"Didnt reach echo threshold for: {batched_message_hash} got: {echo_subscribe.intersection(self.echo_replies[batched_message_hash])} needed: {self.at2_config.ready_threshold}"
            )

        # Step 10
        # Using intersection to only count ready messages from nodes in our ready_replies set() we defined earlier
        retry_time_ready = 0
        while (
            len(ready_subscribe.intersection(self.ready_replies[batched_message_hash]))
            < self.at2_config.delivery_threshold
        ):
            if retry_time_ready == self.max_gossip_timeout_time:
                break

            await asyncio.sleep(0.1)

            retry_time_ready += 0.1

        if (
            len(ready_subscribe.intersection(self.ready_replies[batched_message_hash]))
            >= self.at2_config.delivery_threshold
        ):
            self.delivered_gossips += 1
            vector_clock_without_node_id = [value for key, value in bm.vector_clock]

            self.sequenced_messages.add(
                (tuple(vector_clock_without_node_id), batched_message_hash)
            )

            self.my_logger.warning(f"{batched_message_hash} has been delivered!")
        else:
            self.my_logger.warning(
                f"Didnt receive enough ReadyResponse messages to deliver: {batched_message_hash} got: {ready_subscribe.intersection(self.ready_replies[batched_message_hash])} needed: {self.at2_config.delivery_threshold}"
            )

        self.block_times.append(retry_time_ready + retry_time_echo)
        self.received_msg_metadata.append(
            (retry_time_ready + retry_time_echo, time.time())
        )

        # Step 11
        unsub = UnsubscribeFromTopic(batched_message_hash.encode())
        self.command(unsub)

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

            4) Create a ready_subscribe group of size ready_sample_size
            5) Subscribe to the publisher of all nodes in ready_subscribe
            6) Send all nodes in ready_subscribe a ReadySubscribe message

            7) Increment the message index
            8) Send the message to all nodes in echo_subscribe group

            9) Send a READY message if either:
            9a) you receive at least ready_threshold Echo messages from your echo_subscribe group
            9b) you receive at least feedback threshold Ready messages from your ready_subscribe group

            10) once you receive at least delivery_threshold Ready messages, the message is considered Delivered
            """

        # Algorithm (Gossiper)
        """
            Basically same as above, except a little check is added which may avoid sending the message again.
            When sending an EchoSubscribe message and a ReadySubscribe message, if the nodes in your echo_subscribe
            and ready_subscribe groups have already reached the
            ready_threshold and the feedback_threshold, the node will again broadcast an Echo or Ready message.

            Node receives lots of Ready Messages
            If the regossiping node receives feedback_threshold number of Ready messages from nodes
            in their ready_reply group, they'll immediately send out a
            Ready message. If they receive delivery_threshold number of messages, the node will immediately
            Deliver the message to the application.

            Node receives few Ready messages
            If the node doesn't hit the feedback threshold for their ready_subscribe group when sending a 
            ReadySubscribe message, the node will send the orginal message and regossip it.
            """

    ####################
    # Node Message Bus #
    ####################
    def command(self, command_obj, receiver=""):
        if isinstance(command_obj, SubscribeToPublisher):
            asyncio.create_task(self.subscribe(command_obj))
        elif isinstance(command_obj, Gossip):
            asyncio.create_task(self.batched_message_queue(command_obj))
        elif isinstance(command_obj, UnsubscribeFromTopic):
            asyncio.create_task(self.unsubscribe(command_obj))
        elif issubclass(type(command_obj), BatchedMessages):
            asyncio.create_task(self.send_signed_batched_message(command_obj, receiver))
        elif issubclass(type(command_obj), Echo):
            asyncio.create_task(self.send_signed_message(command_obj, receiver))
        elif issubclass(type(command_obj), Response):
            asyncio.create_task(self.publish_signed_echo_response(command_obj))
        elif issubclass(type(command_obj), DirectMessage):
            asyncio.create_task(self.unsigned_direct_message(command_obj, receiver))
        elif isinstance(command_obj, PublishMessage):
            asyncio.create_task(self.unsigned_publish(command_obj))
        else:
            self.my_logger.error(f"Unrecognised command object: {command_obj}")

    ####################
    # Helper Functions #
    ####################

    def calculate_uniform_params(self):
        num_nodes = len(self.peers)
        mean = (num_nodes - 1) / 2
        std_dev = math.sqrt(num_nodes)
        return mean, std_dev

    def select_nodes(self, algorithm: str, num_nodes_to_select: int) -> set:
        assert algorithm in ["normal", "random", "poisson"]
        selected_nodes = set()

        if algorithm == "poisson":
            rate = 5

            num_nodes = len(self.peers)
            poisson_distribution = poisson(rate)

            while len(selected_nodes) < num_nodes_to_select:
                selected_indices = (
                    poisson_distribution.rvs(size=num_nodes_to_select) % num_nodes
                )
                selected_nodes = set(
                    [list(self.peers)[index] for index in selected_indices]
                )
        elif algorithm == "normal":
            mean, std_dev = self.calculate_uniform_params()
            while len(selected_nodes) < num_nodes_to_select:
                selected_indices = norm.rvs(
                    loc=mean, scale=std_dev, size=num_nodes_to_select
                )
                selected_indices = [
                    int(idx) % len(self.peers) for idx in selected_indices
                ]
                selected_nodes = set(
                    [list(self.peers)[idx] for idx in selected_indices]
                )
        elif algorithm == "random":
            selected_nodes = random.sample(list(self.peers), num_nodes_to_select)

        return set(selected_nodes)

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

    async def subscribe(self, s2p: SubscribeToPublisher):
        # peer_id is a key from the self.peers dict

        # Don't resubscribe to the same ip twice, or else things break
        if s2p.peer_id not in self.connected_subscribers:
            self._subscriber.transport.connect(
                self.peers[s2p.peer_id].publisher_address
            )
            self.connected_subscribers.add(s2p.peer_id)
            self.my_logger.debug(
                f"Connected to publisher: {self.peers[s2p.peer_id].publisher_address}"
            )

        if s2p.topic not in self.subscribed_topics:
            self._subscriber.transport.subscribe(s2p.topic)
            self.subscribed_topics.add(s2p.topic)
            self.my_logger.debug(f"Subscribed to: {s2p.topic}")

    async def unsubscribe(self, unsub: UnsubscribeFromTopic):
        if unsub.topic in self.subscribed_topics:
            self._subscriber.transport.unsubscribe(unsub.topic)
            self.my_logger.debug(f"Unsubscribed from topic: {unsub.topic}")

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

        self.my_logger.debug("Started PUB/SUB Sockets", extra={"published": "aaaa"})

    def statistics(self):
        print(f"ID: {self.id}")
        print(f"Sent BMs: {self.sent_gossips} / Received BMs: {self.received_gossips}")
        print(f"Messages Delivered: {self.delivered_gossips}")
        print(f"Average RTT: {sum(self.block_times) / len(self.block_times)}")
        print(f"Min RTT: {min(self.block_times)} / Max RTT {max(self.block_times)}")

    def stop(self):
        self.running = False
        self._publisher.close()
        self._subscriber.close()
        self._router.close()

    async def start(self):
        self.running = True
        asyncio.create_task(self.router_listener())
        asyncio.create_task(self.subscriber_listener())
        random.seed(self.random_seed)

        await asyncio.sleep(random.randint(1, 3))

        self.current_latency = self.target_latency

        # Add the job to the scheduler, which triggers every 10 seconds
        self.scheduler = AsyncIOScheduler()
        job = self.scheduler.add_job(
            self.batch_message_builder_job, trigger="interval", seconds=5
        )
        self.batched_message_job_id = job.id

        job = self.scheduler.add_job(
            self.increasing_congestion_monitoring_job, trigger="interval", seconds=5
        )

        self.increase_job_id = job.id

        job = self.scheduler.add_job(
            self.decrease_congestion_monitoring_job, trigger="interval", seconds=10
        )

        self.decrease_job_id = job.id

        # Start the scheduler
        self.scheduler.start()
        self.my_logger.debug("Started Jobs")
