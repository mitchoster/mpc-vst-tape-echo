#!/usr/bin/env python3
"""Draw the VU meter for the Tape Echo skin: one filmstrip plus one PNG per step of "vu".

The layout binds the engine-driven step with
  meter cx=760 cy=253 w=464 h=46 key=vu strip=art/vu_strip.png frames=24
(a display-only filmstrip Knob, which MPC redraws live when the wrapper reports the value --
`HAS_DISPLAY_REV` + `DISPLAY_REV_NO_UPDATE`; verified live on an MPC One, docs/SKIN_STUDIO.md
"Meter"). Frame count must equal the "vu" param's options in vst/src/spaceecho_module.json
(VU_STEPS in adapters/schwung_fx). The per-step PNGs are kept for reference/preview.

The scale itself (ticks, "quiet"/"hot") is baked into the page artwork by make_plate.py: the
engine's "vu" value is a linear 0..23 step, not dB, so the scale is printed unnumbered.

Needs Pillow; run it in the browser-art image:

  docker run --rm -u "$(id -u):$(id -g)" -v <host project>:/w -w /w mpc-vst-html-art \\
      python3 vst/art/make_vu.py -o vst/art/vu -s vst/art/vu_strip.png
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import look as L  # noqa: E402

STEPS = 24                       # the "vu" param's option count
W, H = L.VU_METER[2], L.VU_METER[3]   # the trough's inner box: 464 x 46
INSET_X, INSET_Y = 4, 5          # the bar sits this far inside its frame (the trough frames it)


def frame(step):
    """One VU frame: the bar from the left, amber low, orange at the top, a bright head."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    frac = step / (STEPS - 1)
    inner_w = W - 2 * INSET_X
    fill_w = int(round(frac * inner_w))
    if fill_w < 3:
        return img
    d = ImageDraw.Draw(img)
    col = L.lerp(L.VU_LO, L.VU_HI, min(1.0, frac / 0.8))
    if frac > 0.8:
        col = L.lerp(L.VU_HI, L.VU_HOT, (frac - 0.8) / 0.2)
    body_top = INSET_Y
    body_bot = H - INSET_Y
    r = 4
    # the fill, rounded at the moving end so the head reads as a soft bar, not a cut
    d.rounded_rectangle([INSET_X, body_top, INSET_X + fill_w, body_bot], radius=r, fill=L.rgba(col, 242))
    # a light upper half: the bar looks lit from above, like the plate it sits on
    d.rounded_rectangle([INSET_X + 1, body_top + 1, INSET_X + max(3, fill_w - 1),
                         body_top + (body_bot - body_top) // 2],
                        radius=max(1, r - 1), fill=L.rgba(L.lerp(col, L.WHITE, 0.20), 150))
    # step separators: the engine has exactly 24 steps, so the bar reads as a segmented display
    for i in range(1, STEPS):
        x = INSET_X + inner_w * i / float(STEPS)
        if x < INSET_X + fill_w - 1:
            d.line([(x, body_top + 1), (x, body_bot - 1)], fill=(24, 20, 14, 90), width=1)
    # head: a bright 3 px edge so the value reads without a needle
    hx = INSET_X + fill_w
    d.rectangle([max(INSET_X + 2, hx - 3), body_top + 1, min(W - INSET_X - 1, hx), body_bot - 1],
                fill=L.rgba(L.lerp(col, L.WHITE, 0.78), 255))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="vst/art/vu")
    ap.add_argument("-s", "--strip", default="vst/art/vu_strip.png",
                    help="filmstrip output: STEPS frames of WxH stacked down, minimum first")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    frames = [frame(s) for s in range(STEPS)]
    for step, img in enumerate(frames):
        img.save(os.path.join(a.out, "vu_%02d.png" % step))
    strip = Image.new("RGBA", (W, H * STEPS), (0, 0, 0, 0))
    for step, img in enumerate(frames):
        strip.paste(img, (0, step * H))
    strip.save(a.strip)
    print("wrote %d PNGs to %s and %s (%dx%d)" % (STEPS, a.out, a.strip, W, H * STEPS))


if __name__ == "__main__":
    main()
