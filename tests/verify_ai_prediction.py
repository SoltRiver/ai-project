import pandas as pd
import numpy as np
from services.ai_prediction_service import predictor
from services.data_fetcher import fetch_stock_data, format_symbol_for_yfinance


def test_ai_prediction():
    code = "7203"  # Toyota
    symbol = format_symbol_for_yfinance(code)
    df = fetch_stock_data(symbol, period="1y", interval="1d")

    if df is None or df.empty:
        print("Failed to fetch data")
        return

    print(f"Testing AI prediction for {code}...")

    # Check features
    features = predictor.engineer_features(df)
    print(f"Features engineered: {features.columns.tolist()}")
    assert not features.empty, "Features should not be empty"

    # Check prediction
    result = predictor.predict_latest(df)
    print(f"Prediction result keys: {list(result.keys())}")
    print(f"Prediction probability: {result.get('probability')}")

    assert "probability" in result, "Result should contain probability"
    assert "is_provisional" in result, "Result should contain is_provisional"

    if result["probability"] != "-":
        assert (
            "validation" in result
        ), "Result with probability should contain validation info"
        assert (
            0 <= result["probability"] <= 1
        ), f"Probability {result['probability']} should be between 0 and 1"
    else:
        print("Model could not be trained or prediction failed (Insufficient data?)")

    print("Verification successful!")


if __name__ == "__main__":
    test_ai_prediction()
