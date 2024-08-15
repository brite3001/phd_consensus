import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.size"] = 16

# Data
algorithms = ["SAVGOL", "KAMA", "KAL/ZEL", "SMA", "EMA"]
mad_values = [6.21, 9.63, 15.34, 14.48, 16.75]
tsi_values = [6.09, 6.95, 7.17, 5.71, 6.83]

# Sort algorithms based on MAD values
sorted_mad_data = sorted(zip(algorithms, mad_values), key=lambda x: x[1])
algorithms_sorted_mad = [x[0] for x in sorted_mad_data]
mad_values_sorted = [x[1] for x in sorted_mad_data]

# Sort algorithms based on tsi values
sorted_tsi_data = sorted(zip(algorithms, tsi_values), key=lambda x: x[1])
algorithms_sorted_tsi = [x[0] for x in sorted_tsi_data]
tsi_values_sorted = [x[1] for x in sorted_tsi_data]

# Create indices
indices = np.arange(len(algorithms))
bar_width = 0.35

# Plotting
plt.figure(figsize=(12, 6))

# Plotting MAD and tsi as grouped bars
plt.bar(
    indices - bar_width / 2,
    mad_values_sorted,
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
plt.xticks(indices, algorithms_sorted_mad)

plt.title("Mean Absolute Deviation (MAD)")
plt.xlabel("Algorithms")
plt.ylabel("Values")
plt.legend()

# Adjust layout
plt.tight_layout()

# Show plot
plt.show()
