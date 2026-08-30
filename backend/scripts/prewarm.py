import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.config import POPULAR_TICKERS
from backend.app.ml.trainer import ModelTrainer
from backend.app.ml.registry import ModelRegistry

def prewarm_models(tickers=None, epochs=25):
    if tickers is None:
        # Pre-warm top 3 demo tickers by default for fast initialization
        tickers = ["AAPL", "MSFT", "NVDA"]

    print(f"=== Starting Model Pre-warming for: {', '.join(tickers)} ===")
    for ticker in tickers:
        ticker = ticker.upper()
        if ModelRegistry.exists(ticker):
            print(f"[✓] Model for {ticker} already exists in registry. Skipping.")
            continue

        print(f"\n[→] Pre-training LSTM model for {ticker}...")
        try:
            def log_progress(pct, msg):
                print(f"    [{pct}%] {msg}")

            res = ModelTrainer.train_ticker(
                ticker=ticker,
                epochs=epochs,
                progress_callback=log_progress
            )
            metrics = res["metadata"]["metrics"]
            print(f"[✓] {ticker} trained! LSTM RMSE: ${metrics['rmse']} vs Naive Baseline RMSE: ${metrics['baseline_rmse']} (Dir Acc: {metrics['directional_accuracy']}%)")
        except Exception as e:
            print(f"[✗] Failed to pre-train {ticker}: {e}")

    print("\n=== Pre-warming Finished ===")

if __name__ == "__main__":
    tickers_to_warm = sys.argv[1:] if len(sys.argv) > 1 else ["AAPL", "MSFT", "NVDA"]
    prewarm_models(tickers_to_warm)
