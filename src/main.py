from copy import deepcopy

import asyncio
import signal
import uvloop
import random
import time
import os

from iot_node.node import Node
from iot_node.message_classes import Gossip
from iot_node.message_classes import PublishMessage
from iot_node.at2_classes import AT2Configuration
from logs import get_logger

logging = get_logger("runner")


def get_node_port():
    node_port = os.getenv("NODE_ID")
    if node_port is None:
        raise ValueError("NODE_ID environment variable is not set")
    return int(node_port)


async def main():
    nodes = []
    NUM_NODES = 50

    # at2_config = AT2Configuration(10, 10, 10, 6, 8, 9)
    # at2_config = AT2Configuration(7, 7, 7, 5, 6, 7)
    at2_config = AT2Configuration(6, 6, 6, 4, 5, 6)

    my_node_id = get_node_port()

    router_list = []

    for i in range(NUM_NODES):
        if i != my_node_id:
            router_list.append(f"tcp://127.0.0.1:{20001+i}")

    nodes.append(
        Node(
            router_bind=f"tcp://127.0.0.1:{20001 + my_node_id}",
            publisher_bind=f"tcp://127.0.0.1:{21001 + my_node_id}",
            at2_config=at2_config,
        )
    )

    logging.warning("Spinning up nodes...")
    for node in nodes:
        await node.init_sockets()
        await node.start()

    await asyncio.sleep(0.5 * NUM_NODES)

    logging.warning("Running peer discovery...")
    for node in nodes:
        await node.peer_discovery(router_list)

    await asyncio.sleep(0.5 * NUM_NODES)

    n1 = nodes[0]

    # Wait for at least 1 node to be ready.
    # Nodes only become ready once all their peers are ready
    while len(list(n1.sockets.keys())) != len(router_list):
        logging.warning(
            f"Not all nodes ready {len(list(n1.sockets.keys()))} / {len(router_list)} "
        )

        await asyncio.sleep(1)

    logging.warning(
        f"All nodes ready {len(list(n1.sockets.keys()))} / {len(router_list)} "
    )

    await asyncio.sleep(5)

    # ###########
    # # Fast    #
    # ###########

    for i in range(2000):
        gos = Gossip(message_type="Gossip", timestamp=int(time.time()))
        if n1.router_bind == "tcp://127.0.0.1:20001":
            # if random.randint(1, 10) == 5:
            logging.error(f"Fast {i}")
            n1.command(gos)
            n1.command(gos)
            n1.command(gos)
            n1.command(gos)
            n1.command(gos)
            n1.command(gos)
            n1.command(gos)

            await asyncio.sleep(0.5)

    for node in nodes:
        node.scheduler.pause_job(node.increase_job_id)
        node.scheduler.pause_job(node.decrease_job_id)


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
