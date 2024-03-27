import time
import psutil
import resource
import os
from talipp.indicators import ZLEMA, RSI, SMA, EMA, KAMA, TEMA, TSI
from scipy.signal import savgol_filter
from filterpy.kalman import KalmanFilter
import numpy as np


def kalman_filter(data: list):
    data = np.array(data)
    smoothed_data = []

    # Create a Kalman filter
    kf = KalmanFilter(dim_x=1, dim_z=1)

    # Define initial state and covariance
    kf.x = np.array([0])  # Initial state estimate
    kf.P *= 1  # Initial state covariance

    # Define state transition matrix (F) and control matrix (B) if applicable
    kf.F = np.array([[1]])
    kf.B = np.array([[0]])

    # Define measurement matrix (H)
    kf.H = np.array([[1]])

    # Define measurement noise covariance (R)
    kf.R = np.array([[0.5]])

    # Define process noise covariance (Q)
    kf.Q = np.array([[0.1]])

    # Apply Kalman filter to each measurement
    for grtt in data:
        kf.predict()
        kf.update(grtt)
        smoothed_data.append(kf.x[0])  # Store the filtered estimate

    return smoothed_data


# Function to calculate moving average
def moving_average(data, window_size):
    averages = []
    for i in range(len(data) - window_size + 1):
        window = data[i : i + window_size]
        averages.append(sum(window) / window_size)
    return averages


# Function to measure CPU time
def measure_cpu_time():
    return resource.getrusage(resource.RUSAGE_SELF).ru_utime


def measure_memory_usage():
    process = psutil.Process()
    return process.memory_info().rss // 1024  # Convert to KB


def load_list(file_name: str) -> list:
    try:
        # Assuming the subfolder is named 'data'
        subfolder = "moving_average_benchmark"
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


# Generate example data
data = load_list("rsi-kalman-zlema_avg.txt")

# Set window size for moving average
window_size = 3

# Measure start CPU time and memory usage
start_cpu_time = measure_cpu_time()
start_memory_usage = measure_memory_usage()

for _ in range(20):
    # Smooth data
    smoothed_data = kalman_filter(ZLEMA(14, data))
    # smoothed_data = savgol_filter(data, 14, 1)
    # smoothed_data = [x for x in SMA(14, data) if x]
    # smoothed_data = [x for x in EMA(14, data) if x]
    # smoothed_data = [x for x in KAMA(14, 2, 30, data) if x]

    # trend detection
    rsi = int(RSI(14, smoothed_data)[-1])
    # rsi = TSI(3, 6, smoothed_data)[-1]

# Measure end CPU time and memory usage
end_cpu_time = measure_cpu_time()
end_memory_usage = measure_memory_usage()

# Calculate execution time
execution_time = time.process_time()

# Print results
print("Execution time:", execution_time)
print("CPU time:", end_cpu_time - start_cpu_time)
print("Memory usage:", end_memory_usage - start_memory_usage, "KB")
