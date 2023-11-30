from attrs import frozen, field


@frozen
class DirectMessage:
    receiver: str = field()
    message: dict = field()

    @message.validator
    def check(self, attribute, value):
        if type(value) != dict:
            raise ValueError("Message should be a dict")

    @receiver.validator
    def check(self, attribute, value):
        if type(value) != str:
            raise ValueError("Receiver should be a str")


@frozen
class PublishMessage:
    message: dict = field()
    topic: bytes = field()

    @message.validator
    def check(self, attribute, value):
        if type(value) != dict:
            raise ValueError("Message should be a dict")

    @topic.validator
    def check(self, attribute, value):
        if type(value) != bytes:
            raise ValueError("Topic should be bytes")


@frozen
class SubscribeToPublisher:
    publisher: str = field()
    topic: bytes = field()

    @publisher.validator
    def check(self, attribute, value):
        if type(value) != str:
            raise ValueError("Publisher should be a str")

    @topic.validator
    def check(self, attribute, value):
        if type(value) != bytes:
            raise ValueError("Topic should be bytes")
