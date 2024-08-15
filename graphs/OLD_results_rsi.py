import matplotlib.pyplot as plt

plt.rcParams["font.size"] = 14

##########################
# CPU + EXECUTION TIME + MEMORY   #
##########################

# Data for execution time + CPU time
algorithms_exe_cpu = [
    "SAVGOL",
    "EMA",
    "SMA",
    "KAMA",
    "KAL/ZEL",
]
execution_times = [(1.79, 0.53), (1.83, 0.59), (1.85, 0.60), (2.03, 0.78), (8.76, 7.51)]

# Sort algorithms based on execution time
sorted_exe_cpu_data = sorted(
    zip(algorithms_exe_cpu, execution_times), key=lambda x: sum(x[1])
)
algorithms_sorted_exe_cpu = [x[0] for x in sorted_exe_cpu_data]
execution_times_sorted = [x[1][0] for x in sorted_exe_cpu_data]
cpu_times_sorted = [x[1][1] for x in sorted_exe_cpu_data]

# Data for memory usage
algorithms_mem = ["KAMA", "SMA", "EMA", "KAL/ZEL", "SAVGOL"]
memory_usage = [256, 256, 384, 512, 2176]

# Sort algorithms based on memory usage
sorted_mem_data = sorted(zip(algorithms_mem, memory_usage), key=lambda x: x[1])
algorithms_sorted_mem = [x[0] for x in sorted_mem_data]
memory_usage_sorted = [x[1] for x in sorted_mem_data]

# Plotting
plt.figure(figsize=(12, 6))

# Plotting execution time + CPU time
plt.subplot(1, 2, 1)
plt.bar(
    algorithms_sorted_exe_cpu,
    execution_times_sorted,
    color="skyblue",
    label="Execution Time",
    hatch="\\",
)
plt.bar(
    algorithms_sorted_exe_cpu,
    cpu_times_sorted,
    color="salmon",
    label="CPU Time",
    hatch="/",
)
plt.title("Runtime - RSI")
plt.xlabel("Algorithms")
plt.ylabel("Time (s)")
plt.legend()

# Plotting memory usage
plt.subplot(1, 2, 2)
plt.bar(algorithms_sorted_mem, memory_usage_sorted, color="green")
plt.title("Memory Usage - RSI")
plt.xlabel("Algorithms")
plt.ylabel("Memory Usage (KB)")

# Adjust layout
plt.tight_layout()

# Show plot
plt.show()

##########################
# DROPPED MESSAGES       #
##########################


# Data
algorithms = ["SAVGOL", "KAMA", "KALMAN", "EMA", "SMA"]
dropped_values = [28, 228, 346, 4143, 3126]

# Sort algorithms based on the number of dropped values
sorted_data = sorted(zip(algorithms, dropped_values), key=lambda x: x[1])

algorithms_sorted = [x[0] for x in sorted_data]
dropped_values_sorted = [x[1] for x in sorted_data]

# Plotting
plt.figure(figsize=(10, 6))

# Bar width
bar_width = 0.5

# Positions for the bars
positions = range(len(algorithms_sorted))

# Plotting the bars
plt.bar(positions, dropped_values_sorted, bar_width, color="salmon")

# Adding labels and title
plt.xlabel("Algorithms")
plt.ylabel("Number of Dropped Messages")
plt.title("Messages Failures - RSI")
plt.xticks(positions, algorithms_sorted)

# Show plot
plt.tight_layout()
plt.show()

##########################
# MAD and RMSE           #
##########################

# Data
algorithms = ["RSI-SAVGOL", "RSI-KAMA", "RSI-KALMAN", "RSI-SMA", "RSI-EMA"]
mad_values = [6.21, 9.63, 15.34, 14.48, 16.75]
rmse_values = [9.05, 14.17, 19.71, 21.47, 24.53]

# Sort algorithms based on MAD values
sorted_mad_data = sorted(zip(algorithms, mad_values), key=lambda x: x[1])
algorithms_sorted_mad = [x[0] for x in sorted_mad_data]
mad_values_sorted = [x[1] for x in sorted_mad_data]

# Sort algorithms based on RMSE values
sorted_rmse_data = sorted(zip(algorithms, rmse_values), key=lambda x: x[1])
algorithms_sorted_rmse = [x[0] for x in sorted_rmse_data]
rmse_values_sorted = [x[1] for x in sorted_rmse_data]

# Plotting
plt.figure(figsize=(12, 6))

# Plotting MAD
plt.subplot(1, 2, 1)
plt.bar(algorithms_sorted_mad, mad_values_sorted, color="skyblue")
plt.title("Mean Absolute Deviation (MAD) - RSI")
plt.xlabel("Algorithms")
plt.ylabel("MAD")

# Plotting RMSE
plt.subplot(1, 2, 2)
plt.bar(algorithms_sorted_rmse, rmse_values_sorted, color="salmon")
plt.title("Root Mean Squared Error (RMSE) - RSI")
plt.xlabel("Algorithms")
plt.ylabel("RMSE")

# Adjust layout
plt.tight_layout()

# Show plot
plt.show()


#############
# SCORING #
##############

# TIMING
# SAVGOL - 5
# EMA - 4
# SMA - 3
# KAMA - 2
# KALMAN-ZLEMA - 1

# MEMORY
# KAMA - 5
# SMA - 4
# EMA - 3
# KALMAN-ZLEMA - 2
# SAVGOL - 1

# MISSED CONTAGION
# SAVGOL - 5
# KAMA - 4
# KALMAN-ZLEMA 3
# SMA 2
# EMA - 1

# MAD
# SAVGOL - 5
# KAMA - 4
# SMA - 3
# KALMAN-ZLEMA - 2
# EMA - 1

# RMSE:
# SAVGOL - 5
# KAMA - 4
# KALMAN-ZLEMA - 3
# SMA - 2
# EMA - 1

##############
# FINAL RESULTS#
#################

# SAVGOL - 21
# KAMA - 19
# SMA - 14
# KALMAN-ZLEMA - 11
# EMA - 10
