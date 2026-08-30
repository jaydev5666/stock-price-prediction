import uuid
import threading
import datetime
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any

from backend.app.data.cache import get_db_connection, CacheManager
from backend.app.ml.trainer import ModelTrainer
from backend.app.ml.predictor import ModelPredictor

class JobManager:
    """
    Manages asynchronous training jobs for stock tickers.
    Tracks live state in SQLite and in-memory thread pool.
    """
    _executor = ThreadPoolExecutor(max_workers=3)
    _active_jobs: Dict[str, Dict[str, Any]] = {}
    _lock = threading.Lock()

    @classmethod
    def create_job(cls, ticker: str, horizon_days: int = 7) -> str:
        ticker = ticker.strip().upper()
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Insert into DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO jobs (job_id, ticker, status, progress, stage, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (job_id, ticker, "queued", 5, "Job queued in worker pool", now_str, now_str)
        )
        conn.commit()
        conn.close()

        with cls._lock:
            cls._active_jobs[job_id] = {
                "job_id": job_id,
                "ticker": ticker,
                "horizon_days": horizon_days,
                "status": "queued",
                "progress": 5,
                "stage": "Job queued in worker pool",
                "created_at": now_str,
                "updated_at": now_str,
                "error": None,
                "result": None
            }

        # Submit background task
        cls._executor.submit(cls._run_training_job, job_id, ticker, horizon_days)
        return job_id

    @classmethod
    def get_job(cls, job_id: str) -> Optional[Dict[str, Any]]:
        with cls._lock:
            if job_id in cls._active_jobs:
                return cls._active_jobs[job_id]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        res_json = row["result_json"]
        result = json.loads(res_json) if res_json else None

        return {
            "job_id": row["job_id"],
            "ticker": row["ticker"],
            "status": row["status"],
            "progress": row["progress"],
            "stage": row["stage"],
            "error": row["error"],
            "result": result,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }

    @classmethod
    def update_progress(cls, job_id: str, progress: int, stage: str, status: str = "training"):
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with cls._lock:
            if job_id in cls._active_jobs:
                cls._active_jobs[job_id]["progress"] = progress
                cls._active_jobs[job_id]["stage"] = stage
                cls._active_jobs[job_id]["status"] = status
                cls._active_jobs[job_id]["updated_at"] = now_str

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE jobs
            SET progress = ?, stage = ?, status = ?, updated_at = ?
            WHERE job_id = ?
            """,
            (progress, stage, status, now_str, job_id)
        )
        conn.commit()
        conn.close()

    @classmethod
    def _run_training_job(cls, job_id: str, ticker: str, horizon_days: int):
        try:
            def on_progress(pct: int, msg: str):
                cls.update_progress(job_id, pct, msg, status="training")

            # 1. Run model training
            train_output = ModelTrainer.train_ticker(
                ticker=ticker,
                progress_callback=on_progress
            )

            # 2. Run prediction rollout
            cls.update_progress(job_id, 98, "Generating forecast values...", status="training")
            pred_result = ModelPredictor.predict(ticker=ticker, horizon_days=horizon_days)

            # 3. Cache prediction result
            last_date = pred_result.get("last_historical_date", "")
            CacheManager.set_cached_prediction(ticker, horizon_days, last_date, pred_result)

            # 4. Mark job done
            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            with cls._lock:
                if job_id in cls._active_jobs:
                    cls._active_jobs[job_id]["status"] = "done"
                    cls._active_jobs[job_id]["progress"] = 100
                    cls._active_jobs[job_id]["stage"] = "Training and prediction completed."
                    cls._active_jobs[job_id]["result"] = pred_result
                    cls._active_jobs[job_id]["updated_at"] = now_str

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE jobs
                SET status = 'done', progress = 100, stage = 'Completed', result_json = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (json.dumps(pred_result), now_str, job_id)
            )
            conn.commit()
            conn.close()

        except Exception as e:
            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            err_msg = str(e)
            with cls._lock:
                if job_id in cls._active_jobs:
                    cls._active_jobs[job_id]["status"] = "failed"
                    cls._active_jobs[job_id]["error"] = err_msg
                    cls._active_jobs[job_id]["stage"] = f"Failed: {err_msg}"
                    cls._active_jobs[job_id]["updated_at"] = now_str

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE jobs
                SET status = 'failed', error = ?, stage = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (err_msg, f"Failed: {err_msg}", now_str, job_id)
            )
            conn.commit()
            conn.close()
