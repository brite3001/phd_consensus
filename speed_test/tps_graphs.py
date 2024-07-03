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

tps_calculation = [(x[0], 1) for x in delivered_with_batch_size]


# Helper function to convert Unix timestamps to seconds from the start
def convert_to_seconds_from_start(timestamps):
    start_time = timestamps[0]
    return [int(timestamp - start_time) for timestamp in timestamps]


# Helper function to group data into intervals and calculate averages
def group_and_average(data, interval=10):
    grouped = defaultdict(list)
    for timestamp, value in data:
        interval_start = timestamp - (timestamp % interval)
        grouped[interval_start].append(value)

    averaged_data = []
    for interval_start, values in sorted(grouped.items()):
        averaged_data.append((interval_start, sum(values) / len(values)))

    return averaged_data


# Convert Unix timestamps to seconds from the start
latency_unix_timestamp, latency = zip(*smooth_latency)
latency_unix_timestamp_seconds = convert_to_seconds_from_start(latency_unix_timestamp)

batch_unix_timestamp, batch_size = zip(*delivered_with_batch_size)
batch_unix_timestamp_seconds = convert_to_seconds_from_start(batch_unix_timestamp)

tps_unix_timestamp, tps_size = zip(*tps_calculation)
tps_unix_timestamp_seconds = convert_to_seconds_from_start(tps_unix_timestamp)

# Group and average latency and batch size data
average_latency = group_and_average(zip(latency_unix_timestamp_seconds, latency))
average_batch_size = group_and_average(zip(batch_unix_timestamp_seconds, batch_size))
average_tps = group_and_average(zip(tps_unix_timestamp_seconds, tps_size))

# Extract data for plotting
latency_unix_timestamp, latency = zip(*average_latency)
batch_unix_timestamp, batch_size = zip(*average_batch_size)
tps_unix_timestamp, tps = zip(*average_tps)

# Plotting
plt.figure()

# Plotting latency as a line graph on primary y-axis
plt.plot(latency_unix_timestamp, latency, "b-", label="Latency")

# Plotting latency as a line graph on primary y-axis
plt.plot(tps_unix_timestamp, tps, "b-", label="TPS")

# Plotting batch size as a shaded area plot on primary y-axis
plt.fill_between(
    batch_unix_timestamp, 0, batch_size, color="green", alpha=0.3, label="Batch Size"
)

plt.xlabel("Time (Seconds from Start)")
plt.ylabel("Latency / Batch Size")
plt.title("Latency and Batch Size over Time")
plt.legend()

plt.show()
