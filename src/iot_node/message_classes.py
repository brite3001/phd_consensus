from attrs import frozen, field, validators, asdict, define
from py_ecc.bls import G2ProofOfPossession as bls_pop
from fastecdsa import ecdsa, point
from typing import List, Union, Tuple
from time import time
import json
import base64
from merkly.mtree import MerkleTree


def bytes_to_base64(x: bytes):
    try:
        return base64.b64encode(x).decode("utf-8")
    except:
        return base64.b64decode(x)


@frozen
class SenderInformation:
    sender: tuple = field(validator=[validators.instance_of(tuple)])  # ECDSA pubkey
    root_hash: str = field(validator=[validators.instance_of(str)])


@frozen
class PublishMessage:
    message_type: str = field(validator=[validators.instance_of(str)])
    topic: str = field(validator=[validators.instance_of(str)])


@define
class DirectMessage:
    message_type: str = field(validator=[validators.instance_of(str)])


@frozen
class PeerDiscovery(DirectMessage):
    bls_public_key: str = field(converter=bytes_to_base64)
    ecdsa_public_key: tuple = field(converter=tuple)
    router_address: str = field(validator=[validators.instance_of(str)])
    publisher_address: str = field(validator=[validators.instance_of(str)])


@frozen
class Gossip(DirectMessage):
    """
    TODO: Add signature verification to gossiped messages
    """

    timestamp = int(time())


def base64_to_bytes(x: base64) -> bytes:
    return base64.b64decode(x)


def ecdsa_dict_to_point(x: dict) -> point.Point:
    return point.Point(x["x"], x["y"])


def sender_dict_to_object(x: dict) -> SenderInformation:
    return SenderInformation(**x)


def gossip_dict_to_object(x: dict) -> list[DirectMessage]:
    return (Gossip(**g) for g in x)


# These classes are used for the AT2 protocol messages


@frozen
class EchoSubscribe(PublishMessage):
    message_hash: str = field(validator=[validators.instance_of(str)])


@frozen
class ReadySubscribe(PublishMessage):
    message_hash: str = field(validator=[validators.instance_of(str)])


# Used on the senders side, builds a BatchedMessage from multiple DirectMessages
@define
class BatchedMessageBuilder(DirectMessage):
    creator: str = field(converter=bytes_to_base64)  # BLS pubkey
    messages: List[DirectMessage] = field(factory=list)
    aggregated_signature: str = field(init=False)

    sender_signature: str = field(init=False)
    sender_info: SenderInformation = field(init=False)

    batched: bool = False

    def add_msg(self, msg: DirectMessage):
        assert isinstance(msg, DirectMessage)

        self.messages.append(msg)

        if len(self.messages) > 1:
            self.batched = True

    def sign_messages(self, keys):
        # Messages are signed with the BLS private key
        messages_as_bytes = [json.dumps(asdict(x)).encode() for x in self.messages]
        sigs = []
        agg_sig = None

        for msg_byte in messages_as_bytes:
            sigs.append(bls_pop.Sign(keys.bls_private_key, msg_byte))

        # Don't aggregate if we only have 1 signature
        if len(sigs) > 1:
            agg_sig = bls_pop.Aggregate(sigs)
        else:
            agg_sig = sigs[0]

        self.aggregated_signature = bytes_to_base64(agg_sig)

    def sign_sender(self, keys):
        # The sender part is signed with the ECDSA private key
        assert self.aggregated_signature

        mtree = MerkleTree([str(hash(x)) for x in self.messages])

        self.sender_info = SenderInformation(keys.ecdsa_public_key_tuple, mtree.root)
        sender_bytes = json.dumps(asdict(self.sender_info)).encode()

        self.sender_signature = ecdsa.sign(sender_bytes, keys.ecdsa_private_key)


# Used on the receivers side, automatically deserialises and
# converts the objects from json dicts into objects
@frozen
class BatchedMessages:
    creator: str = field(converter=base64_to_bytes)  # BLS pubkey
    messages: Tuple[DirectMessage] = field(converter=gossip_dict_to_object)
    sender_info: SenderInformation = field(converter=sender_dict_to_object)
    aggregated_signature: bytes = field(converter=base64_to_bytes)
    sender_signature: list = field(
        validator=[validators.instance_of(Union[list, tuple])]
    )
    batched: bool = field(validator=[validators.instance_of(bool)])
    message_type: str = field(validator=[validators.instance_of(str)])

    def verify_signatures(self) -> tuple:
        pub_keys = [self.creator for _ in self.messages]
        messages_as_bytes = [json.dumps(asdict(x)).encode() for x in self.messages]

        messages_sig_check = bls_pop.AggregateVerify(
            pub_keys, messages_as_bytes, self.aggregated_signature
        )

        sender_bytes = json.dumps(asdict(self.sender_info)).encode()

        sender_sig_check = ecdsa.verify(
            self.sender_signature,
            sender_bytes,
            ecdsa_dict_to_point(self.sender_info.sender),
        )

        return (messages_sig_check, sender_sig_check)
