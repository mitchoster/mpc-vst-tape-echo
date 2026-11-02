/* companion.h — the read/write feed behind the companion page (phone/tablet).
 *
 * Why this exists: MPC draws a plugin's screen from pre-rendered PNGs and polled values, and
 * every moving widget costs it a redraw. A dense, touch-shaped panel therefore belongs in a
 * browser on the same network, served by the plugin itself.
 *
 * Contract:
 *   - attach() claims one of kSlots static slots and starts the HTTP thread on the first
 *     call; detach() releases the slot and, when it was the last one, STOPS AND JOINS the
 *     listener (a thread parked in poll() after dlclose() takes MPC down).
 *   - publish() is called from the audio thread: stores only, no allocation, no locks, no
 *     syscalls beyond clock_gettime.
 *   - The reader (HTTP thread) never dereferences an instance: all state lives in the static
 *     slots, so destroy_instance() can never race the server into freed memory.
 *   - Writes arrive as Commands over a ring the audio thread drains; the DSP state belongs to
 *     the render loop, so set_param() is never called from the HTTP thread.
 */
#ifndef TEC_COMPANION_H
#define TEC_COMPANION_H

namespace tec {

const int kSlots = 4;

struct Snapshot {
  /* meters */
  float vu;          /* record/echo level 0..1, the core's own record VU */
  float peak;
  /* what the tape is doing right now, not what the knobs say */
  float delay_ms;    /* leading-head time in effect (tempo sync included) */
  float bpm;         /* host tempo */
  float repeat_rate; /* the rate the motor actually runs at, 0..1 */
  float head_ms[3];  /* the three heads' times, derived from delay_ms */
  /* the published parameter surface, one field per key in the contract */
  float intensity;
  float echo_volume;
  float reverb_volume;
  float mix;
  float input_volume;
  float bass;
  float treble;
  float wow_flutter;
  float time_ms;
  float tone_tilt;
  float tape_wear;
  int   mode;            /* 0..11, index into the mode table (H1..Rev) */
  int   tempo_sync;      /* 0/1 */
  int   echo_rate_note;  /* 1..11 detent */
  int   tape_age;        /* 0 New, 1 Used, 2 Old */
  int   input_send;      /* 0/1, the dub switch */
  int   ping_pong;       /* 0/1 */
  int   stereo_width;    /* 0..100 */
  /* derived from the mode table, so the drawing cannot disagree with the sound */
  int   heads;           /* bit 0 = head 1 reads the tape in this mode */
  int   rev_head;        /* 1 = the spring is fed in this mode */
};

/* A parameter change asked for by the page. The HTTP thread only queues it; the audio thread
 * applies it in process_block, because set_param() touches the DSP state the render loop owns. */
struct Command {
  int idx;    /* index into the port's key table */
  float val;  /* real units: 0..1 for continuous, the option index for enums */
};

/* The parameter names, so the server can refuse an unknown key instead of guessing. The module
 * owns the list (it is the append-only contract); it hands it over once at load. */
void register_param_keys(const char *const *keys, int count);

/* Each instance has its OWN ring. A shared ring looked simpler and was wrong: the first audio
 * thread to drain advanced the tail past the other instance's entries and silently ate them. */
int  provide(int slot, const Command &c);        /* HTTP thread: 1 queued, 0 when full */
int  take_commands(int slot, Command *out, int max);   /* audio thread: what arrived */

int  attach();                         /* slot index, or -1 when all four are taken */
void detach(int slot);
void publish(int slot, const Snapshot &s);

/* Port the listener actually bound (0 = none). For tests and the docs. */
int  port();
void stop_server();                    /* host test / shutdown only */

}  // namespace tec

#endif
