import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.size"] = 16

# Data
algorithms = ["SAVGOL", "KAMA", "KALMAN", "SMA", "EMA"]
rmse_values = [9.05, 14.17, 19.71, 21.47, 24.53]
tsi_values = [8.09, 9.81, 9.51, 8.42, 9.74]

# Sort algorithms based on rmse values
sorted_rmse_data = sorted(zip(algorithms, rmse_values), key=lambda x: x[1])
algorithms_sorted_rmse = [x[0] for x in sorted_rmse_data]
rmse_values_sorted = [x[1] for x in sorted_rmse_data]

# Sort algorithms based on tsi values
sorted_tsi_data = sorted(zip(algorithms, tsi_values), key=lambda x: x[1])
algorithms_sorted_tsi = [x[0] for x in sorted_tsi_data]
tsi_values_sorted = [x[1] for x in sorted_tsi_data]

# Create indices
indices = np.arange(len(algorithms))
bar_width = 0.35

# Plotting
plt.figure(figsize=(12, 6))

# Plotting rmse and tsi as grouped bars
plt.bar(
    indices - bar_width / 2,
    rmse_values_sorted,
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
plt.xticks(indices, algorithms_sorted_rmse)

plt.title("Root Mean Square Error (RMSE)")
plt.xlabel("Algorithms")
plt.ylabel("Values")
plt.legend()

# Adjust layout
plt.tight_layout()

# Show plot
plt.show()
