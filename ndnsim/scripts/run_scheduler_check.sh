#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
bash "$root/scripts/apply_scheduler_fix.sh"
deps="$root/../deps/ns-3"
cmp -s "$root/checks/scheduler-regression.cpp" "$deps/scratch/scheduler-regression.cc" || cp "$root/checks/scheduler-regression.cpp" "$deps/scratch/scheduler-regression.cc"
cd "$deps"
./waf -j1 --targets=scheduler-regression
./waf --run-no-build scheduler-regression
