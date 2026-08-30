import sqlite3
import json
import datetime
from typing import Optional, Dict, Any, List
import pandas as pd
from backend.app.config import DB_PATH

def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Table: tickers metadata
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tickers (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        currency TEXT DEFAULT 'USD',
        exchange TEXT DEFAULT 'Unknown',
        last_updated TEXT
    )
    """)
    
    # Table: historical prices cache
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS price_cache (
        ticker TEXT,
        range_str TEXT,
        data_json TEXT,
        cached_at TEXT,
        PRIMARY KEY (ticker, range_str)
    )
    """)

    # Table: prediction results cache
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prediction_cache (
        ticker TEXT,
        horizon_days INTEGER,
        last_historical_date TEXT,
        result_json TEXT,
        cached_at TEXT,
        PRIMARY KEY (ticker, horizon_days)
    )
    """)

    # Table: background jobs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        job_id TEXT PRIMARY KEY,
        ticker TEXT,
        status TEXT,
        progress INTEGER DEFAULT 0,
        stage TEXT,
        error TEXT,
        result_json TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    conn.commit()
    conn.close()

# Initialize DB at import time
init_db()

class CacheManager:
    """Manages caching of market data, prediction results, and job statuses."""

    @staticmethod
    def get_cached_history(ticker: str, range_str: str, max_age_hours: int = 4) -> Optional[pd.DataFrame]:
        ticker = ticker.upper()
        range_str = range_str.lower()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT data_json, cached_at FROM price_cache WHERE ticker = ? AND range_str = ?",
            (ticker, range_str)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        cached_at_str = row["cached_at"]
        cached_at = datetime.datetime.fromisoformat(cached_at_str)
        age = datetime.datetime.now(datetime.timezone.utc) - cached_at
        if age.total_seconds() > max_age_hours * 3600:
            return None  # Expired cache

        try:
            records = json.loads(row["data_json"])
            return pd.DataFrame(records)
        except Exception:
            return None

    @staticmethod
    def set_cached_history(ticker: str, range_str: str, df: pd.DataFrame):
        ticker = ticker.upper()
        range_str = range_str.lower()
        data_json = df.to_json(orient="records")
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO price_cache (ticker, range_str, data_json, cached_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ticker, range_str) DO UPDATE SET
                data_json = excluded.data_json,
                cached_at = excluded.cached_at
            """,
            (ticker, range_str, data_json, now_str)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def get_cached_prediction(ticker: str, horizon_days: int, latest_historical_date: str) -> Optional[Dict[str, Any]]:
        ticker = ticker.upper()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT result_json, last_historical_date, cached_at
            FROM prediction_cache
            WHERE ticker = ? AND horizon_days = ?
            """,
            (ticker, horizon_days)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        # If data is from an older trading day, it should be refreshed
        if row["last_historical_date"] != latest_historical_date:
            return None

        try:
            res = json.loads(row["result_json"])
            res["is_cached"] = True
            return res
        except Exception:
            return None

    @staticmethod
    def set_cached_prediction(ticker: str, horizon_days: int, latest_historical_date: str, result_dict: Dict[str, Any]):
        ticker = ticker.upper()
        result_json = json.dumps(result_dict)
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO prediction_cache (ticker, horizon_days, last_historical_date, result_json, cached_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(ticker, horizon_days) DO UPDATE SET
                last_historical_date = excluded.last_historical_date,
                result_json = excluded.result_json,
                cached_at = excluded.cached_at
            """,
            (ticker, horizon_days, latest_historical_date, result_json, now_str)
        )
        conn.commit()
        conn.close()
