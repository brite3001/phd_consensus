import os
import matplotlib.pyplot as plt
from collections import defaultdict
import json


def load_tuple(test_name: str, file_name: str) -> list:
    try:
        # Assuming the subfolder is named 'data'
        subfolder = test_name
        file_path = os.path.join(subfolder, file_name)

        with open(file_path, "r") as f:  # Open file in read mode
            content = json.load(f)  # Parse the JSON content
            return content  # Return the resulting list
    except FileNotFoundError:
        print(f"File '{file_name}' not found.")
        return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return []


# Helper function to convert Unix timestamps to seconds from the start
def convert_to_seconds_from_start(timestamps):
    start_time = timestamps[0]
    return [int(timestamp - start_time) for timestamp in timestamps]


def group_and_average(data, interval):
    grouped = defaultdict(list)

    for timestamp, value in data:
        # Align the timestamp to the nearest interval start
        interval_start = int(timestamp // interval) * interval
        grouped[interval_start].append(value)

    averaged_data = []
    for interval_start, values in sorted(grouped.items()):
        averaged_data.append((interval_start, sum(values) / len(values)))

    return averaged_data


def group_transactions(timestamps, interval=1):
    # Normalize timestamps
    start_time = timestamps[0]
    normalized_times = [int(ts - start_time) for ts in timestamps]

    # Group transactions by intervals
    max_time = normalized_times[-1]
    num_intervals = (max_time // interval) + 1

    grouped_transactions = [0] * num_intervals

    for time in normalized_times:
        index = time // interval
        if index < len(grouped_transactions):
            grouped_transactions[index] += 1
        else:
            # Extend the grouped_transactions list to accommodate new interval
            grouped_transactions.extend([0] * (index - len(grouped_transactions) + 1))
            grouped_transactions[index] += 1

    # Generate interval ranges
    interval_ranges = [(i * interval) for i in range(len(grouped_transactions))]

    return interval_ranges, grouped_transactions


tests = [
    "GOLD_DATA_LAPTOP_CCA",
    "GOLD_DATA_SERVER_CCA",
    "GOLD_LAPTOP_DOUBLE_BATCH",
    "GOLD_SERVER_DOUBLE_BATCH",
]

markers = ["o", "s", "^", "d"]

colours = ["red", "blue", "green", "magenta"]

names = ["10 Node", "100 Node", "10 Node Double Batch", "100 Node Double Batch"]

interval = 20

for test_name, marker, colour, name in zip(tests, markers, colours, names):
    print(test_name)
    smooth_latency = list(load_tuple(test_name, "current_latency.json"))

    smooth_latency = [tuple(sublist) for sublist in smooth_latency]

    delivered_with_batch_size = list(load_tuple(test_name, "delivered_latency.json"))

    delivered_with_batch_size = [
        tuple(sublist) for sublist in delivered_with_batch_size
    ]

    tps_timestamps = [x[0] for x in delivered_with_batch_size]

    times, tps = group_transactions(tps_timestamps, interval)

    # Convert Unix timestamps to seconds from the start
    latency_unix_timestamp, latency = zip(*smooth_latency)
    latency_unix_timestamp_seconds = convert_to_seconds_from_start(
        latency_unix_timestamp
    )

    batch_unix_timestamp, batch_size = zip(*delivered_with_batch_size)
    batch_unix_timestamp_seconds = convert_to_seconds_from_start(batch_unix_timestamp)

    # Group and average latency and batch size data
    average_latency = group_and_average(
        zip(latency_unix_timestamp_seconds, latency), interval
    )
    average_batch_size = group_and_average(
        zip(batch_unix_timestamp_seconds, batch_size), interval
    )

    # Extract data for plotting
    latency_unix_timestamp, latency = zip(*average_latency)
    batch_unix_timestamp, batch_size = zip(*average_batch_size)

    print(tps)
    print(batch_size)

    # Plotting latency as a line graph on primary y-axis
    # plt.plot(latency_unix_timestamp, latency, "b-", label="Latency")

    throughput = (
        [t * b_size * 1 for t, b_size in zip(tps, batch_size)]
        if test_name != "GOLD_DATA_LAPTOP_CCA"
        else [t * 10 * 1 for t in tps]
    )

    # Plotting throughput as a line graph on primary y-axis
    plt.plot(times, throughput, marker=marker, label=name, color=colour)


plt.xlabel("Time (Seconds from Start)")
plt.ylabel("Throughput (mb/s)")
plt.title("10 Node and 100 Node Throughput")
plt.legend()

plt.show()
