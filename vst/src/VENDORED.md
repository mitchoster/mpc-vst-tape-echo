# Vendored engine source

Port of the **Tape Echo 2** DSP core into this MPC plugin's own repo. The DSP is the work
of **Dusk Audio**; the Schwung (`audio_fx_api_v2`) shell is by **athousanddetails**. Both are
GPL-3.0. This directory is a copy of the upstream at a pinned commit, with one documented,
behaviour-preserving local optimisation (see "Local changes" below).

| | |
|---|---|
| Upstream | `https://github.com/athousanddetails/schwung-tape-echo2` |
| Tag | **v1.4.5** |
| Commit | `10671072a6d02e9008c64136d840d4d2dda2d21b` (2026-09-03) |
| Licence | **GPL-3.0-only** (upstream `LICENSE`, sha256 `c53a65c2fd561c87eaabf1072ef5dcab8653042bc15308465f52413585eb6271`, copied to the port root) |
| Vendored on | 2026-10-10 |
| Core origin | Tape Echo 2 by Dusk Audio (`github.com/dusk-audio/dusk-audio-plugins`, GPL-3.0), vendored by the Schwung port under `ported/` |

## What is vendored (byte-identical to the tag)

Everything the build and the offline tests touch:

```
dsp/tape_echo_plugin.cpp                        dcc39d443c394116d6a48c4884acf6b2a653896c78a742616ad2483c41b8d331
dsp/te2_params.h                                add0b29d4122bf1e4e08c30ba727bc27f0b9fe08077188b9269186b80cfa43e4
host/audio_fx_api_v2.h                          bd66061432327f354ab51f508038ea1dbbfb751d254dbdad638e0353cd94bc4b
host/plugin_api_v1.h                            2c410cbc65202239d35dc0e6cd0cfa451be11d7693bf620ec6337c635358c646
ported/core/TapeEchoDSP.cpp                     7d18713eac5cb0933c64d5585475b3c16c7a2f514d0775fd24cac9dd97b79693  (upstream 433f412b…) *
ported/core/TapeEchoDSP.hpp                     381bb2d18b189fb9cedddec2f94bdb4ba3ce0de6ff56839ee8ec37a5516482db
ported/dpf-plugin/TapeEchoParams.hpp            4205771e575602840ea2a9a0300aceb16fe2619bcf129471aade7ed678211522
ported/shared-dpf/dsp/DuskDenormals.hpp         811e772338572238963239f26cecb15b902c868af08d6ca65c89df7008fbb2c7
ported/shared-dpf/dsp/DuskFilters.hpp           e418a80736a809b1064db4892de5ccb3e55d842f09f753a35f43d4260bf1df5a
ported/shared-dpf/dsp/DuskOversampler.hpp       93c0bb0c9a788e8cc65a2176e7192c9f10bcd868aa59e18b648bacc35bd23a7f
ported/shared-dpf/dsp/DuskSmoothed.hpp          00d705360a140fdc7939de91cef2cf5fecdcd682d88c42f896df97605d741be3
module.json                                     a3f6cc0e7c62ac838162ad7108b51b2bf57062b3fc70088c9cc07b19baa6cdc8
tests/test_dsp.cpp                              f50b1cfb040d18005f93e5ef074c23f8ba4231ab23a7d97312626c86af28a68f
tests/core_equivalence.cpp                      7341c7e173bf8a5befd83bd078d6b0b95d5281f6eabb7525f9680586a6d57f4b
```

`module.json` is kept so `tools/build_port.sh` (via `tools/params.py`) can derive the 19-parameter
`chain_params` list; the two `tests/` files are the upstream native tests. None of the three is
compiled into the plugin.

## Local changes

**One**, in `ported/core/TapeEchoDSP.cpp` (`SpringReverb::process`) — an optimisation that does
**not** change the output:

- **Interleaved spring dispersion.** The tank runs three independent spring waveguides, each a
  cascade of 24 biquads in each direction (144 biquad sections per sample). `SpringReverb::process`
  now steps all three springs through the same section index in one loop instead of calling
  `Spring::process` once per spring, so the CPU can overlap three dependency chains. `Spring::process`
  is kept as the reference implementation. **Behaviour-preserving:** a per-sample output checksum over
  3000 blocks is bit-identical to the upstream build, and `core_equivalence` still reports
  `ours == pristine == 371.540920397`. Device bench (`tools/bench.sh`): worst p99 23.9% → 23.1%
  (small; the tank is latency-heavy, not throughput-bound — see PORTING_NOTES "CPU").

Every other file above is byte-identical to `v1.4.5`. All remaining port-specific glue lives outside
this directory:

- the audio-FX adapter `adapters/schwung_fx/schwung_fx_engine.c` in the framework checkout, and
- `vst/vst.json` (build settings, identity).

A future re-vendor from a newer tag is a straight `diff` against this directory; `* ` above marks the
one file to re-apply.

## Not vendored (deliberate)

The upstream Move web UI and its support files are unused by this port (MPC gets its own
`layout.conf` skin and saves state through the framework's chunk mechanism):

- `src/ui_chain.js`, `src/web_ui.html`, `src/help.json`
- `tools/`, `scripts/`, `CMakeLists.txt`, `docs/`, `patches/`

`vst/tests/{run.sh,modes_render.cpp}` are **port-local** (not upstream): the harness that builds and
runs the vendored tests in a container, and the 12-mode / spring render check. `tools/loadtest.cpp`
and `tools/soak.cpp` are not vendored yet (not needed for Task 7).

## Version discrepancy (recorded, not fixed)

Upstream `src/module.json` declares `"version": "1.4.3"` while the tag and `release.json` say
**v1.4.5**. The content was pinned by the tag commit above, which is what matters; the port ships
its own version through `vst/vst.json`. Do not "correct" `module.json` — it must stay verbatim.

## Build notes (not source changes)

- Compiled with `-std=gnu++17` (`vst.json` `build.cflags`): the framework's default is `gnu++11`,
  which is fine for most of this code but `-std=gnu++17` matches the upstream CMake target.
- `-Isrc/ported/shared-dpf/dsp`: `TapeEchoDSP.hpp` includes `Dusk*.hpp` by bare name.
- `-fno-gnu-unique`: upstream's own `CMakeLists.txt` sets it so the core's C++17 inline variables do
  not mark the `.so` `NODELETE` (MPC's `dlclose` then cannot reuse a stale image across an update).
- `-O3 -ffast-math -fno-finite-math-only -fno-math-errno` (+ `-mfpu=neon-vfpv4 -ftree-vectorize` for
  the device): CPU trim. Upstream Dusk compiles its plugins with `-O3 -ffast-math`, so this matches the
  reference build rather than diverging from it; `-fno-finite-math-only` keeps NaN/Inf handling. Bench
  (`tools/bench.sh`): worst p99 23.9 % → 20.3 %, worst block 26.2 % → 21.0 %. It does change the `.so`'s
  low-order float results (FMA / reassociation) — the offline tests (`test_dsp`, `modes_render`) are green
  under these flags; the port's own test harnesses build their own binaries, so this does not affect them.
- Upstream links libstdc++ **statically** for the Ableton Move; this port links dynamically through
  the framework (the device has a recent enough libstdc++, as the other C++ ports prove).
