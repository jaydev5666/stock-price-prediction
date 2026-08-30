import sys
import os

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Set root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.data.fetcher import YFinanceFetcher
from backend.app.data.preprocessor import DataPreprocessor
from backend.app.ml.trainer import ModelTrainer
from backend.app.ml.predictor import ModelPredictor
from backend.app.ml.registry import ModelRegistry
from backend.app.data.cache import CacheManager

def test_fetcher():
    print("--- 1. Testing YFinanceFetcher ---")
    fetcher = YFinanceFetcher()
    df = fetcher.get_history("AAPL", range_str="1y")
    assert not df.empty, "DataFrame should not be empty"
    assert len(df) > 100, f"Expected >100 rows, got {len(df)}"
    assert all(c in df.columns for c in ["date", "open", "high", "low", "close", "volume"])
    print(f"[OK] Fetched {len(df)} rows for AAPL. Latest date: {df['date'].iloc[-1]}, close: ${df['close'].iloc[-1]}")

    results = fetcher.search_tickers("Apple")
    assert any(r["symbol"] == "AAPL" for r in results)
    print(f"[OK] Search autocomplete returned {len(results)} matches for 'Apple'.")

def test_preprocessor():
    print("\n--- 2. Testing DataPreprocessor ---")
    fetcher = YFinanceFetcher()
    df = fetcher.get_history("AAPL", range_str="1y")
    preprocessor = DataPreprocessor(lookback=60, val_split=0.2)
    prep = preprocessor.prepare_training_data(df)

    assert prep["X_train"].shape[1] == 60
    assert prep["X_train"].shape[2] == 1
    assert prep["y_train"].shape[0] == prep["train_size"]
    assert prep["val_size"] > 0
    print(f"[OK] Preprocessed data: X_train {prep['X_train'].shape}, X_val {prep['X_val'].shape}")

def test_training_and_prediction():
    print("\n--- 3. Testing ModelTrainer & ModelPredictor ---")
    test_ticker = "AAPL"
    
    print(f"Training LSTM model for {test_ticker} (15 epochs)...")
    res = ModelTrainer.train_ticker(
        ticker=test_ticker,
        epochs=15
    )
    
    metrics = res["metadata"]["metrics"]
    print(f"[OK] Model trained! RMSE: ${metrics['rmse']}, Baseline RMSE: ${metrics['baseline_rmse']}, Dir Acc: {metrics['directional_accuracy']}%")
    assert ModelRegistry.exists(test_ticker), "Model should be saved in registry"

    print("\nGenerating multi-step 7-day forecast...")
    pred_res = ModelPredictor.predict(ticker=test_ticker, horizon_days=7)
    assert pred_res["status"] == "ready"
    assert len(pred_res["predictions"]) == 7
    for p in pred_res["predictions"]:
        assert "predicted_close" in p
        assert "lower_bound" in p
        assert "upper_bound" in p
        print(f"  Day {p['date']}: ${p['predicted_close']} (range: ${p['lower_bound']} - ${p['upper_bound']})")
    print("[OK] 7-Day multi-step prediction rollout validated successfully!")

def main():
    print("==========================================")
    print("STARTING END-TO-END PIPELINE VERIFICATION")
    print("==========================================")
    test_fetcher()
    test_preprocessor()
    test_training_and_prediction()
    print("\n==========================================")
    print("ALL ML PIPELINE TESTS PASSED CLEANLY! [OK]")
    print("==========================================")

if __name__ == "__main__":
    main()
