"""
Step 1b: Recursive Feature Elimination (RFE) for feature selection.

Uses a Random Forest estimator inside RFE to rank features by importance,
then saves the reduced feature subset for use in both the RF baseline and
the LSTM model (ensuring a fair comparison).

Outputs:
  data/processed/rfe_selected_features.txt  — top-N feature names
  data/processed/rfe_ranking.csv            — full ranking table
  plots/rfe_feature_importance.png          — bar chart

Usage:
    python 1b_rfe_feature_selection.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import RFE
from sklearn.model_selection import StratifiedShuffleSplit

PROCESSED_PATH = "data/processed/ddos_processed.csv"
OUTPUT_DIR     = "data/processed"
PLOT_DIR       = "plots"
os.makedirs(PLOT_DIR, exist_ok=True)

LABEL_COL   = "label_binary"
N_FEATURES  = 20          # target number of features to keep
RFE_SAMPLE  = 50_000      # rows to use for RFE (keeps runtime manageable)
RANDOM_SEED = 42


def run_rfe(df: pd.DataFrame, feature_cols: list, n_features: int):
    X = df[feature_cols].values
    y = df[LABEL_COL].values

    # Stratified subsample so class balance is preserved
    if len(df) > RFE_SAMPLE:
        sss = StratifiedShuffleSplit(n_splits=1, train_size=RFE_SAMPLE,
                                     random_state=RANDOM_SEED)
        idx, _ = next(sss.split(X, y))
        X, y = X[idx], y[idx]
        print(f"  Using stratified subsample of {RFE_SAMPLE} rows for RFE")

    estimator = RandomForestClassifier(
        n_estimators=100,
        n_jobs=-1,
        random_state=RANDOM_SEED,
        class_weight="balanced",
    )

    rfe = RFE(estimator=estimator, n_features_to_select=n_features, step=1)
    rfe.fit(X, y)

    ranking_df = pd.DataFrame({
        "feature": feature_cols,
        "rfe_rank": rfe.ranking_,
        "selected": rfe.support_,
    }).sort_values("rfe_rank")

    # Also capture feature importances from the fitted estimator
    importances = rfe.estimator_.feature_importances_
    # Map importances back to selected features
    selected_features = [f for f, s in zip(feature_cols, rfe.support_) if s]
    imp_df = pd.DataFrame({
        "feature": selected_features,
        "importance": importances,
    }).sort_values("importance", ascending=False)

    return ranking_df, imp_df, selected_features


def plot_importances(imp_df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(imp_df["feature"][::-1], imp_df["importance"][::-1], color="steelblue")
    ax.set_xlabel("Feature Importance (RF)")
    ax.set_title(f"Top {len(imp_df)} Features Selected by RFE")
    plt.tight_layout()
    path = os.path.join(PLOT_DIR, "rfe_feature_importance.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Saved {path}")


if __name__ == "__main__":
    print("Loading processed data...")
    df = pd.read_csv(PROCESSED_PATH)
    feature_cols = [c for c in df.columns if c not in ("label", LABEL_COL)]
    print(f"  Total features: {len(feature_cols)}  |  Rows: {len(df)}")

    print(f"\nRunning RFE (target = {N_FEATURES} features)...")
    ranking_df, imp_df, selected = run_rfe(df, feature_cols, N_FEATURES)

    # Save outputs
    ranking_df.to_csv(os.path.join(OUTPUT_DIR, "rfe_ranking.csv"), index=False)
    print(f"Saved rfe_ranking.csv")

    with open(os.path.join(OUTPUT_DIR, "rfe_selected_features.txt"), "w") as fh:
        fh.write("\n".join(selected))
    print(f"Saved rfe_selected_features.txt")

    print(f"\nSelected features ({len(selected)}):")
    for f in selected:
        print(f"  {f}")

    plot_importances(imp_df)
    print("\nRFE complete.")
