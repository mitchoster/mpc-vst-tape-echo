#!/usr/bin/env python3
"""Shared look for the MPC Tape Echo skin: palette, geometry and text helpers.

One place for the numbers that the page artwork (make_plate.py), the knob filmstrip
(make_widgets.py), the VU filmstrip (make_vu.py) and the value mock-up (make_values.py)
must agree on, plus the same numbers written into vst/layout.conf. If a coordinate moves
here, move it there too -- the art is baked, the controls are placed by the layout, and
only these files know where the panel, a card or the meter sits.

Composition (Studio style, 2026-10-27 redesign; sibling reference: the MPC DJ FX 2 skin's
Shapey-derived layout): dark charcoal plate, a display panel on top that carries the real
VU plus the tape/head state, then a row of four parameter cards with one accent hue each.
The plugin area is 1280x628 device px; layout.conf is written in DEVICE pixels, the art in
the same page shifted by -86 (Y_OFF), so art_y = device_y - 86.

Needs Pillow. Fonts: Titillium Web, the same face MPC draws its live text in, so baked
captions and device-drawn names/values sit on one grid.
"""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 628           # the plugin area (device y 86..714 -> art y 0..628)
Y_OFF = 86                 # layout.conf device y -> art y
DEV = lambda y: y + Y_OFF  # art y -> device y (the layout's cy)

# ---------------------------------------------------------------- geometry (mirrors vst/layout.conf)
HEADER_H = 56
PANEL = (12, 62, 1268, 356)                  # x0, y0, x1, y1 of the display panel

# display panel zones (art px)
MODE_X = 30                                  # left column: mode block, left aligned
MODE_PLATE = (24, 88, 500, 152)              # the engraved plate the big mode name sits on
MODE_TXT_CY = 120                            # big live mode name (htext) centre
MODE_DESC_CY = 172                           # its one-line description (live, per mode)
MODE_CAP = (30, 72)

VU_WIN = (512, 82, 1008, 206)                # VU window: scale + trough
VU_TROUGH = (528, 138, 992, 184)             # the bar's well (the filmstrip draws inside it)
VU_METER = (760, 161, 464, 46)               # cx, cy, w, h -- the meter widget, art px
VU_SCALE_Y = 126                             # tick baseline

DELAY_CX, DELAY_CY = 1140, 118               # delay read-out plate centre, art px
DELAY_W, DELAY_H = 212, 56
DELAY_CAP = (1028, 70)

TAPE_WELL = (30, 212, 1250, 344)             # the transport window under the panel row

# card row (art px); the four cards are 310 px wide, 8 px apart, 8 px margin
CARDS_Y = 366
CARDS_H = 248
CARD_COUNT = 4
CARD_W = 310
CARD_GAP = 8
CARD_X0 = 8
CARD_PAD = 14
CARD_TITLE_Y = 378                            # title text top
CARD_SUB_DX = 9                               # the sub line starts this far right of the title
CARD_HINT_Y = 442                             # first hint line under an enum
CARD_ENUM_CY = 414                            # enum_h centre (first row) in ART px
CARD_KNOB_CY = 512                            # knob row centre in ART px
CARD_CELL = 68                                # knob cell width (4 cells = 272 inside 310)
KNOB_R = 22                                   # knob radius (the filmstrip is 2r+10 wide)


def card_x(i):
    """Left edge of card i (0..3) in art pixels."""
    return CARD_X0 + i * (CARD_W + CARD_GAP)


def card_cx(i):
    return card_x(i) + CARD_W // 2


def knob_offsets(n):
    """Centre offsets of n knobs inside a card, CARD_CELL apart and centred on the card."""
    return [round((k - (n - 1) / 2.0) * CARD_CELL) for k in range(n)]


def knob_x(i, k, n):
    """Centre x of knob k of n on card i (art px). The layout must use cx + 0 (same column)."""
    return card_cx(i) + knob_offsets(n)[k]

# ---------------------------------------------------------------- palette
BG = (10, 12, 15)             # page
BG_HI = (16, 19, 23)          # vignette centre
PANEL_TOP = (19, 23, 28)
PANEL_BOT = (14, 17, 21)
PANEL_EDGE = (40, 45, 53)
CARD_TOP = (31, 36, 43)
CARD_BOT = (22, 26, 32)
CARD_EDGE = (42, 48, 56)
WELL = (11, 13, 17)           # recessed areas (VU window, transport window, read-out plate)
WELL_EDGE = (36, 42, 51)

INK = (233, 236, 240)
INK_DIM = (143, 152, 162)
INK_FAINT = (92, 100, 110)
GRID_LINE = (36, 42, 51)
WHITE = (255, 255, 255)

