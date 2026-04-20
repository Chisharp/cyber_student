"""
Step 4: Evaluate LSTM and Random Forest on the sealed test set.

Produces:
  - Classification reports for both models
  - Head-to-head metric comparison table
  - McNemar's test for statistical significance
  - Inference latency comparison
  - Confusion matrices, ROC curves, training curves (LSTM)
  - SHAP summary plots for both models

All plots saved to plots/
"""

import numpy as np
import json
import os
import time
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
import tensorflow as tf
from scipy.stats import chi2_contingency
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, roc_curve, f1_score,
    precision_score, recall_score,
)
import shap

SEQ_DIR   = "data/sequences"
MODEL_DIR = "models"
PLOT_DIR  = "plots"
os.makedirs(PLOT_DIR, exist_ok=True)

THRESHOLD = 0.5


# ── loaders ──────────────────────────────────────────────────────────────────

def load_data():
    X_test    = np.load(os.path.join(SEQ_DIR, "X_test.npy"))
    y_test    = np.load(os.path.join(SEQ_DIR, "y_test.npy"))
    X_rf_test = np.load(os.path.join(SEQ_DIR, "X_rf_test.npy"))
    return X_test, y_test, X_rf_test


def load_feature_names() -> list:
    path = os.path.join(SEQ_DIR, "sequence_features.txt")
    if os.path.exists(path):
        with open(path) as fh:
            return [l.strip() for l in fh if l.strip()]
    return [f"f{i}" for i in range(100)]


# ── metrics ──────────────────────────────────────────────────────────────────

def evaluate_model(y_true, y_pred, y_prob, name: str) -> dict:
    print(f"\n{'='*50}")
    print(f"  {name}")
    print('='*50)
    print(classification_report(y_true, y_pred, target_names=["Benign", "Attack"]))
    return {
        "f1":        f1_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred),
        "recall":    recall_score(y_true, y_pred),
        "roc_auc":   roc_auc_score(y_true, y_prob),
    }


def mcnemar_test(y_true, pred_lstm, pred_rf):
    """
    McNemar's test: are the error patterns of LSTM and RF significantly different?
    Contingency table counts cases where one model is right and the other wrong.
    """
    both_correct   = np.sum((pred_lstm == y_true) & (pred_rf == y_true))
    lstm_only      = np.sum((pred_lstm == y_true) & (pred_rf != y_true))
    rf_only        = np.sum((pred_lstm != y_true) & (pred_rf == y_true))
    both_wrong     = np.sum((pred_lstm != y_true) & (pred_rf != y_true))

    table = np.array([[both_correct, lstm_only],
                      [rf_only,      both_wrong]])
    chi2, p, _, _ = chi2_contingency(table)
    print(f"\nMcNemar's test: chi2={chi2:.4f}  p={p:.4f}")
    if p < 0.05:
        print("  → Statistically significant difference (p < 0.05)")
    else:
        print("  → No statistically significant difference (p ≥ 0.05)")
    return chi2, p


def measure_latency(model, X, model_type: str, n_runs=5) -> float:
    """Average inference time per sample in milliseconds."""
    times = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        if model_type == "lstm":
            model.predict(X, batch_size=256, verbose=0)
        else:
            model.predict(X)
        times.append(time.perf_counter() - t0)
    ms_per_sample = (np.mean(times) / len(X)) * 1000
    print(f"  {model_type.upper()} latency: {ms_per_sample:.4f} ms/sample")
    return ms_per_sample


# ── plots ─────────────────────────────────────────────────────────────────────

def plot_confusion_matrix(y_true, y_pred, title: str, filename: str):
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(5, 4))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=["Benign", "Attack"],
                yticklabels=["Benign", "Attack"])
    plt.ylabel("Actual"); plt.xlabel("Predicted"); plt.title(title)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, filename), dpi=150)
    plt.close()
    print(f"Saved plots/{filename}")


def plot_roc_comparison(y_true, probs: dict):
    plt.figure(figsize=(6, 5))
    for name, prob in probs.items():
        fpr, tpr, _ = roc_curve(y_true, prob)
        auc = roc_auc_score(y_true, prob)
        plt.plot(fpr, tpr, label=f"{name} (AUC={auc:.4f})")
    plt.plot([0, 1], [0, 1], "k--")
    plt.xlabel("False Positive Rate"); plt.ylabel("True Positive Rate")
    plt.title("ROC Curve Comparison: LSTM vs Random Forest")
    plt.legend(); plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "roc_comparison.png"), dpi=150)
    plt.close()
    print("Saved plots/roc_comparison.png")


def plot_metric_comparison(lstm_metrics: dict, rf_metrics: dict):
    metrics = list(lstm_metrics.keys())
    x = np.arange(len(metrics))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - width/2, [lstm_metrics[m] for m in metrics], width, label="LSTM")
    ax.bar(x + width/2, [rf_metrics[m]   for m in metrics], width, label="Random Forest")
    ax.set_xticks(x); ax.set_xticklabels(metrics)
    ax.set_ylim(0, 1.05); ax.set_ylabel("Score")
    ax.set_title("LSTM vs Random Forest — Test Set Metrics")
    ax.legend(); plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "metric_comparison.png"), dpi=150)
    plt.close()
    print("Saved plots/metric_comparison.png")


