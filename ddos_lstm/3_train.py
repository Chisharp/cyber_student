"""
Step 3: Train both models on the same feature subset.

  3a. Random Forest baseline  → models/rf_baseline.joblib
  3b. Stacked LSTM            → models/best_model.keras

Both models use the same training/validation split produced in step 2.
Cross-validation is performed only on the training partition.
"""

import numpy as np
import os
import json
import joblib
import tensorflow as tf
from tensorflow.keras import layers, callbacks
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.utils.class_weight import compute_class_weight

SEQ_DIR   = "data/sequences"
MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)

# Reproducibility
tf.random.set_seed(42)
np.random.seed(42)

# ── helpers ──────────────────────────────────────────────────────────────────

def load_splits():
    keys = ("X_train", "y_train", "X_val", "y_val", "X_test", "y_test",
            "X_rf_train", "X_rf_val", "X_rf_test")
    return {k: np.load(os.path.join(SEQ_DIR, f"{k}.npy")) for k in keys}


# ── Random Forest ─────────────────────────────────────────────────────────────

def train_random_forest(X_train, y_train):
    print("\n=== Training Random Forest baseline ===")
    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=2,
        n_jobs=-1,
        random_state=42,
        class_weight="balanced",
    )

    # 5-fold CV on training data only (as per proposal)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_results = cross_validate(
        rf, X_train, y_train, cv=cv,
        scoring=["f1", "recall", "precision", "roc_auc"],
        n_jobs=-1,
    )
    print("  CV results (train partition):")
    for metric, scores in cv_results.items():
        if metric.startswith("test_"):
            print(f"    {metric[5:]:12s}: {scores.mean():.4f} ± {scores.std():.4f}")

    # Save CV results
    cv_summary = {k: {"mean": float(v.mean()), "std": float(v.std())}
                  for k, v in cv_results.items() if k.startswith("test_")}
    with open(os.path.join(MODEL_DIR, "rf_cv_results.json"), "w") as f:
        json.dump(cv_summary, f, indent=2)

    # Final fit on full training set
    rf.fit(X_train, y_train)
    joblib.dump(rf, os.path.join(MODEL_DIR, "rf_baseline.joblib"))
    print("  Saved models/rf_baseline.joblib")
    return rf


# ── LSTM ──────────────────────────────────────────────────────────────────────

def build_lstm(timesteps: int, n_features: int) -> tf.keras.Model:
    model = tf.keras.Sequential([
        layers.Input(shape=(timesteps, n_features)),
        layers.LSTM(64, return_sequences=True),
        layers.Dropout(0.3),
        layers.LSTM(32),
        layers.Dropout(0.3),
        layers.Dense(16, activation="relu"),
        layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="binary_crossentropy",
        metrics=[
            "accuracy",
            tf.keras.metrics.Precision(name="precision"),
            tf.keras.metrics.Recall(name="recall"),
            tf.keras.metrics.AUC(name="auc"),
        ],
    )
    return model


def train_lstm(X_train, y_train, X_val, y_val):
    print("\n=== Training LSTM model ===")
    timesteps, n_features = X_train.shape[1], X_train.shape[2]
    print(f"  Input shape: ({timesteps}, {n_features})")

    classes = np.unique(y_train)
    weights = compute_class_weight("balanced", classes=classes, y=y_train)
    class_weight = dict(zip(classes.astype(int), weights))
    print(f"  Class weights: {class_weight}")

    model = build_lstm(timesteps, n_features)
    model.summary()

    cb = [
        callbacks.EarlyStopping(monitor="val_auc", patience=5,
                                restore_best_weights=True, mode="max"),
        callbacks.ModelCheckpoint(os.path.join(MODEL_DIR, "best_model.keras"),
                                  monitor="val_auc", save_best_only=True, mode="max"),
        callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5,
                                    patience=3, min_lr=1e-6),
    ]

    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=50,
        batch_size=256,
        class_weight=class_weight,
        callbacks=cb,
        verbose=1,
    )

    hist_path = os.path.join(MODEL_DIR, "history.json")
    with open(hist_path, "w") as f:
        json.dump({k: [float(v) for v in vals]
                   for k, vals in history.history.items()}, f, indent=2)
    print(f"  Saved models/best_model.keras + history.json")
    return model


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    d = load_splits()

    # Random Forest (flat features)
    train_random_forest(d["X_rf_train"], d["y_train"])

    # LSTM (sequential features)
    train_lstm(d["X_train"], d["y_train"], d["X_val"], d["y_val"])

    print("\nAll models trained.")
