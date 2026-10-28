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

/* ---- interface switch (2026-10-28, same mechanism as MPC DJ FX 2 3.1.0) ----------------------------
 * All three interfaces ship inside the plugin folder as "Plugin Skins/<name>/" and differ only in the files
 * MPC reads when the plugin is inserted (TUI.json and the Q-Link banks); each interface's artwork lives in
 * its own subfolder. Switching copies those two small JSON files and rewrites no image, so the instance that
 * is running keeps everything it has loaded, and MPC - which binds a skin at insert and has no reload call -
 * shows the new interface on the next insert. Same contract as the DJ FX 2 port; keep them in step.
 */
static const char *const kSkinDirs[] = { "studio", "classic", "rack" };
static const char *const kSkinTxt[]  = { "Studio", "Classic", "Rack" };
#define SKIN_N ((int)(sizeof kSkinDirs / sizeof kSkinDirs[0]))
#define SKIN_DEFAULT_IDX 0

static int skin_clamp_idx(int idx)
{
    if (idx < 0) idx = 0;
    if (idx >= SKIN_N) idx = SKIN_N - 1;
    return idx;
}

static int skin_from(const char *val)   /* label or index, like cal_from */
{
    int idx = atoi(val);
    for (int i = 0; i < SKIN_N; i++)
        if (!strcmp(kSkinTxt[i], val)) { idx = i; break; }
    return skin_clamp_idx(idx);
}

static int copy_file(const char *from, const char *to)
{
    FILE *in = fopen(from, "rb");
    if (!in) return 0;
    FILE *out = fopen(to, "wb");
    if (!out) { fclose(in); return 0; }
    char buf[16384];
    size_t n;
    int ok = 1;
    while ((n = fread(buf, 1, sizeof buf, in)) > 0)
        if (fwrite(buf, 1, n, out) != n) { ok = 0; break; }
    if (ferror(in)) ok = 0;
    fclose(in);
    if (fclose(out) != 0) ok = 0;
    return ok;
}

/* keep in step with the "vu_cal" options in vst/src/spaceecho_module.json (one entry per option) */
static const float      kCalPct[] = { 50.0f, 75.0f, 100.0f, 125.0f, 150.0f, 200.0f, 250.0f, 300.0f };
static const char *const kCalTxt[] = { "min 50 %", "low 75 %", "nom 100 %", "up 125 %",
                                       "plus 150 %", "x2 200 %", "max 250 %", "top 300 %" };
static const int kCalN = (int)(sizeof kCalPct / sizeof kCalPct[0]);
#define CAL_DEFAULT_IDX 2   /* 100 % */

static audio_fx_api_v2_t *inner;
static audio_fx_api_v2_t  trim_api;

typedef struct { void *inst; int cal; int ui; char *dir; } trim_t;

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

static void skin_apply(trim_t *t, int idx)
{
    if (!t->dir || idx < 0 || idx >= SKIN_N) return;
    static const char *const files[] = { "TUI.json", "Q-Links.json", "Q-Links - 8by1.json" };
    char src[900], dst[800], tmp[900];
    int done = 0;
    for (int k = 0; k < (int)(sizeof files / sizeof files[0]); k++) {
        snprintf(src, sizeof src, "%s/Plugin Skins/%s/%s", t->dir, kSkinDirs[idx], files[k]);
        FILE *probe = fopen(src, "rb");
        if (!probe) continue;                       /* this interface has no such file */
        fclose(probe);
        snprintf(dst, sizeof dst, "%s/Plugin Skins/%s", t->dir, files[k]);
        snprintf(tmp, sizeof tmp, "%s.tmp", dst);
        if (copy_file(src, tmp) && rename(tmp, dst) == 0) done = 1;
        else remove(tmp);
    }
    if (!done) return;
    snprintf(dst, sizeof dst, "%s/Plugin Skins/ui.txt", t->dir);
    FILE *f = fopen(dst, "wb");
    if (f) { fprintf(f, "%s\n", kSkinDirs[idx]); fclose(f); }
}

/* the interface on disk is the truth: a project or preset must not rewrite another one */
static void skin_sync(trim_t *t)
{
    t->ui = SKIN_DEFAULT_IDX;
    if (!t->dir) return;
    char p[900], line[32] = { 0 };
    snprintf(p, sizeof p, "%s/Plugin Skins/ui.txt", t->dir);
    FILE *f = fopen(p, "rb");
    if (!f) return;
    if (!fgets(line, sizeof line, f)) line[0] = 0;
    fclose(f);
    line[strcspn(line, "\r\n")] = 0;
    for (int i = 0; i < SKIN_N; i++)
        if (!strcmp(line, kSkinDirs[i])) { t->ui = i; return; }
}

static void *trim_create(const char *dir, const char *cfg)
{
    void *inst = inner->create_instance(dir, cfg);
    if (!inst) return NULL;
    trim_t *t = (trim_t *)calloc(1, sizeof *t);
    if (!t) { inner->destroy_instance(inst); return NULL; }
    t->inst = inst;
    t->cal = CAL_DEFAULT_IDX;
    t->dir = dir ? strdup(dir) : nullptr;
    skin_sync(t);
    return t;
}

static void trim_destroy(void *h)
{
    trim_t *t = (trim_t *)h;
    inner->destroy_instance(t->inst);
    free(t->dir);
    free(t);
}
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
    if (!strcmp(k, "ui")) { t->ui = skin_from(v); skin_apply(t, t->ui); return; }
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
    if (!strcmp(k, "ui")) return snprintf(buf, (size_t)n, "%s", kSkinTxt[t->ui]);
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
