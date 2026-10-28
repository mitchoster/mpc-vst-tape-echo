#!/usr/bin/env python3
"""Draw the sample-value mock-ups of the built skin (docs/ui-preview/page_N_values.png).

`studio.py preview` leaves every live value as an outline placeholder (MPC draws those numbers
itself), so the pages cannot be judged at a glance. This paints them in: one table of sample
values per parameter, then per page it pastes the matching knob/meter filmstrip frame, swaps the
chosen option tile to its "on" image, and writes the value text in Titillium Web on top of each
placeholder.

It is a MOCK-UP, not a render: the numbers are chosen to show the type scale and the density, and
the strings follow the module's own display rules (repeat_rate/intensity/wear are plain 0..1
numbers, stereo_width an int, time_ms "400 ms", the sync division a note). Nothing here ships in
the skin.

  docker run --rm -v <framework>:/mv:ro -v <port>:/w -w /w mpc-vst-html-art \\
      python3 vst/art/make_values.py
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import look as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = os.path.join(HERE, "..", "..")
SKIN = os.path.join(PORT, "vst", "build", "skin", "LarryDaimond - VST - MPC Tape Echo", "Plugin Skins")

# parameter -> (value on the parameter's own scale, the text MPC would print)
SAMPLES = {
    "repeat_rate": (0.415, "0.4"),
    "intensity": (0.44, "0.4"),
    "wow_flutter": (0.22, "0.2"),
    "tape_wear": (0.25, "0.3"),
    "bass": (-0.2, "-0.2"),
    "treble": (0.15, "0.2"),
    "tone_tilt": (0.35, "0.4"),
    "echo_volume": (1.0, "1.0"),
    "reverb_volume": (0.35, "0.4"),
    "input_volume": (0.5, "0.5"),
    "mix": (0.5, "0.5"),
    "stereo_width": (70, "70"),
    "echo_rate_note": (5, "1/8"),
    "time_ms": (400, "400 ms"),
    "vu": (13, ""),           # the meter is a frame index, not a 0..1 fraction: 13 of 24 steps
}
READOUTS = {"time_ms": ("400 ms", "e0a33a")}
ENUMS = {"mode": "H3", "tape_age": "Used", "vu_cal": "nom 100 %", "input_send": "On",
         "tempo_sync": "Off", "ping_pong": "Off"}


def frac(key, params):
    p = next((p for p in params if p["key"] == key), None)
    v = SAMPLES.get(key, (0, ""))[0]
    if p is None or "min" not in p or p["max"] == p["min"]:
        return 0.5
    return max(0.0, min(1.0, (v - p["min"]) / float(p["max"] - p["min"])))


def frame_of(strip, num_frames, f):
    """The filmstrip frame for position f (0..1). Knobs ship one frame more than numFrames."""
    n_img = num_frames + 1 if strip.size[1] == (num_frames + 1) * strip.size[0] else num_frames
    fh = strip.size[1] // n_img
    k = min(n_img - 1, max(0, round(f * (n_img - 1))))
    return strip.crop((0, k * fh, strip.size[0], (k + 1) * fh))


def load_params():
    mod = json.load(open(os.path.join(PORT, "vst", "src", "spaceecho_module.json")))
    return mod["capabilities"]["chain_params"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skin", default=SKIN)
    ap.add_argument("--pages", default=os.path.join(PORT, "docs", "ui-preview", "page_%d.png"))
    ap.add_argument("--out", default=None, help="output pattern (default: <page>_values.png)")
    a = ap.parse_args()
    params = load_params()
    pkey = [p["key"] for p in params]
    tui = json.load(open(os.path.join(a.skin, "TUI.json")))["pageData"]
    defs = {d["key"]: d["value"] for d in tui["componentDefinitions"]["localComponentDefinitions"]}

    for n, tab in enumerate(tui["tabs"]):
        src = a.pages % n
        out = a.out % n if a.out else src.replace(".png", "_values.png")
        if not os.path.exists(src):
            print("skip (no preview):", src)
            continue
        im = Image.open(src).convert("RGB")
        dr = ImageDraw.Draw(im)
        comps = defs[tab["componentName"]]["componentsData"]
        # the page background is the largest placed image; the per-mode images are small overlays
        bgc = max((c for c in comps if c["componentData"]["type"] == "Image"),
                  key=lambda c: int(float(c["bounds"]["bounds"].split()[2])))
        bg = Image.open(os.path.join(a.skin, bgc["componentData"]["data"]["image"])).convert("RGB")
        for c in comps:
            cd = c["componentData"]
            idx = None
            for m in c.get("handle remapping", {}).get("map", []):
                if m.get("key") == "Data":
                    idx = int(str(m["value"]).split()[1]) if str(m.get("value", "")).startswith("Parameter") else None
            x, y, w, h = [int(float(v)) for v in c["bounds"]["bounds"].split()]
            key = pkey[idx] if idx is not None else None
            for s in (defs.get(cd["type"]) or {}).get("componentsData", []):
                sd = s["componentData"]
                sx, sy, sw, sh = [int(float(v)) for v in s["bounds"]["bounds"].split()]
                data = sd.get("data") or {}
                if sd["type"] == "Knob" and key:
                    f = frac(key, params)
                    im.paste(bg.crop((x + sx, y + sy, x + sx + sw, y + sy + sh)), (x + sx, y + sy))
                    strip = Image.open(os.path.join(a.skin, data["filmStrip"])).convert("RGBA")
                    fr = frame_of(strip, int(data.get("numFrames") or 127), f)
                    im.paste(fr, (x + sx, y + sy), fr)
                elif sd["type"] == "Button" and key and key in ENUMS:
                    opts = next((p.get("options") or [] for p in params if p["key"] == key), [])
                    on = data.get("onImage") if ENUMS[key] in opts and \
                        opts.index(ENUMS[key]) == data.get("buttonId") else data.get("offImage")
                    if on:   # the resting image is already there; the chosen one may need the on face
                        img = Image.open(os.path.join(a.skin, on)).convert("RGBA")
                        im.paste(img, (x + sx, y + sy), img)
                elif sd["type"] == "Label" and data.get("type") == "Value":
                    ts = sd["data"]["textStyle"]
                    if key in READOUTS and cd["type"].startswith("shReadout"):
                        text, col = READOUTS[key]
                    elif key in SAMPLES and SAMPLES[key][1]:
                        text, col = SAMPLES[key][1], ts["colour"][2:]
                    else:
                        continue
                    under = im.getpixel((min(x + sx + sw - 4, x + sx + 4),
                                         min(y + sy + sh - 4, y + sy + 4)))
                    dr.rectangle([x + sx, y + sy, x + sx + sw - 1, y + sy + sh - 1], fill=under)
                    fnt = L.font("semi", max(1, round(float(ts["font"]["height"]))))
                    rgb = tuple(int(col[i:i + 2], 16) for i in (0, 2, 4))
                    bx = dr.textbbox((0, 0), text, font=fnt)
                    dr.text((x + sx + (sw - (bx[2] - bx[0])) / 2 - bx[0],
                             y + sy + (sh - (bx[3] - bx[1])) / 2 - bx[1]), text, font=fnt, fill=rgb)
        im.save(out, optimize=True)
        print("wrote", out)


if __name__ == "__main__":
    main()
