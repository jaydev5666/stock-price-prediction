# System Design
## Stock Price Prediction Web App (LSTM)

Companion to `01_PROJECT_REQUIREMENTS.md`. This covers the high-level design, data flow, API contracts, data model, and scale/reliability considerations.

---

## 1. High-Level Architecture

```
                         ┌─────────────────────┐
                         │      Frontend         │
                         │  (React SPA)          │
                         │  - ticker search       │
                         │  - historical chart    │
                         │  - forecast overlay    │
                         └──────────┬───────────┘
                                    │ REST (JSON)
                                    ▼
                         ┌─────────────────────┐
                         │     Backend API       │
                         │     (FastAPI)         │
                         │  /tickers  /history    │
                         │  /predict  /jobs       │
                         └──────┬───────┬────────┘
                                │       │
                 ┌──────────────┘       └───────────────┐
                 ▼                                       ▼
     ┌───────────────────────┐               ┌───────────────────────┐
     │  Data Fetch & Cache    │               │   Prediction Cache /   │
     │  (yfinance + Redis/DB) │               │   Metadata DB          │
     └───────────┬───────────┘               │  (Postgres/SQLite)     │
                 │                            └───────────┬───────────┘
                 ▼                                        │
     ┌───────────────────────┐                            │
     │   Preprocessing        │                            │
     │  (scale, window, split)│                            │
     └───────────┬───────────┘                            │
                 ▼                                        │
     ┌───────────────────────┐    async (queue)           │
     │  Training Worker(s)    │◄───────────────────────────┘
     │  (Celery + TF/Keras)   │
     └───────────┬───────────┘
                 ▼
     ┌───────────────────────┐
     │   Model Registry        │
     │  (file storage: local/  │
     │   S3 — .keras files)    │
     └───────────────────────┘
```

**Key idea:** the API layer never trains a model inline in the request path. It either (a) serves a cached prediction, (b) runs fast inference against an already-trained model, or (c) enqueues a training job and returns a job ID the frontend polls. This keeps the web request path fast regardless of how slow training is.

## 2. Components

| Component | Responsibility | Suggested tech |
|---|---|---|
| Frontend | Ticker search UI, charts, forecast display, job-status polling | React + a charting lib (Recharts/Chart.js) |
| Backend API | Request validation, routing, cache lookups, job enqueueing | FastAPI (Python — pairs naturally with your TF/Keras stack) |
| Data Fetcher | Pulls OHLCV history from the market-data source, normalizes into a common schema | `yfinance` wrapper module (see ADR-001) |
| Cache | Avoids refetching/retraining on every request | Redis (hot cache) + DB (durable cache/metadata) |
| Preprocessing | Scaling (MinMax), windowing into sequences, train/val split | Shared Python module used by both training and inference |
| Training Worker | Trains/updates the LSTM per ticker, computes validation metrics, writes model artifact | Celery worker process running TensorFlow/Keras |
| Model Registry | Versioned storage of trained model files + their metrics | Local disk for MVP → S3/GCS later |
| Metadata DB | Tickers, model versions, job status, prediction cache entries | SQLite for MVP → Postgres when concurrent writes grow |

## 3. Data Flow

**Cached ticker (fast path):**
1. Frontend calls `POST /api/predict` with `{ticker, horizon}`.
2. API checks prediction cache — hit → returns forecast + metrics immediately.

**New/cold ticker (slow path):**
1. API checks cache — miss.
2. API checks model registry for an existing trained model for that ticker.
3. No model → API enqueues a training job, returns `{job_id, status: "training"}`.
4. Frontend polls `GET /api/jobs/{job_id}`.
5. Worker: fetch history → preprocess → train LSTM → validate (RMSE/MAE vs naive baseline) → save model to registry → write prediction to cache → mark job complete.
6. Frontend sees `status: "done"`, fetches the result.

## 4. API Contracts (v1)

```
GET  /api/tickers?query={text}
  -> [{ symbol, name, exchange }]

GET  /api/stock/{ticker}/history?range=1y
  -> { ticker, points: [{ date, open, high, low, close, volume }] }

POST /api/predict
  body: { ticker, horizon_days }
  -> 200 { status: "ready", predictions: [...], metrics: { rmse, mae, baseline_rmse } }
     202 { status: "training", job_id }
     404 { error: "unknown ticker" }

GET  /api/jobs/{job_id}
  -> { status: "training" | "done" | "failed", progress?: 0-100 }

GET  /api/predict/{ticker}?horizon_days=7
  -> latest cached prediction, if any (no training triggered)
```

## 5. Data Model (simplified)

```
tickers            (symbol PK, name, exchange, last_updated)
price_history      (ticker FK, date, open, high, low, close, volume)
models             (id PK, ticker FK, version, trained_at, rmse, mae,
                     baseline_rmse, file_path, lookback_window)
predictions_cache  (id PK, ticker FK, model_id FK, horizon_days,
                     predicted_at, values JSON, expires_at)
jobs               (id PK, ticker FK, status, created_at, updated_at, error)
```

## 6. Model Design Notes (LSTM specifics)

- **Input:** sliding window of the last N days (e.g., 60) of closing price (optionally + volume) per sample.
- **Preprocessing:** MinMax-scale per ticker (fit scaler on training split only, persist the scaler alongside the model so inference uses the same scaling).
- **Architecture (starting point):** 1–2 stacked LSTM layers (e.g., 50–64 units) + Dropout + Dense(1) output. Simple by design — this is a good default for an MVP and avoids overfitting on a single ticker's history.
- **Validation:** hold out the most recent ~10–20% of history chronologically (never randomly shuffle time series). Compare RMSE against a naive persistence baseline — this comparison is what tells you if the model is adding value at all.
- **Retraining cadence:** nightly or weekly batch job refreshes models for actively-requested tickers with the latest data.

## 7. Scale & Reliability

- **MVP scale:** single API instance + single worker is fine for tens of users and a modest ticker set.
- **Growth path:**
  - Scale API horizontally (stateless, behind a load balancer) once traffic grows — it's not doing heavy compute.
  - Scale training workers independently (they're the CPU/GPU-heavy piece); add more Celery workers or move to a managed job runner.
  - Move model registry from local disk to object storage (S3/GCS) once you run more than one API/worker instance, so all instances see the same models.
  - Move metadata DB from SQLite to Postgres once you have concurrent writers (multiple workers finishing jobs at once).
- **Failure handling:**
  - Data source down → serve last-cached historical data with a "data may be stale" notice; don't fail the whole request.
  - Training job fails → mark job `failed` with a reason, let the user retry rather than retrying silently in a loop.
  - Rate-limit `/api/predict` for cold tickers per IP to prevent one user from queuing excessive training jobs.
- **Monitoring (lightweight for MVP):** log every prediction's RMSE vs baseline over time per ticker; if a model's live error drifts far from its validation-time error, that's your signal to retrain sooner.

## 8. What to Revisit as This Grows

- Fixed ticker universe vs. fully open ticker support (open support needs stronger abuse controls).
- Whether to move from per-ticker models to a single multi-ticker model (harder, but avoids retraining N models).
- Adding intraday data / shorter horizons if daily granularity turns out to be too coarse for what you want to show.
- Adding auth if you want to save users' watchlists or forecast history.
