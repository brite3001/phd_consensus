from attrs import frozen, field, validators, asdict, define
from py_ecc.bls import G2ProofOfPossession as bls_pop
from typing import List
import json
import base64


def bytes_to_base64(x: bytes) -> str:
    return base64.b64encode(x).decode("utf-8")


@frozen
class MessageSignatures:
    sender_signature: str = field(validator=[validators.instance_of(str)])
    creator_signature: str = field(validator=[validators.instance_of(str)])


@frozen
class DirectMessage:
    creator: str = field(converter=bytes_to_base64)
    message: str = field(validator=[validators.instance_of(str)])
    message_type: str = field(validator=[validators.instance_of(str)])


@frozen
class PublishMessage:
    creator: str = field(converter=bytes_to_base64)
    message: str = field(validator=[validators.instance_of(str)])
    message_type: str = field(validator=[validators.instance_of(str)])
    topic: str = field(validator=[validators.instance_of(str)])


@define
class BatchMessageBuilder:
    sender: str = field(converter=bytes_to_base64)
    messages: List[DirectMessage] = field(factory=list)
    aggregated_signature: str = field(init=False)

    batched: bool = False

    def add_msg(self, msg: DirectMessage):
        assert isinstance(msg, DirectMessage)

        self.messages.append(msg)

        if len(self.messages) > 1:
            self.batched = True

    def sign_messages(self, private_key: bytes):
        messages_as_bytes = [json.dumps(asdict(x)).encode() for x in self.messages]
        sigs = []
        agg_sig = None

        for msg_byte in messages_as_bytes:
            sigs.append(bls_pop.Sign(private_key, msg_byte))

        # Don't aggregate if we only have 1 signature
        if len(sigs) > 1:
            agg_sig = bls_pop.Aggregate(sigs)
        else:
            agg_sig = sigs[0]

        self.aggregated_signature = bytes_to_base64(agg_sig)

    def verify_signatures(self) -> bool:
        pub_keys = [base64.b64decode(x.creator) for x in self.messages]
        messages_as_bytes = [json.dumps(asdict(x)).encode() for x in self.messages]

        return bls_pop.AggregateVerify(
            pub_keys, messages_as_bytes, base64.b64decode(self.aggregated_signature)
        )
