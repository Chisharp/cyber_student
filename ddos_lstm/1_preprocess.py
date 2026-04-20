"""
Step 1: Load and preprocess CIC IoT-DIAD 2023 CSV data.

Download from: https://www.unb.ca/cic/datasets/iiot-dataset-2023.html
Place the CSV file(s) in the data/ folder and update DATA_PATH below.

Outputs:
  data/processed/ddos_processed.csv   — cleaned, scaled, binary-labelled data
  data/processed/scaler_params.csv    — min/max per feature for inference
  data/processed/feature_names.txt    — ordered feature list
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import os

# --- Config ---
DATA_PATH  = "data/ddos.csv"   # update to your actual CSV filename(s)
OUTPUT_DIR = "data/processed"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Telecom-IoT relevant features from CIC IoT-DIAD 2023
# (Appendix 1 of the dissertation proposal)
FEATURES = [
    "flow_duration",
    "Header_Length",
    "Protocol Type",
    "Duration",
    "Rate",
    "Srate",
    "Drate",
    "fin_flag_number",
    "syn_flag_number",
    "rst_flag_number",
    "psh_flag_number",
    "ack_flag_number",
    "ece_flag_number",
    "cwr_flag_number",
    "ack_count",
    "syn_count",
    "fin_count",
    "urg_count",
    "rst_count",
    "HTTP",
    "HTTPS",
    "DNS",
    "Telnet",
    "SMTP",
    "SSH",
    "IRC",
    "TCP",
    "UDP",
    "DHCP",
    "ARP",
    "ICMP",
    "IPv",
    "LLC",
    "Tot sum",
    "Min",
    "Max",
    "AVG",
    "Std",
    "Tot size",
    "IAT",
    "Number",
    "Magnitue",
    "Radius",
    "Covariance",
    "Variance",
    "Weight",
]

LABEL_COL = "label"   # CIC IoT-DIAD 2023 uses lowercase 'label'


def load_and_clean(path: str):
    print(f"Loading {path} ...")
    df = pd.read_csv(path, low_memory=False)

    # Normalise column names: strip whitespace, lowercase
    df.columns = df.columns.str.strip()

    print(f"  Raw shape: {df.shape}")

    # Find label column (case-insensitive)
    label_match = [c for c in df.columns if c.lower() == "label"]
    if not label_match:
        raise ValueError(f"No 'label' column found. Columns: {list(df.columns)}")
    actual_label = label_match[0]
    if actual_label != LABEL_COL:
        df.rename(columns={actual_label: LABEL_COL}, inplace=True)

    print(f"  Label distribution:\n{df[LABEL_COL].value_counts()}\n")

    # Match available features (case-insensitive fallback)
    col_map = {c.lower(): c for c in df.columns}
    available = []
    for f in FEATURES:
        if f in df.columns:
            available.append(f)
        elif f.lower() in col_map:
            df.rename(columns={col_map[f.lower()]: f}, inplace=True)
            available.append(f)

    missing = set(FEATURES) - set(available)
    if missing:
        print(f"  Warning: {len(missing)} features not found, skipping: {missing}")

    df = df[available + [LABEL_COL]].copy()

    # Replace inf, drop NaN
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)

    print(f"  Clean shape: {df.shape}")
    return df, available


def encode_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Binary encode: BENIGN=0, all attack variants=1"""
    df["label_binary"] = (df[LABEL_COL].str.upper() != "BENIGN").astype(int)
    print(f"  Benign: {(df['label_binary']==0).sum()}  |  Attack: {(df['label_binary']==1).sum()}")
    return df


def scale_and_save(df: pd.DataFrame, features: list):
    scaler = MinMaxScaler()
    df[features] = scaler.fit_transform(df[features])

    out_path = os.path.join(OUTPUT_DIR, "ddos_processed.csv")
    df.to_csv(out_path, index=False)
    print(f"\nSaved processed data  -> {out_path}")

    scale_df = pd.DataFrame({
        "feature": features,
        "min": scaler.data_min_,
        "max": scaler.data_max_,
    })
    scale_df.to_csv(os.path.join(OUTPUT_DIR, "scaler_params.csv"), index=False)
    print("Saved scaler params   -> data/processed/scaler_params.csv")

    with open(os.path.join(OUTPUT_DIR, "feature_names.txt"), "w") as fh:
        fh.write("\n".join(features))
    print("Saved feature names   -> data/processed/feature_names.txt")


if __name__ == "__main__":
    df, features = load_and_clean(DATA_PATH)
    df = encode_labels(df)
    scale_and_save(df, features)
