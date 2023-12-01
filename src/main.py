import asyncio
import signal
import logging

from iot_node.node import Node
from iot_node.commad_arg_classes import SubscribeToPublisher
from iot_node.message_classes import DirectMessage
from iot_node.message_classes import PublishMessage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


async def shutdown(signal, loop):
    logging.info(f"Received exit signal {signal.name}...")

    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    for task in tasks:
        task.cancel()

    logging.info("Cancelling outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


async def main():
    n1 = Node(
        id="node_one",
        router_bind="tcp://127.0.0.1:20001",
        publisher_bind="tcp://127.0.0.1:21002",
    )
    n2 = Node(
        id="node_two",
        router_bind="tcp://127.0.0.1:20002",
        publisher_bind="tcp://127.0.0.1:21001",
    )

    await n1.init_pub_sub()
    await n1.start()

    await n2.init_pub_sub()
    await n2.start()

    sub = SubscribeToPublisher("tcp://127.0.0.1:21002", "yolo")
    n1.command(sub)

    while True:
        dm = DirectMessage(
            sender=n1.id,
            message="Hello!!!",
            message_type="DirectMessage",
            receiver="tcp://127.0.0.1:20002",
        )
        n1.command(dm)
        await asyncio.sleep(5)

        pub = PublishMessage(n1.id, "Testing Da Publish", "PublishMessage", "yolo")
        n1.command(pub)
        await asyncio.sleep(5)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(s, lambda s=s: asyncio.create_task(shutdown(s, loop)))

    try:
        loop.create_task(main())
        loop.run_forever()
    finally:
        logging.info("Successfully shutdown service")
        loop.close()
