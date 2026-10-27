#!/usr/bin/env python3
"""Faceplate, engravings, tiles and switches for the MPC Tape Echo skin (Rack style).

The same anodised-panel language as the MPC DJ FX 2 port: one graphite plate per page with engraved
letterspaced caps, milled bays, one warm amber LED colour, cream option tiles and a cream VU. Adapted to
the tape echo - a warmer chassis and an oxide-rust second accent, plus the instrument's own identity drawn
as panel engraving: the three play heads with their tape ribbon (TAPE page) and the spring tank (TONE).

Everything is drawn procedurally with Pillow, so the build needs nothing but this file, the framework's
Titillium Web TTFs and Python 3 + Pillow:

    docker run --rm -v <framework>:/mv -v <port>:/w -w /w mpc-vst-html-art \\
        python3 vst/art/make_te_skin.py

Output (written next to vst/):
    bg_program.png  bg_tape.png  bg_tone.png   1280x628 page backgrounds (texture, masthead, engravings)
    art/seg_mode_off.png  art/seg_mode_on.png  148x62  the twelve head/tank tiles
    art/seg_age_off.png   art/seg_age_on.png   200x48  the three tape-stock tiles
    art/switch_off.png    art/switch_on.png    34x50   bat-lever switch in its machined base

The VU filmstrip is make_vu.py's job (it is the live meter). Two things are read back out of
vst/layout.conf so the artwork cannot drift from the layout: the `meter` widget (its inset window) and a
knob on `vu_cal` (its trimmer well). Bay rectangles come from the `frame` lines, matched by title.

Nothing live is baked: MPC draws every parameter name and value on top of this art.
"""
import os
import math
import os
import random
import shlex
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 628
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)                      # vst/
LAYOUT = os.path.join(OUT, "layout.conf")

# ---------------------------------------------------------------- palette
# A warm graphite: the chassis of a tape machine rather than a synth. The only two accents are amber
# (LEDs, the live value ink) and oxide rust (tape ribbon, overload marks); everything else is engraving.
PANEL_TOP = (37, 35, 31)
PANEL_BOT = (18, 17, 15)
RULE = (66, 62, 55)
RULE_HI = (99, 94, 84)
RULE_DIM = (45, 42, 37)
BONE = (211, 201, 180)          # engraved labels
BONE_HI = (240, 232, 212)       # values / masthead
DIM = (138, 132, 122)
AMBER = (226, 166, 74)
AMBER_HI = (246, 199, 112)
OXIDE = (152, 84, 52)           # tape ribbon, hot marks
CREAM = (238, 230, 208)         # tiles, VU dial
INK = (26, 25, 22)
BEZEL = (12, 12, 10)

FONT_DIRS = [os.environ.get("TAPEECHO_FONT_DIR", ""), "/mv/tools/html_art/fonts",
             os.environ.get("MPC_VST_FONTS", "/usr/share/fonts/truetype"),
             os.path.join(HERE, "fonts")]
_FONTS = {}


def font(weight, size):
    key = (weight, size)
    if key in _FONTS:
        return _FONTS[key]
    name = {"bold": "TitilliumWeb-Bold.ttf", "semi": "TitilliumWeb-SemiBold.ttf",
            "reg": "TitilliumWeb-Regular.ttf"}[weight]
    for d in FONT_DIRS:
        if d and os.path.isfile(os.path.join(d, name)):
            f = ImageFont.truetype(os.path.join(d, name), size)
            _FONTS[key] = f
            return f
    sys.exit("make_te_skin: %s not found (set TAPEECHO_FONT_DIR)" % name)


# ---------------------------------------------------------------- small helpers
def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def over(base, layer_img):
    return Image.alpha_composite(base.convert("RGBA"), layer_img)


def layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def th_len(text, f, tracking):
    return sum(f.getlength(c) for c in text) + tracking * max(0, len(text) - 1)


