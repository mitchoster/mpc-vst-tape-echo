#!/usr/bin/env python3
"""Draw the widget artwork for the MPC Tape Echo skin: the knob filmstrip.

MPC has no drawing API: everything that moves is a parameter-driven filmstrip, so this file
is a stack of frames and the wrapper picks one by the parameter's value.

  knob_strip.png   127 frames 54x54   the knob: track ring, value arc, dome, pointer
                                      (every knob on the page shares it; r=22 -> 2r+10 = 54)

127 frames is shadow_skin.ROT_FRAMES (a rotary Knob reads one frame fewer than its strip
length); the layout says `knob_frames=127` so the generator and the skin agree.

  docker run --rm -v <port>:/w -w /w mpc-vst-html-art python3 vst/art/make_widgets.py -o vst/art
"""
import argparse
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import look as L  # noqa: E402

KNOB_R = L.KNOB_R           # layout r= (all knobs, card and panel)
KNOB_S = 2 * KNOB_R + 10    # the frame size shadow_skin.py emits for a knob of that radius
KNOB_FRAMES = 127           # shadow_skin.ROT_FRAMES


def _arc_pts(cx, cy, rad, a0, a1, n=48):
    return [(cx + rad * math.sin(math.radians(a0 + (a1 - a0) * i / n)),
             cy - rad * math.cos(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def _ring(d, cx, cy, rad, a0, a1, fill, width):
    """An arc with round caps (PIL's arc has square ends)."""
    if abs(a1 - a0) < 0.4:
        return
    d.line(_arc_pts(cx, cy, rad, a0, a1), fill=fill, width=width, joint="curve")
    for a in (a0, a1):
        x = cx + rad * math.sin(math.radians(a))
        y = cy - rad * math.cos(math.radians(a))
        d.ellipse([x - width / 2, y - width / 2, x + width / 2, y + width / 2], fill=fill)


def _dome(size, r):
    """The knob body: a radial gradient from a light top-left to a dark bottom-right, plus a rim."""
    s = size
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    grad = Image.new("RGB", (s, s), (0, 0, 0))
    gd = ImageDraw.Draw(grad)
    cx, cy = s / 2, s / 2
    for i in range(int(r) + 1, -1, -1):
        t = i / r
        # t=0 at the centre (light), 1 at the rim (dark): a soft dome, not a flat disc
        col = L.lerp((76, 84, 95), (22, 26, 31), min(1.0, t ** 0.72))
        dx, dy = -r * 0.35 * (1 - t), -r * 0.4 * (1 - t)
        gd.ellipse([cx - i + dx, cy - i + dy, cx + i + dx, cy + i + dy], fill=col)
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    img.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(img)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(7, 8, 11, 255), width=1)          # contact edge
    hi = [(cx + (r - 1.2) * math.sin(math.radians(a)), cy - (r - 1.2) * math.cos(math.radians(a)))
          for a in range(-150, -40, 4)]
    d.line(hi, fill=(96, 104, 116, 90), width=1, joint="curve")                             # top rim light
    spec = Image.new("RGBA", (s, s), (0, 0, 0, 0))                                          # specular blob
    ImageDraw.Draw(spec).ellipse([cx - r * 0.62, cy - r * 0.78, cx + r * 0.12, cy - r * 0.24],
                                fill=(255, 255, 255, 26))
    img.alpha_composite(spec.filter(ImageFilter.GaussianBlur(2.2)))
    return img


def make_knob(path, frames=KNOB_FRAMES):
    s = KNOB_S
    c = s / 2.0
    ring_r = KNOB_R + 2.5
    dome = _dome(s, KNOB_R - 2.5)
    strip = Image.new("RGBA", (s, s * frames), (0, 0, 0, 0))
    for k in range(frames):
        fr = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(fr)
        a = -135.0 + 270.0 * k / (frames - 1)
        _ring(d, c, c, ring_r, -135, 135, (44, 50, 58, 255), 3)                  # the unlit track
        if k > 0:
            glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
            _ring(ImageDraw.Draw(glow), c, c, ring_r, -135, a, L.rgba(L.ARC, 70), 7)
            fr.alpha_composite(glow.filter(ImageFilter.GaussianBlur(2.0)))
            _ring(d, c, c, ring_r, -135, a, L.rgba(L.ARC), 3)                    # the value arc
        fr.alpha_composite(dome)
        # pointer: a bright bar from the middle out to the rim, with a dark shadow under it
        p0, p1 = KNOB_R * 0.30, KNOB_R * 0.80
        for dx, dy, col in ((0.8, 1.0, (0, 0, 0, 150)), (0, 0, (244, 247, 250, 255))):
            x0 = c + p0 * math.sin(math.radians(a)) + dx
            y0 = c - p0 * math.cos(math.radians(a)) + dy
            x1 = c + p1 * math.sin(math.radians(a)) + dx
            y1 = c - p1 * math.cos(math.radians(a)) + dy
            d.line([(x0, y0), (x1, y1)], fill=col, width=3)
        strip.paste(fr, (0, k * s))
    strip.save(path, optimize=True)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="vst/art", help="output directory (default vst/art)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    print("wrote", make_knob(os.path.join(a.out, "knob_strip.png")))


if __name__ == "__main__":
    main()
