#!/usr/bin/env bash
# Companion feed: the plugin's own HTTP listener and the page it serves. No device.
#   vst/tests/companion.sh
# Two runs: one with the listener on a test port (all endpoint checks), one with TEC_HTTP=0 to
# prove the switch really closes the socket (never leave a listener behind unintentionally).
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"   # .../vst
# The Docker daemon runs on the host and only sees host-visible paths: set
# MPC_VST_HOST_ROOT to how it sees this repo (empty when docker runs here).
WS="${MPC_VST_WORKSPACE:-$(git -C "$HERE" rev-parse --show-toplevel 2>/dev/null || echo "")}"
HOST_ROOT="${MPC_VST_HOST_ROOT:-}"
host() { case "$1" in
  "$WS")   printf '%s' "${HOST_ROOT:-$WS}" ;;
  "$WS"/*) printf '%s%s' "$HOST_ROOT" "${1#"$WS"}" ;;
  *)       printf '%s' "$1" ;;
esac; }

PORT="${TEC_TEST_PORT:-18101}"
OFF_PORT=$((PORT + 1))

# The page is generated into a .so string: a stale header would serve an old panel.
python3 "$HERE/web/embed.py" --check || exit 1

docker run --rm -e "TEC_HTTP_PORT=$PORT" -e "TEC_OFF_PORT=$OFF_PORT" \
  -v "$(host "$WS")":/w -w "/w${HERE#"$WS"}" gcc:12 bash -lc '
set -e
c++ -std=gnu++17 -O2 -Wall -Wextra -I. -Isrc -Isrc/ported/shared-dpf/dsp -o /tmp/tec_test \
  tests/companion_test.cpp src/dsp/spaceecho_trim.cpp src/dsp/companion.cpp \
  src/ported/core/TapeEchoDSP.cpp \
  -lm -lpthread 2>&1 | grep -E "error|Error" && exit 1 || true
/tmp/tec_test

# The switch: with TEC_HTTP=0 nothing may listen, even though an instance exists.
TEC_HTTP=0 TEC_HTTP_PORT=$TEC_OFF_PORT /tmp/tec_test --instance-only >/dev/null 2>&1 &
pid=$!
sleep 0.5
if /tmp/tec_test --probe $TEC_OFF_PORT; then
  echo "PASS: TEC_HTTP=0 opens no listener"
else
  echo "FAIL: TEC_HTTP=0 still opened a listener"
  kill $pid 2>/dev/null || true
  exit 1
fi
kill $pid 2>/dev/null || true; wait $pid 2>/dev/null || true

# The read-only switch: page and /state stay, writes are refused.
RO_PORT=$((TEC_OFF_PORT + 1))
TEC_HTTP_RW=0 TEC_HTTP_PORT=$RO_PORT /tmp/tec_test --rw-off $RO_PORT
'
