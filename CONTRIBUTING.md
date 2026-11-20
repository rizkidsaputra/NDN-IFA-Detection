# Contributing & Future Work

Contributions, bug fixes, and extensions are welcome. If you plan to build on this codebase, below is a summary of current limitations, open research directions, and practical guidelines.

---

## Current Scope & Limitations

* **Single Topology:** All primary experiments use a controlled 10-router tree (`R1`..`R10`) with a single `1 Mbps` bottleneck (`R8 -> R10`), a single producer (`P`), and no multipath rerouting.
* **Combined Queue Intervention:** The priority policy combines strict non-preemptive priority scheduling and push-out admission; their individual effects have not yet been isolated.
* **Online Cohort Size:** The fresh online evaluation covers `n = 4` independent workload families per background rate and one `seed 11` checkpoint per model.
* **Detection Without Mitigation:** Prioritizing monitoring traffic restores detector visibility, not user service (~32% regular consumer completion under attack), and 100% on-time telemetry does not eliminate false positives during legitimate traffic bursts.
* **Simulated Timing:** Online runs use `ndnSIM` synchronized to wall-clock time on a laptop CPU (`2` numerical threads), rather than physical router hardware or hard real-time guarantees.

---

## Future Work & Open Directions

Areas where extensions or pull requests would be especially valuable:

1. **Larger & Multipath Topologies:** Extending the `ndnSIM` scenarios and ML graph pipeline to **DFN / DFN-like** or **Rocketfuel** topologies to test cross-topology generalization.
2. **Scheduling vs. Push-Out Ablation:** Separating strict priority scheduling from push-out buffer eviction to measure each mechanism's standalone impact.
3. **Closed-Loop Attack Mitigation:** Connecting detector alerts to rate-limiting or prefix-throttling mechanisms at routers to measure actual user-service recovery.
4. **Reducing Benign-Burst False Positives:** Improving features, temporal horizons, or architectures to better distinguish legitimate traffic bursts from IFA under heavy congestion.
5. **Broader Online Benchmarks:** Expanding evaluations with more independent workload families, multiple training seeds, and matched compute/tuning budgets.

---

## Practical Guidelines

1. **Organizing New Experiments:** To keep the published paper's baseline results easy to compare and reproduce, please place new simulation scenarios, datasets, or trained checkpoints in a new directory or branch rather than replacing the existing ones directly.
2. **Recommended Evaluation Practices:**
   * For online detection comparisons, restrict detector inputs to monitoring reports that arrive at collector `M` on or before the decision cutoff (`w + 0.25 s`).
   * Fit feature scalers on the training split only, and calibrate thresholds on the validation split only.
   * Keep workload-family splits disjoint across train, validation, and test sets to avoid overlapping-window leakage.
3. **Before Opening a PR:**
   * Run `python detector/verify_files.py` and `python config/architecture/scripts/verify_package.py` if you modified files inside `detector/` or `config/`.
   * Avoid committing large raw packet traces, local build/virtual-env directories (`build/`, `.venv/`), host IP addresses, or credentials.
