import os
import matplotlib.pyplot as plt
from collections import defaultdict
import numpy as np


def calculate_average_transactions(data, interval):
    # Adjust timestamps to start at 0
    start_time = data[0][0]
    adjusted_data = [(timestamp - start_time, count) for timestamp, count in data]

    # Determine the range of intervals
    end_time = adjusted_data[-1][0]
    num_intervals = (
        int(np.ceil(end_time / interval)) + 1
    )  # Add 1 to include the last interval

    # Initialize a list to store the number of transactions per interval
    interval_transactions = [0] * num_intervals

    # Aggregate transactions in each interval
    for timestamp, count in adjusted_data:
        interval_index = int(timestamp // interval)
        if interval_index < num_intervals:  # Ensure the index is within range
            interval_transactions[interval_index] += count

    # Calculate the average transactions per interval
    average_transactions = [count / interval for count in interval_transactions]

    # Prepare the data for plotting
    x_values = [i * interval for i in range(num_intervals)]

    return x_values, average_transactions


def load_tuple(test_name: str, file_name: str) -> list:
    try:
        # Assuming the subfolder is named 'data'
        subfolder = test_name
        file_path = os.path.join(subfolder, file_name)

        with open(file_path, "r") as f:  # Open file in read mode
            content = (
                f.read().strip()
            )  # Read the content of the file and remove leading/trailing whitespace
            return eval(
                content
            )  # Evaluate the content as Python code and return the resulting list
    except FileNotFoundError:
        print(f"File '{file_name}' not found.")
        return []


smooth_latency = list(load_tuple("tps", "smooth_latency.txt"))

smooth_latency = [item for sublist in smooth_latency for item in sublist]

delivered_with_batch_size = list(load_tuple("tps", "delivered_with_batch_size.txt"))

delivered_with_batch_size = [
    item for sublist in delivered_with_batch_size for item in sublist
]


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


###########################
###### TPS CALC ##########
##########################
tps_calculation = [(x[0], 1) for x in delivered_with_batch_size]

interval = 5  # Calculate average transactions every 10 seconds
x_values, average_transactions = calculate_average_transactions(
    tps_calculation, interval
)

###########################
###### LATENCY AND BATCHSIZE CALC ##########
##########################
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

# Extract data for plotting
latency_unix_timestamp, latency = zip(*average_latency)
batch_unix_timestamp, batch_size = zip(*average_batch_size)

# Plotting
plt.figure()

# Plotting latency as a line graph on primary y-axis
plt.plot(latency_unix_timestamp, latency, "b-", label="Latency")

# Plotting latency as a line graph on primary y-axis
plt.plot(x_values, average_transactions, marker="o", label="TPS")

# Plotting batch size as a shaded area plot on primary y-axis
plt.fill_between(
    batch_unix_timestamp, 0, batch_size, color="green", alpha=0.3, label="Batch Size"
)

plt.xlabel("Time")
plt.ylabel("Latency (s) / Batch Size (number of transactions)")
plt.title("Latency and Batch Size over Time")
plt.legend()

plt.show()
