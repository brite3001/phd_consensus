from attrs import frozen, field, validators
from fastecdsa import ecdsa, point


def ecdsa_tuple_to_point(ecdsa_tuple: tuple) -> point.Point:
    return point.Point(ecdsa_tuple[0], ecdsa_tuple[1])


@frozen
class SequenceProposal:
    message_type: str = field(validator=[validators.instance_of(str)])
    sequence_round: int = field(validator=[validators.instance_of(int)])

    creator_ecdsa: tuple = field(converter=tuple)
    proposed_message_hashes: tuple = field(converter=tuple)

    def __hash__(self):
        return hash(self.get_creator_bytes())

    def get_creator_bytes(self):
        creator_bytes = (
            self.message_type
            + str(self.sequence_round)
            + str(self.creator_ecdsa[0])
            + str(self.creator_ecdsa[1])
            + str(hash(self.proposed_message_hashes))
        )

        return creator_bytes.encode()

    def sign_message(self, keys):
        # Here we sign the whole message, but don't sign the sender part

        return ecdsa.sign(self.get_creator_bytes(), keys.ecdsa_private_key)

    def verify_message(self, signature: tuple) -> bool:
        sig_check = ecdsa.verify(
            signature,
            (self.get_creator_bytes()),
            ecdsa_tuple_to_point(self.sender_ecdsa),
        )

        return sig_check
