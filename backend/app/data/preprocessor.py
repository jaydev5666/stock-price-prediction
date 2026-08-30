import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, Optional
from sklearn.preprocessing import MinMaxScaler

class DataPreprocessor:
    """
    Handles scaling, sliding-window sequence creation, and chronological train/validation splitting.
    Strictly fits the scaler only on the training set to prevent data leakage.
    """

    def __init__(self, lookback: int = 60, val_split: float = 0.2):
        self.lookback = lookback
        self.val_split = val_split
        self.scaler = MinMaxScaler(feature_range=(0, 1))

    def prepare_training_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Prepares training and validation datasets from a historical DataFrame.
        Splits chronologically (e.g. 80% train, 20% val) to strictly respect temporal order.
        """
        if len(df) <= self.lookback + 10:
            raise ValueError(f"Insufficient data points ({len(df)}) for lookback window of {self.lookback}.")

        # We focus on the 'close' price column
        close_prices = df["close"].values.reshape(-1, 1)

        # Chronological split index
        split_idx = int(len(close_prices) * (1 - self.val_split))
        # Ensure we have at least lookback samples in train and val
        if split_idx <= self.lookback or (len(close_prices) - split_idx) <= self.lookback:
            split_idx = max(self.lookback + 10, len(close_prices) - 30)

        train_raw = close_prices[:split_idx]
        val_raw = close_prices[split_idx - self.lookback:]  # overlap lookback window so val sequences start at split_idx

        # Fit scaler ONLY on train_raw
        self.scaler.fit(train_raw)

        train_scaled = self.scaler.transform(train_raw)
        val_scaled = self.scaler.transform(val_raw)

        # Create sliding window sequences
        X_train, y_train = self._create_sequences(train_scaled, self.lookback)
        X_val, y_val = self._create_sequences(val_scaled, self.lookback)

        # Unscaled ground truth validation target values for calculating true metrics
        y_val_unscaled = self.scaler.inverse_transform(y_val.reshape(-1, 1)).flatten()

        # Naive baseline on validation set: predict y_hat[t] = close[t-1]
        # In our sequence X_val[:, -1, 0] is the exact last known day before target y_val
        last_known_scaled = X_val[:, -1, 0].reshape(-1, 1)
        naive_baseline_unscaled = self.scaler.inverse_transform(last_known_scaled).flatten()

        return {
            "X_train": X_train,
            "y_train": y_train,
            "X_val": X_val,
            "y_val": y_val,
            "y_val_unscaled": y_val_unscaled,
            "naive_baseline_unscaled": naive_baseline_unscaled,
            "scaler": self.scaler,
            "train_size": len(X_train),
            "val_size": len(X_val),
            "lookback": self.lookback
        }

    def prepare_inference_input(self, df: pd.DataFrame, scaler: MinMaxScaler) -> np.ndarray:
        """
        Extracts the most recent `lookback` closing prices and scales them with the saved scaler.
        Returns tensor shaped (1, lookback, 1).
        """
        if len(df) < self.lookback:
            raise ValueError(f"Need at least {self.lookback} price points for inference, got {len(df)}.")

        recent_closes = df["close"].values[-self.lookback:].reshape(-1, 1)
        scaled_input = scaler.transform(recent_closes)
        return scaled_input.reshape(1, self.lookback, 1)

    @staticmethod
    def _create_sequences(data: np.ndarray, lookback: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Converts 1D/2D series into (samples, lookback, 1) and (samples,)
        """
        X, y = [], []
        for i in range(lookback, len(data)):
            X.append(data[i - lookback:i, :])
            y.append(data[i, 0])
        return np.array(X), np.array(y)