def tracked(d, xy, text, f, fill, tracking=0.0, anchor="left", shadow=None, sh_off=(0, 1)):
    """Letterspaced text, vertically centred on xy[1]; shadow = (r,g,b,a) drawn sh_off px lower."""
    x, y = xy
    total = th_len(text, f, tracking)
    if anchor == "center":
        x -= total / 2
    elif anchor == "right":
        x -= total
    for col, off in ((shadow, sh_off), (fill, (0, 0))):
        if col is None:
            continue
        xx = x + off[0]
        for ch in text:
            d.text((xx, y + off[1]), ch, font=f, fill=col, anchor="lm")
            xx += f.getlength(ch) + tracking
    return total


def panel_base():
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        d.line([(0, y), (W, y)], fill=lerp(PANEL_TOP, PANEL_BOT, (y / (H - 1)) ** 0.85))

    # brushed anodising: fine horizontal streaks, then a soft light wash from the top left
    rnd = random.Random(90125)
    streaks = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(streaks)
    for _ in range(2600):
        y = rnd.randrange(H)
        x0 = rnd.randrange(-200, W // 2)
        sd.line([(x0, y), (x0 + rnd.randrange(300, W), y)], fill=rnd.randint(1, 6))
    streaks = streaks.filter(ImageFilter.GaussianBlur(0.7))
    wash = Image.new("RGBA", (W, H), (140, 132, 116, 0))
    wash.putalpha(streaks.point(lambda v: int(v * 1.9)))
    img = over(img, wash)
    # a whisper of grain so the large areas are not flat
    grain = Image.effect_noise((W, H), 7).filter(ImageFilter.GaussianBlur(0.4))
    g = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    g.putalpha(grain.point(lambda v: int(max(0, v - 120) * 0.15)))
    img = over(img, g)

    grad = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(grad)
    for i in range(90):
        gd.line([(0, i), (W, i)], fill=int(50 * (1 - i / 90.0)))
    hi = Image.new("RGBA", (W, H), (255, 249, 234, 0))
    hi.putalpha(grad)
    return over(img, hi)


def vignette(img, strength=0.55):
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).ellipse([-W * 0.25, -H * 0.55, W * 1.25, H * 1.55], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(150))
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dark.putalpha(m.point(lambda v: int((255 - v) * strength)))
    return over(img, dark)


def rule(img, x0, y0, x1, y1=None, col=RULE, a=110, w=1):
    """An engraved hairline: the cut, then a light lip under it (one px each)."""
    lay = layer()
    d = ImageDraw.Draw(lay)
    if y1 is None:
        d.line([(x0, y0), (x1, y0)], fill=col + (a,), width=w)
        d.line([(x0, y0 + 1), (x1, y0 + 1)], fill=(0, 0, 0, int(a * 0.8)), width=1)
    else:
        d.line([(x0, y0), (x0, y1)], fill=col + (a,), width=w)
        d.line([(x0 + 1, y0), (x0 + 1, y1)], fill=(0, 0, 0, int(a * 0.8)), width=1)
    return over(img, lay)


def recess(img, box, radius=7, rim=True):
    """A milled-out window: dark fill, a lit top lip and a shadow along the bottom."""
    x0, y0, x1, y1 = [int(v) for v in box]
    lay = layer()
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x0 - 1, y0 - 1, x1 + 1, y1 + 1], radius=radius + 1, fill=(70, 66, 58, 190))
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=(9, 9, 8, 252))
    if rim:
        d.rounded_rectangle([x0, y0, x1, y1], radius=radius, outline=(0, 0, 0, 200), width=2)
        d.line([(x0 + radius, y0 + 1), (x1 - radius, y0 + 1)], fill=(110, 104, 92, 120), width=1)
        d.line([(x0 + radius, y1 - 1), (x1 - radius, y1 - 1)], fill=(0, 0, 0, 210), width=1)
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for i in range(7):
        sd.line([(x0 + radius, y0 + 2 + i), (x1 - radius, y0 + 2 + i)], fill=(0, 0, 0, int(70 * (1 - i / 7.0))))
    lay = over(lay, shade)
    return over(img, lay)


def screw(img, cx, cy, r=7):
    lay = layer()
    d = ImageDraw.Draw(lay)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(16, 15, 13, 255), outline=(6, 5, 4, 255), width=1)
    d.ellipse([cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2], fill=(40, 38, 33, 255))
    d.arc([cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1], 200, 340, fill=(126, 120, 108, 190), width=1)
    d.line([(cx - r + 3, cy + r - 3), (cx + r - 3, cy - r + 3)], fill=(9, 8, 7, 235), width=2)
    d.line([(cx - r + 3, cy + r - 2), (cx + r - 2, cy - r + 2)], fill=(104, 98, 88, 90), width=1)
    return over(img, lay)


