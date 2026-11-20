# Research Status & Experiment Details

This document summarizes the experimental design, completed evaluation stages through **25 October 2026**, and the methodological boundaries for interpreting the results in this repository.

---

## 1. Research Questions

1. **RQ1 (Monitoring Delivery & Detection Reliability):** To what extent does a combined *strict non-preemptive priority + push-out admission* policy improve timely telemetry availability and centralized Interest Flooding Attack (IFA) detection reliability under congestion compared against *FIFO/tail-drop* queuing?
2. **RQ2 (Service Trade-offs):** What service cost does prioritizing monitoring traffic impose on legitimate traffic (*regular consumer completion* and *background payload delivery*), and what is the runtime inference cost of the centralized detector?

---

## 2. Network Parameters & Monitoring Protocol

All primary experiments run in **ndnSIM** on a 10-router tree topology (`R1`..`R10`) with 7 separate application endpoints (`C1`..`C3`, `A1`..`A2`, producer `P` at `R4`, and collector `M` at `R10`):

* **Link Capacity & Queuing:** Link `R8 -> R10` is configured as a 1 Mbps bottleneck (reverse direction `R10 -> R8` is 10 Mbps). All other links run at 10 Mbps with a 2 ms propagation delay and a 100-packet queue limit per direction. In-network caching (Content Store) is disabled (`cs_packets = 0`) to isolate forwarding and `PIT` behavior.
* **User Traffic & Background Load:**
  * Each simulation lasts 30 seconds.
  * Three regular consumers (`C1`..`C3`) each send 5 Interests/s during `t in [2, 25)` with a 512-byte Data payload (345 regular requests per run).
  * Background traffic between `P` and `R8` is generated at four rates (**100, 200, 300, and 1500 Hz**) so that monitoring reports from the six left-branch routers (`R1, R2, R3, R5, R6, R8`) share the `R8 -> R10` corridor with background Data packets.
  * Scenario **S2** runs benign + background traffic without an attacker; scenario **S3** adds an IFA flow from `A1` or `A2` targeting an unsatisfied prefix at `P`.
* **Sampling & Causal Cutoff:**
  * Router agents sample local NFD counters every 1 second (28 windows per run, `w = 1..28`).
  * Collector `M` polls each router starting at `w + 0.05 s` with a 1 ms stagger and a 1 s Interest lifetime (no retransmissions).
  * The decision cutoff is `d_w = w + 0.25 s`. Only report Data packets received by `M` on or before `d_w` may enter the detector input for window `w`. Late reports never revise past decisions.
* **Queue Policies Compared:**
  * **FIFO:** Single arrival-order queue with tail-drop when the 100-packet buffer is full.
  * **Priority + Push-Out:** Monitoring packets (`/report/...`) are placed in a non-preemptive priority class within the shared 100-packet buffer. If the buffer is full when a monitoring packet arrives, the last queued normal packet is evicted (*push-out*).

---

## 3. Experiment Cohorts

This repository contains code and artifacts from multiple distinct stages (metrics from different cohorts are kept separate and never pooled into one dataset):

| Stage | Scope | Repository Location |
|---|---|---|
| **1. Topology & IFA Mechanism Pilot** | 17-node/16-link plumbing verification, NFD counter vs. packet-trace audits, `ndn-cxx` scheduler fix, and 12 no-ML IFA/burst pilot conditions. | [`config/architecture/`](config/architecture/README.md), [`ndnsim/scenarios/ifa-tree.cpp`](ndnsim/scenarios/ifa-tree.cpp) |
| **2. Offline 10-Family Model Evaluation (384 Runs / 9,216 Rows)** | 96 workload families (48 test families = 12 per rate at 100/200/300/1500 Hz). Trains and freezes the scaler, thresholds, and checkpoints for 10 model families. | [`detector/`](detector/README.md), [`detector/dataset/`](detector/dataset/README.md), [`detector/pretrained/`](detector/pretrained/FREEZE.json) |
| **3. Fresh Online Evaluation (640 Runs / 15,360 Decisions)** | 16 new workload families (4 per rate at 100/200/300/1500 Hz) x `S2/S3` x `FIFO/Priority` x 10 frozen `seed 11` checkpoints. Live inference runs over a UNIX socket alongside `ndnSIM`. | [`ndnsim/scenarios/rq1-online-tree.cc`](ndnsim/scenarios/rq1-online-tree.cc), [`detector/detector.py`](detector/detector.py), [`configs/`](configs/plan.json), [`results/metrics-fresh-macro.csv`](results/metrics-fresh-macro.csv) |
| **4. Post-Hoc Online Burst Diagnosis (80 Runs / 1,920 Decisions)** | Paired *burst-on* vs. *burst-off* runs on a 1500 Hz pilot workload (`S2/S3` x `FIFO/Priority` x 10 models) to isolate the cause of post-attack false positives. | [`configs/cases/`](configs/families.json), [`results/burst-pairs.csv`](results/burst-pairs.csv) |

---

## 4. Key Findings & Integrity Verification

1. **Bitwise Input Parity & Audit Checks:**
   * All 720 online runs passed application and queue validation checks.
   * Independent offline reconstruction from `collector-received.csv` produced `5 x 10 x 13` tensors that are bitwise identical to the live detector inputs and matched all 17,280 classification decisions.
2. **Telemetry Recovery & Detection:**
   * At 100 Hz and 200 Hz, both FIFO and Priority delivered all reports intact, yielding identical detection behavior.
   * At 300 Hz and 1500 Hz, FIFO suffered report drops and delays across `R8 -> R10`, causing sharp drops in recall and F1 across all models.
   * On `S3 / 1500 Hz`, **Priority + push-out** raised on-time report delivery from **63.04% (706/1,120)** to **100% (1,120/1,120)** and restored timely episode detection (`4/4` episodes) for all 10 models.
3. **Online Inference Timing:**
   * Across all 17,280 online decisions, the maximum elapsed time from cutoff (`w + 250 ms`) to flushed decision output was **181.091 ms** (within the 250 ms target), with 0 IPC failures ([`results/COMPUTE-COST.csv`](results/COMPUTE-COST.csv)).
4. **Methodological Limitations:**
   * **Benign-Burst False Positives:** 100% report availability does not eliminate false positives when a legitimate traffic burst occurs under heavy congestion.
   * **No Attack Mitigation:** Priority + push-out protects monitoring packets (at a ~0.432% relative reduction in background Data delivery on `S3 / 1500 Hz`), while regular consumer completion remains near 32% during active attacks because no mitigation is applied.
   * **Sample Size & Topology:** The fresh online cohort uses `n = 4` independent families per rate and one `seed 11` checkpoint per model on a single 10-router tree. Repeating 10 models and 24 overlapping windows on the same workload does not create independent network samples.
