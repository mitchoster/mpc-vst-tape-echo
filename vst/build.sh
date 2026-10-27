#!/usr/bin/env bash
# Build this port with the upstream mpc-vst-plugins toolchain.
#   vst/build.sh [extra args]
# Needs Docker (with QEMU for arm32v7). Set MPC_VST_PLUGINS to the framework checkout if it is
# not the default sibling.
#
# The Docker daemon runs on the host and mounts only host-visible paths, so translate this
# container's workspace paths to the host alias before calling the tools (MPC_VST_HOST_ROOT).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MV="${MPC_VST_PLUGINS:-$(cd "$(dirname "$0")/../../mpc-vst-plugins" 2>/dev/null && pwd || echo "")}"
[ -n "$MV" ] || { echo "set MPC_VST_PLUGINS to the mpc-vst-plugins checkout" >&2; exit 2; }

# Translate a path under the workspace to the prefix the Docker daemon sees: set MPC_VST_WORKSPACE to the
# directory holding this port and the framework, MPC_VST_HOST_ROOT to how the daemon sees it (both empty
# when docker runs on this machine).
WORKSPACE="${MPC_VST_WORKSPACE:-$(cd "$MV/.." 2>/dev/null && pwd)}"
HOST_ROOT="${MPC_VST_HOST_ROOT:-}"
host() { case "$1" in "$WORKSPACE"/*) printf '%s%s' "$HOST_ROOT" "${1#"$WORKSPACE"}" ;; *) printf '%s' "$1" ;; esac; }

"$(host "$MV")/tools/build_port.sh" "$(host "$HERE")/vst.json" "$@"
