# Architecture Decision Records
## Stock Price Prediction Web App (LSTM)

---

# ADR-001: Market Data Source

**Status:** Proposed
**Date:** 2026-08-29
**Deciders:** You

## Context
The app needs historical daily OHLCV (open/high/low/close/volume) data for arbitrary stock tickers, refreshed at least daily, at minimal cost for an MVP.

## Decision
Use **`yfinance`** (a Python library that pulls data from Yahoo Finance) as the primary data source for MVP, behind a small internal `DataFetcher` interface so it can be swapped later without touching the rest of the app.

## Options Considered

### Option A: yfinance (Yahoo Finance, unofficial)
| Dimension | Assessment |
|-----------|------------|
| Complexity | Low — one `pip install`, no API key |
| Cost | Free |
| Scalability | Fine for daily-batch use; not meant for heavy real-time load |
| Team familiarity | High (widely used, well-documented, plain pandas output) |

**Pros:** Free, no signup/API key, returns clean OHLCV data, huge community usage for exactly this kind of project.
**Cons:** Unofficial — scrapes/wraps Yahoo endpoints, so it can break or get rate-limited without notice; not intended for production-scale or commercial use.

### Option B: Alpha Vantage (or similar paid/free-tier API)
| Dimension | Assessment |
|-----------|------------|
| Complexity | Low-Medium — needs an API key, has request quotas |
| Cost | Free tier is heavily rate-limited (e.g., a handful of requests/minute); paid tiers cost money |
| Scalability | Better long-term reliability guarantees than an unofficial wrapper |
| Team familiarity | Medium |

**Pros:** Official, documented SLA-ish behavior, more data types available (fundamentals, indicators).
**Cons:** Free-tier rate limits will bite quickly with an interactive "search any ticker" UI; costs money to scale.

### Option C: Static Kaggle dataset
**Pros:** Zero integration work, good for a pure ML notebook exercise.
**Cons:** Frozen in time — cannot fulfill "user picks any ticker" or "daily-refreshed data" requirements. Rejected for a live web app.

## Trade-off Analysis
For a learning/portfolio web app with no budget, yfinance's reliability risk is acceptable in exchange for zero cost and zero signup friction. The mitigation is architectural, not vendor-side: isolate all data access behind one module/interface so that if Yahoo's data breaks or rate-limits become a problem, swapping in Alpha Vantage (or another source) is a contained change, not a rewrite.

