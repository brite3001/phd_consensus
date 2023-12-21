from attrs import frozen, field, validators
from math import ceil

"""
Subscribing and sample sizes
echo_sample_size
ready_sample_size / delivery_sample_size

Thresholds
ready_threshold
feedback_threshold
delivery_threshold
"""


@frozen
class AT2Configuration:
    echo_sample_size: int = field(validator=[validators.instance_of(int)])
    ready_sample_size: int = field(validator=[validators.instance_of(int)])
    delivery_sample_size: int = field(validator=[validators.instance_of(int)])
    ready_threshold: int = field(validator=[validators.instance_of(int)])
    feedback_threshold: int = field(validator=[validators.instance_of(int)])
    delivery_threshold: int = field(validator=[validators.instance_of(int)])

    def __attrs_post_init__(self):
        # Make sure earlier thresholds are lower than later thresholds
        assert self.ready_threshold < self.feedback_threshold < self.delivery_threshold

        # make sure ready_threshold is at least 51% of the sample size
        assert self.ready_threshold >= (ceil(self.echo_sample_size) / 2) + 1

        # Make sure the feedback_threshold is at least 75%
        assert self.feedback_threshold >= ceil(self.ready_sample_size * 0.75)

        # Make sure the delivery_threshold is at least 85%
        assert self.delivery_threshold >= ceil(self.delivery_threshold * 0.85)


# aaa = AT2Configuration(10, 10, 10, 6, 8, 9)
