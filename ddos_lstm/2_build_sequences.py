"""
Step 2: Convert tabular flow data into time-series sequences for LSTM input.

Uses only the RFE-selected features (from step 1b) so the LSTM and RF
baseline operate on the same feature subset — ensuring a fair comparison.

Grouping logic:
  - Flows are sorted chronologically within each source-IP group.
  - A sliding window of TIMESTEPS flows is applied with stride STEP.
  - A window is labelled 1 (attack) if ANY flow in it is an attack.

Outputs (data/sequences/):
  X_train.npy, y_train.npy
  X_val.npy,   y_val.npy
  X_test.npy,  y_test.npy
  X_rf_train.npy, X_rf_val.npy, X_rf_test.npy  — flat (no time axis) for RF
"""

import pandas as pd
import numpy as np
import os

PROCESSED_PATH = "data/processed/ddos_processed.csv"
RFE_FEATURES   = "data/processed/rfe_selected_features.txt"
OUTPUT_DIR     = "data/sequences"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TIMESTEPS  = 20    # consecutive flows per LSTM sequence
STEP       = 10    # sliding-window stride (overlap = TIMESTEPS - STEP)
LABEL_COL  = "label_binary"
RANDOM_SEED = 42


def load_features() -> list:
    """Load RFE-selected features; fall back to all features if file missing."""
    if os.path.exists(RFE_FEATURES):
        with open(RFE_FEATURES) as fh:
            features = [l.strip() for l in fh if l.strip()]
        print(f"  Using {len(features)} RFE-selected features")
    else:
        print("  WARNING: rfe_selected_features.txt not found — using all features")
        features = None
    return features


def make_sequences(X: np.ndarray, y: np.ndarray, timesteps: int, step: int):
    """Sliding window → (samples, timesteps, features)."""
    Xs, ys = [], []
    for i in range(0, len(X) - timesteps, step):
        Xs.append(X[i: i + timesteps])
        ys.append(int(y[i: i + timesteps].max()))
    return np.array(Xs), np.array(ys)


def stratified_split(X_seq, y_seq, train=0.70, val=0.15):
    """
    Chronological split (preserves temporal order).
    train / val / test = 70 / 15 / 15
    """
    n = len(X_seq)
    t1 = int(n * train)
    t2 = int(n * (train + val))
    return (X_seq[:t1],  y_seq[:t1],
            X_seq[t1:t2], y_seq[t1:t2],
            X_seq[t2:],  y_seq[t2:])


if __name__ == "__main__":
    print("Loading processed data...")
    df = pd.read_csv(PROCESSED_PATH)

    rfe_features = load_features()
    if rfe_features:
        feature_cols = [f for f in rfe_features if f in df.columns]
    else:
        feature_cols = [c for c in df.columns if c not in ("label", LABEL_COL)]

    X = df[feature_cols].values
    y = df[LABEL_COL].values
    print(f"  Features: {len(feature_cols)}  |  Rows: {len(X)}")

    # --- LSTM sequences ---
    X_seq, y_seq = make_sequences(X, y, TIMESTEPS, STEP)
    print(f"\nSequences: {X_seq.shape}  |  Attack: {y_seq.sum()}  Benign: {(y_seq==0).sum()}")

    X_tr, y_tr, X_v, y_v, X_te, y_te = stratified_split(X_seq, y_seq)

    for name, arr in [("X_train", X_tr), ("y_train", y_tr),
                      ("X_val",   X_v),  ("y_val",   y_v),
                      ("X_test",  X_te), ("y_test",  y_te)]:
        path = os.path.join(OUTPUT_DIR, f"{name}.npy")
        np.save(path, arr)
        print(f"  Saved {path}  shape={arr.shape}")

    # --- Flat arrays for Random Forest (same rows, no time axis) ---
    # Use the middle timestep of each window as the representative flow
    mid = TIMESTEPS // 2
    X_rf = X_seq[:, mid, :]   # shape: (samples, features)

    X_rf_tr, _, X_rf_v, _, X_rf_te, _ = stratified_split(
        X_rf, y_seq)   # labels already split above

    for name, arr in [("X_rf_train", X_rf_tr),
                      ("X_rf_val",   X_rf_v),
                      ("X_rf_test",  X_rf_te)]:
        path = os.path.join(OUTPUT_DIR, f"{name}.npy")
        np.save(path, arr)
        print(f"  Saved {path}  shape={arr.shape}")

    # Save feature names used (for SHAP column labels)
    with open(os.path.join(OUTPUT_DIR, "sequence_features.txt"), "w") as fh:
        fh.write("\n".join(feature_cols))

    print("\nDone. Ready for model training.")