def frame_edges(img):
    """The plate's own double hairline, then the four corner screws."""
    lay = layer()
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([6, 6, W - 7, H - 7], radius=12, outline=(5, 5, 4, 255), width=1)
    d.rounded_rectangle([8, 8, W - 9, H - 9], radius=11, outline=(78, 73, 64, 210), width=1)
    d.rounded_rectangle([13, 13, W - 14, H - 14], radius=8, outline=(40, 37, 32, 190), width=1)
    img = over(img, lay)
    for cx, cy in ((22, 22), (W - 23, 22), (22, H - 23), (W - 23, H - 23)):
        img = screw(img, cx, cy, 7)
    return img


def masthead(img, title, sub, page, pages):
    lay = layer()
    d = ImageDraw.Draw(lay)
    f_title = font("bold", 31)
    tracked(d, (36, 40), title, f_title, BONE_HI, tracking=5.0, shadow=(6, 6, 5, 210), sh_off=(0, 1))
    tw = th_len(title, f_title, 5.0)
    d.rectangle([36, 57, 36 + tw - 4, 58], fill=AMBER + (170,))
    tracked(d, (38, 72), sub, font("semi", 10), DIM + (235,), tracking=2.4, shadow=(6, 6, 5, 160))

    # page indicator: one engraved pip per page, the current one lit
    f_pip = font("semi", 9)
    x = 1252
    for i in reversed(range(len(pages))):
        on = i == page
        wlab = th_len(pages[i], f_pip, 2.2)
        x -= wlab
        tracked(d, (x, 34), pages[i], f_pip, AMBER + (255,) if on else DIM + (170,),
                tracking=2.2, shadow=None if on else (6, 6, 5, 140))
        if on:
            d.rectangle([x, 43, x + wlab - 2, 45], fill=AMBER + (230,))
        x -= 26
    tracked(d, (1252, 58), "MPCTE  \u00b7  TAPE ECHO", font("semi", 8), (124, 118, 108, 210),
            tracking=2.6, anchor="right")
    img = over(img, lay)
    img = rule(img, 28, 88, W - 28, col=RULE, a=120)
    return rule(img, 28, 91, W - 28, col=RULE_DIM, a=120)


def footer(img, page, pages):
    lay = layer()
    d = ImageDraw.Draw(lay)
    f = font("semi", 8)
    tracked(d, (32, 614), "MPCTE  \u00b7  MPC TAPE ECHO", f, (112, 106, 96, 190), tracking=2.4)
    tracked(d, (W - 32, 614), "PAGE %d / %d" % (page + 1, len(pages)), f, (112, 106, 96, 190),
            tracking=2.4, anchor="right")
    img = over(img, lay)
    return rule(img, 28, 604, W - 28, col=RULE_DIM, a=90)


def caption(img, xy, text, size, colour=DIM, tracking=2.4, anchor="center", weight="semi", shadow=True):
    lay = layer()
    d = ImageDraw.Draw(lay)
    tracked(d, xy, text, font(weight, size), colour + (232,), tracking=tracking, anchor=anchor,
            shadow=(0, 0, 0, 170) if shadow else None)
    return over(img, lay)


# ---------------------------------------------------------------- engravings
def coil_turn(d, cx, cy, rx, ry, tilt, fill, width=2):
    """One turn of a spring, as a tilted ellipse drawn point by point (PIL cannot rotate an arc)."""
    pts = []
    for k in range(25):
        a = 2 * math.pi * k / 24
        x, y = rx * math.cos(a), ry * math.sin(a)
        pts.append((cx + x * math.cos(tilt) - y * math.sin(tilt),
                    cy + x * math.sin(tilt) + y * math.cos(tilt)))
    d.line(pts, fill=fill, width=width, joint="curve")


