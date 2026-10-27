# MPC Tape Echo (working name: Space Echo)

A native stereo **insert effect** for first-generation Akai MPC/Force standalone
devices: a faithful **Roland RE-201 Space Echo** emulation (three tape heads,
spring reverb, tape saturation, wow & flutter, 12 head/reverb modes).

- Engine: **Tape Echo 2** core by Dusk Audio, as the Schwung `audio_fx` module
  [`athousanddetails/schwung-tape-echo2`](https://github.com/athousanddetails/schwung-tape-echo2)
  @ **v1.4.5** (GPL-3.0).
- Built with the [`sd88me/mpc-vst-plugins`](https://github.com/sd88me/mpc-vst-plugins)
  framework (MIT), through a new audio-FX Schwung adapter.
- Spec: [`MPC_Space_Echo_Agent_Spec.md`](./MPC_Space_Echo_Agent_Spec.md)
- Plan / tasks: [`tasks/plan.md`](./tasks/plan.md), [`tasks/todo.md`](./tasks/todo.md)

**Status: Phase 2 in progress (2026-10-11).** Engine vendored at v1.4.5, the framework `adapters/schwung_fx` builds
an armhf `.so`, the 19-param contract is frozen (+ a display-only `vu` param for the live VU), offline suites are
green, and the skin (3 tabs, 12-mode selector, RE-202-inspired faceplate, live VU) is previewed in
`docs/ui-preview/`. **Deployed** to an MPC Live II (MPC OS 3.9.1.2), registered as an Effect, md5 verified; bench
**WARN** (p99 24.9 %, ~4× headroom) — device test pending. See `PORTING_NOTES.md`.

## Build & test levers

- `vst/build.sh` — armhf `.so` + params + skin (needs Docker).
- `vst/preview.sh` — render every skin page to `docs/ui-preview/` (offline).
- `vst/redeploy.sh` — build + deploy to the MPC (`--no-restart` to skip the restart).
- `vst/device_test.sh` — drive the device via the remote addin over an SSH tunnel (screenshot/tap/drag/MCP tools); see its header for the one-time addin setup.
- `vst/art/make_faceplate.py` / `vst/art/make_vu.py` — draw the `bg.png` faceplate / the VU steps.
- `vst/test.sh` — offline host test under ASan/UBSan (`tools/test_port.sh`), must print PASSED.
- `vst/tests/run.sh` — upstream native DSP tests + 12-mode/spring render check (offline, x86).

## Why this engine

Of the four sources first proposed, none was both licence-clean and a genuine
RE-201. `schwung-tape-echo2` is the upstream that `charlesvestal/schwung-space-delay`
v1.3.5 copies: framework-free C++ component core, GPL-3.0, and the framework
author already ships four `athousanddetails` Schwung ports (GPL-3.0-only).
See spec §3 for the full comparison.

## Licence

The port ships as **GPL-3.0-only** (the vendored core is GPL-3.0). The MIT
framework is GPL-compatible; the combined work is GPL-3.0.
