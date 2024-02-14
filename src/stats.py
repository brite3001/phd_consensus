import numpy as np
import matplotlib.pyplot as plt


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


def plot_avg_min_max_block_time(avg_list, min_list, max_list):
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


def plot_batched_message_magnitude(data):
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
