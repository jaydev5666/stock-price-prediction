from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.routes import tickers, stock, predict, jobs

app = FastAPI(
    title="Stock Price Prediction API",
    description="Educational LSTM-based Stock Price Forecasting API",
    version="1.0.0"
)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers under /api prefix
app.include_router(tickers.router, prefix="/api", tags=["Tickers"])
app.include_router(stock.router, prefix="/api", tags=["Stock History"])
app.include_router(predict.router, prefix="/api", tags=["Forecast"])
app.include_router(jobs.router, prefix="/api", tags=["Jobs"])

@app.get("/api/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "service": "Stock Price Prediction LSTM Service",
        "version": "1.0.0"
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc)}
    )
