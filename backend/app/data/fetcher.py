from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd
import yfinance as yf
import datetime
from backend.app.config import POPULAR_TICKERS

class DataFetchError(Exception):
    """Raised when data fetching fails from an upstream market data provider."""
    pass

class TickerNotFoundError(DataFetchError):
    """Raised when a requested ticker cannot be found or has no price history."""
    pass

class BaseDataFetcher(ABC):
    """Abstract interface for market data providers (ADR-001)."""

    @abstractmethod
    def get_history(self, ticker: str, range_str: str = "1y") -> pd.DataFrame:
        """
        Fetches historical OHLCV data.
        Returns a DataFrame with columns: ['date', 'open', 'high', 'low', 'close', 'volume']
        """
        pass

    @abstractmethod
    def search_tickers(self, query: str) -> List[Dict[str, str]]:
        """
        Searches for tickers matching query string.
        Returns list of dicts: [{'symbol': '...', 'name': '...', 'exchange': '...'}]
        """
        pass

    @abstractmethod
    def get_info(self, ticker: str) -> Dict[str, Any]:
        """Returns metadata such as company name, currency, exchange."""
        pass


class YFinanceFetcher(BaseDataFetcher):
    """Implementation of BaseDataFetcher using Yahoo Finance (yfinance)."""

    RANGE_MAP = {
        "1m": "1mo",
        "1mo": "1mo",
        "3m": "3mo",
        "3mo": "3mo",
        "6m": "6mo",
        "6mo": "6mo",
        "1y": "1y",
        "2y": "2y",
        "5y": "5y",
        "max": "max"
    }

    def get_history(self, ticker: str, range_str: str = "1y") -> pd.DataFrame:
        ticker = ticker.strip().upper()
        period = self.RANGE_MAP.get(range_str.lower(), "1y")

        try:
            yticker = yf.Ticker(ticker)
            df = yticker.history(period=period, interval="1d", auto_adjust=False)

            if df is None or df.empty or len(df) < 5:
                raise TickerNotFoundError(f"No price history found for ticker '{ticker}'. Please verify the symbol.")

            # Reset index to get Date as a column
            df = df.reset_index()

            # Ensure columns are normalized
            # yfinance columns may be Title Case (Date, Open, High, Low, Close, Volume)
            df.columns = [str(c).lower().strip() for c in df.columns]

            # Parse date string YYYY-MM-DD
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            elif "datetime" in df.columns:
                df["date"] = pd.to_datetime(df["datetime"]).dt.strftime("%Y-%m-%d")

            # Check required columns
            required_cols = ["date", "open", "high", "low", "close", "volume"]
            for col in required_cols:
                if col not in df.columns:
                    raise DataFetchError(f"Missing required column '{col}' in upstream data for '{ticker}'.")

            df = df[required_cols].copy()
            # Clean nulls
            df = df.dropna(subset=["close"]).reset_index(drop=True)

            # Cast data types cleanly
            df["open"] = df["open"].astype(float).round(4)
            df["high"] = df["high"].astype(float).round(4)
            df["low"] = df["low"].astype(float).round(4)
            df["close"] = df["close"].astype(float).round(4)
            df["volume"] = df["volume"].fillna(0).astype(int)

            return df

        except TickerNotFoundError:
            raise
        except Exception as e:
            raise DataFetchError(f"Error fetching data for ticker '{ticker}': {str(e)}")

    def get_info(self, ticker: str) -> Dict[str, Any]:
        ticker = ticker.strip().upper()
        try:
            yticker = yf.Ticker(ticker)
            fast_info = getattr(yticker, "fast_info", None)
            info = getattr(yticker, "info", {}) or {}

            name = info.get("shortName") or info.get("longName") or ticker
            currency = info.get("currency") or "USD"
            exchange = info.get("exchange") or "Unknown"

            if fast_info:
                if not name or name == ticker:
                    name = getattr(fast_info, "name", name)
                currency = getattr(fast_info, "currency", currency)
                exchange = getattr(fast_info, "exchange", exchange)

            return {
                "symbol": ticker,
                "name": name or ticker,
                "currency": currency or "USD",
                "exchange": exchange or "Unknown"
            }
        except Exception:
            return {
                "symbol": ticker,
                "name": ticker,
                "currency": "USD",
                "exchange": "Unknown"
            }

    def search_tickers(self, query: str) -> List[Dict[str, str]]:
        query = query.strip().upper()
        if not query:
            return POPULAR_TICKERS

        # First filter local popular tickers for instant high-quality match
        matched_popular = [
            t for t in POPULAR_TICKERS
            if query in t["symbol"] or query in t["name"].upper()
        ]

        # Use yfinance Search API for arbitrary public symbols
        results = list(matched_popular)
        try:
            search_obj = yf.Search(query, max_results=8)
            quotes = getattr(search_obj, "quotes", [])
            for q in quotes:
                sym = q.get("symbol", "").upper()
                # Skip invalid / obscure types if needed
                if not sym or any(r["symbol"] == sym for r in results):
                    continue
                results.append({
                    "symbol": sym,
                    "name": q.get("shortname") or q.get("longname") or sym,
                    "exchange": q.get("exchange", "Unknown")
                })
        except Exception:
            # Fallback gracefully to popular tickers
            pass

        return results[:10]