## Consequences
- Easier to start building immediately.
- Must add caching (don't refetch on every request) both for speed and to be a good citizen of a free/unofficial data source.
- Should design the `DataFetcher` interface now, even though there's only one implementation, so migration later is cheap.

## Action Items
1. [ ] Build `DataFetcher` interface with a single `get_history(ticker, range)` method.
2. [ ] Implement `YFinanceFetcher` against it.
3. [ ] Add a cache layer in front of it (Redis or DB-backed) with a sensible TTL (e.g., refresh once/day).

---

# ADR-002: Model Serving Pattern (Pretrained vs. On-Demand Training)

**Status:** Proposed
**Date:** 2026-08-29
**Deciders:** You

## Context
LSTM training takes on the order of minutes, which is far too slow for a synchronous web request. The app needs to support users picking arbitrary tickers while keeping the UI responsive.

## Decision
Use a **hybrid** approach: pretrain models for a fixed set of popular tickers at deploy time / on a schedule; for any other ticker, train asynchronously on first request via a background job queue, and cache the result for subsequent requests.

## Options Considered

### Option A: Fully pretrained (fixed ticker list only)
| Dimension | Assessment |
|-----------|------------|
| Complexity | Low |
| Cost | Predictable, bounded |
| Scalability | Simple to scale (inference-only, fast) |
| Team familiarity | High |

**Pros:** Every request is fast; no training infrastructure needed at request time.
**Cons:** Doesn't satisfy "user picks any stock" — limits the product significantly.

### Option B: Fully on-demand (train on first request for any ticker)
| Dimension | Assessment |
|-----------|------------|
| Complexity | Medium — needs async jobs, polling/websocket UI |
| Cost | Scales with distinct tickers requested; could be abused |
| Scalability | Needs worker pool that can be scaled independently of the API |
| Team familiarity | Medium |

**Pros:** Fully general — any ticker works.
**Cons:** First-time experience is slow (minutes); needs abuse/rate-limit protection; more moving parts (queue, workers).

### Option C: Hybrid — pretrain popular tickers, on-demand for the rest
**Pros:** Best of both — instant results for the common case (demo-friendly), full flexibility for the long tail, and it naturally becomes "fully general" over time as more tickers get trained and cached.
**Cons:** Slightly more to build initially (both a batch pretraining script and an on-demand job pipeline).

## Trade-off Analysis
Option C costs a bit more upfront complexity than A or B alone, but it's the only option that satisfies both the "responsive demo" goal and the "pick any stock" requirement in the PRD. Given the project already needs an async job pattern for correctness (LSTM training is just too slow to do inline), the incremental cost of also pretraining a shortlist (e.g., S&P 500, or even just the top 20–50 most-searched names) is small.

## Consequences
- Need a job queue (Celery + Redis is a reasonable default) even in the MVP.
- Need simple frontend polling/status UI for the "training..." state.
- Need a scheduled batch job (cron/Celery beat) to keep pretrained models fresh.
- Must rate-limit on-demand training requests per user/IP to prevent abuse.

## Action Items
1. [ ] Pick an initial pretrained ticker list (e.g., top 20 by search popularity or market cap).
2. [ ] Build the async training job + status endpoint.
3. [ ] Add per-IP rate limiting on job creation.
4. [ ] Add a nightly/weekly retraining schedule for models with fresh data.

---

# ADR-003: Backend Framework

**Status:** Proposed
**Date:** 2026-08-29
**Deciders:** You

## Decision
Use **FastAPI** for the backend API.

## Options Considered

| Dimension | FastAPI | Flask | Django |
|---|---|---|---|
| Complexity | Low-Medium | Low | Medium-High |
| Async support | Native (good for job polling endpoints) | Bolt-on | Bolt-on |
| Fit with ML stack | Excellent — same Python process can call TF/Keras directly | Excellent | Excellent but heavier than needed |
| Auto docs | Built-in OpenAPI/Swagger docs | Manual | Manual (DRF adds it) |
| Team familiarity | Assume similar to Flask for most Python devs | High | Medium |

## Trade-off Analysis
Django brings a lot (ORM, admin, auth) this project doesn't need for v1 (no user accounts). Flask is fine but FastAPI's native async support maps well onto the polling-style `/jobs/{id}` endpoint, and its automatic OpenAPI docs are a nice bonus for a portfolio project you might want to show off.

## Consequences
- Very small learning curve if coming from Flask; if new to both, FastAPI is not meaningfully harder.
- Will need `SQLAlchemy` (or similar) directly for DB access since FastAPI doesn't bundle an ORM.

---

# ADR-004: Job Queue for Async Training

**Status:** Proposed
**Date:** 2026-08-29
**Deciders:** You

## Decision
Use **Celery + Redis** for background training jobs, with room to downgrade to simple Python threading/`BackgroundTasks` for a quick local prototype before wiring up the full queue.

## Options Considered

### Option A: Celery + Redis
**Pros:** Battle-tested, handles retries/failures, decouples workers from the API process (can scale independently), Redis doubles as the hot-path prediction cache too.
**Cons:** Extra moving part to run (a broker) — slightly more ops overhead than in-process solutions.

### Option B: FastAPI `BackgroundTasks` / plain threading
**Pros:** Zero extra infrastructure — good for a quick local demo.
**Cons:** Jobs die if the API process restarts; no built-in retry/monitoring; doesn't scale training separately from the API.

## Trade-off Analysis
For a first local prototype, `BackgroundTasks` is fine and gets you moving fastest. But since the PRD explicitly wants this deployed as a web app (not just a local script), and training workers are the part most likely to need independent scaling, Celery+Redis is the right target architecture — it's also not much extra work if you're already using Redis for the prediction cache (ADR referenced in System Design §7).

## Consequences
- Requires running a Redis instance (cheap/free on most hosting platforms) and at least one Celery worker process alongside the API.
- Gives you job retries and failure visibility largely for free.

## Action Items
1. [ ] Prototype with `BackgroundTasks` locally if you want the fastest path to a working demo.
2. [ ] Migrate to Celery + Redis before/at deployment.
