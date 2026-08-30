from fastapi import APIRouter, Query
from typing import List
from backend.app.schemas.models import TickerInfo
from backend.app.data.fetcher import YFinanceFetcher

router = APIRouter()
fetcher = YFinanceFetcher()

@router.get("/tickers", response_model=List[TickerInfo])
def get_tickers(query: str = Query("", description="Search term for ticker symbol or company name")):
    """
    Returns matching stock tickers with autocomplete support.
    """
    results = fetcher.search_tickers(query)
    return [
        TickerInfo(
            symbol=r["symbol"],
            name=r.get("name", r["symbol"]),
            exchange=r.get("exchange", "Unknown")
        )
        for r in results
    ]
