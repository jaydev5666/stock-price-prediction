import datetime
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Callable
from sklearn.metrics import mean_squared_error, mean_absolute_error
from tensorflow import keras
from keras.callbacks import EarlyStopping, Callback

from backend.app.config import DEFAULT_LOOKBACK, DEFAULT_EPOCHS, DEFAULT_BATCH_SIZE, DEFAULT_VALIDATION_SPLIT
from backend.app.data.fetcher import YFinanceFetcher
from backend.app.data.preprocessor import DataPreprocessor
from backend.app.ml.model import build_lstm_model
from backend.app.ml.registry import ModelRegistry

class ProgressCallback(Callback):
    """Keras callback to report training epoch progress to async job tracker."""
    def __init__(self, total_epochs: int, on_progress: Optional[Callable[[int, str], None]] = None):
        super().__init__()
        self.total_epochs = total_epochs
        self.on_progress = on_progress

    def on_epoch_end(self, epoch, logs=None):
        if self.on_progress:
            # Training phase spans from 30% to 80% of total job progress
            pct = 30 + int(((epoch + 1) / self.total_epochs) * 50)
            loss_val = logs.get("loss", 0.0) if logs else 0.0
            val_loss = logs.get("val_loss", 0.0) if logs else 0.0
            msg = f"Epoch {epoch+1}/{self.total_epochs} - loss: {loss_val:.4f}, val_loss: {val_loss:.4f}"
            self.on_progress(pct, msg)


class ModelTrainer:
    """Trains and validates LSTM models for stock tickers."""

    @staticmethod
    def train_ticker(
        ticker: str,
        df: Optional[pd.DataFrame] = None,
        lookback: int = DEFAULT_LOOKBACK,
        epochs: int = DEFAULT_EPOCHS,
        batch_size: int = DEFAULT_BATCH_SIZE,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        ticker = ticker.upper()

        # Step 1: Fetch data if not supplied
        if df is None:
            if progress_callback:
                progress_callback(10, f"Fetching historical data for {ticker}...")
            fetcher = YFinanceFetcher()
            # Fetch 5 years of daily data for rich training history
            df = fetcher.get_history(ticker, range_str="5y")

        if len(df) < lookback + 30:
            raise ValueError(f"Ticker {ticker} has only {len(df)} historical points, minimum {lookback + 30} needed.")

        # Step 2: Preprocess
        if progress_callback:
            progress_callback(25, "Preprocessing data and creating sequences...")
        preprocessor = DataPreprocessor(lookback=lookback, val_split=DEFAULT_VALIDATION_SPLIT)
        prep_data = preprocessor.prepare_training_data(df)

        X_train = prep_data["X_train"]
        y_train = prep_data["y_train"]
        X_val = prep_data["X_val"]
        y_val = prep_data["y_val"]
        y_val_unscaled = prep_data["y_val_unscaled"]
        naive_baseline_unscaled = prep_data["naive_baseline_unscaled"]
        scaler = prep_data["scaler"]

        # Step 3: Build Model
        if progress_callback:
            progress_callback(30, "Initializing LSTM architecture...")
        model = build_lstm_model(lookback=lookback)

        callbacks = [
            EarlyStopping(monitor="val_loss", patience=8, restore_best_weights=True),
            ProgressCallback(total_epochs=epochs, on_progress=progress_callback)
        ]

        # Step 4: Fit Model
        model.fit(
            X_train,
            y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=0
        )

        # Step 5: Evaluate on validation set
        if progress_callback:
            progress_callback(85, "Calculating validation metrics against naive persistence baseline...")
        
        # Predict on validation set
        val_pred_scaled = model.predict(X_val, verbose=0)
        val_pred_unscaled = scaler.inverse_transform(val_pred_scaled).flatten()

        # Calculate LSTM metrics
        lstm_rmse = float(np.sqrt(mean_squared_error(y_val_unscaled, val_pred_unscaled)))
        lstm_mae = float(mean_absolute_error(y_val_unscaled, val_pred_unscaled))

        # Calculate Naive Baseline metrics (predicting t = t-1)
        baseline_rmse = float(np.sqrt(mean_squared_error(y_val_unscaled, naive_baseline_unscaled)))
        baseline_mae = float(mean_absolute_error(y_val_unscaled, naive_baseline_unscaled))

        # Relative improvement: positive means LSTM has lower RMSE than naive baseline
        rmse_improvement_pct = round(((baseline_rmse - lstm_rmse) / baseline_rmse) * 100, 2)

        # Directional accuracy (sign of day-over-day change)
        val_actual_diff = np.diff(y_val_unscaled)
        val_pred_diff = val_pred_unscaled[1:] - y_val_unscaled[:-1]
        matching_directions = np.sum(np.sign(val_actual_diff) == np.sign(val_pred_diff))
        directional_acc = float(matching_directions / len(val_actual_diff) * 100) if len(val_actual_diff) > 0 else 50.0

        # Residual std for forecast confidence intervals
        residuals = y_val_unscaled - val_pred_unscaled
        residual_std = float(np.std(residuals))

        metadata = {
            "ticker": ticker,
            "trained_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "lookback_window": lookback,
            "train_samples": prep_data["train_size"],
            "val_samples": prep_data["val_size"],
            "last_date": str(df["date"].iloc[-1]),
            "last_close": float(df["close"].iloc[-1]),
            "residual_std": residual_std,
            "metrics": {
                "rmse": round(lstm_rmse, 4),
                "mae": round(lstm_mae, 4),
                "baseline_rmse": round(baseline_rmse, 4),
                "baseline_mae": round(baseline_mae, 4),
                "rmse_improvement_pct": rmse_improvement_pct,
                "directional_accuracy": round(directional_acc, 2),
                "validation_samples": prep_data["val_size"],
                "lookback_window": lookback
            }
        }

        # Step 6: Save to Registry
        if progress_callback:
            progress_callback(95, "Persisting model artifact and scaler...")
        ModelRegistry.save(ticker, model, scaler, metadata)

        if progress_callback:
            progress_callback(100, "Model training completed successfully.")

        return {
            "ticker": ticker,
            "model": model,
            "scaler": scaler,
            "metadata": metadata
        }
