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
from collections import deque
from async_timeout import timeout
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
        return str(hash(ecdsa))[:10]

    def bls_bytes_to_base64(self, bls_bytes: bytes) -> base64:
        base64.b64encode(bls_bytes).decode("utf-8")

    def bls_base64_to_bytes(self, bls_base64: base64) -> bytes:
        return base64.b64decode(bls_base64)


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
    target_latency: int = 2.5
    target_publishing_frequency = 2.5
    max_publishing_frequency = 10
    minimum_latency: int = 1
    max_gossip_timeout_time = 60
    max_response_delay_time = 5
    node_selection_type = "normal"

    # Congestion control
    scheduler = field(init=False)
    pending_gossips: list[Gossip] = field(factory=list)
    pending_responses: list[Response] = field(factory=list)
    batched_message_job_id = field(init=False)
    increase_job_id = field(init=False)
    decrease_job_id = field(init=False)
    publish_pending_frequency: int = field(factory=int)
    publish_pending_responses_job_id = field(init=False)
    job_time_change_flag: bool = field(factory=bool)
    publish_pending_change_flag: bool = field(factory=bool)
    current_latency: int = field(factory=int)
    peers_latency: deque = field(factory=lambda: deque(maxlen=100))
    our_latency: deque = field(factory=lambda: deque(maxlen=100))
    recently_missed_delivery: defaultdict[bool] = field(
        factory=lambda: defaultdict(bool)
    )

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
    current_latency_metadata: list = field(factory=list)
    delivered_msg_metadata: list = field(factory=list)

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

                er = Response(
                    "EchoResponse",
                    str(bm_hash),
                    self._crypto_keys.ecdsa_public_key_tuple,
                )
                self.command(er)

                bm = message.become_sender(self._crypto_keys)
                # regossip the message from the original creator, now with you as sender
                asyncio.create_task(self.gossip(bm))

        elif isinstance(message, Echo):
            if message.message_type == "EchoSubscribe":
                if message.batched_messages_hash in self.received_messages:
                    # publish an echo_reply for that particular message hash
                    er = Response(
                        "EchoResponse",
                        message.batched_messages_hash,
                        self._crypto_keys.ecdsa_public_key_tuple,
                    )
                    self.command(er)
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

            attempts = 0
            while attempts < 50:
                try:
                    async with timeout(1):
                        await req.transport.connect(message.router_address)
                        self.my_logger.info(f"Successfully added {ecdsa_id}'s socket")
                        break
                except asyncio.TimeoutError:
                    self.my_logger.warning(
                        f"Couldnt add socket for {ecdsa_id}, attempt: {attempts}"
                    )
                    req.close()
                    req = await aiozmq.create_zmq_stream(zmq.REQ)
                    attempts += 1
                    await asyncio.sleep(1)
            else:
                self.my_logger.error(
                    f"Failed to add socket for {ecdsa_id} after {attempts} attempts"
                )

            self.sockets[ecdsa_id] = PeerSocket(message.router_address, ecdsa_id, req)
            self.recently_missed_delivery[ecdsa_id] = False

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

                router_response = json.dumps(
                    {
                        "status": "OK",
                    }
                ).encode()

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

                        router_response = json.dumps(
                            {
                                "status": "CongestionUpdate",
                                "current_latency": self.current_latency,
                                "recently_missed": self.recently_missed_delivery[
                                    sender_id
                                ],
                            }
                        ).encode()

                        self.recently_missed_delivery[sender_id] = False

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

            multi_topic = recv[0].decode()
            responses = recv[1].decode()
            signatures = recv[2].decode()

            multi_topic = multi_topic.split("|")
            responses = responses.split("|")
            signatures = signatures.split("|")

            multi_topic = [x for x in multi_topic if x]
            responses = [json.loads(x) for x in responses if x]
            signatures = [json.loads(x) for x in signatures if x]

            for topic, message, echo_sig in zip(multi_topic, responses, signatures):
                if topic in self.subscribed_topics:
                    message_type = message["message_type"]

                    message = Response(**message)

                    if message_type == "EchoResponse":
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
                    elif message_type == "ReadyResponse":
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
                    else:
                        self.my_logger.error(
                            f"Received unrecognised message: {message}"
                        )

    ####################
    # Message Sending  #
    ####################
    async def unsigned_publish(self, pub: dict):
        #####################
        # WARNING!!! THIS WILL NOT WORK!
        # sub listen now expects multi_topic pubs
        ########################
        message = json.dumps(asdict(pub)).encode()

        self._publisher.write([pub.topic.encode(), message])

    async def unsigned_direct_message(self, message: DirectMessage, receiver=""):
        assert issubclass(type(message), DirectMessage)

        req = await aiozmq.create_zmq_stream(zmq.REQ)

        attempts = 0
        while attempts < 50:
            try:
                async with timeout(1):
                    await req.transport.connect(receiver)
                    self.my_logger.info(f"Successfully connected to {receiver}")
                    break
            except asyncio.TimeoutError:
                self.my_logger.warning(
                    f"Couldnt connect to {receiver}, attempt: {attempts}"
                )
                req.close()
                req = await aiozmq.create_zmq_stream(zmq.REQ)
                attempts += 1
                await asyncio.sleep(1)
        else:
            self.my_logger.error(
                f"Failed to connect to {receiver} after {attempts} attempts"
            )

        message = json.dumps(asdict(message)).encode()

        async with self.rep_lock:
            req.write([message])

            attempts = 0
            while attempts < 50:
                try:
                    async with timeout(1):
                        await req.read()
                        self.my_logger.info(f"Received response from {receiver}")
                        break
                except asyncio.TimeoutError:
                    self.my_logger.warning(
                        f"Didnt receive response from {receiver}, attempt: {attempts}"
                    )
                    attempts += 1
                    await asyncio.sleep(1)
            else:
                self.my_logger.error(
                    f"No reponse received from {receiver} after {attempts} attempts"
                )

        req.close()

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
            peer_current_latency = await req_socket.read()

            congestion_info = json.loads(peer_current_latency[0].decode())
            status = congestion_info["status"]

            if status == "CongestionUpdate":
                peer_latency = float(congestion_info["current_latency"])
                recently_missed = congestion_info["recently_missed"]
                if peer_latency > 0.0:
                    self.peers_latency.append(peer_latency)

                if recently_missed:
                    if self.current_latency + 1 < self.max_gossip_timeout_time * 0.85:
                        self.current_latency += 1
            elif status == "OK":
                pass
            else:
                self.my_logger.warning("Received unknown response after sending BM")

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

    async def publish_signed_echo_response(self):
        # message = json.dumps(asdict(to_publish)).encode()
        # echo_sig = json.dumps(to_publish.sign(self._crypto_keys)).encode()
        # self._publisher.write([to_publish.topic.encode(), message, echo_sig])

        if len(self.pending_responses) >= 1:
            multi_topic_str = ""
            resps = ""
            resp_sigs = ""

            for resp in self.pending_responses:
                multi_topic_str += resp.topic + "|"
                resps += json.dumps(asdict(resp)) + "|"
                resp_sigs += json.dumps(resp.sign(self._crypto_keys)) + "|"

            self._publisher.write(
                [multi_topic_str.encode(), resps.encode(), resp_sigs.encode()]
            )

            self.pending_responses.clear()

        if self.job_time_change_flag:
            self.scheduler.remove_job(self.publish_pending_responses_job_id)
            updated_job = self.scheduler.add_job(
                self.publish_signed_echo_response,
                trigger="interval",
                seconds=self.publish_pending_frequency,
            )
            self.publish_pending_responses_job_id = updated_job.id
            self.publish_pending_change_flag = False

    ######################
    # Congestion Control #
    ######################

    async def ready_response_queue(self, response: Response):
        if response not in self.pending_responses:
            self.pending_responses.append(response)

    async def batched_message_queue(self, gossip: Gossip):
        self.pending_gossips.append(gossip)
        # asyncio.create_task(self.batch_message_builder_job())

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

        await asyncio.sleep(random.uniform(0.1, 2.5))
        # Increase the block time if we start overshooting the target
        if len(self.our_latency) >= 20 and len(self.peers_latency) >= 20:
            # filtered_zlema = savgol_filter(self.our_latency, 14, 1)
            # filtered_zlema = kalman_filter(ZLEMA(14, self.our_latency))
            # filtered_zlema = [x for x in SMA(14, self.our_latency) if x]
            # filtered_zlema = [x for x in EMA(14, self.our_latency) if x]
            # filtered_zlema = [x for x in KAMA(14, 2, 30, self.our_latency) if x]

            our_smooth_latency = savgol_filter(self.our_latency, 14, 1)
            our_peers_smooth_latency = savgol_filter(self.peers_latency, 14, 1)

            weighted_latest_latency = round(
                (our_smooth_latency[-1] * 0.6) + (our_peers_smooth_latency[-1] * 0.4),
                3,
            )

            # Latency ca

            if self.current_latency <= 0.5 * weighted_latest_latency:
                if self.current_latency * 2 < self.max_gossip_timeout_time * 0.85:
                    # Make sure current latency stays below max gossip
                    self.current_latency *= 2
                    self.my_logger.error(
                        f"[{weighted_latest_latency}] [Latency Fastforward] (/\) - New Target: {self.current_latency}"
                    )

                    self.job_time_change_flag = True
            elif len(our_smooth_latency) >= 15 and len(our_peers_smooth_latency) >= 15:
                # rsi = int(RSI(21, filtered_zlema)[-1])
                # rsi = TSI(3, 6, filtered_zlema)[-1]

                our_latency_rsi = int(RSI(14, our_smooth_latency)[-1])
                our_peers_latency_rsi = int(RSI(14, our_peers_smooth_latency)[-1])

                increase = random.uniform(1.01, 1.1)

                dont_exceed_max_target = (
                    self.current_latency * increase
                    < self.max_gossip_timeout_time * 0.85
                )

                # Stops current_latency increase when network has low latency.
                latency_under_target = (
                    False if our_smooth_latency[-1] < self.target_latency else True
                )

                # TSI +30
                if (
                    (our_latency_rsi > 70 and our_peers_latency_rsi > 70)
                    and dont_exceed_max_target
                    and latency_under_target
                ):
                    self.current_latency = round(self.current_latency * increase, 3)
                    self.job_time_change_flag = True

                    if self.publish_pending_frequency < self.max_publishing_frequency:
                        self.publish_pending_frequency = round(
                            self.publish_pending_frequency * increase, 3
                        )
                        self.publish_pending_change_flag = True

                    self.my_logger.error(
                        f"[High RSI - /\] T: {self.current_latency} P/FQ: {self.publish_pending_frequency} W: {weighted_latest_latency} O/L: {our_latency_rsi} O/P: {our_peers_latency_rsi}"
                    )

            self.current_latency_metadata.append((time.time(), weighted_latest_latency))

    async def decrease_congestion_monitoring_job(self):
        from scipy.signal import savgol_filter

        # Increase the block time if we start overshooting the target
        if len(self.our_latency) >= 45 and len(self.peers_latency) >= 45:
            # filtered_zlema = kalman_filter(ZLEMA(21, self.our_latency))
            # filtered_zlema = savgol_filter(self.our_latency, 21, 1)
            # filtered_zlema = [x for x in SMA(22, self.our_latency) if x]
            # filtered_zlema = [x for x in EMA(21, self.our_latency) if x]
            # filtered_zlema = [x for x in KAMA(21, 2, 30, self.our_latency) if x]

            our_smooth_latency = savgol_filter(self.our_latency, 21, 1)
            our_peers_smooth_latency = savgol_filter(self.peers_latency, 21, 1)

            weighted_latest_latency = round(
                (our_smooth_latency[-1] * 0.6) + (our_peers_smooth_latency[-1] * 0.4), 3
            )

            if len(our_smooth_latency) >= 21 and len(our_peers_smooth_latency) >= 21:
                # rsi = int(RSI(21, filtered_zlema)[-1])
                # rsi = TSI(9, 15, filtered_zlema)[-1]

                our_latency_rsi = int(RSI(21, our_smooth_latency)[-1])
                our_peers_latency_rsi = int(RSI(21, our_peers_smooth_latency)[-1])

                decrease = random.uniform(0.9, 0.99)

                dont_go_below_minimum = (
                    True
                    if round(self.current_latency * decrease, 3) > self.minimum_latency
                    else False
                )

                # TSI -30
                # Trend is downwards, start slowly increase message sending frequency
                if (
                    our_latency_rsi < 30
                    and our_peers_latency_rsi < 30
                    and our_peers_latency_rsi > 0
                    and dont_go_below_minimum
                ):
                    self.current_latency = round(self.current_latency * decrease, 3)

                    self.my_logger.error(
                        f"[{weighted_latest_latency}] [Low RSI] [{our_latency_rsi}] / [{our_peers_latency_rsi}] (\/) - New Target: {self.current_latency}"
                    )
                    self.job_time_change_flag = True

                    if self.publish_pending_frequency > self.minimum_latency:
                        self.publish_pending_frequency = round(
                            self.publish_pending_frequency * decrease, 3
                        )

                        self.publish_pending_change_flag = True
                else:
                    self.my_logger.error(
                        f" latest: [{weighted_latest_latency}] current: {self.current_latency}"
                    )

            # Latency is very low, increase message sending frequency
            # elif (
            #     our_smooth_latency[-1] < 0.25 * self.target_latency
            #     and dont_go_below_minimum
            # ):
            #     self.current_latency = round(self.current_latency * decrease, 3)

            #     self.my_logger.error(
            #         f"[Low Latency] [{our_latency_rsi}] / [{our_peers_latency_rsi}] (\/) - New Target: {self.current_latency}"
            #     )
            #     self.job_time_change_flag = True

            self.current_latency_metadata.append((time.time(), weighted_latest_latency))

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
            s2p = SubscribeToPublisher(peer_id, batched_message_hash)
            self.command(s2p)

        # Step 3
        es = Echo(
            "EchoSubscribe",
            batched_message_hash,
            self._crypto_keys.ecdsa_public_key_tuple,
        )

        # Step 4
        ready_subscribe = self.select_nodes(
            self.node_selection_type, self.at2_config.ready_sample_size
        )

        # Step 5
        for peer_id in ready_subscribe:
            s2p = SubscribeToPublisher(peer_id, batched_message_hash)
            self.command(s2p)

        for peer_id in echo_subscribe:
            self.command(es, peer_id)

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
        echo_failure = False
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
                f"Echo Failure: {batched_message_hash} got: {len(echo_subscribe.intersection(self.echo_replies[batched_message_hash]))} needed: {self.at2_config.ready_threshold}"
            )

            for peer in self.recently_missed_delivery:
                self.recently_missed_delivery[peer] = True

            echo_failure = True

        # Step 10
        # Using intersection to only count ready messages from nodes in our ready_replies set() we defined earlier
        retry_time_ready = 0
        while (
            len(ready_subscribe.intersection(self.ready_replies[batched_message_hash]))
            < self.at2_config.delivery_threshold
        ):
            if retry_time_ready == self.max_gossip_timeout_time:
                break
            elif echo_failure:
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

            if i_am_message_creator:
                self.delivered_msg_metadata.append((time.time(), len(bm.messages)))

            self.my_logger.warning(f"{batched_message_hash} has been delivered!")
        else:
            self.my_logger.error(
                f"ReadyResponse Failure: {batched_message_hash} got: {len(ready_subscribe.intersection(self.ready_replies[batched_message_hash]))} needed: {self.at2_config.delivery_threshold}"
            )

            # Dount double enter missed delivery if the echo also failed
            if not echo_failure:
                for peer in self.recently_missed_delivery:
                    self.recently_missed_delivery[peer] = True

        self.our_latency.append(retry_time_ready + retry_time_echo)
        self.received_msg_metadata.append(
            (retry_time_ready + retry_time_echo, time.time())
        )

        # Step 11
        unsub = UnsubscribeFromTopic(batched_message_hash)
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
            asyncio.create_task(self.ready_response_queue(command_obj))
            # asyncio.create_task(self.publish_signed_echo_response(command_obj))
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

        random.shuffle(routers)

        # Send the PD message to all peers
        for ip in routers:
            await self.unsigned_direct_message(pd, ip)

    async def subscribe_to_all_peers_and_topics(self):
        # peer_id is a key from the self.peers dict

        for peer_id in self.peers:
            self._subscriber.transport.connect(self.peers[peer_id].publisher_address)

        self._subscriber.transport.subscribe(b"")

    async def subscribe(self, s2p: SubscribeToPublisher):
        # peer_id is a key from the self.peers dict

        if s2p.topic not in self.subscribed_topics:
            self.subscribed_topics.add(s2p.topic)

    async def unsubscribe(self, s2p: UnsubscribeFromTopic):
        # peer_id is a key from the self.peers dict

        if s2p.topic in self.subscribed_topics:
            self.subscribed_topics.remove(s2p.topic)

    async def init_sockets(self):
        self._subscriber = await aiozmq.create_zmq_stream(zmq.SUB)

        import os

        node_port = int(os.getenv("NODE_ID"))

        self._publisher = await aiozmq.create_zmq_stream(
            zmq.PUB, bind=f"tcp://*:{21001 + node_port}"
        )
        self._router = await aiozmq.create_zmq_stream(
            zmq.ROUTER, bind=f"tcp://*:{20001 + node_port}"
        )

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

        self.id = str(hash(self._crypto_keys.ecdsa_public_key_tuple))[:10]

        self.my_logger = get_logger(self.id)

        self.my_logger.debug("Started PUB/SUB Sockets", extra={"published": "aaaa"})

    def statistics(self):
        print(f"ID: {self.id}")
        print(f"Sent BMs: {self.sent_gossips} / Received BMs: {self.received_gossips}")
        print(f"Messages Delivered: {self.delivered_gossips}")
        print(f"Average RTT: {sum(self.our_latency) / len(self.our_latency)}")
        print(f"Min RTT: {min(self.our_latency)} / Max RTT {max(self.our_latency)}")

    def stop(self):
        self.running = False
        self._publisher.close()
        self._subscriber.close()
        self._router.close()

    async def start(self):
        self.running = True
        asyncio.create_task(self.router_listener())
        asyncio.create_task(self.subscriber_listener())

        await asyncio.sleep(random.randint(1, 3))

        self.current_latency = self.target_latency

        self.publish_pending_frequency = self.target_publishing_frequency

        # # Add the job to the scheduler, which triggers every 10 seconds
        self.scheduler = AsyncIOScheduler()
        job = self.scheduler.add_job(
            self.batch_message_builder_job,
            trigger="interval",
            seconds=random.randint(
                int(self.target_latency * 0.75), int(self.target_latency * 1.25)
            ),
        )
        self.batched_message_job_id = job.id

        job = self.scheduler.add_job(
            self.increasing_congestion_monitoring_job,
            trigger="interval",
            seconds=random.randint(4, 6),
        )

        self.increase_job_id = job.id

        job = self.scheduler.add_job(
            self.decrease_congestion_monitoring_job,
            trigger="interval",
            seconds=random.randint(8, 12),
        )

        self.decrease_job_id = job.id

        job = self.scheduler.add_job(
            self.publish_signed_echo_response,
            trigger="interval",
            seconds=random.randint(
                int(self.publish_pending_frequency * 0.75),
                int(self.publish_pending_frequency * 1.25),
            ),
        )

        self.publish_pending_responses_job_id = job.id

        # # Start the scheduler
        self.scheduler.start()
        self.my_logger.debug("Started Jobs")

        self.my_logger.error("READY!!")
        self.my_logger.error(f"my peer id is {self.id}!!")
