#!/usr/bin/env python3
"""Ship named MPC presets (.xpl) for MPC Tape Echo, like MPC Dub Station's gen_presets.py.

MPC reads an insert EFFECT's presets from `MPC Documents/Plugin Presets/Insert Effects/
<vendor> - VST - <name>/` (one .xpl per preset); the skin's own `Presets/` is the
instruments path. An .xpl is MPC's <pluginstate>: a <PLUGIN .../> description, a <preset>
name and a <state> holding the wrapper chunk (= get_param("state") + a NUL) inside a JUCE
fxb chunk set.

The engine state here is the module's JSON blob (`{"te2":1,"<key>":<value>,...}`), NOT
DubStation's key=value lines. Every key in that blob is listed by `te2_params.h`; a preset
that omits a key leaves it at its default, so the generator writes ALL keys to make the
patch fully determined.

TIME: the DSP's delay comes from `repeat_rate`; `time_ms` is only the readout, and the
state path restores both literally (the module's macro does not fan out there). A preset
therefore gives "delay_ms" (head-1 time, 69.33..177.354 ms) and the generator fills BOTH
via the DSP's own rate<->ms law, so they cannot disagree.

    vst/gen_presets.py                                   # into the built skin's Presets/
    vst/gen_presets.py --out-dir <dir> --so-path <abs>   # into a device effect-preset folder
"""
import argparse
import importlib.util
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))          # .../vst
MV = os.environ.get("MPC_VST_PLUGINS") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mpc-vst-plugins")

# ---- the DSP's repeat-rate <-> head-1 delay-ms law (TapeEchoDSP.cpp / .hpp) -------------
KMIN, KMAX = 69.33, 177.354


def _clamp01(x):
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def delay_ms_for_rate(v):
    x = _clamp01(v)
    x2 = x * x
    slow = _clamp01(1.0 - 2.14728717 * x2 + 0.90911783 * x2 * x
                    + 0.23816934 * x2 * x2 + 0.06891 * x2 * (1.0 - x) * (1.0 - x))
    return KMIN + slow * (KMAX - KMIN)


def rate_for_ms(ms):
    target = KMIN if ms < KMIN else (KMAX if ms > KMAX else ms)
    lo, hi = 0.0, 1.0
    for _ in range(24):
        mid = 0.5 * (lo + hi)
        if delay_ms_for_rate(mid) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ---- presets (mode index 0..11 = H1..Rev; only listed keys differ from the defaults) ---
# Use the MACRO knobs, never their members: `tone_tilt` owns bass/treble and `tape_wear` owns
# wow_flutter/tape_age (see te2_macro_tone / te2_macro_tape). The state path does NOT run the
# macros, so the generator derives the members from the macro for the blob; the program path
# (presets.json) sets the macro and omits the members. Where both routes then agree.
# delay_ms is the head-1 time; the MODE scales it (H3 ~ 3x, H123R etc. differ per mode).
PRESETS = [
    ("Init", {}),
    ("Dub Classic", {           # the classic three-head dub echo
        "mode": 2, "intensity": 0.72, "echo_volume": 1.0, "reverb_volume": 0.20,
        "mix": 0.35, "tone_tilt": -0.20, "tape_wear": 0.35, "input_send": 1, "delay_ms": 120,
    }),
    ("King Tubby", {            # dark, heavy, filtered
        "mode": 1, "intensity": 0.80, "echo_volume": 1.0, "reverb_volume": 0.0,
        "mix": 0.40, "tone_tilt": -0.45, "tape_wear": 0.50, "delay_ms": 110,
    }),
    ("Bristol Steppers", {      # UK steppers, militant
        "mode": 3, "intensity": 0.86, "echo_volume": 1.0, "reverb_volume": 0.10,
        "mix": 0.42, "tone_tilt": -0.35, "tape_wear": 0.55, "delay_ms": 100,
    }),
    ("Slapback", {              # one short repeat
        "mode": 0, "intensity": 0.18, "echo_volume": 0.85, "reverb_volume": 0.0,
        "mix": 0.25, "delay_ms": 88,
    }),
    ("Spring Dub", {            # head 3 + the spring tank
        "mode": 6, "intensity": 0.65, "echo_volume": 0.80, "reverb_volume": 0.85,
        "mix": 0.45, "tone_tilt": -0.15, "delay_ms": 115,
    }),
    ("Ambient Wash", {          # all heads + spring, long and wide
        "mode": 10, "intensity": 0.80, "echo_volume": 0.90, "reverb_volume": 0.75,
        "mix": 0.60, "tone_tilt": -0.10, "tape_wear": 0.60, "delay_ms": 130,
    }),
]

MACRO_MEMBERS = ("bass", "treble", "wow_flutter", "tape_age")   # owned by tone_tilt / tape_wear


def state_value(key, default, ov):
    """The value a table key gets in the state blob, with the macros expanded to their members."""
    if key == "repeat_rate" and "delay_ms" in ov:
        return rate_for_ms(ov["delay_ms"])
    if key == "time_ms" and "delay_ms" in ov:
        return ov["delay_ms"]
    if key in ("bass", "treble") and "tone_tilt" in ov:      # te2_macro_tone
        t = max(-1.0, min(1.0, ov["tone_tilt"]))
        return -t * 0.6 if key == "bass" else t
    if key in ("wow_flutter", "tape_age") and "tape_wear" in ov:   # te2_macro_tape
        w = max(0.0, min(1.0, ov["tape_wear"]))
        if key == "wow_flutter":
            v = (w - 0.25) / 0.75
            return v if v > 0.0 else 0.0
        return 0.0 if w < 0.15 else (1.0 if w < 0.60 else 2.0)
    return ov.get(key, default)



