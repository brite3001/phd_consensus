from attrs import frozen, field, validators
from typing import List


@frozen
class MessageMetaData:
    batched: bool = field(validator=[validators.instance_of(bool)])
    sender: str = field(validator=[validators.instance_of(str)])


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


@frozen
class SignedDirectMessages:
    messages: List[DirectMessage] = field(factory=list)
    signatures: List[MessageSignatures] = field(factory=list)
    metadatas: List[MessageMetaData] = field(factory=list)
    batched: bool = False

    def add_msg(
        self, msg: DirectMessage, sigs: MessageSignatures, meta: MessageMetaData
    ):
        assert isinstance(msg, DirectMessage)
        assert isinstance(sigs, MessageSignatures)
        assert isinstance(meta, MessageMetaData)

        self.messages.append(msg)
        self.signatures.append(sigs)
        self.metadatas.append(meta)

        if len(self.messages) > 1:
            self.batched = True
