from copy import deepcopy
import asyncio
import signal
import uvloop
import random

from iot_node.node import Node
from iot_node.message_classes import Gossip
from iot_node.message_classes import PublishMessage
from iot_node.message_classes import Response
from iot_node.commad_arg_classes import SubscribeToPublisher
from iot_node.at2_classes import AT2Configuration
from logs import get_logger

logging = get_logger("runner")


async def main():
    router_start = 20001
    publisher_start = 21001
    nodes = []
    num_nodes = 10

    # at2_config = AT2Configuration(10, 10, 10, 6, 8, 9)
    # at2_config = AT2Configuration(7, 7, 7, 5, 6, 7)
    at2_config = AT2Configuration(6, 6, 6, 4, 5, 6)

    router_list = [
        "tcp://127.0.0.1:20001",
        "tcp://127.0.0.1:20002",
        "tcp://127.0.0.1:20003",
        "tcp://127.0.0.1:20004",
        "tcp://127.0.0.1:20005",
        "tcp://127.0.0.1:20006",
        "tcp://127.0.0.1:20007",
        "tcp://127.0.0.1:20008",
        "tcp://127.0.0.1:20009",
        "tcp://127.0.0.1:20010",
    ]

    for _ in range(num_nodes):
        nodes.append(
            Node(
                router_bind=f"tcp://127.0.0.1:{router_start}",
                publisher_bind=f"tcp://127.0.0.1:{publisher_start}",
                at2_config=at2_config,
            )
        )
        router_start += 1
        publisher_start += 1

    for node in nodes:
        await node.init_sockets()
        await node.start()

    await asyncio.sleep(2.5)

    for node in nodes:
        await node.peer_discovery(deepcopy(router_list))

    # sub = SubscribeToPublisher("tcp://127.0.0.1:21001", "yolo")
    # n2.command(sub)

    await asyncio.sleep(1)

    n1 = nodes[0]
    n2 = nodes[1]
    n3 = nodes[2]

    while True:
        gos = Gossip(
            message_type="Gossip",
        )

        n1.command(gos)

        # n1.command(gos, "tcp://127.0.0.1:20002")
        # n1.command(gos, "tcp://127.0.0.1:20002")
        # n1.command(gos, "tcp://127.0.0.1:20002")
        # n1.command(gos, "tcp://127.0.0.1:20002")
        # n1.command(gos, "tcp://127.0.0.1:20002")
        # n1.command(gos, "tcp://127.0.0.1:20002")
        # n1.command(gos, "tcp://127.0.0.1:20002")
        # n1.command(gos, "tcp://127.0.0.1:20002")
        # n1.command(gos, "tcp://127.0.0.1:20002")
        # n1.command(gos, "tcp://127.0.0.1:20002")

        # print(n2.received_messages)
        await asyncio.sleep(1)


async def shutdown(signal, loop):
    logging.info(f"Received exit signal {signal.name}...")

    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    for task in tasks:
        task.cancel()

    logging.info("Cancelling outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


if __name__ == "__main__":
    loop = uvloop.new_event_loop()
    asyncio.set_event_loop(loop)

    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(s, lambda s=s: asyncio.create_task(shutdown(s, loop)))

    try:
        loop.create_task(main())
        loop.run_forever()
    finally:
        logging.info("Successfully shutdown service")
        loop.close()
