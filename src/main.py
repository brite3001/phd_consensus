from copy import deepcopy
from matplotlib.colors import ListedColormap
import numpy as np
import matplotlib.pyplot as plt
import asyncio
import signal
import uvloop
import random
import time

from iot_node.node import Node
from iot_node.message_classes import Gossip
from iot_node.at2_classes import AT2Configuration
from logs import get_logger

logging = get_logger("runner")


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


def adjust_timestamps(data):
    # Find the oldest timestamp
    oldest_timestamp = min(data, key=lambda x: x[1])[1]

    # Adjust timestamps relative to the oldest timestamp
    adjusted_timestamps = [timestamp - oldest_timestamp for _, timestamp, _ in data]

    return adjusted_timestamps


def plot_avg_min_max(avg_list, min_list, max_list):
    # Create x-axis values
    x = np.arange(len(avg_list))

    # Plot the average line
    plt.plot(x, avg_list, label="Average", color="blue")

    # Plot the shaded region between the minimum and maximum curves
    plt.fill_between(
        x, min_list, max_list, color="gray", alpha=0.3, label="Range (Min-Max)"
    )

    # Plot the minimum and maximum curves
    plt.plot(x, min_list, label="Minimum", linestyle="--", color="green")
    plt.plot(x, max_list, label="Maximum", linestyle="--", color="red")
    plt.axhline(y=28, color="orange", linestyle="--", label="TPS")

    # Add labels, title, and legend
    plt.xlabel("Message Index")
    plt.ylabel("Latency (s)")
    plt.title("Network Latency")
    plt.legend()

    # Show the plot
    plt.show()


def plot_message_data(data):
    # flatten
    data = [item for sublist in data for item in sublist]

    # Adjust timestamps relative to the oldest timestamp
    adjusted_timestamps = adjust_timestamps(data)

    # Create a dictionary to map each nodeid to a unique color
    unique_ids = set(item[2] for item in data)
    num_ids = len(unique_ids)
    cmap = plt.cm.get_cmap("tab10", num_ids)
    id_color_map = {id: cmap(i) for i, id in enumerate(unique_ids)}

    # Extract message sizes and nodeids from the data
    message_sizes = [item[0] for item in data]
    nodeids = [item[2] for item in data]

    # Plot the data and collect legend handles and labels
    handles = []
    labels = []
    for timestamp, message_size, nodeid in zip(
        adjusted_timestamps, message_sizes, nodeids
    ):
        line = plt.vlines(
            x=timestamp, ymin=0, ymax=message_size, color=id_color_map[nodeid]
        )
        if nodeid not in labels:
            handles.append(line)
            labels.append(nodeid)

    # Add legend for the colors of the different nodes
    plt.legend(handles, labels, title="Node ID", loc="upper left")

    # Add labels, title, and legend
    plt.xlabel("Time (seconds)")
    plt.ylabel("Message Size")
    plt.title("Message Size Over Time")

    # Show the plot
    plt.show()


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
    for i in range(200):
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

        # print(n2.received_messages)
        await asyncio.sleep(0.25)
    end_time = time.time()

    await asyncio.sleep(30)

    print(f"Time taken: {round(end_time - start_time, 3)}s")
    for n in nodes:
        n.statistics()
        print("---------------------------")

    received_msg_metadata = []
    sent_msg_metadatas = []
    node_ids = []

    for node in nodes:
        received_msg_metadata.append(node.block_times)
        sent_msg_metadatas.append(node.sent_msg_metadata)
        node_ids.append(node.id)

    avg_list, min_list, max_list = average_min_max_lists(received_msg_metadata)
    plot_message_data(sent_msg_metadatas)
    plot_avg_min_max(avg_list, min_list, max_list)


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
