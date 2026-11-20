# Online confirmation and benign-burst diagnosis — 24 October 2026

Authorized by user after the online pilot. Written before any new run. Paper revisions remain on hold for user approval. This is simulated NDN running in wall-clock real time on Mint, not a physical network deployment.

## Frozen components

Reuse the ten selected LOCF seed11 checkpoints, thresholds, scaler, model implementation, collector-only input assembly and online binary of online-20261024, with exact hashes checked. No fitting, threshold changes, selection, early stopping based on accuracy or removal of failed/slow runs. One model per simulation, two numerical threads, sequential runs. Keep prior results and failed attempts untouched.

Input cutoff window+.25s, history5x10x13, 24 decisions/run, duration30s. Output target cutoff+250ms, simulator lag>100ms flagged. Record real monotonic emission/flush, cold start separately. Priority is scheduling plus push-out. No network mitigation. The inherited validator's 'no detector/ML' scope refers to its network checks, not the external Python detector.

## Stage A: post-hoc mechanism diagnosis, 80 runs

Reuse the observed pilot1500 workload (seed102490002, attack8–11s, A1,100Hz, background5–19s, burst C3/100Hz/18–22s). Rerun BOTH burst-on and burst-off, each S2/S3 x FIFO/Priority x10 models =80runs. The only semantic configuration change within burst pairs is removal of flow B1. Keep background request times, attack, seed and model identical. Burst-on is rerun rather than timing compared with an old session. This is a controlled diagnostic chosen after seeing the pilot, not an independent confirmation. It tests the total effect of enabling that burst in this simulator; it does not isolate individual input features or explain all false alarms.

## Stage B: fresh bounded online expansion, 640 runs

Four independent fresh workload draws at each background100/200/300/1500Hz, sixteen families total, each S2/S3 x FIFO/Priority x10 models. No reuse of old train/validation/test workloads. Seeds103240001..103240016 produce schedules before execution. Attack onset8–16s, duration3/5/7s, intensity25/50/100Hz, attacker A1/A2; background starts3–7s and lasts14–18s with fixed randomized request times. Per rate, exactly two burst-on and two burst-off draws (assignment chosen before execution); burst C1/C3,20/50/100Hz,2/4s starting8–18s. Burst metadata retained even if flow absent.

Within a family, scenario/policy/model comparisons share the generated schedule. Across rates the families differ: between-rate differences are descriptive, not isolated causal rate effects. Stage B burst-on/off groups are different families, not matched burst interventions. Stage A supplies the matched contrast. n4/rate remains small and one model seed is used. Model repeats and overlapping windows are not independent workloads. No universal winner or robustness guarantee.

## Order, gates and analysis

Deterministically randomize case order within each stage and model order per case; Stage A first. Preflight verifies registry/scaler/binary, generated pair contracts and source/config hashes. Run causal frame fixtures and single-vs-batch all10 models; smoke two runs (diagnostic burst-off1500 HistGB and fresh200 RF). Smoke is integrity-only and excluded from720run metrics. Preserve and stop on integrity/process failure, do not silently retry. Real deadline misses are measurements, not exclusions or integrity failures.

After execution, independently reconstruct all inputs from collector files and replay frozen checkpoint scores; audit raw packet/queue contracts, all event/clock/alarm files, frozen hashes and between-model trajectory parity. A parity difference is disclosed, not filtered. Compare online and offline on the SAME observations; do not compare pilot vs old mean as the same test set.

Report per-family/policy/model TP/FP/FN/TN, positive F1, precision/recall, all-S2 and busy-S2 FPR, pre-onset/post-attack false alarms, timely detection before actual attack stop, actual latency/deadline misses, telemetry completeness and service metrics. Macro mean/range over four families and pooled window metrics are separate. No seed/window/model-repeat pseudoreplication or population confidence from n1 diagnostic. Show each Stage A burst-pair delta and decision disagreements, explicitly distinguishing score correctness from timeliness. Retain actual observations even if results worsen.

Seal full raw archive on Mint and a smaller review archive with collector/input/decision/config/audit evidence plus all checkpoint provenance. Automated report is provisional until readback/manual interpretation. No automatic paper edits, tuning, external messages or publication. Expected720runs/17280decisions plus2smoke; pilot runtime suggests7–9hours including audit, contingent on laptop availability.
