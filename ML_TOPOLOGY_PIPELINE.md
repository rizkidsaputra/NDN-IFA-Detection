# Spatio-Temporal Feature Pipeline & ML Evaluation

This document describes how telemetry reports from the 10 NDN routers are assembled into causal input tensors and evaluated across 10 machine learning model families (both offline via [`detector/test.py`](detector/test.py) and live via [`detector/detector.py`](detector/detector.py)).

---

## 1. From Router Reports to Causal Tensors (`5 x 10 x 13`)

At every 1-second boundary (`w = 1..28`), each router (`R1`..`R10`) serializes 11 NFD measurements into an NDN Data payload:

```text
router;sequence;window_start;window_end;ready;delta_in_I;delta_out_I;delta_in_D;delta_out_D;delta_in_N;delta_out_N;delta_satisfied;delta_unsatisfied;delta_CS_hit;delta_CS_miss;PIT_entries
```

At decision cutoff `d_w = w + 0.25 s`, the detector process at collector `M` constructs a `10 routers x 13 channels` frame for window `w` ([`detector/detector.py`](detector/detector.py)):

1. **Channels 0..10 (11 Router Measurements):** Taken from the newest report for that router satisfying `sequence <= w` and `arrival <= d_w`. If the report for window `w` has not arrived by `d_w`, the detector carries forward the most recent eligible report (*Last Observation Carried Forward* / LOCF).
2. **Channel 11 (`current_mask`):** `1` if the report for window `w` arrived on time by `d_w`, otherwise `0`.
3. **Channel 12 (`sample_age`):** Time elapsed `d_w - window_end` since the carried sample's window closed (`0.25 s` when on time, or larger when stale).

Five consecutive frames (`w-4 .. w`) are stacked into a **`5 x 10 x 13`** input sample (starting at `w = 5`, yielding 24 decisions per 30-second run for `w = 5..28`).

### Leakage-Free Normalization (*Train-Only Scaling*)
Feature scaling is locked in [`detector/locked_preprocessing.py`](detector/locked_preprocessing.py) and [`configs/scaler.json`](configs/scaler.json):
* The 11 measurement channels (`0..10`) and `sample_age` (`12`) are transformed via `log1p(x)` and standardized (`(z - mean) / std`) using statistics computed **strictly from the training split**.
* `current_mask` (`11`) is kept as a binary `0/1` indicator.

---

## 2. Ten Model Families Evaluated

All model definitions reside in [`detector/models.py`](detector/models.py):

* **Tabular & Boosting Models (Flattened input `5 x 10 x 13 = 650` features):**
  1. `logistic` -- Logistic Regression
  2. `rf` -- Random Forest (*paper panel*)
  3. `histgb` -- Histogram-Based Gradient Boosting (`HistGradientBoostingClassifier`)
  4. `gbdt` -- Gradient Boosting Decision Trees (`GradientBoostingClassifier`, *paper panel*)
  5. `adaboost` -- AdaBoost
  6. `xgboost` -- XGBoost (*paper panel*)
  7. `lightgbm` -- LightGBM
  8. `catboost` -- CatBoost
* **Sequential & Graph-Temporal Models (Structured tensor `(batch, 5, 10, 13)`):**
  9. `gru` -- GRU-only (*paper panel*): flattens router features per time step (`10 x 13 = 130` features across 5 steps) and models temporal dynamics with a GRU.
  10. `graph` -- GraphSAGE+GRU (*paper panel*): applies GraphSAGE layers over the 10-router adjacency matrix ([`detector/dataset/graph.json`](detector/dataset/graph.json)) at each time step, aggregates node embeddings via `mean + max` readout pooling, and passes the 5-step sequence through a GRU.

### Hyperparameter Selection & Threshold Calibration
* Each model family was evaluated across 8 hyperparameter candidates ([`detector/presets.json`](detector/presets.json)) on the validation split.
* A single global classification threshold per checkpoint was selected **on the validation split only** to maximize mean validation recall across rates and policies subject to `all-S2` and `busy-S2` False Positive Rate (FPR) `<= 5%`.
* Once selected, weights, scaler, and thresholds were frozen ([`detector/pretrained/FREEZE.json`](detector/pretrained/FREEZE.json) and [`configs/registry.json`](configs/registry.json)) and never retuned on the test set or online runs.

---

## 3. Offline Evaluation Dataset (9,216 Rows)

The offline dataset in [`detector/dataset/`](detector/dataset/README.md) comes from the 384-run confirmation campaign (96 workload families x 4 runs per family: `S2/S3 x FIFO/Priority`, 24 decisions per run):

| Split | Families | Runs | Decision Rows (`5 x 10 x 13`) | NPZ File |
|---|---:|---:|---:|---|
| **Train** | 32 (8/rate) | 128 | 3,072 | [`detector/dataset/npz/train.npz`](detector/dataset/npz/train.npz) |
| **Validation** | 16 (4/rate) | 64 | 1,536 | [`detector/dataset/npz/validation.npz`](detector/dataset/npz/validation.npz) |
| **Test** | 48 (12/rate) | 192 | 4,608 | [`detector/dataset/npz/test.npz`](detector/dataset/npz/test.npz) |

Splits are strictly **family-disjoint** so overlapping sliding windows from the same workload never cross between train, validation, and test. Flattened CSV exports are also included in `detector/dataset/csv/`.

---

## 4. Offline Reproduction Commands

From the [`detector/`](detector/README.md) directory after installing [`requirements.txt`](requirements.txt):

```bash
cd detector

# 1. Verify SHA-256 checksums for all dataset, code, and checkpoint files
python verify_files.py

# 2. Evaluate the 10 frozen seed-11 checkpoints on the 4,608-row test set
python test.py --models-dir pretrained --out results/eval-original --reference reference/expected-original-predictions.csv

# 3. Retrain all models with the selected hyperparameters (seeds 11, 23, 37)
python train.py --models all --seeds 11,23,37 --search selected --out results/train-selected
python test.py --models-dir results/train-selected --out results/test-selected

# 4. Run the full 8-candidate validation grid search
python train.py --models all --seeds 11,23,37 --search grid --out results/train-grid
python test.py --models-dir results/train-grid --out results/test-grid
```

*(For archival notes on the earlier local v3+v4 evaluation and single-model replay module prior to the 10-model expansion, see [`config/architecture/README.md`](config/architecture/README.md)).*
