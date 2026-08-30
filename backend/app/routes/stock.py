from fastapi import APIRouter, HTTPException, Query, Path
from backend.app.schemas.models import StockHistoryResponse, PricePoint
from backend.app.data.fetcher import YFinanceFetcher, TickerNotFoundError, DataFetchError
from backend.app.data.cache import CacheManager

router = APIRouter()
fetcher = YFinanceFetcher()

@router.get("/stock/{ticker}/history", response_model=StockHistoryResponse)
def get_stock_history(
    ticker: str = Path(..., description="Stock symbol (e.g. AAPL)"),
    range: str = Query("1y", description="Time horizon (1m, 6m, 1y, 5y, max)")
):
    """
    Fetches historical OHLCV data for a ticker with multi-level caching.
    """
    ticker = ticker.strip().upper()
    range_clean = range.lower()

    # 1. Check cache
    df = CacheManager.get_cached_history(ticker, range_clean, max_age_hours=4)

    info = fetcher.get_info(ticker)

    # 2. If not cached, fetch from upstream provider
    if df is None:
        try:
            df = fetcher.get_history(ticker, range_str=range_clean)
            CacheManager.set_cached_history(ticker, range_clean, df)
        except TickerNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except DataFetchError as e:
            raise HTTPException(status_code=502, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    # 3. Format points
    points = [
        PricePoint(
            date=row["date"],
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row["volume"])
        )
        for _, row in df.iterrows()
    ]

    return StockHistoryResponse(
        ticker=ticker,
        name=info.get("name", ticker),
        currency=info.get("currency", "USD"),
        range=range_clean,
        points=points
    )
