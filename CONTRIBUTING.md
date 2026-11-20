# Contributing & Extending Experiments

This repository preserves frozen checkpoints, configurations, and audited summaries for reproducibility. When extending the codebase (for example, testing a new topology or queue policy):

1. **Keep Frozen Artifacts Intact:** Do not overwrite `detector/pretrained/`, `detector/dataset/`, `configs/registry.json`, or `results/`. Place new simulation scenarios, datasets, and trained checkpoints in a new directory or namespace.
2. **Maintain Causal Evaluation Rules:**
   - Detector inputs may only use monitoring reports that arrive at collector `M` on or before the decision cutoff (`w + 0.25 s`).
   - Fit feature scalers on the training split only, and calibrate thresholds on the validation split only.
   - Keep workload-family splits disjoint across train, validation, and test sets.
3. **Verify Before Committing:**
   - Run `python detector/verify_files.py` to confirm offline dataset/checkpoint integrity.
   - Run `python config/architecture/scripts/verify_package.py` to confirm reference lab package integrity.
   - Do not commit large raw packet traces, local build directories (`build/`, `.venv/`), host IP addresses, or credentials.
