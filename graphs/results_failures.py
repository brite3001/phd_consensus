import matplotlib.pyplot as plt

plt.rcParams["font.size"] = 14

# Data
algorithms = ["SAVGOL", "KAMA", "KAL/ZEL", "EMA", "SMA"]
dropped_values_rsi = [28, 228, 346, 4143, 3126]
dropped_values_tsi = [18, 21, 7, 14, 196]

# Sort algorithms based on the number of dropped values
sorted_rsi = sorted(zip(algorithms, dropped_values_rsi), key=lambda x: x[1])
sorted_tsi = sorted(zip(algorithms, dropped_values_tsi), key=lambda x: x[1])

algorithms_sorted = [x[0] for x in sorted_rsi]
dropped_values_sorted_rsi = [x[1] for x in sorted_rsi]
dropped_values_sorted_tsi = [x[1] for x in sorted_tsi]

# Bar width
bar_width = 0.6  # Increased bar width to 0.4 from 0.5

# Positions for the bars
positions = range(len(algorithms_sorted))

# Create a figure and axis
fig, ax = plt.subplots()

# Plotting the first set of bars
ax.bar(
    [
        x - bar_width / 4 for x in positions
    ],  # Adjusted position to make bars side by side
    dropped_values_sorted_rsi,
    bar_width / 2,
    color="skyblue",
    label="RSI",
    hatch="\\",
)

# Plotting the second set of bars
ax.bar(
    [
        x + bar_width / 4 for x in positions
    ],  # Adjusted position to make bars side by side
    dropped_values_sorted_tsi,
    bar_width / 2,
    color="salmon",
    label="TSI",
    hatch="/",
)

# Adding labels and title
ax.set_xlabel("Algorithms")
ax.set_ylabel("Number of Failed Gossips")
ax.set_title("Gossip Failures")
ax.set_xticks(positions)
ax.set_xticklabels(algorithms_sorted)
ax.legend()

# Show plot
plt.show()
