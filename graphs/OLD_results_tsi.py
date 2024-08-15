import matplotlib.pyplot as plt

##########################
# CPU + EXECUTION TIME + MEMORY   #
##########################

# Data for execution time + CPU time
algorithms_exe_cpu = [
    "TSI-SAVGOL",
    "TSI-EMA",
    "TSI-SMA",
    "TSI-KAMA",
    "TSI-KALMAN",
]
execution_times = [(2.96, 1.71), (3.15, 1.9), (3.08, 1.82), (3.07, 2.02), (9.88, 8.63)]

# Sort algorithms based on execution time
sorted_exe_cpu_data = sorted(
    zip(algorithms_exe_cpu, execution_times), key=lambda x: sum(x[1])
)
algorithms_sorted_exe_cpu = [x[0] for x in sorted_exe_cpu_data]
execution_times_sorted = [x[1][0] for x in sorted_exe_cpu_data]
cpu_times_sorted = [x[1][1] for x in sorted_exe_cpu_data]

# Data for memory usage
algorithms_mem = ["TSI-KAMA", "TSI-SMA", "TSI-EMA", "TSI-KALMAN", "TSI-SAVGOL"]
memory_usage = [768, 768, 768, 768, 2688]

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
)
plt.bar(algorithms_sorted_exe_cpu, cpu_times_sorted, color="salmon", label="CPU Time")
plt.title("Execution Time and CPU Time")
plt.xlabel("Algorithms")
plt.ylabel("Time (s)")
plt.legend()

# Plotting memory usage
plt.subplot(1, 2, 2)
plt.bar(algorithms_sorted_mem, memory_usage_sorted, color="green")
plt.title("Memory Usage")
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
algorithms = ["TSI-SAVGOL", "TSI-KAMA", "TSI-KALMAN", "TSI-EMA", "TSI-SMA"]
dropped_values = [18, 21, 7, 14, 196]

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
plt.title("Messages That didnt Reach Contagion Threshold")
plt.xticks(positions, algorithms_sorted)

# Show plot
plt.tight_layout()
plt.show()

##########################
# MAD and RMSE           #
##########################

# Data
algorithms = ["TSI-SAVGOL", "TSI-KAMA", "TSI-KALMAN", "TSI-SMA", "TSI-EMA"]
mad_values = [6.09, 6.95, 7.17, 5.71, 6.83]
rmse_values = [8.09, 9.81, 9.51, 8.42, 9.74]

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
plt.title("Mean Absolute Deviation (MAD)")
plt.xlabel("Algorithms")
plt.ylabel("MAD")

# Plotting RMSE
plt.subplot(1, 2, 2)
plt.bar(algorithms_sorted_rmse, rmse_values_sorted, color="salmon")
plt.title("Root Mean Squared Error (RMSE)")
plt.xlabel("Algorithms")
plt.ylabel("RMSE")

# Adjust layout
plt.tight_layout()

# Show plot
plt.show()


################
# RESULTS #
#################

# TIME:
# SAVGOL - 5
# SMA - 4
# EMA - 3
# KAMA - 2
# KALMAN-ZLEMA - 1

# MEMORY:
# KAMA/SMA/EMA/KALMAN-ZLEMA - 5
# SAVGOL - 4

# CONTAGION MISS:
# KALMAN-ZLEMA - 5
# EMA - 4
# SAVGOL - 3
# KAMA - 2
# SMA - 1

# MAD:
# SMA - 5
# SAVGOL - 4
# EMA - 3
# KAMA - 2
# KALMAN-ZLEMA - 1

# RMSE:
# SAVGOL - 5
# SMA - 4
# KALMAN-ZLEMA - 3
# EMA - 2
# KAMA - 1

################
# FINAL SCORES #
##################

# SAVGOL - 21
# SMA - 19
# EMA - 17
# KALMAN-ZLEMA - 15
# KAMA - 12
