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


smooth_latency = list(load_tuple("tps", "current_latency.json"))

# print(smooth_latency)

smooth_latency = [tuple(sublist) for sublist in smooth_latency]

delivered_with_batch_size = list(load_tuple("tps", "delivered_latency.json"))

# delivered_with_batch_size = [
#     item for sublist in delivered_with_batch_size for item in sublist
# ]

delivered_with_batch_size = [tuple(sublist) for sublist in delivered_with_batch_size]

tps_timestamps = [x[0] for x in delivered_with_batch_size]

interval = 1


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


times, tps = group_transactions(tps_timestamps, interval)

print(times)
print(tps)


# Convert Unix timestamps to seconds from the start
latency_unix_timestamp, latency = zip(*smooth_latency)
latency_unix_timestamp_seconds = convert_to_seconds_from_start(latency_unix_timestamp)

batch_unix_timestamp, batch_size = zip(*delivered_with_batch_size)
batch_unix_timestamp_seconds = convert_to_seconds_from_start(batch_unix_timestamp)

# tps_unix_timestamp, tps_size = zip(*tps_calculation)
# tps_unix_timestamp_seconds = convert_to_seconds_from_start(tps_unix_timestamp)

# Group and average latency and batch size data
average_latency = group_and_average(
    zip(latency_unix_timestamp_seconds, latency), interval
)
average_batch_size = group_and_average(
    zip(batch_unix_timestamp_seconds, batch_size), interval
)
# average_tps = group_and_average(zip(tps_unix_timestamp_seconds, tps_size))

# print(average_tps)

# Extract data for plotting
latency_unix_timestamp, latency = zip(*average_latency)
batch_unix_timestamp, batch_size = zip(*average_batch_size)
# tps_unix_timestamp, tps = zip(*average_tps)

# Plotting
plt.figure()

# Plotting latency as a line graph on primary y-axis
plt.plot(latency_unix_timestamp, latency, "b-", label="Latency")

# Plotting latency as a line graph on primary y-axis
plt.plot(times, tps, "b--", label="TPS")

# Plotting batch size as a shaded area plot on primary y-axis
plt.fill_between(
    batch_unix_timestamp, 0, batch_size, color="green", alpha=0.3, label="Batch Size"
)

plt.xlabel("Time (Seconds from Start)")
plt.ylabel("Latency / Batch Size")
plt.title("Latency and Batch Size over Time")
plt.legend()

plt.show()
