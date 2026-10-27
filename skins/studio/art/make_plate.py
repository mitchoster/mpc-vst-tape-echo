#!/usr/bin/env python3
"""Draw the page plates for the MPC Tape Echo skin (1280x628, one PNG per tab).

Composition (Studio style, 2026-10-27): header strip, one display panel that carries the
tape-echo state -- the big engraved mode name, the real VU window with its scale, the delay
read-out, and a transport window with the three heads and the spring tank -- then a row of
four parameter cards (310 px wide, 8 px apart), one accent hue per card.

Everything static is baked here; vst/layout.conf only places the live controls on top:
  * the 12 mode names + their description lines are `text when=mode:<option>` lines in the
    layout (MPC swaps them per mode; verified live on this port since 2026-10-14),
  * the VU bar is a 24-frame filmstrip (vst/art/make_vu.py) inside the trough drawn here,
  * the delay time is a `readout` on its baked plate.
Rules kept: no text where MPC draws a live name or value, and the areas where controls sit
stay calm enough for the live text to read.

  docker run --rm -v <framework>:/mv:ro -v <port>:/w -w /w mpc-vst-html-art \\
      python3 vst/art/make_plate.py -o vst
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import look as L  # noqa: E402


def card(title, accent, sub, hints=(), hint_y=None):
    return {"title": title, "accent": accent, "sub": sub, "hints": list(hints),
            "hint_y": L.CARD_HINT_Y if hint_y is None else hint_y}


PAGES = {
    "tape": {
        "tag": "TAPE",
        "file": "bg_tape.png",
        "cards": [
            card("MODE \u00b7 HEADS", L.AMBER, "12-WAY SELECTOR",
                 ["12 MODES = HEAD + SPRING COMBOS",
                  "MODE SETS THE LEADING HEAD",
                  "SYNC DIVISION FOLLOWS THAT HEAD"], hint_y=556),
            card("TAPE", L.CYAN, "AGE \u00b7 RATE \u00b7 FEEDBACK",
                 ["AGE SCALES THE FLUTTER", "RATE IS TIME'S RAW HALF"]),
            card("TONE", L.TEAL, "EQ \u00b7 DRIVE",
                 ["BASS + TREBLE = TAPE EQ", "TILT TIPS THE TAPE TONE", "DRIVE = INPUT GAIN"]),
            card("ECHO \u00b7 VERB", L.VIOLET, "SEND \u00b7 RETURN",
                 ["MIX LIVES ON THE OUT PAGE", "VERB = SPRING RETURN"]),
        ],
    },
    "sync": {
        "tag": "SYNC \u00b7 OUT",
        "file": "bg_sync.png",
        "cards": [
            card("SYNC \u00b7 TIME", L.CYAN, "DIV \u00b7 TIME",
                 ["SYNC SWITCH IS IN THE HEADER", "TIME SHOWS THE NOTE WHEN SYNCED"]),
            card("INPUT", L.ORANGE, "ARM \u00b7 DRIVE",
                 ["ARM = RECORD SEND", "DRIVE FEEDS THE RECORD HEAD"]),
            card("OUTPUT", L.BLUE, "MIX \u00b7 WIDTH",
                 ["MIX = DRY / WET", "WIDTH 0 = MONO", "PONG IS IN THE HEADER"]),
            card("VU \u00b7 CAL", L.MAGENTA, "METER TRIM",
                 ["TRIMMED 50 - 300 %", "METER ONLY \u00b7 NOT THE AUDIO"], hint_y=478),
        ],
    },
}

# the mode's own head/spring code, explained once in the transport window
HEAD_CODE = ("H1 H2 H3 = ONE HEAD EACH",
             "H2+3 = TWO HEADS TOGETHER",
             "R = SPRING TANK ADDED",
             "REV = SPRING TANK ONLY")


def header(img, d, tag):
    d.rectangle([0, 0, L.W, L.HEADER_H], fill=(16, 19, 23))
    d.line([(0, L.HEADER_H), (L.W, L.HEADER_H)], fill=(35, 40, 48), width=1)
    # accent block + product name + page tag (MPC does not draw tab names, so the page is named here)
    d.rectangle([24, 17, 28, 39], fill=L.AMBER)
    L.tracked(d, (40, 8), "MPC TAPE ECHO", L.font("bold", 27), L.INK, 1.4)
    L.tracked(d, (258, 22), tag, L.font("semi", 11), L.AMBER, 2.6)
    # captions for the two header switches (the controls themselves are placed by the layout)
    L.cap(d, (933, 24), "sync", 10, L.INK_DIM, 1.4, anchor="r")
    L.cap(d, (1113, 24), "pong", 10, L.INK_DIM, 1.4, anchor="r")


def mode_block(img, d):
    """Left column: the big mode name sits on an engraved plate; its description line is live."""
    L.cap(d, L.MODE_CAP, "mode \u00b7 head select", 10, L.INK_FAINT, 1.8)
    x0, y0, x1, y1 = L.MODE_PLATE
    L.plate(img, L.MODE_PLATE, 7, (24, 28, 34), (17, 20, 25), (44, 50, 59), width=1)
    d.line([(x0 + 7, y1 - 1), (x1 - 7, y1 - 1)], fill=(56, 63, 73), width=1)   # engraved lower lip


def vu_window(img, d):
    """The real VU: a printed scale above a recessed trough; the filmstrip draws the bar."""
    x0, y0, x1, y1 = L.VU_WIN
    L.well(img, d, L.VU_WIN, 8)
    L.cap(d, (x0 + 16, y0 + 8), "vu", 10, L.INK_DIM, 1.8)
    L.cap(d, (x1 - 16, y0 + 8), "output level", 10, L.INK_FAINT, 1.6, anchor="r")
    tx0, ty0, tx1, ty1 = L.VU_TROUGH
    base = L.VU_SCALE_Y
    # graduated scale: 8 long marks, 3 short ones between each -- unnumbered on purpose (the
    # engine publishes a linear 0..23 step, not a dB value, so printed dB numerals would lie)
    steps = 24
    for i in range(steps + 1):
        x = tx0 + (tx1 - tx0) * i / steps
        long_mark = i % 3 == 0
        d.line([(x, base - (14 if long_mark else 7)), (x, base)],
               fill=(64, 72, 84) if long_mark else (44, 50, 59), width=1)
    d.line([(tx0, base), (tx1, base)], fill=L.GRID_LINE, width=1)
    # the trough the bar fills, with segment ticks under the fill so the 24 steps read
    d.rounded_rectangle([tx0, ty0, tx1, ty1], radius=6, fill=(8, 10, 13), outline=(38, 44, 53), width=1)
    for i in range(1, 8):
        x = tx0 + 6 + (tx1 - tx0 - 12) * i / 8.0
        d.line([(x, ty1 - 7), (x, ty1 - 3)], fill=(54, 60, 70), width=1)
    L.cap(d, (tx0, ty1 + 5), "quiet", 9, L.INK_FAINT, 1.4)
    L.cap(d, (tx1, ty1 + 5), "hot", 9, L.INK_FAINT, 1.4, anchor="r")


def delay_block(img, d):
    x0, y0 = L.DELAY_CX - L.DELAY_W // 2, L.DELAY_CY - L.DELAY_H // 2
    x1, y1 = x0 + L.DELAY_W, y0 + L.DELAY_H
    L.cap(d, L.DELAY_CAP, "delay time", 10, L.INK_FAINT, 1.8)
    L.well(img, d, (x0, y0, x1, y1), 6)
    L.cap(d, (x0, y1 + 10), "ms \u00b7 note while synced", 9, L.INK_FAINT, 1.0)
    d.line([(x0, y1 + 30), (x1, y1 + 30)], fill=L.GRID_LINE, width=1)
    L.cap(d, (x0, y1 + 38), "in \u00b7 tape \u00b7 heads \u00b7 spring", 9, L.INK_FAINT, 1.0)


def transport(img, d):
    """The tape visualisation: three heads on a tape band, plus the spring tank (baked, not live)."""
    x0, y0, x1, y1 = L.TAPE_WELL
    L.well(img, d, L.TAPE_WELL, 8)
    L.cap(d, (x0 + 16, y0 + 10), "tape path", 10, L.INK_FAINT, 1.8)
    for i, line in enumerate(HEAD_CODE):
        L.cap(d, (x0 + 16, y0 + 34 + 17 * i), line, 9, L.INK_FAINT, 1.0)
    bx0, bx1, by0, by1 = 320, 800, 250, 294
    L.plate(img, (bx0, by0, bx1, by1), 4, (44, 48, 55), (26, 29, 34), L.TAPE_EDGE, width=1)
    d.line([(bx0 + 4, by0 + 6), (bx1 - 4, by0 + 6)], fill=(58, 64, 74), width=1)
    for x in range(bx0 + 14, bx1 - 24, 16):        # the tape's own dashes, as a path marker
        d.line([(x, (by0 + by1) // 2), (x + 8, (by0 + by1) // 2)], fill=(30, 34, 40), width=1)
    d.polygon([(bx1 - 16, (by0 + by1) // 2 - 5), (bx1 - 6, (by0 + by1) // 2),
               (bx1 - 16, (by0 + by1) // 2 + 5)], fill=(96, 104, 116))
    # heads: three blocks pressing the band from below, one head gap each
    for n, cx in enumerate((380, 500, 620)):
        hx0, hx1, hy0, hy1 = cx - 44, cx + 44, by1, by1 + 44
        L.plate(img, (hx0, hy0, hx1, hy1), 4, (52, 57, 66), (30, 34, 40), (66, 73, 84), width=1)
        d.line([(cx - 12, hy0 + 2), (cx + 12, hy0 + 2)], fill=L.rgba(L.AMBER, 210), width=2)
        L.cap(d, (cx, hy1 - 15), "h%d" % (n + 1), 10, L.INK_DIM, 1.6, anchor="m")
    # capstan + pinch roller on the band
    for cx, r, fill in ((700, 19, (54, 59, 68)), (748, 11, (46, 51, 59))):
        d.ellipse([cx - r, (by0 + by1) // 2 - r, cx + r, (by0 + by1) // 2 + r],
                  fill=fill, outline=(78, 85, 97), width=1)
        d.ellipse([cx - 3, (by0 + by1) // 2 - 3, cx + 3, (by0 + by1) // 2 + 3], fill=(30, 34, 40))
    # divider + spring tank
    d.line([(830, y0 + 26), (830, y1 - 12)], fill=L.GRID_LINE, width=1)
    tx0, ty0, tx1, ty1 = 860, 238, 1220, 336
    L.plate(img, (tx0, ty0, tx1, ty1), 6, (24, 27, 32), (15, 17, 21), (52, 58, 68), width=1)
    L.cap(d, (tx0 + 14, ty0 + 10), "spring tank", 9, L.INK_FAINT, 1.4)
    sx0, sx1, sy = tx0 + 30, tx1 - 30, (ty0 + ty1) // 2 + 6
    d.line([(sx0 - 12, sy - 14), (sx0 - 12, sy + 14)], fill=(74, 80, 92), width=2)
    d.line([(sx1 + 12, sy - 14), (sx1 + 12, sy + 14)], fill=(74, 80, 92), width=2)
    pts = [(sx0 + (sx1 - sx0) * i / 34.0, sy + (9 if i % 2 else -9)) for i in range(35)]
    d.line(pts, fill=(120, 128, 142), width=2, joint="curve")
    L.cap(d, (tx1 - 14, ty1 - 20), "reverb return", 9, L.INK_FAINT, 1.2, anchor="r")


def cards(img, d, page):
    for i in range(L.CARD_COUNT):
        spec = page["cards"][i] if i < len(page["cards"]) else None
        x0 = L.card_x(i)
        x1 = x0 + L.CARD_W
        top = L.CARDS_Y
        bot = top + L.CARDS_H
        if spec is None:                      # an empty slot stays a plain card, never a hole
            L.plate(img, (x0, top, x1, bot), 9, (26, 30, 36), (18, 21, 26), (34, 39, 45), shadow=6)
            continue
        L.plate(img, (x0, top, x1, bot), 9, L.CARD_TOP, L.CARD_BOT, L.CARD_EDGE, shadow=6)
        # accent cap: the card's own colour, the only saturated thing on it besides its title
        d.rounded_rectangle([x0 + 2, top + 1, x1 - 3, top + 3], radius=1, fill=spec["accent"])
        f_title = L.font("bold", 13)
        end = L.tracked(d, (x0 + L.CARD_PAD, L.CARD_TITLE_Y), spec["title"].upper(), f_title,
                        spec["accent"], 1.3)
        if spec["sub"]:
            L.cap(d, (end + L.CARD_SUB_DX, L.CARD_TITLE_Y + 2), spec["sub"], 9.5, L.INK_FAINT, 1.1)
        for n, line in enumerate(spec["hints"]):
            L.cap(d, (x0 + L.CARD_PAD, spec["hint_y"] + 15 * n), line, 9, L.INK_FAINT, 1.0)


def draw_page(name, out_dir):
    page = PAGES[name]
    img = Image.new("RGB", (L.W, L.H), L.BG)
    L.grain(img)
    L.vignette(img)
    d = ImageDraw.Draw(img)
    header(img, d, page["tag"])
    panel(img, d)
    cards(img, d, page)
    path = os.path.join(out_dir, page["file"])
    img.save(path, optimize=True)
    return path


def panel(img, d):
    L.plate(img, L.PANEL, 12, L.PANEL_TOP, L.PANEL_BOT, L.PANEL_EDGE, shadow=8)
    mode_block(img, d)
    vu_window(img, d)
    delay_block(img, d)
    transport(img, d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="vst", help="output directory (default vst)")
    ap.add_argument("--page", default=None, help="draw one page (%s)" % ", ".join(PAGES))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for name in ([a.page] if a.page else list(PAGES)):
        print("wrote", draw_page(name, a.out))


if __name__ == "__main__":
    main()
