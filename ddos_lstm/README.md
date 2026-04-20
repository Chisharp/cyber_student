# LSTM-Based DDoS Detection — CIC IoT-DIAD 2023

Empirical comparison of LSTM vs Random Forest for binary DDoS detection
in telecom IoT traffic, using the CIC IoT-DIAD 2023 dataset.

Implements the methodology from the MSc dissertation proposal:
- RFE feature selection (step 1b)
- Identical feature subset for both models (fair comparison)
- 5-fold cross-validation on training partition only
- Sealed test set evaluation
- McNemar's statistical significance test
- SHAP explanations for both models

## Project structure

```
ddos_lstm/
├── 1_preprocess.py           # Load CSV, clean, scale, save
├── 1b_rfe_feature_selection.py  # RFE to select top-N features
├── 2_build_sequences.py      # Sliding-window sequences (LSTM) + flat arrays (RF)
├── 3_train.py                # Train RF baseline + LSTM model
├── 4_evaluate.py             # Metrics, McNemar test, SHAP, plots
├── 5_infer.py                # Inference on new flow data (lstm / rf / both)
├── ddos_lstm_colab.ipynb     # All-in-one Colab notebook
├── requirements.txt
└── data/                     # Created at runtime
    ├── ddos.csv              ← place your CIC IoT-DIAD 2023 CSV here
    ├── processed/
    └── sequences/
```

## Quick start

```bash
pip install -r requirements.txt

# 1. Place your CSV at data/ddos.csv, then run in order:
python 1_preprocess.py              # → data/processed/ddos_processed.csv
python 1b_rfe_feature_selection.py  # → data/processed/rfe_selected_features.txt
python 2_build_sequences.py         # → data/sequences/*.npy
python 3_train.py                   # → models/rf_baseline.joblib + best_model.keras
python 4_evaluate.py                # → plots/*.png + evaluation_summary.json
python 5_infer.py --input new.csv --model both
```

## Dataset

Download from UNB: https://www.unb.ca/cic/datasets/iiot-dataset-2023.html  
The label column should contain `BENIGN` and attack variant names
(e.g. `DDoS-SYN_Flood`, `DDoS-UDP_Flood`, `DDoS-ICMP_Flood`).

## Evaluation outputs

| File | Contents |
|---|---|
| `models/evaluation_summary.json` | F1, precision, recall, AUC, latency, McNemar p-value |
| `models/rf_cv_results.json` | 5-fold CV scores for RF on training data |
| `plots/roc_comparison.png` | LSTM vs RF ROC curves on same axes |
| `plots/metric_comparison.png` | Side-by-side bar chart of all metrics |
| `plots/cm_lstm.png` / `cm_rf.png` | Confusion matrices |
| `plots/shap_rf_bar.png` / `shap_rf_beeswarm.png` | SHAP for RF |
| `plots/shap_lstm_bar.png` / `shap_lstm_beeswarm.png` | SHAP for LSTM |
| `plots/training_curves.png` | LSTM loss + AUC over epochs |

## Model architecture

```
LSTM:
  Input (20 timesteps × N_rfe_features)
  → LSTM(64, return_sequences=True) → Dropout(0.3)
  → LSTM(32)                        → Dropout(0.3)
  → Dense(16, relu) → Dense(1, sigmoid)

Random Forest:
  300 trees, balanced class weights, 5-fold CV on training partition
```
