from attrs import frozen, field, validators


@frozen
class DirectMessage:
    sender: str = field(validator=[validators.instance_of(str)])
    message: str = field(validator=[validators.instance_of(str)])
    message_type: str = field(validator=[validators.instance_of(str)])
    receiver: str = field(validator=[validators.instance_of(str)])


@frozen
class PublishMessage:
    sender: str = field(validator=[validators.instance_of(str)])
    message: str = field(validator=[validators.instance_of(str)])
    message_type: str = field(validator=[validators.instance_of(str)])
    topic: str = field(validator=[validators.instance_of(str)])
