import numpy as np
import matplotlib.pyplot as plt
import os


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


def plot_avg_min_max_block_time(avg_list, min_list, max_list, TEST_NAME):
    # Create x-axis values
    x = np.arange(len(avg_list))

    # Plot the average line
    plt.plot(x, avg_list, label="Average", linestyle=":", color="blue")

    # Plot the shaded region between the minimum and maximum curves
    plt.fill_between(
        x, min_list, max_list, color="gray", alpha=0.3, label="Range (Min-Max)"
    )

    # Plot the minimum and maximum curves
    plt.plot(x, min_list, label="Minimum", linestyle="--", color="green")
    plt.plot(x, max_list, label="Maximum", linestyle="-.", color="red")
    plt.axhline(y=10, color="orange", linestyle="-", label="Target Latency")

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

    plt.savefig(file_path)

    # Show the plot
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
        0.95,
        0.95,
        text_content,
        fontsize=12,
        color="black",
        ha="right",
        va="top",
        bbox=dict(facecolor="white", edgecolor="gray", boxstyle="round,pad=0.25"),
        transform=plt.gca().transAxes,
    )

    subfolder = TEST_NAME
    file_name = "batch" + ".png"
    folder_path = os.path.join(
        os.getcwd(), subfolder
    )  # Get the current working directory and append the subfolder name
    os.makedirs(folder_path, exist_ok=True)  # Create the subfolder if it doesn't exist

    file_path = os.path.join(
        folder_path, file_name
    )  # Create the complete file path within the subfolder

    plt.savefig(file_path)

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


test = "graphs/tsi-ema"
avg, min, max = (
    load_floats(test, "avg.txt"),
    load_floats(test, "min.txt"),
    load_floats(test, "max.txt"),
)

plot_avg_min_max_block_time(avg, min, max, test)

sent_metadata = list(load_tuple(test, "sent_metadata.txt"))

sent, recv, deliv = load_ints(test, "sent_recv_deliv.txt")

# print(sent_metadata)

plot_batched_message_magnitude(sent_metadata, test, sent, recv, deliv)