def spring_tank(img, box):
    """A spring reverb tank: milled shell, two long springs on their hooks, corner screws, mounting posts."""
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0, y1 - y0
    img = recess(img, (x0, y0, x1, y1), radius=9)
    lay = layer()
    d = ImageDraw.Draw(lay)
    # shell with a top-lit face
    shell = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shell)
    for i in range(y1 - y0 - 22):
        t = i / max(1.0, (y1 - y0 - 23))
        sd.line([(x0 + 10, y0 + 12 + i), (x1 - 10, y0 + 12 + i)], fill=lerp((58, 54, 46), (32, 30, 25), t ** 0.9) + (255,))
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).rounded_rectangle([x0 + 10, y0 + 12, x1 - 10, y1 - 12], radius=6, fill=255)
    shell.putalpha(m)
    lay = over(lay, shell)
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x0 + 10, y0 + 12, x1 - 10, y1 - 12], radius=6, outline=(13, 12, 10, 255), width=2)
    d.line([(x0 + 18, y0 + 14), (x1 - 18, y0 + 14)], fill=(126, 119, 105, 110))
    d.line([(x0 + 18, y1 - 14), (x1 - 18, y1 - 14)], fill=(0, 0, 0, 190))
    # inner shadow at the top of the shell, so the lid reads as sunk
    for i in range(8):
        d.line([(x0 + 16, y0 + 16 + i), (x1 - 16, y0 + 16 + i)], fill=(0, 0, 0, int(56 * (1 - i / 8.0))))
    # corner screws
    for cx, cy in ((x0 + 22, y0 + 24), (x1 - 22, y0 + 24), (x0 + 22, y1 - 24), (x1 - 22, y1 - 24)):
        d.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=(20, 19, 16, 255), outline=(78, 73, 63, 255))
        d.line([(cx - 2, cy + 2), (cx + 2, cy - 2)], fill=(126, 120, 106, 160))
    # two springs: end brackets, hooks, coils
    for y in (y0 + int(h * 0.37), y0 + int(h * 0.68)):
        ax0, ax1 = x0 + 40, x1 - 40
        for ax in (ax0, ax1):
            d.rounded_rectangle([ax - 5, y - 13, ax + 5, y + 13], radius=2, fill=(64, 60, 52, 255),
                                outline=(11, 10, 8, 255))
            d.line([(ax - 3, y - 10), (ax - 3, y + 10)], fill=(128, 121, 106, 120))
            d.ellipse([ax - 2, y - 2, ax + 2, y + 2], fill=(22, 21, 18, 255))
        # hook wires from bracket to the first and last turn
        d.line([(ax0 + 4, y), (ax0 + 13, y)], fill=(198, 192, 177, 220), width=2)
        d.line([(ax1 - 13, y), (ax1 - 4, y)], fill=(198, 192, 177, 220), width=2)
        # coil: turns running left to right, lit on the upper left side
        rxt, ryt, tilt = 4.6, 9.0, math.radians(26)
        cx0, cx1 = ax0 + 12, ax1 - 12
        stepx = 6.4
        n = int((cx1 - cx0) / stepx)
        for i in range(n):
            coil_turn(d, cx0 + i * stepx, y, rxt, ryt, tilt, (88, 82, 71, 220), width=3)
            coil_turn(d, cx0 + i * stepx, y, rxt, ryt, tilt, (222, 215, 198, 210), width=2)
    return over(img, lay)


def detent_arc(img, cx, cy, r, n, span=88.0, labels=("LONG", "SHORT")):
    """An engraved 11-detent scale: ticks outside the knob, the two end legends beneath them."""
    lay = layer()
    d = ImageDraw.Draw(lay)
    a0 = -span / 2.0
    for i in range(n):
        a = math.radians(a0 + span * i / (n - 1))
        r_in, r_out = r, r + (9 if i % 5 == 0 else 5)
        x0, y0 = cx + r_in * math.sin(a), cy - r_in * math.cos(a)
        x1, y1 = cx + r_out * math.sin(a), cy - r_out * math.cos(a)
        d.line([(x0, y0), (x1, y1)], fill=(158, 151, 137, 210 if i % 5 == 0 else 150), width=2 if i % 5 == 0 else 1)
    # the arc itself, thin, between the ticks and the knob
    pts = []
    for i in range(41):
        a = math.radians(a0 + span * i / 40.0)
        pts.append((cx + (r - 3) * math.sin(a), cy - (r - 3) * math.cos(a)))
    d.line(pts, fill=(104, 99, 89, 150), width=1, joint="curve")
    img = over(img, lay)
    a = math.radians(a0)
    lx, ly = cx + (r + 20) * math.sin(a), cy - (r + 20) * math.cos(a)
    a = math.radians(-a0)
    rx, ry = cx + (r + 20) * math.sin(a), cy - (r + 20) * math.cos(a)
    img = caption(img, (lx, ly), labels[0], 8, DIM, 1.8, anchor="right")
    return caption(img, (rx, ry), labels[1], 8, DIM, 1.8, anchor="left")


