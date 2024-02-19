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
    kf.R = np.array([[1]])

    # Define process noise covariance (Q)
    kf.Q = np.array([[0.01]])

    # Apply Kalman filter to each measurement
    for price in data:
        kf.predict()
        kf.update(price)
        smoothed_data.append(kf.x[0])  # Store the filtered estimate

    return smoothed_data
