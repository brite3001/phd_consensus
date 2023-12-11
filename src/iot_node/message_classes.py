from attrs import frozen, field, validators, asdict, define
from py_ecc.bls import G2ProofOfPossession as bls_pop
from typing import List
import json


@frozen
class MessageSignatures:
    sender_signature: str = field(validator=[validators.instance_of(str)])
    creator_signature: str = field(validator=[validators.instance_of(str)])


@frozen
class DirectMessage:
    creator: str = field(validator=[validators.instance_of(str)])
    message: str = field(validator=[validators.instance_of(str)])
    message_type: str = field(validator=[validators.instance_of(str)])


@frozen
class PublishMessage:
    creator: str = field(validator=[validators.instance_of(str)])
    message: str = field(validator=[validators.instance_of(str)])
    message_type: str = field(validator=[validators.instance_of(str)])
    topic: str = field(validator=[validators.instance_of(str)])


@define
class BatchMessageBuilder:
    sender: bytes = field(validator=[validators.instance_of(bytes)])
    messages: List[DirectMessage] = field(factory=list)
    aggregated_signature: list = field(factory=list)

    batched: bool = False

    def add_msg(self, msg: DirectMessage):
        assert isinstance(msg, DirectMessage)

        self.messages.append(msg)

        if len(self.messages) > 1:
            self.batched = True

    def add_signed_message(self, msg: DirectMessage, sigs: MessageSignatures):
        assert isinstance(msg, DirectMessage)
        assert isinstance(sigs, MessageSignatures)

        self.aggregated_signature.append()

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

        return agg_sig

    def verify_signatures():
        # Verify aggregate signature with different messages
        assert bls_pop.AggregateVerify(public_keys, messages, agg_sig)

    def get_frozen():
        pass
