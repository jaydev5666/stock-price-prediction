import json
import joblib
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import tensorflow as tf
from tensorflow import keras
from sklearn.preprocessing import MinMaxScaler
from backend.app.config import MODELS_DIR

class ModelRegistry:
    """Manages versioned storage and retrieval of trained LSTM models and their scalers."""

    @classmethod
    def get_model_path(cls, ticker: str) -> Path:
        return MODELS_DIR / f"{ticker.upper()}_lstm.keras"

    @classmethod
    def get_scaler_path(cls, ticker: str) -> Path:
        return MODELS_DIR / f"{ticker.upper()}_scaler.joblib"

    @classmethod
    def get_metadata_path(cls, ticker: str) -> Path:
        return MODELS_DIR / f"{ticker.upper()}_meta.json"

    @classmethod
    def exists(cls, ticker: str) -> bool:
        return (
            cls.get_model_path(ticker).exists() and
            cls.get_scaler_path(ticker).exists() and
            cls.get_metadata_path(ticker).exists()
        )

    @classmethod
    def save(
        cls,
        ticker: str,
        model: keras.Model,
        scaler: MinMaxScaler,
        metadata: Dict[str, Any]
    ) -> None:
        ticker = ticker.upper()
        # Save Keras model
        model_path = cls.get_model_path(ticker)
        model.save(str(model_path))

        # Save Scaler
        scaler_path = cls.get_scaler_path(ticker)
        joblib.dump(scaler, str(scaler_path))

        # Save Metadata
        meta_path = cls.get_metadata_path(ticker)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    @classmethod
    def load(cls, ticker: str) -> Optional[Tuple[keras.Model, MinMaxScaler, Dict[str, Any]]]:
        ticker = ticker.upper()
        if not cls.exists(ticker):
            return None

        try:
            model_path = cls.get_model_path(ticker)
            model = keras.models.load_model(str(model_path))

            scaler_path = cls.get_scaler_path(ticker)
            scaler = joblib.load(str(scaler_path))

            meta_path = cls.get_metadata_path(ticker)
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            return model, scaler, metadata
        except Exception as e:
            print(f"Error loading model for {ticker}: {e}")
            return None
