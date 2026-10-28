#!/usr/bin/env bash
# MPC Tape Echo - build the skin and render every page offline (no device needed).
# The preview is rendered with the same shadow_art the device uses, so knob/toggle names and
# label_scale look exactly like on the MPC. Use it to try sizes before deploying.
#
#   vst/preview.sh        -> docs/ui-preview/page_0..N.png (+ mode variants for the mode panels)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"          # .../vst
PROJECT="$(cd "$HERE/.." && pwd)"              # the port (contains docs/, vst/)
MV="${MPC_VST_PLUGINS:-$(cd "$(dirname "$0")/../../mpc-vst-plugins" 2>/dev/null && pwd || echo "")}"
[ -n "$MV" ] || { echo "set MPC_VST_PLUGINS to the mpc-vst-plugins checkout" >&2; exit 2; }
FOLDER="LarryDaimond - VST - MPC Tape Echo"

# Translate a path under the workspace to the prefix the Docker daemon sees: set MPC_VST_WORKSPACE to the
# directory holding this port and the framework, MPC_VST_HOST_ROOT to how the daemon sees it (both empty
# when docker runs on this machine).
WORKSPACE="${MPC_VST_WORKSPACE:-$(cd "$MV/.." 2>/dev/null && pwd)}"
HOST_ROOT="${MPC_VST_HOST_ROOT:-}"
host() { case "$1" in "$WORKSPACE"/*) printf '%s%s' "$HOST_ROOT" "${1#"$WORKSPACE"}" ;; *) printf '%s' "$1" ;; esac; }

echo "== build skin =="
"$(host "$MV")/tools/build_port.sh" "$(host "$HERE")/vst.json" >/dev/null

mkdir -p "$PROJECT/docs/ui-preview"
echo "== render pages -> docs/ui-preview/page_*.png =="
docker run --rm -v "$(host "$MV")":/mv:ro -v "$(host "$PROJECT")":/w -w /w python:3.11-slim sh -c '
  pip install -q --no-warn-script-location Pillow >/dev/null 2>&1
  python3 /mv/tools/studio.py preview "/w/vst/build/skin/'"$FOLDER"'/Plugin Skins" -o "/w/docs/ui-preview/page_%d.png"
'
echo "done."