# one accent hue per card (cap + title); the meter and the knobs stay one warm pair
AMBER = (224, 163, 58)
CYAN = (79, 184, 217)
GREEN = (92, 192, 122)
VIOLET = (155, 134, 232)
BLUE = (94, 143, 232)
MAGENTA = (217, 107, 176)
TEAL = (69, 196, 176)
ORANGE = (232, 118, 58)
RED = (224, 82, 82)

ARC = (224, 163, 58)          # knob value arc (one hardware part across all cards)
VU_LO = (214, 158, 54)        # VU fill, low
VU_HI = (232, 118, 58)        # VU fill, high
VU_HOT = (226, 74, 62)        # VU fill, top of the scale
TAPE_BAND = (38, 42, 48)      # the tape band in the transport window
TAPE_EDGE = (72, 78, 88)

FONT_DIRS = ("/mv/tools/html_art/fonts", os.path.join(os.path.dirname(__file__), "fonts"),
             "/usr/share/fonts/truetype/dejavu")
FONTS = {"regular": "TitilliumWeb-Regular.ttf", "semi": "TitilliumWeb-SemiBold.ttf",
         "bold": "TitilliumWeb-Bold.ttf"}
FALLBACK = {"regular": "DejaVuSans.ttf", "semi": "DejaVuSans-Bold.ttf", "bold": "DejaVuSans-Bold.ttf"}


def font(kind, size):
    for d in FONT_DIRS:
        for name in (FONTS[kind], FALLBACK[kind]):
            p = os.path.join(d, name)
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    pass
    return ImageFont.load_default()


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def rgba(c, a=255):
    return (c[0], c[1], c[2], a)


# ---------------------------------------------------------------- drawing helpers
def vgrad(size, top, bot):
    """A vertical gradient image."""
    w, h = size
    strip = Image.new("RGB", (1, max(2, h)))
    for y in range(strip.size[1]):
        strip.putpixel((0, y), lerp(top, bot, y / (strip.size[1] - 1)))
    return strip.resize((w, h))


def plate(img, box, radius, top, bot, edge, width=1, shadow=0):
    """A rounded panel with a vertical gradient, a 1 px edge and an optional soft drop shadow."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if shadow:
        sh = Image.new("RGBA", (w + 2 * shadow, h + 2 * shadow), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([shadow, shadow, shadow + w, shadow + h], radius=radius,
                                             fill=(0, 0, 0, 110))
        sh = sh.filter(ImageFilter.GaussianBlur(shadow * 0.7))
        img.paste(sh, (x0 - shadow, y0 - shadow + 2), sh)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    img.paste(vgrad((w, h), top, bot), (x0, y0), mask)
    if edge:
        ImageDraw.Draw(img).rounded_rectangle([x0, y0, x1 - 1, y1 - 1], radius=radius, outline=edge, width=width)
    return mask


def well(img, d, box, radius=8, fill=WELL):
    """A recessed window: dark fill, dark top edge, a hairline of light along the bottom."""
    x0, y0, x1, y1 = box
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill, outline=WELL_EDGE, width=1)
    d.line([(x0 + radius, y0 + 1), (x1 - radius, y0 + 1)], fill=(6, 7, 9), width=1)
    d.line([(x0 + radius, y1 - 1), (x1 - radius, y1 - 1)], fill=(46, 52, 61), width=1)


def tracked(d, xy, s, fnt, fill, tracking=0.0, anchor="l"):
    """Draw text with letter spacing; anchor l/m/r around x."""
    x, y = xy
    if anchor != "l":
        total = sum(d.textlength(c, font=fnt) + tracking for c in s) - tracking
        x -= total if anchor == "r" else total / 2.0
    for c in s:
        d.text((x, y), c, font=fnt, fill=fill)
        x += d.textlength(c, font=fnt) + tracking
    return x


def cap(d, xy, s, size=10, fill=INK_DIM, tracking=1.6, weight="semi", anchor="l"):
    """A small letterspaced caption (the skin's caption style)."""
    tracked(d, xy, s.upper(), font(weight, size), fill, tracking, anchor)


def grain(img, amount=5):
    """Faint sensor-style noise so large dark areas don't band; deterministic."""
    noise = Image.effect_noise((W, H), amount).convert("L")
    noise = noise.filter(ImageFilter.GaussianBlur(0.4))
    img.paste(Image.blend(img, Image.merge("RGB", (noise, noise, noise)), 0.05))


def vignette(img):
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).ellipse([-W * 0.30, -H * 0.55, W * 1.30, H * 1.55], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(90))
    dark = Image.new("RGB", (W, H), (0, 0, 0))
    img.paste(Image.composite(img, dark, m))
