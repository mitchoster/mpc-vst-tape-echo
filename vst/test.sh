#!/usr/bin/env bash
# Offline x86 host test (ASan/UBSan) for this port; must print PASSED. No device needed.
#   vst/test.sh
# Uses the host gcc/g++ when present, else the gcc:12 Docker image. The Docker daemon runs on the
# host and mounts only host-visible paths, so translate workspace paths to the host alias first.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MV="${MPC_VST_PLUGINS:?set MPC_VST_PLUGINS to a checkout of sd88me/mpc-vst-plugins}"


MPC_VST_PLUGINS="$MV" "$MV"/tools/test_port.sh" "$HERE"/vst.json" "$@"
