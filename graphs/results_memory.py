import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.size"] = 16

# Data
algorithms = ["KAMA", "SMA", "EMA", "KAL/ZEL", "SAVGOL"]
memory_values = [256, 256, 384, 512, 2176]
tsi_values = [768, 768, 768, 768, 2688]

# Sort algorithms based on memory values
sorted_memory_data = sorted(zip(algorithms, memory_values), key=lambda x: x[1])
algorithms_sorted_memory = [x[0] for x in sorted_memory_data]
memory_values_sorted = [x[1] for x in sorted_memory_data]

# Sort algorithms based on tsi values
sorted_tsi_data = sorted(zip(algorithms, tsi_values), key=lambda x: x[1])
algorithms_sorted_tsi = [x[0] for x in sorted_tsi_data]
tsi_values_sorted = [x[1] for x in sorted_tsi_data]

# Create indices
indices = np.arange(len(algorithms))
bar_width = 0.35

# Plotting
plt.figure(figsize=(12, 6))

# Plotting memory and tsi as grouped bars
plt.bar(
    indices - bar_width / 2,
    memory_values_sorted,
    bar_width,
    color="skyblue",
    hatch="\\",
    label="RSI",
)
plt.bar(
    indices + bar_width / 2,
    tsi_values_sorted,
    bar_width,
    color="salmon",
    hatch="/",
    label="TSI",
)

# Adding labels to the x-axis and setting algorithm names as labels
plt.xticks(indices, algorithms_sorted_memory)

plt.title("Memory Usage")
plt.xlabel("Algorithms")
plt.ylabel("Memory Usage (KB)")
plt.legend()

# Adjust layout
plt.tight_layout()

# Show plot
plt.show()
