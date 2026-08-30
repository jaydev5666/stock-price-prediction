import sys
import os
import time

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Set root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_api():
    print("==========================================")
    print("TESTING FASTAPI BACKEND ENDPOINTS")
    print("==========================================")

    # 1. Health Check
    print("\n--- 1. Testing GET /api/health ---")
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    print(f"[OK] Health check passed: {res.json()}")

    # 2. Tickers Search Autocomplete
    print("\n--- 2. Testing GET /api/tickers ---")
    res = client.get("/api/tickers?query=Microsoft")
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    assert any(t["symbol"] == "MSFT" for t in data)
    print(f"[OK] Ticker search returned {len(data)} results, found MSFT!")

    # 3. Stock History
    print("\n--- 3. Testing GET /api/stock/AAPL/history ---")
    res = client.get("/api/stock/AAPL/history?range=1y")
    assert res.status_code == 200
    hist = res.json()
    assert hist["ticker"] == "AAPL"
    assert len(hist["points"]) > 100
    first_pt = hist["points"][0]
    last_pt = hist["points"][-1]
    print(f"[OK] History points: {len(hist['points'])} (First: {first_pt['date']} ${first_pt['close']}, Last: {last_pt['date']} ${last_pt['close']})")

    # 4. Predict on pre-warmed ticker (Instant 200)
    print("\n--- 4. Testing POST /api/predict for pre-warmed AAPL ---")
    res = client.post("/api/predict", json={"ticker": "AAPL", "horizon_days": 7})
    assert res.status_code == 200
    pred = res.json()
    assert pred["status"] == "ready"
    assert len(pred["predictions"]) == 7
    assert pred["metrics"] is not None
    print(f"[OK] Instant prediction received! RMSE: ${pred['metrics']['rmse']}, Horizon: {pred['horizon_days']} days")

    # 5. Predict on new ticker (202 Accepted -> async training -> poll)
    print("\n--- 5. Testing POST /api/predict async for cold ticker TSLA ---")
    res = client.post("/api/predict", json={"ticker": "TSLA", "horizon_days": 7})
    if res.status_code == 202:
        job_data = res.json()
        job_id = job_data["job_id"]
        print(f"[OK] Job enqueued! Job ID: {job_id}. Starting polling...")

        # Poll job
        max_attempts = 40
        for attempt in range(max_attempts):
            time.sleep(1.5)
            j_res = client.get(f"/api/jobs/{job_id}")
            assert j_res.status_code == 200
            j_stat = j_res.json()
            print(f"  [{j_stat['progress']}%] Status: {j_stat['status']} - {j_stat.get('stage', '')}")
            if j_stat["status"] == "done":
                print(f"[OK] Job completed successfully! Prediction count: {len(j_stat['prediction_result']['predictions'])}")
                break
            elif j_stat["status"] == "failed":
                raise RuntimeError(f"Training job failed: {j_stat.get('error')}")
    else:
        assert res.status_code == 200
        print(f"[OK] Ticker was already ready: {res.json()['status']}")

    # 6. Error handling on unknown ticker
    print("\n--- 6. Testing Error handling on invalid ticker ---")
    res = client.get("/api/stock/INVALIDTICKERXYZ999/history")
    assert res.status_code in [404, 502]
    print(f"[OK] Handled invalid ticker with clean status code: {res.status_code} ({res.json()})")

    print("\n==========================================")
    print("ALL API ENDPOINT TESTS PASSED CLEANLY! [OK]")
    print("==========================================")

if __name__ == "__main__":
    test_api()
