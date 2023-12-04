from attrs import frozen, field, validators


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


# @frozen
# class batchedMessages:
#     batched: list = field(validator=[validators.instance_of(list)])
#     creator_signature: str = field(validator=[validators.instance_of(str)])

#     def check_signature(self):
#         pass
