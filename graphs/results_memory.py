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
bars_memory = plt.bar(
    indices - bar_width / 2,
    memory_values_sorted,
    bar_width,
    color="skyblue",
    hatch="\\",
    label="RSI",
)
bars_tsi = plt.bar(
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

# Adding bar labels
for bars in [bars_memory, bars_tsi]:
    for bar in bars:
        yval = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2, yval, int(yval), ha="center", va="bottom"
        )

# Adjust layout
plt.tight_layout()

# Show plot
plt.show()
