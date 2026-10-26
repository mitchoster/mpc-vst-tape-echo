/* spaceecho_trim.cpp — port-local trim shell around the vendored Schwung shell.
 *
 * Why this exists: the engine (Tape Echo 2 / Dusk) publishes its record VU as the `out_level` key, and the
 * vendored upstream shell (`dsp/tape_echo_plugin.cpp`, byte-identical, GPL-3.0) answers it. A user-facing
 * calibration ("VU CAL", the set-screw of this port) therefore cannot live in that file — patching it would
 * break the "vendored copy is pristine" property that keeps a re-vendor a real diff.
 *
 * So this file *is* the module: it unity-includes the upstream shell with its entry point renamed (the file on
 * disk stays untouched), and exports `move_audio_fx_init_v2` itself, delegating everything and intercepting
 * only the trim:
 *   - set_param("vu_cal", <index|label>)  stores the trim (option list, labels must not start with a digit —
 *     the wrapper reads a digit-leading engine string as an option INDEX, see the skill's gotcha),
 *   - get_param("vu_cal")                 returns the label,
 *   - get_param("out_level")              returns the module's value scaled by the trim,
 *   - get_param/set_param("state")        carries the trim inside the module's state blob (the module ignores
 *     keys it does not know), so the setting survives save/reload.
 * Everything else goes straight through. Only read on the ~10 Hz display poll, so it costs nothing in audio.
 */
#define move_audio_fx_init_v2 spaceecho_inner_init
#include "tape_echo_plugin.cpp"
#undef move_audio_fx_init_v2

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

/* keep in step with the "vu_cal" options in vst/src/spaceecho_module.json (one entry per option) */
static const float      kCalPct[] = { 50.0f, 75.0f, 100.0f, 125.0f, 150.0f, 200.0f, 250.0f, 300.0f };
static const char *const kCalTxt[] = { "min 50 %", "low 75 %", "nom 100 %", "up 125 %",
                                       "plus 150 %", "x2 200 %", "max 250 %", "top 300 %" };
static const int kCalN = (int)(sizeof kCalPct / sizeof kCalPct[0]);
#define CAL_DEFAULT_IDX 2   /* 100 % */

static audio_fx_api_v2_t *inner;
static audio_fx_api_v2_t  trim_api;

typedef struct { void *inst; int cal; } trim_t;

static int cal_clamp_idx(int idx)
{
    if (idx < 0) idx = 0;
    if (idx >= kCalN) idx = kCalN - 1;
    return idx;
}

static int cal_from(const char *val)
{
    int idx = atoi(val);
    for (int i = 0; i < kCalN; i++)
        if (!strcmp(kCalTxt[i], val)) { idx = i; break; }
    return cal_clamp_idx(idx);
}

static int json_number(const char *json, const char *key, float *out)
{
    char pat[64];
    if (snprintf(pat, sizeof pat, "\"%s\"", key) >= (int)sizeof pat) return -1;
    const char *p = strstr(json, pat);
    if (!p) return -1;
    p += strlen(pat);
    while (*p == ' ' || *p == '\t') p++;
    if (*p != ':') return -1;
    p++;
    while (*p == ' ' || *p == '\t') p++;
    char *end = nullptr;
    const double v = strtod(p, &end);
    if (end == p) return -1;
    *out = (float)v;
    return 0;
}

static void *trim_create(const char *dir, const char *cfg)
{
    void *inst = inner->create_instance(dir, cfg);
    if (!inst) return NULL;
    trim_t *t = (trim_t *)calloc(1, sizeof *t);
    if (!t) { inner->destroy_instance(inst); return NULL; }
    t->inst = inst;
    t->cal = CAL_DEFAULT_IDX;
    return t;
}

static void trim_destroy(void *h) { trim_t *t = (trim_t *)h; inner->destroy_instance(t->inst); free(t); }
static void trim_process(void *h, int16_t *io, int frames) { inner->process_block(((trim_t *)h)->inst, io, frames); }
static void trim_midi(void *h, const uint8_t *m, int n, int src)
{
    trim_t *t = (trim_t *)h;
    if (inner->on_midi) inner->on_midi(t->inst, m, n, src);
}

static void trim_set_param(void *h, const char *k, const char *v)
{
    trim_t *t = (trim_t *)h;
    if (!strcmp(k, "vu_cal")) { t->cal = cal_from(v); return; }
    if (!strcmp(k, "state")) {                       /* our field rides along in the module's blob */
        float cal;
        if (json_number(v, "vu_cal", &cal) == 0) t->cal = cal_clamp_idx((int)lrintf(cal));
    }
    inner->set_param(t->inst, k, v);                 /* the module reads its own keys and ignores ours */
}

static int trim_get_param(void *h, const char *k, char *buf, int n)
{
    trim_t *t = (trim_t *)h;
    if (!strcmp(k, "vu_cal")) return snprintf(buf, (size_t)n, "%s", kCalTxt[t->cal]);
    if (!strcmp(k, "out_level")) {
        char b[32];
        if (inner->get_param(t->inst, "out_level", b, sizeof b) <= 0) return -1;
        return snprintf(buf, (size_t)n, "%.4f", atof(b) * kCalPct[t->cal] / 100.0f);
    }
    if (!strcmp(k, "state")) {                       /* append our field so it round-trips */
        char b[4096];
        if (inner->get_param(t->inst, "state", b, sizeof b) <= 0) return -1;
        size_t len = strlen(b);
        if (len && b[len - 1] == '}') b[--len] = 0;
        return snprintf(buf, (size_t)n, "%s,\"vu_cal\":%d}", b, t->cal);
    }
    return inner->get_param(t->inst, k, buf, n);
}

extern "C" audio_fx_api_v2_t *move_audio_fx_init_v2(const host_api_v1_t *host)
{
    inner = spaceecho_inner_init(host);
    if (!inner) return NULL;
    memset(&trim_api, 0, sizeof trim_api);
    trim_api.api_version      = AUDIO_FX_API_VERSION_2;
    trim_api.create_instance  = trim_create;
    trim_api.destroy_instance = trim_destroy;
    trim_api.process_block    = trim_process;
    trim_api.set_param        = trim_set_param;
    trim_api.get_param        = trim_get_param;
    trim_api.on_midi          = trim_midi;
    return &trim_api;
}
