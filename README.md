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

**Status (2026-10-28):** 1.2.0 ships three interfaces in one plugin, switchable from inside it. The engine is
vendored at v1.4.5 through the `adapters/schwung_fx` adapter, 22 parameters (21 engine controls plus the
interface selector), offline suites green, bench **WARN** (p99 ~22 %, same as 1.1.0). See `PORTING_NOTES.md`.

## Three interfaces, one plugin

Studio, Classic and Rack ship inside the plugin folder — no separate download, no reinstall:

| Interface | Look | Pages |
| --- | --- | --- |
| **Studio** (default) | display panel on top, parameter cards below (reference: 3dthc's Shapey) | TAPE · SYNC OUT |
| **Classic** | RE-202-inspired ivory faceplate | MAIN · TAPE · OUT |
| **Rack** | anodised graphite bays (reference: MagicStino's PulyTek) | PROGRAM · TAPE · TONE |

**INTERFACE** is on the TAPE page's ECHO/VERB card (Studio), the OUT page (Classic) and the SYNC/DIV bay
(Rack). MPC binds a skin when an instance is inserted and has no reload call, so the switch lands on the
next insert: pick, then remove the plugin instance and insert it again.

The three interfaces live under `Plugin Skins/{studio,classic,rack}/` and differ only in the files MPC reads
on insert (`TUI.json` and the Q-Link banks). Switching copies those two small JSON files — via a `.tmp` name
and a rename — and rewrites no image, so the instance that is playing is untouched. `Plugin Skins/ui.txt`
records the choice; a project or preset carrying an older value is corrected from disk on load, so a preset
can never flip the interface. `tools/make_skinset.py` builds that folder from three skin builds.

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
