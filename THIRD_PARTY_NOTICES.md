# Third-party notices — MPC Tape Echo

This port is **GPL-3.0-only**. See `LICENSE` (the upstream GPL-3.0 text, unchanged).

## Bundled / linked third-party code

1. **Tape Echo 2 DSP core** — Dusk Audio, GPL-3.0.
   `github.com/dusk-audio/dusk-audio-plugins`. Vendored (unmodified) under
   `vst/src/ported/**` via the Schwung port below.

2. **schwung-tape-echo2** — the Schwung `audio_fx` module wrapper (shell + parameter surface) by
   `athousanddetails`, GPL-3.0. `github.com/athousanddetails/schwung-tape-echo2`, tag **v1.4.5**,
   commit `10671072a6d02e9008c64136d840d4d2dda2d21b`. Vendored verbatim under `vst/src/{dsp,host}`
   and `vst/src/module.json`; see `vst/src/VENDORED.md` for the exact file list and hashes.

3. **mpc-vst-plugins** framework — sd88me, MIT. Build/port framework
   (`github.com/sd88me/mpc-vst-plugins`); not vendored into this repo, checked out alongside and
   used through its `tools/build_port.sh` and the `adapters/schwung_fx` adapter. MIT is compatible
   with the GPL-3.0 combined work.

## Assets

No Akai stock skin art/JSON, ROMs, or OS files are included. Skin artwork produced for this port
(e.g. a generated background) is our own and is licensed with the port.