# ---------------------------------------------------------------- layout read-back
def read_layout():
    """{tab name: [widget dict]} - enough to place the VU window and the trimmer well."""
    tabs, cur = {}, None
    for raw in open(LAYOUT):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[tab "):
            cur = line[5:].rstrip("]").strip()
            tabs[cur] = []
            continue
        if cur is None or "=" not in line or line.startswith("qlinks"):
            continue
        try:
            toks = shlex.split(line)
        except ValueError:
            continue
        w = {"kind": toks[0]}
        for t in toks[1:]:
            k, _, v = t.partition("=")
            w[k] = v
        for k in ("cx", "cy", "x", "y", "w", "h", "r", "sw", "sh", "rows", "bw", "ns", "vs"):
            if k in w:
                try:
                    w[k] = int(w[k])
                except ValueError:
                    pass
        tabs[cur].append(w)
    return tabs


def wells(img, widgets, dy=86):
    """Recess the live meter window, and sink a well under the VU-cal trimmer."""
    for w in widgets:
        if w["kind"] == "meter":
            cx, cy = w["cx"], w["cy"] - dy
            rw, rh = w["w"], w["h"]
            img = recess(img, (cx - rw // 2 - 7, cy - rh // 2 - 7, cx + rw // 2 + 7, cy + rh // 2 + 7), radius=10)
        elif w["kind"] == "knob" and w.get("key") == "vu_cal":
            cx, cy = w["cx"], w["cy"] - dy
            r = w["r"] + 13
            lay = layer()
            d = ImageDraw.Draw(lay)
            d.ellipse([cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3], fill=(0, 0, 0, 150))
            d.ellipse([cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1], fill=(88, 83, 73, 200))
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(11, 10, 9, 252))
            d.arc([cx - r, cy - r, cx + r, cy + r], 200, 345, fill=(126, 119, 105, 140), width=2)
            img = over(img, lay)
    return img


# ---------------------------------------------------------------- tiles and switches
def tile_pair(name, w, h, big_radius=5):
    """A machined push-button: dark plate when off, cream plate with an amber rim when on."""
    m = 1.5
    off = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(off)
    d.rounded_rectangle([m, m, w - 1 - m, h - 1 - m], radius=big_radius, fill=(33, 31, 27, 255))
    d.rounded_rectangle([m, m, w - 1 - m, h - 1 - m], radius=big_radius, outline=(7, 6, 6, 255), width=1)
    d.line([(m + 5, m + 1.5), (w - m - 6, m + 1.5)], fill=(108, 102, 90, 110), width=1)
    d.line([(m + 5, h - m - 1.5), (w - m - 6, h - m - 1.5)], fill=(0, 0, 0, 190), width=1)

    on = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(on)
    d.rounded_rectangle([m, m, w - 1 - m, h - 1 - m], radius=big_radius, fill=(234, 225, 202, 255))
    d.rounded_rectangle([m, m, w - 1 - m, h - 1 - m], radius=big_radius, outline=(226, 166, 74, 235), width=1)
    d.line([(m + 5, m + 1.5), (w - m - 6, m + 1.5)], fill=(255, 252, 238, 210), width=1)
    d.line([(m + 5, h - m - 1.5), (w - m - 6, h - m - 1.5)], fill=(178, 168, 144, 220), width=1)
    for im in (off, on):
        pass
    off.save(os.path.join(OUT, "art", "seg_%s_off.png" % name))
    on.save(os.path.join(OUT, "art", "seg_%s_on.png" % name))
    print("wrote art/seg_%s_off.png art/seg_%s_on.png (%dx%d)" % (name, name, w, h))


def bat_switch():
    """A mini bat-lever in a machined base plate, with an amber lamp that lights when on."""
    w, h = 40, 58
    cx = w / 2
    for on in (0, 1):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([1, 1, w - 2, h - 2], radius=6, fill=(33, 31, 27, 255))
        d.rounded_rectangle([1, 1, w - 2, h - 2], radius=6, outline=(7, 6, 6, 255), width=1)
        d.line([(7, 2), (w - 8, 2)], fill=(116, 110, 98, 130), width=1)
        d.line([(7, h - 3), (w - 8, h - 3)], fill=(0, 0, 0, 210), width=1)

        base_y, tip_y = 27.0, (11.0 if on else 41.0)
        d.polygon([(cx - 3.0, base_y), (cx + 3.0, base_y), (cx + 1.7, tip_y), (cx - 1.7, tip_y)],
                  fill=(196, 189, 170, 255))
        d.line([(cx - 2.2, base_y), (cx - 1.1, tip_y)], fill=(246, 241, 226, 190), width=1)
        d.line([(cx + 2.3, base_y), (cx + 1.3, tip_y)], fill=(96, 92, 82, 190), width=1)
        d.ellipse([cx - 4.8, tip_y - 4.8, cx + 4.8, tip_y + 4.8], fill=(222, 214, 194, 255),
                  outline=(112, 106, 92, 220))

        d.ellipse([cx - 10, 27 - 10, cx + 10, 27 + 10], fill=(49, 46, 40, 255), outline=(7, 6, 6, 255))
        d.arc([cx - 10, 27 - 10, cx + 10, 27 + 10], 185, 355, fill=(128, 122, 110, 160), width=1)
        d.ellipse([cx - 4.5, 27 - 4.5, cx + 4.5, 27 + 4.5], fill=(24, 23, 20, 255))

        if on:
            glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow)
            gd.ellipse([cx - 8, 44, cx + 8, 60], fill=(240, 176, 74, 95))
            img = over(img, glow)
        d = ImageDraw.Draw(img)
        d.ellipse([cx - 3.0, 48.0, cx + 3.0, 54.0],
                  fill=(244, 182, 84, 255) if on else (42, 40, 35, 255))
        img.save(os.path.join(OUT, "art", "switch_%s.png" % ("on" if on else "off")))
    print("wrote art/switch_off.png art/switch_on.png (%dx%d)" % (w, h))


# ---------------------------------------------------------------- page 1: PROGRAM
def page_program(tabs, pages):
    img = panel_base()
    img = vignette(img)
    img = frame_edges(img)
    img = masthead(img, "PROGRAM", "FRONT PANEL  \u00b7  RECORD METER  \u00b7  HEAD SELECT  \u00b7  ECHO TIME", 0, pages)
    # the mode legend plate: the live per-mode description sits in it
    img = recess(img, (404, 438, 884, 508), radius=8)
    # a hairline under the program knobs, and the SYNC bay's detent scale
    img = recess(img, (44, 532, 344, 578), radius=6)
    img = caption(img, (194, 556), "DRY  +  ECHO  +  SPRING  \u203a  MIX  \u203a  OUT", 9, BONE, 2.0)
    img = rule(img, 944, 232, 1236, col=RULE_DIM, a=90)
    img = caption(img, (1090, 210), "TIME READS THE DIVISION WHILE SYNCED", 8, DIM, 1.6)
    img = detent_arc(img, 1090, 505, 44, 11, span=96.0, labels=("LONG", "SHORT"))
    img = wells(img, tabs.get("PROGRAM", []))
    img = footer(img, 0, pages)
    return img


# ---------------------------------------------------------------- page 2: TAPE
def tape_path(img, pts, width=18):
    """A tape run drawn as one thick oxide stroke with rounded corners (the path the heads read)."""
    lay = layer()
    d = ImageDraw.Draw(lay)
    d.line(pts, fill=(30, 22, 16, 255), width=width + 4, joint="curve")
    d.line(pts, fill=(86, 58, 37, 255), width=width, joint="curve")
    # a lit edge along the path and a shadowed one, so the ribbon has thickness
    off = width // 2 - 2
    d.line([(x, y - off) for x, y in pts], fill=(156, 112, 76, 130), width=1, joint="curve")
    d.line([(x, y + off) for x, y in pts], fill=(20, 14, 10, 200), width=1, joint="curve")
    return over(img, lay)


def reel(img, cx, cy, r, pack=0.66):
    """A tape reel: machined flange with three windows, the wound pack just inside it, a hub."""
    lay = layer()
    d = ImageDraw.Draw(lay)
    d.ellipse([cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3], fill=(0, 0, 0, 160))
    # flange
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(58, 54, 46, 255), outline=(9, 8, 7, 255), width=2)
    d.arc([cx - r, cy - r, cx + r, cy + r], 195, 345, fill=(168, 159, 142, 160), width=1)
    d.ellipse([cx - r + 4, cy - r + 4, cx + r - 4, cy + r - 4], fill=(40, 37, 32, 255))
    # wound pack
    pr = r * 0.90
    for i in range(int(pr), int(pr * 0.30), -1):
        t = (i - pr * 0.30) / max(1.0, pr * 0.70)
        d.ellipse([cx - i, cy - i, cx + i, cy + i], fill=lerp((116, 78, 48), (58, 39, 26), t ** 0.6) + (255,))
    d.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], outline=(34, 23, 16, 200), width=1)
    # three windows in the flange: dark cut-outs over the pack, so the reel reads as metal
    wr = r * 0.23
    for k in range(3):
        a = math.radians(k * 120 + 90)
        wx, wy = cx + math.cos(a) * r * 0.56, cy + math.sin(a) * r * 0.56
        d.ellipse([wx - wr * 0.86, wy - wr, wx + wr * 0.86, wy + wr], fill=(24, 21, 17, 235))
        d.arc([wx - wr * 0.86, wy - wr, wx + wr * 0.86, wy + wr], 150, 330, fill=(92, 86, 74, 110), width=1)
    # hub
    hr = r * 0.30
    d.ellipse([cx - hr, cy - hr, cx + hr, cy + hr], fill=(66, 62, 54, 255), outline=(10, 9, 8, 255), width=2)
    d.arc([cx - hr, cy - hr, cx + hr, cy + hr], 200, 340, fill=(152, 144, 128, 170), width=1)
    d.ellipse([cx - hr * 0.34, cy - hr * 0.34, cx + hr * 0.34, cy + hr * 0.34], fill=(22, 21, 18, 255))
    return over(img, lay)


