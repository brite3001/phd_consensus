import os
import matplotlib.pyplot as plt


def load_list(sub_folder, file_name: str) -> list:
    try:
        # Assuming the subfolder is named 'data'
        file_path = os.path.join(sub_folder, file_name)

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


avg_latency = load_list("latency", "avg.txt")

tps = 0.5

# X-axis values, representing time in seconds
time_intervals = [i * 5 for i in range(len(avg_latency))]

# Plotting the avg_latency
plt.plot(time_intervals, avg_latency, label="Average Latency", marker="o")

# Plotting the TPS line (assuming TPS is constant over time)
plt.plot(time_intervals, [tps] * len(time_intervals), label="TPS", linestyle="--")

# Adding title and labels
plt.title("Average Latency and TPS over Time")
plt.xlabel("Time (seconds)")
plt.ylabel("Value")

# Adding legend
plt.legend()

# Display the graph
plt.show()
