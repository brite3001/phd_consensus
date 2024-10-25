import matplotlib.pyplot as plt

plt.rcParams["font.size"] = 16

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

# Plotting
plt.figure(figsize=(12, 6))

# Plotting execution time + CPU time
ax1 = plt.subplot(1, 2, 1)

bars_exec_1 = ax1.bar(
    algorithms_sorted_exe_cpu,
    execution_times_sorted,
    color="skyblue",
    label="Execution Time",
    hatch="\\",
)
bars_cpu_1 = ax1.bar(
    algorithms_sorted_exe_cpu,
    cpu_times_sorted,
    bottom=execution_times_sorted,
    color="salmon",
    label="CPU Time",
    hatch="/",
)

# Add labels to the top of each bar
ax1.bar_label(bars_exec_1, label_type="center")
ax1.bar_label(bars_cpu_1, label_type="edge")

plt.title("Runtime - RSI")
plt.xlabel("Algorithms")
plt.ylabel("Time (s)")
plt.legend()

# Plotting runtine TSI
execution_times = [(2.96, 1.71), (3.15, 1.9), (3.08, 1.82), (3.07, 2.02), (9.88, 8.63)]

# Sort algorithms based on execution time
sorted_exe_cpu_data = sorted(
    zip(algorithms_exe_cpu, execution_times), key=lambda x: sum(x[1])
)
algorithms_sorted_exe_cpu = [x[0] for x in sorted_exe_cpu_data]
execution_times_sorted = [x[1][0] for x in sorted_exe_cpu_data]
cpu_times_sorted = [x[1][1] for x in sorted_exe_cpu_data]

ax2 = plt.subplot(1, 2, 2)

# Create the first set of bars
bars_exec_2 = ax2.bar(
    algorithms_sorted_exe_cpu,
    execution_times_sorted,
    color="skyblue",
    label="Execution Time",
    hatch="\\",
)
bars_cpu_2 = ax2.bar(
    algorithms_sorted_exe_cpu,
    cpu_times_sorted,
    bottom=execution_times_sorted,
    color="salmon",
    label="CPU Time",
    hatch="/",
)

# Add labels to the top of each bar
ax2.bar_label(bars_exec_2, label_type="center")
ax2.bar_label(bars_cpu_2, label_type="edge")

plt.title("Runtime - TSI")
plt.xlabel("Algorithms")
plt.ylabel("Time (s)")
plt.legend()

# Adjust layout
plt.tight_layout()

# Show plot
plt.show()
