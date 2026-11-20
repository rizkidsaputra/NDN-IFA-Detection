#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
config=${1:?Usage: run_ifa.sh config/file.json [output-label]}
run_id=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["runId"])' "$config")
label=${2:-$run_id}
case "$run_id/$label" in *[!a-zA-Z0-9_/-]*|/|*/../*) echo 'Invalid ID' >&2; exit 2;; esac
case "$label" in */*|'') echo 'Invalid output label' >&2; exit 2;; esac
out="$root/runs/$label"
mkdir -p runs docs
if [ -e "$out" ]; then echo "Refusing to overwrite $out" >&2; exit 2; fi
deps="$root/../deps/ns-3"
jobs=${BUILD_JOBS:-1}
budget=${RUN_TIMEOUT_S:-180}
case "$jobs" in ''|*[!0-9]*|0) echo 'BUILD_JOBS must be a positive integer' >&2; exit 2;; esac
case "$budget" in ''|*[!0-9]*|0) echo 'RUN_TIMEOUT_S must be a positive integer' >&2; exit 2;; esac
bash scripts/apply_scheduler_fix.sh
cmp -s scenarios/ifa-tree.cpp "$deps/scratch/ifa-tree.cc" || cp scenarios/ifa-tree.cpp "$deps/scratch/ifa-tree.cc"
(cd "$deps" && ./waf -j"$jobs" --targets=ifa-tree) > "docs/build-$(date +%Y%m%dT%H%M%S).log" 2>&1
mkdir "$out"
cp "$config" "$out/config.json"
cp scenarios/ifa-tree.cpp "$out/scenario.cpp"
cp scripts/validate_ifa.py "$out/validator.py"
cp scripts/run_ifa.sh "$out/runner.sh"
cp docs/ndn-cxx-scheduler-single-wakeup.patch "$out/scheduler.patch"
python3 -c 'import json,sys; print(json.dumps({"build_jobs":int(sys.argv[1]),"machine_timeout_s":int(sys.argv[2]),"scheduler_patch":"single-wakeup","ndn_cxx_commit":"2b51e5796415b5d41fe268b35250b9453f16d3d6"},indent=2))' "$jobs" "$budget" > "$out/run-settings.json"
sha256sum "$out/scenario.cpp" "$out/validator.py" "$out/config.json" > "$out/input-sha256.txt"
printf '%s\n' "./waf --run-no-build \"ifa-tree --config=$root/$config --out=$out\" (machine timeout ${budget}s)" > "$out/command.txt"
date -Is > "$out/wall-start.txt"
set +e
(cd "$deps" && /usr/bin/time -v timeout "$budget" ./waf --run-no-build "ifa-tree --config=$root/$config --out=$out") > "$out/simulator.log" 2> "$out/resources.txt"
rc=$?
set -e
echo "$rc" > "$out/exit-code.txt"
date -Is > "$out/wall-end.txt"
if [ "$rc" != 0 ]; then echo "Simulation failed ($rc); evidence preserved" >&2; exit "$rc"; fi
python3 "$out/validator.py" --config "$out/config.json" --run "$out" > "$out/validation-stdout.txt"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); m=d["metrics"]; print(d["run_id"],d["status"],{k:m[k] for k in ["benign_data","report_status_counts","report_missing","attack_requests","attack_sink_received","queue_drops"]},"R1_PIT_peak",m["pit_by_node"]["R1"]["peak_entries"])' "$out/validation.json"
