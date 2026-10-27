#!/usr/bin/env python3
"""Draw the live record-VU filmstrip for the MPC Tape Echo skin.

The layout binds the engine-driven step with `meter cx= cy= w=304 h=132 key=vu strip=art/vu_strip.png
frames=24` - a display-only filmstrip Knob, which MPC repaints when the wrapper reports the value
(HAS_DISPLAY_REV + DISPLAY_REV_NO_UPDATE). Frame count must equal the "vu" param's options in
vst.json (`vu`, 0..23), one frame per step.

The dial is a cream VU behind glass in a machined bezel: a horizontal fan scale, a rust-red needle
pivoting below the window, tick marks only. **No dB numbers**: the engine's vu step is a linear
record-VU level (VU_FULL = 0.05 in vst.json), not a calibrated dBFS scale, so printing "-6 / -12" on
it would be a lie. The live record VU is read from the meter window, the value text is the knob's own.

Needs Pillow; run it in the browser-art image:

  docker run --rm -v <framework>:/mv -v <port>:/w -w /w mpc-vst-html-art \\
      python3 vst/art/make_vu.py
"""
import os
import math
import os

from PIL import Image, ImageDraw, ImageFont

W, H = 304, 132
STEPS = 24

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)                 # vst/

BEZEL = (12, 12, 10)
FACE_TOP = (247, 240, 220)
FACE_BOT = (223, 213, 188)
INK = (30, 28, 23)
INK_DIM = (104, 96, 78)
RED = (168, 52, 34)
RUST = (150, 84, 52)

FONT_DIRS = [os.environ.get("TAPEECHO_FONT_DIR", ""), "/mv/tools/html_art/fonts",
             os.environ.get("MPC_VST_FONTS", "/usr/share/fonts/truetype"),
             os.path.join(HERE, "fonts")]


def font(weight, size):
    name = {"bold": "TitilliumWeb-Bold.ttf", "semi": "TitilliumWeb-SemiBold.ttf"}[weight]
    for d in FONT_DIRS:
        if d and os.path.isfile(os.path.join(d, name)):
            return ImageFont.truetype(os.path.join(d, name), size)
    raise SystemExit("make_vu: %s not found (set TAPEECHO_FONT_DIR)" % name)


def tracked(d, xy, text, f, fill, tracking=0.0, anchor="center"):
    total = sum(f.getlength(c) for c in text) + tracking * max(0, len(text) - 1)
    x, y = xy
    if anchor == "center":
        x -= total / 2
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill, anchor="lm")
        x += f.getlength(ch) + tracking


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def frame(step):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # bezel: machined frame, lit top lip, shadow along the bottom
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=9, fill=BEZEL + (255,))
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=9, outline=(60, 56, 49, 255), width=1)
    d.line([(12, 1), (W - 13, 1)], fill=(124, 118, 106, 110), width=1)
    d.line([(12, H - 2), (W - 13, H - 2)], fill=(0, 0, 0, 220), width=1)
    d.rounded_rectangle([4, 4, W - 5, H - 5], radius=6, fill=(26, 24, 20, 255))

    # dial face, warm cream with a soft falloff
    fw, fh = W - 16, H - 16
    face = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
    fd = ImageDraw.Draw(face)
    for y in range(fh):
        t = y / (fh - 1)
        fd.line([(0, y), (fw, y)], fill=lerp(FACE_TOP, FACE_BOT, t ** 1.2) + (255,))
    mask = Image.new("L", (fw, fh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, fw - 1, fh - 1], radius=4, fill=255)
    img.paste(face, (8, 8), mask)
    d = ImageDraw.Draw(img)

    # fan scale: pivot below the window, the needle sweeping across the face
    px, py = W / 2.0, 240.0
    sweep = 72.0
    R_arc, R_tick, R_needle = 204.0, 204.0, 200.0

    def at(frac, rad):
        a = math.radians(-sweep / 2 + sweep * frac)
        return px + rad * math.sin(a), py - rad * math.cos(a)

    arc = [at(i / 140.0, R_arc) for i in range(141)]
    d.line(arc, fill=(74, 66, 50, 200), width=1)
    for i in range(STEPS):
        frac = i / (STEPS - 1)
        major = i in (0, 6, 12, 18, 23)
        hot = i >= STEPS - 3
        x0, y0 = at(frac, R_tick)
        x1, y1 = at(frac, R_tick - (14 if major else 7))
        d.line([(x0, y0), (x1, y1)], fill=(RED if hot else (62, 54, 40)) + (255,),
               width=2 if major else 1)
    # the overload band, just inside the last three ticks
    band = [at((STEPS - 3) / (STEPS - 1) + (2.0 / (STEPS - 1)) * i / 14.0, R_tick - 22) for i in range(15)]
    d.line(band, fill=(172, 56, 38, 175), width=3, joint="curve")

    tracked(d, (W / 2, 100), "VU", font("bold", 21), (52, 47, 38), tracking=4.4)
    tracked(d, (W / 2, 117), "RECORD", font("semi", 7), (116, 106, 86), tracking=1.8)

    # needle: tapered, rust red, pivot outside the window
    a = math.radians(-sweep / 2 + sweep * (step / (STEPS - 1)))
    nx, ny = px + R_needle * math.sin(a), py - R_needle * math.cos(a)
    ox, oy = math.cos(a) * 1.7, math.sin(a) * 1.7
    d.polygon([(px - ox, py - oy), (px + ox, py + oy), (nx, ny)], fill=RUST + (255,))
    d.line([(px + ox * 0.4, py + oy * 0.4), (nx, ny)], fill=(206, 118, 84, 110), width=1)

    # glass: a diagonal reflection across the top left, and a faint rim light inside
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gl)
    gd.polygon([(9, 9), (W - 9, 9), (W - 9, 26), (9, 58)], fill=(255, 255, 255, 14))
    gd.rounded_rectangle([8, 8, W - 9, H - 9], radius=4, outline=(255, 255, 255, 22), width=1)
    return Image.alpha_composite(img, gl)


def main():
    strip = Image.new("RGBA", (W, H * STEPS), (0, 0, 0, 0))
    for i in range(STEPS):
        strip.paste(frame(i), (0, i * H))
    p = os.path.join(OUT, "art", "vu_strip.png")
    strip.save(p, optimize=True)
    print("wrote %s (%dx%d, %d frames)" % (p, W, H * STEPS, STEPS))


if __name__ == "__main__":
    main()
