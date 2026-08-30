import datetime
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

from backend.app.ml.registry import ModelRegistry
from backend.app.data.fetcher import YFinanceFetcher

def get_next_trading_days(start_date_str: str, n_days: int) -> List[str]:
    """Generates the next n trading days (Monday-Friday), skipping weekends."""
    cur_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
    trading_days = []
    while len(trading_days) < n_days:
        cur_date += datetime.timedelta(days=1)
        # 5 is Saturday, 6 is Sunday
        if cur_date.weekday() < 5:
            trading_days.append(cur_date.strftime("%Y-%m-%d"))
    return trading_days

class ModelPredictor:
    """Performs multi-step autoregressive forecasting using trained LSTM models."""

    @staticmethod
    def predict(
        ticker: str,
        horizon_days: int = 7,
        df: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        ticker = ticker.upper()

        # Step 1: Load model from registry
        loaded = ModelRegistry.load(ticker)
        if not loaded:
            raise ValueError(f"No trained model found for ticker '{ticker}'.")

        model, scaler, metadata = loaded
        lookback = metadata.get("lookback_window", 60)
        residual_std = metadata.get("residual_std", 2.0)

        # Step 2: Fetch latest price data if not provided
        if df is None:
            fetcher = YFinanceFetcher()
            df = fetcher.get_history(ticker, range_str="1y")

        if len(df) < lookback:
            raise ValueError(f"Not enough recent data ({len(df)}) for lookback of {lookback}.")

        last_date = str(df["date"].iloc[-1])
        last_close = float(df["close"].iloc[-1])

        # Step 3: Autoregressive multi-step rollout
        # Extract last `lookback` closing values and scale
        recent_closes = df["close"].values[-lookback:].reshape(-1, 1)
        current_seq = scaler.transform(recent_closes)  # shape (lookback, 1)

        future_dates = get_next_trading_days(last_date, horizon_days)
        prediction_points = []

        for step_idx, f_date in enumerate(future_dates, start=1):
            # Shape for Keras model: (1, lookback, 1)
            inp = current_seq[-lookback:].reshape(1, lookback, 1)
            pred_scaled = model.predict(inp, verbose=0)  # shape (1, 1)
            pred_val_scaled = float(pred_scaled[0, 0])

            # Inverse scale to actual dollar price
            pred_price = float(scaler.inverse_transform([[pred_val_scaled]])[0, 0])

            # Multi-step uncertainty band widens with sqrt(step)
            margin = 1.96 * residual_std * np.sqrt(step_idx)
            lower_b = max(0.01, round(pred_price - margin, 2))
            upper_b = round(pred_price + margin, 2)

            prediction_points.append({
                "date": f_date,
                "predicted_close": round(pred_price, 2),
                "lower_bound": lower_b,
                "upper_bound": upper_b
            })

            # Append prediction to current_seq to roll forward
            current_seq = np.vstack([current_seq, [[pred_val_scaled]]])

        return {
            "status": "ready",
            "ticker": ticker,
            "horizon_days": horizon_days,
            "last_historical_date": last_date,
            "last_historical_close": round(last_close, 2),
            "predictions": prediction_points,
            "metrics": metadata.get("metrics", {}),
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
