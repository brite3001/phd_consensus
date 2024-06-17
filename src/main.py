from copy import deepcopy
from pathlib import Path

import asyncio
import signal
import uvloop
import random
import time
import os
import ifaddr

from iot_node.node import Node
from iot_node.message_classes import Gossip
from iot_node.at2_classes import AT2Configuration
from logs import get_logger

logging = get_logger("runner")


async def main():
    nodes = []
    NUM_NODES = 5
    transport_type = "DOCKER"

    # at2_config = AT2Configuration(10, 10, 10, 6, 8, 9)
    # at2_config = AT2Configuration(7, 7, 7, 5, 6, 7)
    at2_config = AT2Configuration(6, 6, 6, 4, 5, 6)

    router_list = []
    if transport_type == "DOCKER":
        network_interface = "eth0"
        adapters = ifaddr.get_adapters()

        for adapter in adapters:
            # print("IPs of network adapter " + adapter.nice_name)
            for ip in adapter.ips:
                if adapter.nice_name == network_interface and ip.is_IPv4:
                    docker_ip = f"tcp://{str(ip.ip)}"
            # print("   %s/%s" % (ip.ip, ip.network_prefix))
        print("Docker environment detected")
        print(f"Network interface {network_interface} has IP: {docker_ip}")

        for i in range(NUM_NODES):
            router_list.append(f"tcp://192.168.99.{2+i}:20001")

        nodes.append(
            Node(
                router_bind=f"{docker_ip}:{20001}",
                publisher_bind=f"{docker_ip}:{21001}",
                at2_config=at2_config,
                startup_ready=set(),
            )
        )

    else:
        logging.error("Check transport type")

    logging.info("Spinning up nodes...")
    for node in nodes:
        await node.init_sockets()
        await node.start()

    logging.info("Running peer discovery...")
    for node in nodes:
        asyncio.create_task(node.peer_discovery(deepcopy(router_list)))

    n1 = nodes[0]

    # Wait for at least 1 node to be ready.
    # Nodes only become ready once all their peers are ready
    while len(list(n1.sockets.keys())) != len(router_list) - 1:
        logging.info(
            f"Not all nodes ready {len(list(n1.sockets.keys()))} / {len(router_list) -1} "
        )
        await asyncio.sleep(1)

    logging.info(
        f"All nodes ready {len(list(n1.sockets.keys()))} / {len(router_list) -1} "
    )

    await asyncio.sleep(5)

    # ###########
    # # Fast    #
    # ###########

    for i in range(1000):
        gos = Gossip(message_type="Gossip", timestamp=int(time.time()))
        n = random.choice(nodes)

        # if n1.router_bind == "tcp://192.168.99.2:20001":
        logging.info(f"Fast {i}")
        n1.command(gos)
        n1.command(gos)
        n1.command(gos)
        n1.command(gos)
        n1.command(gos)
        n1.command(gos)
        n1.command(gos)

        await asyncio.sleep(10)

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
