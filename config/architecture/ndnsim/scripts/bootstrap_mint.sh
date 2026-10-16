#!/usr/bin/env bash
# Run only in a new workspace containing this project's source/config/scripts/docs.
# Sudo authenticates interactively; no credential file/environment/command arguments.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
mkdir -p deps docs runs
if [ -e deps/ns-3 ]; then echo 'Existing ns-3: inspect and reuse manually; refusing to overwrite' >&2; exit 2; fi
sudo apt-get install -y build-essential git pkg-config python3 python3-setuptools time libboost-all-dev libssl-dev libsqlite3-dev
git clone https://github.com/named-data-ndnSIM/ns-3-dev.git deps/ns-3
git -C deps/ns-3 checkout --detach 1b3bab9b6dba5f1e616c0b286eb889e9ce3d5d59
git clone https://github.com/named-data-ndnSIM/ndnSIM.git deps/ns-3/src/ndnSIM
git -C deps/ns-3/src/ndnSIM checkout --detach 90d50396654dabad54b6979f2dc8fa929ade544c
git -C deps/ns-3/src/ndnSIM submodule update --init --recursive
git -C deps/ns-3 apply "$root/docs/ns3-compatibility.patch"
git -C deps/ns-3/src/ndnSIM/ndn-cxx apply "$root/docs/ndn-cxx-compatibility.patch"
cd deps/ns-3
./waf configure --disable-python --enable-examples --enable-modules=ndnSIM,point-to-point -d optimized
./waf -j2 --targets=ndn-simple
./waf -j2 --targets=ndn-simple --run=ndn-simple
