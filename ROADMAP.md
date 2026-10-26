# Roadmap

Three milestones. Each is done when the stated artifact exists, not when the work starts.

## 1. A signed-off device walkthrough

The plugin has been played on an MPC Live II, but not systematically.

- Every control position on all three tabs, touched and heard.
- All 12 modes switched through, including the reverb-only mode.
- The VU meter against a known input level; `VU_FULL` currently reads low (bar at ~2/24 on a chord),
  candidate 0.35–0.4.
- Every Q-Link page, including the second bank if a tab has one.
- Result recorded in `tested.json` with device, firmware and date, per the framework's format.

Done when `tested.json` names the device and firmware and the list above is ticked.

## 2. Release and catalog listing

- A release zip with `install.sh`, `uninstall.sh`, `INSTALL.md`, `SHA256SUMS`, built by the framework's
  `tools/release.py`, with the measured CPU numbers attached (`--bench`).
- `tools/catalog_check.py <zip> --catalog` reports no errors.
- A registry entry in `sd88me/mpc-vst-plugins` under `catalog/plugins/`.

Done when the plugin appears in the catalog with its bench verdict visible.

## 3. Firmware 3.10 and a second device generation

Everything here was measured on MPC OS 3.9.1.2.

- Install and play on 3.10; record what changed, if anything.
- If Gen2 devices are in reach, an aarch64 build and the same bench, recorded separately.

Done when the README says which firmware and which device generation were actually tested.

## Not planned

An "eco" mode. The measurements say it cannot reach the PASS threshold: bypassing the oversampler
entirely buys 0.8 pp and a single spring buys 1.5 pp, while the spring tank itself is 60 % of the load.
Reaching PASS means running the spring at a reduced internal rate, which changes the reverb tail this
plugin exists for. The numbers are in the README so the trade-off is visible instead of implied.
