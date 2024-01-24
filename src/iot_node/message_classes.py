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
    """
    TODO: Add signature verification to gossiped messages
    """

    timestamp = int(time())


def base64_to_bytes(x: base64) -> bytes:
    return base64.b64decode(x)


def ecdsa_tuple_to_point(ecdsa_tuple: tuple) -> point.Point:
    return point.Point(ecdsa_tuple[0], ecdsa_tuple[1])


# These classes are used for the AT2 protocol messages


@frozen
class EchoSubscribe(DirectMessage):
    message_hash: int = field(validator=[validators.instance_of(int)])
    creator: Union[tuple, list] = field(
        validator=[validators.instance_of(Union[tuple, list])]
    )  # ECDSA pubkey

    def get_echo_subscribe_bytes(self):
        message_bytes = (
            self.message_type
            + str(self.message_hash)  # The hash of the BatchedMessage we're echoing
            + str(self.creator[0])
            + str(self.creator[1])
        )

        return message_bytes.encode()

    def sign_echo(self, keys):
        # The sender part is signed with the ECDSA private key

        return ecdsa.sign(self.get_echo_subscribe_bytes(), keys.ecdsa_private_key)

    def verify_echo(self, signature: tuple):
        creator_sig_check = ecdsa.verify(
            signature,
            self.get_echo_subscribe_bytes(),
            ecdsa_tuple_to_point(self.creator),
        )

        return creator_sig_check


@frozen
class BatchedMessages:
    message_type: str = field(validator=[validators.instance_of(str)])
    creator_bls: str = field(
        validator=[validators.instance_of(str)]
    )  # BLS pubkey, bytes encoded in base64

    creator_ecdsa: Union[Tuple, list] = field(
        validator=[validators.instance_of(Union[Tuple, list])]
    )

    sender_ecdsa: Union[Tuple, list] = field(
        validator=[validators.instance_of(Union[Tuple, list])]
    )

    messages: Union[Tuple[DirectMessage], Tuple[dict]] = field()
    messages_agg_sig: str = field(
        validator=[validators.instance_of(str)]
    )  # bytes encoded as base64

    merkle_root: str = field(validator=[validators.instance_of(str)])

    def get_creator_bytes(self):
        creator_bytes = (
            self.message_type
            + self.creator_bls
            + str(self.creator_ecdsa[0])
            + str(self.creator_ecdsa[1])
            + self.messages_agg_sig
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
            + self.messages_agg_sig
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

    def verify_creator_and_sender(self, signature: tuple, signature_to_check: str):
        assert signature_to_check in {
            "creator",
            "sender",
        }, "Invalid signature_to_check value"

        sig_check = ecdsa.verify(
            signature,
            self.get_creator_bytes()
            if signature_to_check == "creator"
            else self.get_sender_bytes(),
            ecdsa_tuple_to_point(self.sender_ecdsa),
        )

        return sig_check

    # def verify_signatures(self) -> tuple:
    #     pub_keys = [self.creator for _ in self.messages]
    #     messages_as_bytes = [json.dumps(asdict(x)).encode() for x in self.messages]

    #     messages_sig_check = bls_pop.AggregateVerify(
    #         pub_keys, messages_as_bytes, self.aggregated_signature
    #     )

    #     sender_bytes = json.dumps(asdict(self.sender_info)).encode()

    #     sender_sig_check = ecdsa.verify(
    #         self.sender_signature,
    #         sender_bytes,
    #         ecdsa_dict_to_point(self.sender_info.sender),
    #     )

    #     return (messages_sig_check, sender_sig_check)