def head_block(img, cx, cy, w, h, num):
    """A play head: a machined shield with a bright pole-piece gap against the tape, on two screws."""
    lay = layer()
    d = ImageDraw.Draw(lay)
    x0, y0, x1, y1 = int(cx - w // 2), int(cy - h // 2), int(cx + w // 2), int(cy + h // 2)
    # cast shadow under the block
    d.rounded_rectangle([x0 + 2, y0 + 5, x1 + 4, y1 + 6], radius=5, fill=(0, 0, 0, 130))
    # body
    d.rounded_rectangle([x0, y0, x1, y1], radius=5, fill=(52, 49, 42, 255))
    d.rounded_rectangle([x0, y0, x1, y1], radius=5, outline=(9, 8, 7, 255), width=1)
    d.line([(x0 + 5, y0 + 1), (x1 - 5, y0 + 1)], fill=(126, 119, 105, 140))
    d.line([(x0 + 5, y1 - 1), (x1 - 5, y1 - 1)], fill=(0, 0, 0, 200))
    # shield: a darker inset, offset away from the tape
    d.rounded_rectangle([x0 + 10, y0 + 9, x1 - 20, y1 - 9], radius=3, fill=(34, 32, 27, 255))
    d.line([(x0 + 12, y0 + 11), (x1 - 22, y0 + 11)], fill=(84, 79, 69, 140))
    # pole piece: a bright narrow face at the tape side, with the gap down its middle
    d.rectangle([x1 - 16, y0 + 8, x1 - 6, y1 - 8], fill=(158, 151, 136, 255))
    d.line([(x1 - 16, y0 + 8), (x1 - 16, y1 - 8)], fill=(214, 206, 188, 200), width=1)
    d.line([(x1 - 11, y0 + 10), (x1 - 11, y1 - 10)], fill=(14, 12, 10, 255), width=2)
    for sy in (y0 + 6, y1 - 6):
        d.ellipse([x0 + 6, sy - 2, x0 + 10, sy + 2], fill=(14, 13, 11, 255))
        d.ellipse([x0 + 6, sy - 2, x0 + 10, sy + 2], outline=(104, 98, 86, 120))
    img = over(img, lay)
    lay = layer()
    d = ImageDraw.Draw(lay)
    tracked(d, (x0 - 17, cy), str(num), font("bold", 20), BONE + (225,), tracking=0.5, anchor="center",
            shadow=(0, 0, 0, 190))
    return over(img, lay)


def transport(img):
    """The three play heads against the tape, between the two reels: the instrument's identity.

    Geometry (screen coords): the supply reel lets the tape off at its right side into a top run, the run
    turns down the right edge past the three heads, and returns into the take-up reel at the bottom.
    """
    img = reel(img, 930, 244, 72)
    img = reel(img, 930, 512, 56, pack=0.58)
    img = tape_path(img, [(1002, 244), (1176, 244), (1176, 512), (1004, 512)])
    # tape-travel chevrons on the run, between the heads
    lay = layer()
    d = ImageDraw.Draw(lay)
    for y in (348, 432):
        d.line([(1172, y - 5), (1180, y), (1172, y + 5)], fill=(244, 234, 212, 190), width=2)
    img = over(img, lay)
    # three heads facing the vertical run
    for i, cy in enumerate((306, 390, 474)):
        img = head_block(img, 1118, cy, 104, 64, i + 1)
    img = caption(img, (930, 340), "SUPPLY", 8, DIM, 2.0)
    img = caption(img, (930, 424), "TAKE-UP", 8, DIM, 2.0)
    return img



def page_tape(tabs, pages):
    img = panel_base()
    img = vignette(img)
    img = frame_edges(img)
    img = masthead(img, "TAPE", "MOTOR AND TAPE STOCK  \u00b7  THREE PLAY HEADS  \u00b7  HEAD OUTPUT", 1, pages)
    img = rule(img, 44, 528, 804, col=RULE_DIM, a=110)
    img = transport(img)
    img = caption(img, (1054, 156), "THREE PLAY HEADS  \u00b7  ONE TAPE RUN", 9, BONE, 2.4)
    img = footer(img, 1, pages)
    return img


# ---------------------------------------------------------------- page 3: TONE
def page_tone(tabs, pages):
    img = panel_base()
    img = vignette(img)
    img = frame_edges(img)
    img = masthead(img, "TONE", "EQUALISATION  \u00b7  INPUT TRIM  \u00b7  SPACE", 2, pages)
    img = rule(img, 44, 508, 664, col=RULE_DIM, a=110)
    img = spring_tank(img, (742, 190, 1218, 438))
    img = caption(img, (980, 172), "SPRING REVERB TANK", 9, BONE, 2.6)
    img = recess(img, (742, 456, 1218, 578), radius=6)
    img = caption(img, (980, 482), "VERB SETS THE SPRING RETURN LEVEL", 9, BONE, 2.2)
    img = caption(img, (980, 510), "THE SPRING SEND IS ZERO IN EVERY MODE WITHOUT AN R", 8, DIM, 1.8)
    img = caption(img, (980, 546), "R  =  SPRING TANK ENGAGED", 9, AMBER, 2.4)
    img = footer(img, 2, pages)
    return img


# ---------------------------------------------------------------- main
def main():
    pages = ("PROGRAM", "TAPE", "TONE")
    tabs = read_layout()
    for name, fn in (("program", page_program), ("tape", page_tape), ("tone", page_tone)):
        img = fn(tabs, pages)
        p = os.path.join(OUT, "bg_%s.png" % name)
        img.convert("RGB").save(p, optimize=True)
        print("wrote", p)

    tile_pair("mode", 148, 62)
    tile_pair("age", 200, 48)
    bat_switch()


if __name__ == "__main__":
    main()
