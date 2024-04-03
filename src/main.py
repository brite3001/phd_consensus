from copy import deepcopy

import asyncio
import signal
import uvloop
import random
import time
import os

from iot_node.node import Node
from iot_node.message_classes import Gossip
from iot_node.at2_classes import AT2Configuration
from logs import get_logger

logging = get_logger("runner")


def save_list(ints_to_save: list, test_name: str, file_name: str):
    subfolder = f"graphs/{test_name}"
    folder_path = os.path.join(
        os.getcwd(), subfolder
    )  # Get the current working directory and append the subfolder name
    os.makedirs(folder_path, exist_ok=True)  # Create the subfolder if it doesn't exist

    file_path = os.path.join(
        folder_path, file_name
    )  # Create the complete file path within the subfolder
    try:
        with open(
            file_path, "x"
        ) as f:  # 'x' mode opens for exclusive creation, fails if the file already exists
            f.write(",".join(map(str, ints_to_save)))
    except FileExistsError:
        print("File already exists. Use a different file name.")


def average_min_max_lists(lists):
    # Find the length of the longest list
    max_length = max(len(lst) for lst in lists)

    # Initialize lists to store the sums, counts, minimums, and maximums
    sum_list = [0] * max_length
    count_list = [0] * max_length
    min_list = [float("inf")] * max_length
    max_list = [float("-inf")] * max_length

    # Calculate the sums, counts, minimums, and maximums
    for lst in lists:
        for i, val in enumerate(lst):
            sum_list[i] += val
            count_list[i] += 1
            min_list[i] = min(min_list[i], val)
            max_list[i] = max(max_list[i], val)

    # Calculate the averages
    avg_list = [
        sum_val / count_val if count_val != 0 else float("nan")
        for sum_val, count_val in zip(sum_list, count_list)
    ]

    return avg_list, min_list, max_list


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

    TEST_NAME = "tsi-kama"
    start_time = time.time()

    # ###########
    # # Fast    #
    # ###########

    for i in range(2000):
        print(f"Fast {i}")
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

    for node in nodes:
        node.scheduler.pause_job(node.increase_job_id)
        node.scheduler.pause_job(node.decrease_job_id)

    await asyncio.sleep(60)

    for node in nodes:
        node.scheduler.resume_job(node.increase_job_id)
        node.scheduler.resume_job(node.decrease_job_id)

    ###########
    # Slow    #
    ###########
    for i in range(1000):
        print(f"Slow {i}")
        gos = Gossip(message_type="Gossip", timestamp=int(time.time()))
        n = random.choice(nodes)

        n.command(gos)
        n.command(gos)
        n.command(gos)
        n.command(gos)
        n.command(gos)
        n.command(gos)
        n.command(gos)

        await asyncio.sleep(1)

    for node in nodes:
        node.scheduler.pause_job(node.increase_job_id)
        node.scheduler.pause_job(node.decrease_job_id)

    await asyncio.sleep(60)

    for node in nodes:
        node.scheduler.resume_job(node.increase_job_id)
        node.scheduler.resume_job(node.decrease_job_id)

    ###########
    # Mixed   #
    ###########
    for i in range(2000):
        print(f"Mixed {i}")
        gos = Gossip(message_type="Gossip", timestamp=int(time.time()))
        n = random.choice(nodes)

        n.command(gos)
        n.command(gos)
        n.command(gos)
        n.command(gos)
        n.command(gos)
        n.command(gos)
        n.command(gos)

        await asyncio.sleep(random.uniform(0.1, 1))

    for node in nodes:
        node.scheduler.pause_job(node.increase_job_id)
        node.scheduler.pause_job(node.decrease_job_id)

    await asyncio.sleep(60)

    end_time = time.time()

    for n in nodes:
        print(hash(tuple(n.sequenced_messages)))

    print(f"Time taken: {round(end_time - start_time, 3)}s")
    # for n in nodes:
    #     n.statistics()
    #     print("---------------------------")

    received_msg_metadata = []
    sent_msg_metadata = []
    node_ids = []
    total_sent_messages = 0
    total_received_messages = 0
    total_messages_delivered = 0

    for node in nodes:
        received_msg_metadata.append(node.block_times)
        sent_msg_metadata.append(node.sent_msg_metadata)
        node_ids.append(node.id)
        total_sent_messages += node.sent_gossips
        total_received_messages += node.received_gossips
        total_messages_delivered += node.delivered_gossips

    avg_list, min_list, max_list = average_min_max_lists(received_msg_metadata)

    save_list(avg_list, TEST_NAME, "avg.txt")
    save_list(min_list, TEST_NAME, "min.txt")
    save_list(max_list, TEST_NAME, "max.txt")
    aaa = [total_sent_messages, total_received_messages, total_messages_delivered]
    save_list(aaa, TEST_NAME, "sent_recv_deliv.txt")
    save_list(sent_msg_metadata, TEST_NAME, "sent_metadata.txt")

    print("**********************************")
    print("FINISHED!!!")
    print("Dont forget to change the TEST TYPE!!")
    print("**********************************")


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
