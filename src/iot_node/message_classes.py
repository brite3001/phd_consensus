from attrs import frozen, field, validators, asdict, define
from py_ecc.bls import G2ProofOfPossession as bls_pop
from fastecdsa import ecdsa, point
from typing import Union, Tuple
from time import time
import json
import base64


def bytes_to_base64(x: bytes):
    try:
        return base64.b64encode(x).decode("utf-8")
    except:
        return base64.b64decode(x)


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
    timestamp: int = field(validator=[validators.instance_of(int)])


def base64_to_bytes(x: base64) -> bytes:
    return base64.b64decode(x)


def ecdsa_tuple_to_point(ecdsa_tuple: tuple) -> point.Point:
    return point.Point(ecdsa_tuple[0], ecdsa_tuple[1])


# These classes are used for the AT2 protocol messages


@frozen
class Echo(DirectMessage):
    batched_messages_hash: str = field(validator=[validators.instance_of(str)])
    creator: tuple = field(converter=tuple)  # ECDSA pubkey

    def get_echo_bytes(self):
        message_bytes = (
            self.batched_messages_hash
            + str(self.message_type)
            + str(self.creator[0])
            + str(self.creator[1])
        )

        return message_bytes.encode()

    def sign_echo(self, keys):
        # The sender part is signed with the ECDSA private key

        return ecdsa.sign(self.get_echo_bytes(), keys.ecdsa_private_key)

    def verify_echo(self, signature: tuple):
        creator_sig_check = ecdsa.verify(
            signature,
            self.get_echo_bytes(),
            ecdsa_tuple_to_point(self.creator),
        )

        return creator_sig_check


@frozen
class Response(PublishMessage):
    creator: tuple = field(converter=tuple)  # ECDSA pubkey

    def get_echo_bytes(self):
        message_bytes = (
            str(self.topic)
            + str(self.message_type)
            + str(self.creator[0])
            + str(self.creator[1])
        )

        return message_bytes.encode()

    def sign_echo_response(self, keys):
        # The sender part is signed with the ECDSA private key

        return ecdsa.sign(self.get_echo_bytes(), keys.ecdsa_private_key)

    def verify_echo_response(self, signature: tuple):
        creator_sig_check = ecdsa.verify(
            signature,
            self.get_echo_bytes(),
            ecdsa_tuple_to_point(self.creator),
        )

        return creator_sig_check


@frozen
class BatchedMessages:
    message_type: str = field(validator=[validators.instance_of(str)])
    creator_bls: str = field(
        validator=[validators.instance_of(str)]
    )  # BLS pubkey, bytes encoded in base64

    creator_ecdsa: tuple = field(converter=tuple)
    sender_ecdsa: tuple = field(converter=tuple)

    messages: Union[Tuple[DirectMessage], Tuple[dict]] = field(converter=tuple)
    aggregated_bls_signature: str = field(
        validator=[validators.instance_of(str)]
    )  # bytes encoded as base64

    merkle_root: str = field(validator=[validators.instance_of(str)])

    def __hash__(self):
        return hash(self.get_creator_bytes())

    def get_creator_bytes(self):
        creator_bytes = (
            self.message_type
            + self.creator_bls
            + str(self.creator_ecdsa[0])
            + str(self.creator_ecdsa[1])
            + self.aggregated_bls_signature
            + self.merkle_root
        )

        return creator_bytes.encode()

    def get_sender_bytes(self):
        sender_bytes = (
            self.message_type
            + self.creator_bls
            + str(self.creator_ecdsa[0])
            + str(self.creator_ecdsa[1])
            + str(self.sender_ecdsa[0])
            + str(self.sender_ecdsa[1])
            + self.aggregated_bls_signature
            + self.merkle_root
        )

        return sender_bytes.encode()

    def sign_as_creator(self, keys):
        # Here we sign the whole message, but don't sign the sender part

        return ecdsa.sign(self.get_creator_bytes(), keys.ecdsa_private_key)

    def sign_as_sender(self, keys):
        # Here we sign the whole message and include the sender ecdsa
        # Most of the time the sender won't be the original message creator

        return ecdsa.sign(self.get_sender_bytes(), keys.ecdsa_private_key)

    def verify_creator_and_sender(
        self, signature: tuple, signature_to_check: str
    ) -> bool:
        assert signature_to_check in {
            "creator",
            "sender",
        }, "Invalid signature_to_check value"

        sig_check = ecdsa.verify(
            signature,
            (
                self.get_creator_bytes()
                if signature_to_check == "creator"
                else self.get_sender_bytes()
            ),
            ecdsa_tuple_to_point(self.sender_ecdsa),
        )

        return sig_check

    def verify_aggregated_bls_signature(self) -> bool:
        creator_bls_decoded = base64.b64decode(self.creator_bls)
        pub_keys = [creator_bls_decoded for _ in self.messages]
        messages_as_bytes = [json.dumps(asdict(x)).encode() for x in self.messages]

        aggregated_bls_check = bls_pop.AggregateVerify(
            pub_keys, messages_as_bytes, base64.b64decode(self.aggregated_bls_signature)
        )

        return aggregated_bls_check

    def become_sender(self, keys):
        return BatchedMessages(
            message_type=self.message_type,
            creator_bls=self.creator_bls,
            creator_ecdsa=self.creator_ecdsa,
            sender_ecdsa=keys.ecdsa_public_key_tuple,
            messages=self.messages,
            aggregated_bls_signature=self.aggregated_bls_signature,
            merkle_root=self.merkle_root,
        )
