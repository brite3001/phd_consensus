import numpy as np
import matplotlib.pyplot as plt
import os
import matplotlib.markers as markers

plt.rcParams["font.size"] = 18


def mean_absolute_deviation(y, target):
    return np.mean(np.abs(np.array(y) - target))


def root_mean_squared_error(y, target):
    return np.sqrt(np.mean((np.array(y) - target) ** 2))


def adjust_timestamps(data):
    # Find the oldest timestamp

    min_timestamp = [x[1] for x in data]
    min_timestamp.sort()
    min_timestamp = min_timestamp[0]

    # Adjust timestamps relative to the oldest timestamp
    adjusted_timestamps = [timestamp - min_timestamp for _, timestamp, _ in data]

    return adjusted_timestamps


def adjust_timestamps_simple(data):
    # Find the oldest timestamp

    min_timestamp = [x[1] for x in data]
    min_timestamp.sort()
    min_timestamp = min_timestamp[0]

    # Adjust timestamps relative to the oldest timestamp
    adjusted_timestamps = [
        (magnitude, timestamp - min_timestamp, node_id)
        for magnitude, timestamp, node_id in data
    ]

    return adjusted_timestamps


def random_color():
    """Generate a random RGB color."""
    return np.random.rand(
        3,
    )


def random_marker():
    """Select a random marker from the available options."""
    marker_list = list(markers.MarkerStyle.markers.keys())
    return np.random.choice(marker_list)


def plot_simple_combined_average():
    rsi_tests = [
        "graphs/tsi-savgol",
        "graphs/tsi-ema",
        "graphs/tsi-kalman-zlema",
        "graphs/tsi-kama",
        "graphs/tsi-sma",
    ]
    savgol = []
    ema = []
    zlema = []
    kama = []
    sma = []

    for test in rsi_tests:
        if test == "graphs/tsi-savgol":
            savgol = np.array(load_floats(test, "avg.txt"))
        elif test == "graphs/tsi-ema":
            ema = np.array(load_floats(test, "avg.txt"))
        elif test == "graphs/tsi-kalman-zlema":
            zlema = np.array(load_floats(test, "avg.txt"))
        elif test == "graphs/tsi-kama":
            kama = np.array(load_floats(test, "avg.txt"))
        else:
            sma = np.array(load_floats(test, "avg.txt"))

    # print(block_averages)

    for test_name, plt_marker, plt_colour, test_data in zip(
        ["Savgol", "EMA", "KALMAN-ZLEMA", "KAMA", "SMA"],
        ["o", "s", "^", "D", "*"],
        ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
        [savgol, ema, zlema, kama, sma],
    ):
        # Average out the data, make less verbose
        # Desired block size
        block_size = 10

        # Full blocks
        full_blocks = len(test_data) // block_size
        block_averages = (
            test_data[: full_blocks * block_size]
            .reshape(full_blocks, block_size)
            .mean(axis=1)
        )

        # Remainder block
        remainder = test_data[full_blocks * block_size :]
        if remainder.size > 0:
            remainder_average = remainder.mean()
            block_averages = np.append(block_averages, remainder_average)

        block_averages = [x for x in block_averages if x <= 60]

        # Plot the average line
        plt.plot(
            np.arange(len(block_averages)),
            block_averages,
            label=test_name,
            marker=plt_marker,
            linestyle="-",
            color=plt_colour,
        )

    plt.axhline(y=10, color="black", linestyle="-", label="Target Latency")

    # Add labels, title, and legend
    plt.xlabel("Message Index")
    plt.ylabel("Latency (s)")
    plt.title("Message Latency - TSI")
    plt.legend()

    plt.show()


def plot_avg_min_max_block_time(avg_list, min_list, max_list, TEST_NAME):
    # Create x-axis values
    x = np.arange(len(avg_list))

    # Plot the average line
    plt.plot(x, avg_list, label="Average", linestyle=":", color="blue")

    # # Plot the shaded region between the minimum and maximum curves
    # plt.fill_between(
    #     x, min_list, max_list, color="gray", alpha=0.3, label="Range (Min-Max)"
    # )

    # # Plot the minimum and maximum curves
    # plt.plot(x, min_list, label="Minimum", linestyle="--", color="green")
    # plt.plot(x, max_list, label="Maximum", linestyle="-.", color="red")
    plt.axhline(y=10, color="black", linestyle="-", label="Target Latency")

    # Add labels, title, and legend
    plt.xlabel("Message Index")
    plt.ylabel("Latency (s)")
    plt.title(f"Message Confirmation Time - {TEST_NAME}")
    plt.legend()

    target = 10  # Target linear line value

    # Calculate MAD and RMSE
    mad = round(mean_absolute_deviation(avg_list, target), 3)
    rmse = round(root_mean_squared_error(avg_list, target), 3)

    # Text content
    text_content = f"Mean Absolute Deviation: {mad}\nRoot Mean Squared error: {rmse}"

    # Add text in the top right corner with a box around it
    plt.text(
        x=0.5,
        y=0.98,
        s=text_content,
        fontsize=12,
        color="black",
        ha="center",
        va="top",
        bbox=dict(facecolor="white", edgecolor="gray", boxstyle="round,pad=0.25"),
        transform=plt.gca().transAxes,
    )

    subfolder = TEST_NAME
    file_name = "timing" + ".png"
    folder_path = os.path.join(
        os.getcwd(), subfolder
    )  # Get the current working directory and append the subfolder name
    os.makedirs(folder_path, exist_ok=True)  # Create the subfolder if it doesn't exist

    file_path = os.path.join(
        folder_path, file_name
    )  # Create the complete file path within the subfolder

    # plt.savefig(file_path)

    # Show the plot
    plt.show()


