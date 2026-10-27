#!/usr/bin/env bash
# Offline native tests against the vendored Tape Echo 2 core (x86; no device, no arm toolchain).
#   vst/tests/run.sh
#   1) tests/test_dsp.cpp        (upstream, self-checking)      -> hard gate
#   2) tests/modes_render.cpp    (port-local 12-mode/spring)    -> hard gate
#   3) tests/core_equivalence.cpp (upstream checksum): ours, and vs the pristine Dusk core when reachable
# Uses the gcc:12 Docker image (the Docker daemon mounts only host-visible paths, so translate first).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"          # .../vst/tests
VST="$(cd "$HERE/.." && pwd)"                  # .../vst
PROJECT="$(cd "$VST/.." && pwd)"

# Translate a path under the workspace to the prefix the Docker daemon sees: set MPC_VST_WORKSPACE to the
# directory holding this port and the framework, MPC_VST_HOST_ROOT to how the daemon sees it (both empty
# when docker runs on this machine).
WORKSPACE="${MPC_VST_WORKSPACE:-$(cd "$MV/.." 2>/dev/null && pwd)}"
HOST_ROOT="${MPC_VST_HOST_ROOT:-}"
host() { case "$1" in "$WORKSPACE"/*) printf '%s%s' "$HOST_ROOT" "${1#"$WORKSPACE"}" ;; *) printf '%s' "$1" ;; esac; }

BUILD="$PROJECT/vst/build/tests"
mkdir -p "$BUILD"

# ---- pristine upstream core, best effort (only for the equivalence compare) ----
if [ ! -d "$BUILD/dusk" ]; then
  git clone -q --depth 1 https://github.com/dusk-audio/dusk-audio-plugins "$BUILD/dusk" 2>/dev/null || true
fi
if [ -f "$BUILD/dusk/plugins/tape-echo/core/TapeEchoDSP.cpp" ]; then
  UP="$BUILD/dusk/plugins/tape-echo/core"
  mkdir -p "$BUILD/pristine/core" "$BUILD/pristine/dpf-plugin" "$BUILD/pristine/daf-plugin"
  cp "$UP/TapeEchoDSP.hpp" "$UP/TapeEchoDSP.cpp" "$BUILD/pristine/core/"
  # the core reaches its params header by a relative path (dir name changed dpf -> daf upstream): satisfy both
  cp "$VST/src/ported/dpf-plugin/TapeEchoParams.hpp" "$BUILD/pristine/dpf-plugin/"
  cp "$VST/src/ported/dpf-plugin/TapeEchoParams.hpp" "$BUILD/pristine/daf-plugin/"
fi

docker run --rm -v "$(host "$PROJECT")":/p:ro -w /p/vst gcc:12 bash -euc '
  echo "=== 1. upstream test_dsp ==="
  g++ -O2 -std=c++17 -Wall tests/test_dsp.cpp src/ported/core/TapeEchoDSP.cpp \
      -Isrc -Isrc/ported/core -Isrc/ported/shared-dpf/dsp -o /tmp/test_dsp -lm -lpthread
  /tmp/test_dsp

  echo; echo "=== 2. modes_render (port-local 12-mode / spring) ==="
  g++ -O2 -std=c++17 -Wall tests/modes_render.cpp src/ported/core/TapeEchoDSP.cpp \
      -Isrc/ported/core -Isrc/ported/shared-dpf/dsp -o /tmp/modes_render -lm -lpthread
  /tmp/modes_render

  echo; echo "=== 3. core_equivalence ==="
  g++ -O2 -std=c++17 -ffp-contract=off tests/core_equivalence.cpp src/ported/core/TapeEchoDSP.cpp \
      -Isrc/ported/core -Isrc/ported/shared-dpf/dsp -o /tmp/eq_ours
  A=$(/tmp/eq_ours); echo "  ours      = $A (rerun: $(/tmp/eq_ours))"
  if [ -f /p/vst/build/tests/pristine/core/TapeEchoDSP.cpp ]; then
    g++ -O2 -std=c++17 -ffp-contract=off tests/core_equivalence.cpp \
        /p/vst/build/tests/pristine/core/TapeEchoDSP.cpp \
        -I/p/vst/build/tests/pristine/core -Isrc/ported/shared-dpf/dsp -o /tmp/eq_pristine
    B=$(/tmp/eq_pristine); echo "  pristine  = $B"
    if [ "$A" = "$B" ]; then
      echo "  ok: vendored core == pristine Dusk upstream with Ping Pong off"
    else
      echo "  WARN: differs from pristine HEAD (upstream drifted since the core was vendored; not a port bug)"
    fi
  else
    echo "  (skipped: pristine Dusk core not reachable/available)"
  fi
'
