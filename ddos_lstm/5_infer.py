"""
Step 5: Run inference on new flow data using the trained LSTM model.

Usage:
    python 5_infer.py --input path/to/new_flows.csv [--model lstm|rf|both]
"""

import argparse
import numpy as np
import pandas as pd
import tensorflow as tf
import joblib
import os

MODEL_DIR   = "models"
SCALER_PATH = "data/processed/scaler_params.csv"
RFE_PATH    = "data/processed/rfe_selected_features.txt"
TIMESTEPS   = 20
THRESHOLD   = 0.5


def load_features() -> list:
    if os.path.exists(RFE_PATH):
        with open(RFE_PATH) as fh:
            return [l.strip() for l in fh if l.strip()]
    raise FileNotFoundError("Run 1b_rfe_feature_selection.py first.")


def scale(df: pd.DataFrame, scaler_df: pd.DataFrame) -> pd.DataFrame:
    for _, row in scaler_df.iterrows():
        feat = row["feature"]
        if feat in df.columns:
            rng = row["max"] - row["min"]
            df[feat] = (df[feat] - row["min"]) / (rng if rng != 0 else 1)
    return df


def prepare(csv_path: str, features: list, scaler_df: pd.DataFrame) -> np.ndarray:
    df = pd.read_csv(csv_path, low_memory=False)
    df.columns = df.columns.str.strip()
    available = [f for f in features if f in df.columns]
    df = df[available].copy()
    df.replace([float("inf"), float("-inf")], float("nan"), inplace=True)
    df.dropna(inplace=True)
    df = scale(df, scaler_df[scaler_df["feature"].isin(available)])
    return df.values


def make_sequences(X: np.ndarray) -> np.ndarray:
    return np.array([X[i: i + TIMESTEPS]
                     for i in range(0, len(X) - TIMESTEPS, TIMESTEPS)])


def predict(csv_path: str, use_model: str):
    features  = load_features()
    scaler_df = pd.read_csv(SCALER_PATH)
    X_flat    = prepare(csv_path, features, scaler_df)

    if len(X_flat) < TIMESTEPS:
        print(f"Need at least {TIMESTEPS} rows; got {len(X_flat)}.")
        return

    results = {}

    if use_model in ("lstm", "both"):
        model    = tf.keras.models.load_model(os.path.join(MODEL_DIR, "best_model.keras"))
        X_seq    = make_sequences(X_flat)
        probs    = model.predict(X_seq, batch_size=128, verbose=0).flatten()
        preds    = (probs >= THRESHOLD).astype(int)
        results["lstm"] = (preds, probs)

    if use_model in ("rf", "both"):
        rf    = joblib.load(os.path.join(MODEL_DIR, "rf_baseline.joblib"))
        probs = rf.predict_proba(X_flat)[:, 1]
        preds = rf.predict(X_flat)
        results["rf"] = (preds, probs)

    for name, (preds, probs) in results.items():
        print(f"\n[{name.upper()}] Total samples: {len(preds)}")
        print(f"  Predicted BENIGN : {(preds == 0).sum()}")
        print(f"  Predicted ATTACK : {(preds == 1).sum()}")

        out = pd.DataFrame({
            "sample_index":       range(len(preds)),
            "attack_probability": probs,
            "prediction":         ["ATTACK" if p else "BENIGN" for p in preds],
        })
        out_path = os.path.splitext(csv_path)[0] + f"_predictions_{name}.csv"
        out.to_csv(out_path, index=False)
        print(f"  Saved -> {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  required=True, help="Path to new flow CSV")
    parser.add_argument("--model",  default="both", choices=["lstm", "rf", "both"],
                        help="Which model to use for inference")
    args = parser.parse_args()
    predict(args.input, args.model)