def load_xpl():
    path = os.path.join(MV, "tools", "xpl.py")
    spec = importlib.util.spec_from_file_location("xpl", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def te2_table(path):
    """[(key, type, default)] from te2_params.h, deduped by key, 'preset' dropped."""
    text = open(path, encoding="utf-8").read()
    rows = re.findall(
        r'\{\s*"([^"]+)",\s*"[^"]*",\s*TE2_(FLOAT|INT|ENUM),\s*(-?[\d.]+)f?,\s*(-?[\d.]+)f?,\s*(-?[\d.]+)f?',
        text)
    out, seen = [], set()
    for key, typ, _lo, _hi, default in rows:
        if key == "preset" or key in seen:
            continue
        seen.add(key)
        out.append((key, typ, float(default)))
    if len(out) < 10:
        raise SystemExit("could not parse the te2 param table at %s" % path)
    return out


def value_for(typ, raw):
    if isinstance(raw, str):
        raise SystemExit("te2 presets take numbers, not %r" % raw)
    if typ in ("ENUM", "INT"):
        return "%d" % int(round(raw))
    return "%g" % raw


def _collect_param_keys(obj, out):
    if isinstance(obj, list):
        for x in obj:
            _collect_param_keys(x, out)
    elif isinstance(obj, dict):
        if isinstance(obj.get("key"), str):
            out.add(obj["key"])
        for v in obj.values():
            _collect_param_keys(v, out)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", help="write the .xpl files here instead of the built skin's Presets/. "
                                      "Use the device effect-preset folder for an insert effect.")
    ap.add_argument("--so-path", help="the <PLUGIN file=...> value; default '%%payload-path%%/<skin>/<so>'. "
                                      "For a device effect preset pass the absolute .so path.")
    a = ap.parse_args()

    cfg = json.load(open(os.path.join(HERE, "vst.json"), encoding="utf-8"))
    table = te2_table(os.path.join(HERE, "src", "dsp", "te2_params.h"))
    keys = {k for k, _t, _d in table}

    unknown = set().union(*[set(ov) for _n, ov in PRESETS]) - keys - {"delay_ms"}
    if unknown:
        raise SystemExit("preset uses unknown key(s): %s" % ", ".join(sorted(unknown)))

    skin_name = "%s - VST - %s" % (cfg["vendor"], cfg["name"])
    so_path = a.so_path or ("%%payload-path%%/%s/%s" % (skin_name, cfg["so"]))
    uid = int.from_bytes(cfg["uid"].encode(), "big")

    if a.out_dir:
        presets_dir = a.out_dir
        fname = lambda i, name: "%s.xpl" % name                        # noqa: E731
    else:
        skin = os.path.join(HERE, "build", "skin", skin_name)
        if not os.path.isdir(skin):
            raise SystemExit("no built skin at %s - run vst/preview.sh or vst/build.sh first" % skin)
        presets_dir = os.path.join(skin, "Presets")
        fname = lambda i, name: "%04d-%s.xpl" % (i, name)              # noqa: E731
    os.makedirs(presets_dir, exist_ok=True)

    xpl = load_xpl()
    for i, (name, ov) in enumerate(PRESETS, start=1):
        state = ["{\"te2\":1"]
        for key, typ, default in table:
            state.append(",\"%s\":%s" % (key, value_for(typ, state_value(key, default, ov))))
        state.append("}")
        chunk = ("".join(state)).encode("utf-8") + b"\0"
        text = xpl.xpl(cfg["name"], cfg["vendor"], so_path, uid,
                       cfg.get("version", 1000), chunk, preset=name, effect=bool(cfg.get("effect")))
        dst = os.path.join(presets_dir, fname(i, name))
        with open(dst, "w", encoding="utf-8") as f:
            f.write(text)
        print("preset:", dst)

    # Also emit the VST-program list next to vst.json (vst.json "presets"), so MPC's PRESET
    # field lists the same names - the .xpl route sits behind the folder icon, this one behind
    # the field. Values use the module's own parameter keys (time_ms, not delay_ms).
    allowed = set()
    _collect_param_keys(json.load(open(os.path.join(HERE, cfg["module"]), encoding="utf-8")), allowed)
    programs = []
    for name, ov in PRESETS:
        vals = {}
        for key, typ, default in table:
            if key in ("preset", "repeat_rate", "vu", "vu_cal") or key in MACRO_MEMBERS or key not in allowed:
                continue
            raw = ov.get(key, default)
            if key == "time_ms" and "delay_ms" in ov:
                raw = ov["delay_ms"]
            vals[key] = int(round(raw)) if typ in ("ENUM", "INT") else raw
        programs.append({"name": name, "values": vals})
    out_json = os.path.join(HERE, "presets.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"presets": programs}, f, indent=2)
        f.write("\n")
    print("programs:", out_json)


if __name__ == "__main__":
    main()