def plot_simple_magnitude(data):
    # flatten

    rsi_tests = [
        "graphs/rsi-savgol",
        "graphs/rsi-ema",
        "graphs/rsi-kalman-zlema",
        "graphs/rsi-kama",
        "graphs/rsi-sma",
    ]

    # Set the time bin size (e.g., 60 seconds)
    time_bin_size = 60
    data = list(load_tuple(test, "sent_metadata.txt"))
    data = [item for sublist in data for item in sublist]
    data = adjust_timestamps_simple(data)

    for test_name, plt_colour, plt_marker, test_path in zip(
        ["Savgol", "EMA", "KALMAN-ZLEMA", "KAMA", "SMA"],
        ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
        ["o", "s", "^", "D", "*"],
        rsi_tests,
    ):
        data = list(load_tuple(test_path, "sent_metadata.txt"))
        data = [item for sublist in data for item in sublist]
        data = adjust_timestamps_simple(data)

        # Determine the range of timestamps
        start_time = int(min(item[1] for item in data))
        end_time = int(max(item[1] for item in data))

        # Create bins for the histogram
        num_bins = (end_time - start_time) // time_bin_size + 1
        bins = np.linspace(
            start_time, end_time, num_bins + 1
        )  # Adding one more bin edge to include the last bin

        # Aggregate the data into time bins
        histogram_data = np.zeros(num_bins)
        for message_size, timestamp, _ in data:
            bin_index = int((timestamp - start_time) // time_bin_size)
            if bin_index < num_bins:  # Ensure bin_index is within bounds
                histogram_data[bin_index] += message_size

        # Plot the line graph
        plt.plot(
            bins[:-1],  # x-values: bin edges (excluding the last edge)
            histogram_data,  # y-values: aggregated message sizes
            linestyle="-",  # Solid line
            marker=plt_marker,  # Circle markers at data points
            color=plt_colour,  # Use black color for visibility in black and white
            label=test_name,
        )

        plt.legend(title="Legend", loc="upper right")

    # Add labels and title
    plt.xlabel("Time (seconds)")
    plt.ylabel("Average Transaction Size")
    plt.title("Message Batching - RSI")

    plt.show()


def plot_batched_message_magnitude(
    data, TEST_NAME, sent: int, received: int, delivered: int
):
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
    plt.ylabel("Number of batched messages per message")
    plt.title(f"Batch Size Over Time {TEST_NAME}")

    # Text content
    text_content = f"Total Sent Messages: {sent}\nTotal Received Messages: {received}\nTotal Delivered Messages: {delivered}\nTotal Missed: {sent+received-delivered}"

    # Add text in the top right corner with a box around it
    plt.text(
        0.98,
        0.98,
        text_content,
        fontsize=12,
        color="black",
        ha="right",
        va="top",
        bbox=dict(facecolor="white", edgecolor="gray", boxstyle="round,pad=0.25"),
        transform=plt.gca().transAxes,
    )

    subfolder = "rsi-ema"
    file_name = "batch" + ".png"
    folder_path = os.path.join(
        os.getcwd(), subfolder
    )  # Get the current working directory and append the subfolder name
    os.makedirs(folder_path, exist_ok=True)  # Create the subfolder if it doesn't exist

    file_path = os.path.join(
        folder_path, file_name
    )  # Create the complete file path within the subfolder

    # plt.savefig(file_path)

    # Show the plot
    plt.show()


def load_floats(test_name: str, file_name: str) -> list:
    try:
        # Assuming the subfolder is named 'data'
        subfolder = test_name
        file_path = os.path.join(subfolder, file_name)

        with open(file_path, "r") as f:  # Open file in read mode
            content = (
                f.read().strip()
            )  # Read the content of the file and remove leading/trailing whitespace
            float_list = [
                float(x) for x in content.split(",")
            ]  # Split the content by comma and convert each element to int
            return float_list
    except FileNotFoundError:
        print(f"File '{file_name}' not found.")
        return []


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


def load_ints(test_name: str, file_name: str) -> list:
    try:
        # Assuming the subfolder is named 'data'
        subfolder = test_name
        file_path = os.path.join(subfolder, file_name)

        with open(file_path, "r") as f:  # Open file in read mode
            content = (
                f.read().strip()
            )  # Read the content of the file and remove leading/trailing whitespace
            int_list = [
                int(x) for x in content.split(",")
            ]  # Split the content by comma and convert each element to int
            return int_list
    except FileNotFoundError:
        print(f"File '{file_name}' not found.")
        return []


test = "graphs/tsi-savgol"
avg, min_vals, max_vals = (
    load_floats(test, "avg.txt"),
    load_floats(test, "min.txt"),
    load_floats(test, "max.txt"),
)

# plot_avg_min_max_block_time(avg, min_vals, max_vals, test)

sent_metadata = list(load_tuple(test, "sent_metadata.txt"))

sent, recv, deliv = load_ints(test, "sent_recv_deliv.txt")

# print(sent_metadata)

# plot_batched_message_magnitude(sent_metadata, test, sent, recv, deliv)

# plot_simple_magnitude(sent_metadata)


plot_simple_combined_average()
