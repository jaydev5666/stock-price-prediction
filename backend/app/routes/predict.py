from fastapi import APIRouter, HTTPException, Query, Response, status
from backend.app.schemas.models import PredictRequest, PredictionResponse
from backend.app.ml.registry import ModelRegistry
from backend.app.ml.predictor import ModelPredictor
from backend.app.jobs.manager import JobManager
from backend.app.data.fetcher import YFinanceFetcher, TickerNotFoundError
from backend.app.data.cache import CacheManager

router = APIRouter()
fetcher = YFinanceFetcher()

@router.post("/predict", response_model=PredictionResponse)
def predict_stock(request: PredictRequest, response: Response):
    """
    Generates or retrieves multi-step LSTM price forecast.
    If model is already trained and prediction is cached, returns 200 instantly.
    If model is trained but prediction not cached, runs fast inference (200 OK).
    If model is not yet trained for ticker, triggers background training job (202 Accepted).
    """
    ticker = request.ticker.strip().upper()
    horizon = request.horizon_days

    # Validate ticker existence
    try:
        df = fetcher.get_history(ticker, range_str="1y")
    except TickerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch market data for {ticker}: {str(e)}")

    last_date = str(df["date"].iloc[-1])

    # Check if force_retrain is requested
    if not request.force_retrain:
        # Check prediction cache
        cached_pred = CacheManager.get_cached_prediction(ticker, horizon, last_date)
        if cached_pred:
            return PredictionResponse(**cached_pred)

        # Check if model already trained in registry
        if ModelRegistry.exists(ticker):
            try:
                # Fast inference path
                pred_result = ModelPredictor.predict(ticker=ticker, horizon_days=horizon, df=df)
                CacheManager.set_cached_prediction(ticker, horizon, last_date, pred_result)
                return PredictionResponse(**pred_result)
            except Exception as e:
                # Fall back to retraining if model load/inference failed
                pass

    # Cold ticker / retrain path: enqueue async training job
    job_id = JobManager.create_job(ticker=ticker, horizon_days=horizon)
    response.status_code = status.HTTP_202_ACCEPTED
    return PredictionResponse(
        status="training",
        job_id=job_id,
        ticker=ticker,
        horizon_days=horizon,
        message=f"Training LSTM model for ticker {ticker} in background. Poll /api/jobs/{job_id} for progress."
    )


@router.get("/predict/{ticker}", response_model=PredictionResponse)
def get_cached_prediction(
    ticker: str,
    horizon_days: int = Query(7, ge=1, le=90)
):
    """
    Retrieves latest cached prediction for ticker without triggering a retrain.
    """
    ticker = ticker.strip().upper()
    try:
        df = fetcher.get_history(ticker, range_str="1m")
        last_date = str(df["date"].iloc[-1])
    except Exception:
        last_date = ""

    cached = CacheManager.get_cached_prediction(ticker, horizon_days, last_date)
    if not cached:
        raise HTTPException(status_code=404, detail=f"No cached prediction found for {ticker} (horizon {horizon_days}d).")

    return PredictionResponse(**cached)
