from copy import deepcopy
import asyncio
import signal
import logging
import uvloop

from iot_node.node import Node
from iot_node.commad_arg_classes import SubscribeToPublisher
from iot_node.message_classes import DirectMessage
from iot_node.message_classes import PublishMessage
from iot_node.message_classes import Gossip
from iot_node.message_classes import PeerDiscovery

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


async def main():
    router_start = 20001
    publisher_start = 21001
    nodes = []

    n1 = Node(
        router_bind="tcp://127.0.0.1:20001",
        publisher_bind="tcp://127.0.0.1:21001",
    )
    n2 = Node(
        router_bind="tcp://127.0.0.1:20002",
        publisher_bind="tcp://127.0.0.1:21002",
    )

    router_list = ["tcp://127.0.0.1:20001", "tcp://127.0.0.1:20002"]

    await n1.init_sockets()
    await n1.start()
    await n1.peer_discovery(deepcopy(router_list))

    await n2.init_sockets()
    await n2.start()
    await n2.peer_discovery(deepcopy(router_list))

    sub = SubscribeToPublisher("tcp://127.0.0.1:21001", "yolo")
    n2.command(sub)

    await asyncio.sleep(2.5)

    while True:
        dm = DirectMessage(
            message_type="DirectMessage",
        )

        gos = Gossip(
            message_type="Gossip",
        )

        n1.command(gos, "tcp://127.0.0.1:20002")
        n1.command(gos, "tcp://127.0.0.1:20002")
        n1.command(gos, "tcp://127.0.0.1:20002")
        n1.command(gos, "tcp://127.0.0.1:20002")
        n1.command(gos, "tcp://127.0.0.1:20002")
        n1.command(gos, "tcp://127.0.0.1:20002")
        n1.command(gos, "tcp://127.0.0.1:20002")
        n1.command(gos, "tcp://127.0.0.1:20002")
        n1.command(gos, "tcp://127.0.0.1:20002")
        n1.command(gos, "tcp://127.0.0.1:20002")

        # pub = PublishMessage(
        #     creator=n1.id,
        #     message="Testing Da Publish",
        #     message_type="PublishMessage",
        #     topic="yolo",
        # )
        # meta = MessageMetaData(batched=False, sender=n1.id)
        # n1.command(pub, meta)
        # await asyncio.sleep(1)

        # print(n2.received_messages)
        await asyncio.sleep(5)


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
