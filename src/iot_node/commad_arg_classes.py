from attrs import frozen, field, validators


@frozen
class SubscribeToPublisher:
    peer_id: str = field(validator=[validators.instance_of(str)])
    topic: bytes = field(validator=[validators.instance_of(bytes)])


@frozen
class UnsubscribeFromTopic:
    topic: bytes = field(validator=[validators.instance_of(bytes)])