def plot_training_curves(history: dict):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].plot(history["loss"], label="train"); axes[0].plot(history["val_loss"], label="val")
    axes[0].set_title("Loss"); axes[0].legend()
    axes[1].plot(history["auc"], label="train"); axes[1].plot(history["val_auc"], label="val")
    axes[1].set_title("AUC"); axes[1].legend()
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "training_curves.png"), dpi=150)
    plt.close()
    print("Saved plots/training_curves.png")


# ── SHAP ──────────────────────────────────────────────────────────────────────

def shap_random_forest(rf_model, X_test_flat, feature_names: list):
    print("\nComputing SHAP values for Random Forest...")
    # TreeExplainer is exact and fast for RF
    explainer = shap.TreeExplainer(rf_model)
    sample = X_test_flat[:500]   # SHAP on a representative sample
    shap_values = explainer.shap_values(sample)

    # shap_values is a list [class0, class1] for binary RF
    sv = shap_values[1] if isinstance(shap_values, list) else shap_values

    plt.figure()
    shap.summary_plot(sv, sample, feature_names=feature_names,
                      show=False, plot_type="bar")
    plt.title("SHAP Feature Importance — Random Forest")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "shap_rf_bar.png"), dpi=150, bbox_inches="tight")
    plt.close()

    plt.figure()
    shap.summary_plot(sv, sample, feature_names=feature_names, show=False)
    plt.title("SHAP Beeswarm — Random Forest")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "shap_rf_beeswarm.png"), dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved SHAP plots for RF")


def shap_lstm(lstm_model, X_test_seq, feature_names: list):
    print("\nComputing SHAP values for LSTM (GradientExplainer)...")
    # GradientExplainer works with Keras models
    background = X_test_seq[:100]
    sample     = X_test_seq[100:200]

    explainer   = shap.GradientExplainer(lstm_model, background)
    shap_values = explainer.shap_values(sample)

    # shap_values shape: (samples, timesteps, features) — average over timesteps
    sv = np.array(shap_values).squeeze()
    if sv.ndim == 3:
        sv_mean = sv.mean(axis=1)   # (samples, features)
    else:
        sv_mean = sv

    plt.figure()
    shap.summary_plot(sv_mean, sample.mean(axis=1),
                      feature_names=feature_names, show=False, plot_type="bar")
    plt.title("SHAP Feature Importance — LSTM (avg over timesteps)")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "shap_lstm_bar.png"), dpi=150, bbox_inches="tight")
    plt.close()

    plt.figure()
    shap.summary_plot(sv_mean, sample.mean(axis=1),
                      feature_names=feature_names, show=False)
    plt.title("SHAP Beeswarm — LSTM")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "shap_lstm_beeswarm.png"), dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved SHAP plots for LSTM")


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    X_test, y_test, X_rf_test = load_data()
    feature_names = load_feature_names()

    # --- Load models ---
    lstm_model = tf.keras.models.load_model(os.path.join(MODEL_DIR, "best_model.keras"))
    rf_model   = joblib.load(os.path.join(MODEL_DIR, "rf_baseline.joblib"))

    # --- Predictions ---
    lstm_prob = lstm_model.predict(X_test, batch_size=256, verbose=1).flatten()
    lstm_pred = (lstm_prob >= THRESHOLD).astype(int)

    rf_prob   = rf_model.predict_proba(X_rf_test)[:, 1]
    rf_pred   = rf_model.predict(X_rf_test)

    # --- Metrics ---
    lstm_metrics = evaluate_model(y_test, lstm_pred, lstm_prob, "LSTM")
    rf_metrics   = evaluate_model(y_test, rf_pred,   rf_prob,   "Random Forest")

    # --- Statistical test ---
    chi2, p = mcnemar_test(y_test, lstm_pred, rf_pred)

    # --- Latency ---
    print("\nMeasuring inference latency...")
    lstm_lat = measure_latency(lstm_model, X_test,    "lstm")
    rf_lat   = measure_latency(rf_model,   X_rf_test, "rf")

    # --- Save summary ---
    summary = {
        "lstm":          lstm_metrics,
        "random_forest": rf_metrics,
        "mcnemar":       {"chi2": chi2, "p_value": p},
        "latency_ms_per_sample": {"lstm": lstm_lat, "rf": rf_lat},
    }
    with open(os.path.join(MODEL_DIR, "evaluation_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("\nSaved models/evaluation_summary.json")

    # --- Plots ---
    plot_confusion_matrix(y_test, lstm_pred, "Confusion Matrix — LSTM",          "cm_lstm.png")
    plot_confusion_matrix(y_test, rf_pred,   "Confusion Matrix — Random Forest", "cm_rf.png")
    plot_roc_comparison(y_test, {"LSTM": lstm_prob, "Random Forest": rf_prob})
    plot_metric_comparison(lstm_metrics, rf_metrics)

    with open(os.path.join(MODEL_DIR, "history.json")) as f:
        history = json.load(f)
    plot_training_curves(history)

    # --- SHAP ---
    shap_random_forest(rf_model, X_rf_test, feature_names)
    shap_lstm(lstm_model, X_test, feature_names)

    print("\nEvaluation complete.")
