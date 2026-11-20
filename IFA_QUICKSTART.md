# Quick Start: ndnSIM Simulation & Detector Evaluation

This guide provides step-by-step commands to run:
1. **Offline ML Model Verification & Evaluation** (Windows or Linux, no simulator needed).
2. **ndnSIM Stack Build & Simulator Smoke Tests** (Ubuntu 24.04 / Linux Mint 22.x).
3. **Reference Package & Online Artifact Audits**.

---

## 1. Offline ML Evaluation (No ndnSIM Required)

Requires Python 3.11 or 3.12. The 9,216-row offline dataset and 10 frozen model checkpoints are bundled inside [`detector/`](detector/README.md).

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# Verify SHA-256 checksums of all bundled files
cd detector
python verify_files.py

# Evaluate the 10 frozen checkpoints on the 4,608-row test set
python test.py --models-dir pretrained --out results/test-check --reference reference/expected-original-predictions.csv
```

When successful, `verify_files.py` prints `PACKAGE_FILES_PASS`, and `test.py` writes `summary.csv`, `predictions.csv`, `metrics-per-family-seed.csv`, and `receipt.json` under `detector/results/test-check/`.

---

## 2. Building ndnSIM & Running Simulator Smoke Tests (Linux)

On Ubuntu 24.04 or Linux Mint 22.x, `bootstrap_mint.sh` installs system prerequisites, checks out `ns-3`, `ndnSIM`, `NFD`, and `ndn-cxx` at the pinned commits ([`ndnsim/docs/stack-lock.json`](ndnsim/docs/stack-lock.json)), applies the GCC 13 compatibility and `ndn-cxx` single-wakeup scheduler patches, and compiles the simulator:

```bash
cd config/architecture/ndnsim
bash scripts/bootstrap_mint.sh
```

Once built, run the two simulator smoke tests (benign baseline vs. light 50 Interest/s IFA):

```bash
cd ifa-pilot
bash scripts/run_ifa.sh config/ifa-base-00000-s1.json
bash scripts/run_ifa.sh config/ifa-atk1-00050-s1.json
```

### Expected Smoke-Test Output

| Validator Check | Baseline (`ifa-base-00000-s1`) | Light IFA (`ifa-atk1-00050-s1`) |
|---|---:|---:|
| `validation.json` status | `PASS` | `PASS` |
| Attack Interests reaching sink at `P` | 0 | 250 / 250 |
| Peak `PIT` entries at router `R1` | 1 | 51 |
| Regular consumer Data received (`C1`..`C3`) | 345 / 345 | 345 / 345 |
| Monitoring reports received on time at `M` | 280 / 280 | 280 / 280 |

Each run is written to `config/architecture/ndnsim/ifa-pilot/runs/<run-id>/`. The runner refuses to overwrite an existing run directory; pass a custom run label to repeat a run:

```bash
bash scripts/run_ifa.sh config/ifa-atk1-00050-s1.json test-run-2
```

---

## 3. Online Detection Scenario (`FIFO` vs. `Priority + Push-Out`)

The core files for the 720-run online campaign are located at:
* **ndnSIM C++ Scenario:** [`ndnsim/scenarios/rq1-online-tree.cc`](ndnsim/scenarios/rq1-online-tree.cc)
* **Live Detector Process (UNIX Datagram Socket):** [`detector/detector.py`](detector/detector.py)
* **Runner & Verifier:** [`detector/runner.py`](detector/runner.py) and [`detector/verify.py`](detector/verify.py)
* **Run Plan & Case Configs:** [`configs/plan.json`](configs/plan.json) and [`configs/cases/`](configs/families.json)
* **Summary Metrics & Compute Cost:** [`results/metrics-fresh-macro.csv`](results/metrics-fresh-macro.csv) and [`results/COMPUTE-COST.csv`](results/COMPUTE-COST.csv)

To verify the reference documentation and evidence checksums offline without running a simulation:

```bash
python config/architecture/scripts/verify_package.py
```
