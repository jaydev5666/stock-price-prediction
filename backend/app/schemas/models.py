from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class TickerInfo(BaseModel):
    symbol: str
    name: str
    exchange: Optional[str] = "Unknown"

class PricePoint(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int

class StockHistoryResponse(BaseModel):
    ticker: str
    name: Optional[str] = ""
    currency: Optional[str] = "USD"
    range: str
    points: List[PricePoint]

class PredictRequest(BaseModel):
    ticker: str
    horizon_days: int = Field(default=7, ge=1, le=90)
    force_retrain: bool = False

class PredictionPoint(BaseModel):
    date: str
    predicted_close: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None

class ModelMetrics(BaseModel):
    rmse: float
    mae: float
    baseline_rmse: float
    baseline_mae: float
    rmse_improvement_pct: Optional[float] = None
    directional_accuracy: Optional[float] = None
    validation_samples: Optional[int] = None
    lookback_window: Optional[int] = 60

class PredictionResponse(BaseModel):
    status: str  # "ready" or "training"
    job_id: Optional[str] = None
    ticker: str
    horizon_days: int
    last_historical_date: Optional[str] = None
    last_historical_close: Optional[float] = None
    predictions: Optional[List[PredictionPoint]] = None
    metrics: Optional[ModelMetrics] = None
    generated_at: Optional[str] = None
    is_cached: Optional[bool] = False
    message: Optional[str] = None

class JobStatusResponse(BaseModel):
    job_id: str
    ticker: str
    status: str  # "queued", "fetching_data", "preprocessing", "training", "evaluating", "done", "failed"
    progress: int  # 0 to 100
    stage: Optional[str] = ""
    error: Optional[str] = None
    created_at: str
    updated_at: str
    prediction_result: Optional[PredictionResponse] = None
