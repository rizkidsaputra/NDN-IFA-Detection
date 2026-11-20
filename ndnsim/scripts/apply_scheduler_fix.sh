#!/usr/bin/env bash
# Idempotent fix for the pinned ndnSIM scheduler adapter; no traffic changes.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cxx="$root/../deps/ns-3/src/ndnSIM/ndn-cxx"
patch="$root/docs/ndn-cxx-scheduler-single-wakeup.patch"
expected=2b51e5796415b5d41fe268b35250b9453f16d3d6
if [ "$(git -C "$cxx" rev-parse HEAD)" != "$expected" ]; then
  echo 'Unexpected ndn-cxx commit; inspect before applying the scheduler patch.' >&2
  exit 2
fi
if git -C "$cxx" apply --reverse --check "$patch" 2>/dev/null; then
  echo 'Scheduler single-wakeup patch already applied.'
elif git -C "$cxx" apply --check "$patch"; then
  git -C "$cxx" apply "$patch"
  echo 'Applied scheduler single-wakeup patch.'
else
  echo 'Scheduler differs from the pinned source; no automatic overwrite.' >&2
  exit 2
fi
