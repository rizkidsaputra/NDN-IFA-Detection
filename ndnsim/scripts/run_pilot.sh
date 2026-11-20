#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
config=${1:-config/benign-pilot.json}
run_id=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["runId"])' "$config")
case "$run_id" in *[!a-zA-Z0-9_-]*|'') echo 'Invalid run ID' >&2; exit 2;; esac
output_label=${2:-$run_id}
case "$output_label" in *[!a-zA-Z0-9_-]*|'') echo 'Invalid output label' >&2; exit 2;; esac
out="$root/runs/$output_label"
if [ -e "$out" ]; then echo "Refusing to overwrite $out; choose a new runId in a copied config" >&2; exit 2; fi
bash ifa-pilot/scripts/apply_scheduler_fix.sh
cmp -s scenarios/benign-tree.cpp deps/ns-3/scratch/benign-tree.cc || cp scenarios/benign-tree.cpp deps/ns-3/scratch/benign-tree.cc
(cd deps/ns-3 && ./waf -j1 --targets=benign-tree) > "docs/scenario-build-$(date +%Y%m%dT%H%M%S).log" 2>&1
mkdir "$out"
cp "$config" "$out/config.json"
cp scenarios/benign-tree.cpp "$out/scenario.cpp"
cp scripts/validate_run.py "$out/validator.py"
sha256sum "$out/scenario.cpp" "$out/validator.py" "$out/config.json" > "$out/input-sha256.txt"
printf '%s\n' "./waf -j1 --targets=benign-tree --run \"benign-tree --config=$root/$config --out=$out\"" > "$out/command.txt"
date -Is > "$out/wall-start.txt"
set +e
(cd deps/ns-3 && /usr/bin/time -v ./waf -j1 --targets=benign-tree --run "benign-tree --config=$root/$config --out=$out") > "$out/simulator.log" 2> "$out/resources.txt"
rc=$?
set -e
echo "$rc" > "$out/exit-code.txt"
date -Is > "$out/wall-end.txt"
if [ "$rc" != 0 ]; then echo "Simulation failed; preserve run directory for audit" >&2; exit "$rc"; fi
python3 "$out/validator.py" --config "$out/config.json" --run "$out"
echo "Validated $out"
