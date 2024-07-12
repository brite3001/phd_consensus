from attrs import frozen, field, validators


@frozen
class SubscribeToPublisher:
    peer_id: str = field(validator=[validators.instance_of(str)])
    topic: str = field(validator=[validators.instance_of(str)])


@frozen
class UnsubscribeFromTopic:
    topic: str = field(validator=[validators.instance_of(str)])
