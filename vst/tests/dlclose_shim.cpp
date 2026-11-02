/* dlclose_shim.cpp — the two calls dlclose_test.cpp needs, exported unmangled so the host can
 * dlsym() them. It is the whole plugin lifecycle that matters here: attach (start the listener),
 * one publish, detach (which must stop and join the thread), then the host dlclose()s this file.
 * If anything still runs in here after dlclose, the process dies — which is exactly what MPC did
 * on the device on 2026-11-01. */
#include "../src/dsp/companion.h"

extern "C" int tc_attach() { return tec::attach(); }

extern "C" void tc_publish(int slot) {
  tec::Snapshot s;
  s.vu = 0.5f;
  s.peak = 0.6f;
  s.delay_ms = 190.0f;
  s.bpm = 120.0f;
  s.repeat_rate = 0.414888f;
  s.head_ms[0] = 69.3f;
  s.head_ms[1] = 132.5f;
  s.head_ms[2] = 191.4f;
  s.intensity = 0.44f;
  s.echo_volume = 1.0f;
  s.reverb_volume = 0.35f;
  s.mix = 0.5f;
  s.input_volume = 0.5f;
  s.bass = 0.0f;
  s.treble = 0.0f;
  s.wow_flutter = 0.0f;
  s.time_ms = 400.0f;
  s.tone_tilt = 0.0f;
  s.tape_wear = 0.25f;
  s.mode = 2;
  s.tempo_sync = 0;
  s.echo_rate_note = 5;
  s.tape_age = 1;
  s.input_send = 1;
  s.ping_pong = 0;
  s.stereo_width = 0;
  s.heads = 4;
  s.rev_head = 0;
  tec::publish(slot, s);
}

extern "C" void tc_detach(int slot) { tec::detach(slot); }
