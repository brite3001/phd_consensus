from copy import deepcopy

import asyncio
import signal
import uvloop
import random
import time

from stats import plot_avg_min_max_block_time
from stats import plot_batched_message_magnitude
from stats import average_min_max_lists
from iot_node.node import Node
from iot_node.message_classes import Gossip
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

    logging.info("Spinning up nodes...")
    for node in nodes:
        await node.init_sockets()
        await node.start()

    await asyncio.sleep(2.5)

    logging.info("Running peer discovery...")
    for node in nodes:
        await node.peer_discovery(deepcopy(router_list))

    # sub = SubscribeToPublisher("tcp://127.0.0.1:21001", "yolo")
    # n2.command(sub)

    await asyncio.sleep(1)

    n1 = nodes[0]

    start_time = time.time()
    for i in range(1000):
        print(i)
        gos = Gossip(message_type="Gossip", timestamp=int(time.time()))
        n = random.choice(nodes)

        n.command(gos)
        n.command(gos)
        n.command(gos)
        n.command(gos)
        n.command(gos)
        n.command(gos)
        n.command(gos)

        await asyncio.sleep(0.25)
    end_time = time.time()

    await asyncio.sleep(30)

    print(f"Time taken: {round(end_time - start_time, 3)}s")
    for n in nodes:
        n.statistics()
        print("---------------------------")

    received_msg_metadata = []
    sent_msg_metadata = []
    node_ids = []

    for node in nodes:
        received_msg_metadata.append(node.block_times)
        sent_msg_metadata.append(node.sent_msg_metadata)
        node_ids.append(node.id)

    avg_list, min_list, max_list = average_min_max_lists(received_msg_metadata)
    plot_batched_message_magnitude(sent_msg_metadata)
    plot_avg_min_max_block_time(avg_list, min_list, max_list)


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
