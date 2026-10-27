#!/usr/bin/env bash
# MPC Tape Echo - rebuild + deploy in one step (self-service skin/plugin updates).
#
#   vst/redeploy.sh                 build -> deploy to the MPC -> restart acvs
#   vst/redeploy.sh --no-restart    build + deploy only (no MPC restart)
#   DEVICE=<mpc ip> vst/redeploy.sh
#
# First install/registration (2026-10-11) went through `tools/release.py` + the packaged
# `install.sh` (stops MPC, backs up MPC.settings, adds the plugin-list entry). This script is for
# UPDATES to the already-registered plugin: same file= path, so no settings edit is needed. A skin
# change needs the restart; a .so-only change can instead remove+re-insert the plugin in MPC.
#
# Environment: the Docker daemon is the TrueNAS host daemon and mounts only host-visible paths, so
# every path handed to the framework's tools is mapped to the host path (MPC_VST_HOST_ROOT) .
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"     # .../vst
MV="${MPC_VST_PLUGINS:-$(cd "$(dirname "$0")/../../mpc-vst-plugins" 2>/dev/null && pwd || echo "")}"
[ -n "$MV" ] || { echo "set MPC_VST_PLUGINS to the mpc-vst-plugins checkout" >&2; exit 2; }
DEVICE="${DEVICE:?set DEVICE to the MPC IP address}"
FOLDER="MPCTE - VST - MPC Tape Echo"
SO="mpc_tape_echo.so"

# Translate a path under the workspace to the prefix the Docker daemon sees: set MPC_VST_WORKSPACE to the
# directory holding this port and the framework, MPC_VST_HOST_ROOT to how the daemon sees it (both empty
# when docker runs on this machine).
WORKSPACE="${MPC_VST_WORKSPACE:-$(cd "$MV/.." 2>/dev/null && pwd)}"
HOST_ROOT="${MPC_VST_HOST_ROOT:-}"
host() { case "$1" in "$WORKSPACE"/*) printf '%s%s' "$HOST_ROOT" "${1#"$WORKSPACE"}" ;; *) printf '%s' "$1" ;; esac; }

echo "== 1/3 build (skin + .so) =="
"$(host "$MV")/tools/build_port.sh" "$(host "$HERE")/vst.json"

SKIN="$HERE/build/skin/$FOLDER"
[ -d "$SKIN" ] || { echo "skin folder not found: $SKIN" >&2; exit 1; }
cp "$HERE/build/$SO" "$SKIN/$SO"

echo "== 2/3 deploy to $DEVICE =="
# tar (not scp): the folder name has spaces. Staged next to the target, then swapped in.
tar -C "$HERE/build/skin" -cf - "$FOLDER" | ssh -o StrictHostKeyChecking=no "root@$DEVICE" \
  "tar -C /sdcard/Synths -xf -"
ssh -o StrictHostKeyChecking=no "root@$DEVICE" \
  "echo -n 'device md5: '; md5sum '/sdcard/Synths/$FOLDER/$SO' | cut -d' ' -f1"
echo -n "local  md5: "; md5sum "$SKIN/$SO" | cut -d' ' -f1

echo "== 2b/3 presets -> device Insert Effects =="
# MPC lists an insert EFFECT's presets from 'MPC Documents/Plugin Presets/Insert Effects/<skin>/',
# one .xpl per preset with an absolute file= to the .so (the skin's own Presets/ is the instruments
# path). Generated here, not committed, so a param change cannot leave them stale.
PRESET_STAGE="$(mktemp -d)"
python3 "$HERE/gen_presets.py" --out-dir "$PRESET_STAGE" --so-path "/sdcard/Synths/$FOLDER/$SO" >/dev/null
ssh -o StrictHostKeyChecking=no "root@$DEVICE" "mkdir -p '/sdcard/MPC Documents/Plugin Presets/Insert Effects/$FOLDER'"
tar -C "$PRESET_STAGE" -cf - . | ssh -o StrictHostKeyChecking=no "root@$DEVICE" \
  "tar -C '/sdcard/MPC Documents/Plugin Presets/Insert Effects/$FOLDER' -xf -"
rm -rf "$PRESET_STAGE"
echo -n "device presets: "; ssh -o StrictHostKeyChecking=no "root@$DEVICE" \
  "ls '/sdcard/MPC Documents/Plugin Presets/Insert Effects/$FOLDER/'/*.xpl | wc -l"

if [ "${1:-}" = "--no-restart" ]; then
  echo "== 3/3 skipped restart (--no-restart); re-insert the plugin in MPC for a .so-only change =="
  exit 0
fi
echo "== 3/3 restart acvs (MPC) so the new skin loads =="
ssh -o StrictHostKeyChecking=no "root@$DEVICE" "systemctl restart acvs"
sleep 12
ssh -o StrictHostKeyChecking=no "root@$DEVICE" "echo -n 'acvs: '; systemctl is-active acvs"
echo "done. Re-insert the plugin if it lost its instance, then open its page."
