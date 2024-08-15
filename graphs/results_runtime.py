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

# Plotting runtine TSI
execution_times = [(2.96, 1.71), (3.15, 1.9), (3.08, 1.82), (3.07, 2.02), (9.88, 8.63)]

# Sort algorithms based on execution time
sorted_exe_cpu_data = sorted(
    zip(algorithms_exe_cpu, execution_times), key=lambda x: sum(x[1])
)
algorithms_sorted_exe_cpu = [x[0] for x in sorted_exe_cpu_data]
execution_times_sorted = [x[1][0] for x in sorted_exe_cpu_data]
cpu_times_sorted = [x[1][1] for x in sorted_exe_cpu_data]

plt.subplot(1, 2, 2)
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
plt.title("Runtime - TSI")
plt.xlabel("Algorithms")
plt.ylabel("Time (s)")
plt.legend()

# Adjust layout
plt.tight_layout()

# Show plot
plt.show()
