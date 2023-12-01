from attrs import frozen, field, validators


def str_to_bytes(x: str) -> bytes:
    return x.encode()


@frozen
class SubscribeToPublisher:
    publisher: str = field(validator=[validators.instance_of(str)])
    topic: bytes = field(converter=str_to_bytes)
