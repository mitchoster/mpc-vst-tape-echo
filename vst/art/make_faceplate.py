#!/usr/bin/env python3
"""Draw the RE-202-inspired faceplate background for the HTML skin (1280x628).

An homage, not a clone: dark metal chassis, a red accent rule and a recessed
window for the live VU (the meter itself is engine-driven;
see vst/art/make_vu.py). No Roland/Boss logos or exact trade dress; no text (MPC
draws the live knob names/values on top; see the mpc-vst-plugin skill,
"Background artwork" design rules -- keep the areas where controls sit
dark/low-contrast so the live labels read).

The window only makes sense on the MAIN tab (that is where the live `meter key=vu`
lives). TAPE and OUT reuse a plain variant without the window, so the recessed
hole does not show up empty there (2026-10-14).

Needs Pillow; run it in the browser-art image (built by build_port.sh when vst.json
has "art":"html"):

  docker run --rm -u "$(id -u):$(id -g)" -v <host project>:/w -w /w mpc-vst-html-art \
      python3 vst/art/make_faceplate.py -o vst/bg.png
  ... vst/art/make_faceplate.py --no-vu-window -o vst/bg_plain.png
"""
import argparse
import random

from PIL import Image, ImageDraw, ImageFilter

W, H = 1280, 628
R, G, B = 0, 1, 2


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vgrad(img, top, bot):
    d = ImageDraw.Draw(img)
    for y in range(H):
        d.line([(0, y), (W, y)], fill=lerp(top, bot, y / (H - 1)))


def brushed(img, y0, y1, strength=5, seed=7):
    """Fine horizontal brushed-metal streaks over a band (low contrast)."""
    rnd = random.Random(seed)
    px = img.load()
    for y in range(y0, y1):
        n = rnd.randint(-strength, strength)
        for x in range(W):
            r, g, b = px[x, y]
            px[x, y] = (max(0, min(255, r + n)), max(0, min(255, g + n)), max(0, min(255, b + n)))


def blotches(img, amount=7, cell=16, seed=3):
    """Low-frequency worn-metal unevenness: cheap value noise, barely visible."""
    rnd = random.Random(seed)
    sw, sh = max(1, W // cell), max(1, H // cell)
    small = Image.new("L", (sw, sh))
    small.putdata([rnd.randint(-amount, amount) for _ in range(sw * sh)])
    noise = small.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(cell / 2.0))
    px, np_ = img.load(), noise.load()
    for y in range(H):
        for x in range(W):
            n = np_[x, y] - 128
            if n:
                r, g, b = px[x, y]
                px[x, y] = (max(0, min(255, r + n)), max(0, min(255, g + n)), max(0, min(255, b + n)))


def soft_shadow(img, box, radius, alpha=110):
    """A soft dark drop shadow around a rounded rect, so recessed parts read."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = box
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=(0, 0, 0, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(12))
    img.alpha_composite(layer)


def vignette(img, strength=46):
    """Slightly darken the edges/corners so the plate reads as a lit object."""
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).ellipse([-W * 0.25, -H * 0.4, W * 1.25, H * 1.4], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(120))
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    dark.putalpha(mask.point(lambda v: int((255 - v) * strength / 255)))
    img.alpha_composite(dark)


def top_sheen(img, alpha=14):
    """A faint light wash from the top, like light falling on the chassis."""
    sheen = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(sheen)
    for y in range(H):
        a = int(alpha * (1 - y / (H * 0.5))) if y < H * 0.5 else 0
        if a > 0:
            d.line([(0, y), (W, y)], fill=(255, 255, 255, max(0, a)))
    img.alpha_composite(sheen)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="vst/bg.png")
    ap.add_argument("--no-vu-window", action="store_true",
                    help="omit the recessed VU window (use for tabs without the live meter)")
    ap.add_argument("--texture", default="vst/art/metal.png",
                    help="a base texture image (e.g. generated with ComfyUI); falls back to a drawn plate")
    a = ap.parse_args()

    import os
    if a.texture and os.path.exists(a.texture):
        base = Image.open(a.texture).convert("RGB").resize((W, H), Image.LANCZOS)
    else:
        base = Image.new("RGB", (W, H), (0, 0, 0))
        vgrad(base, (46, 47, 52), (22, 23, 26))          # charcoal body, lighter top
        brushed(base, 0, H, strength=4)
        blotches(base, amount=7, cell=18)

    # header band slightly darker (keeps the title strip calm) + red accent rule
    hdr = Image.new("RGB", (W, 150), (0, 0, 0))
    vgrad(hdr, (33, 34, 38), (44, 45, 50))
    base.paste(hdr, (0, 0))
    d = ImageDraw.Draw(base)
    d.rectangle([0, 150, W, 154], fill=(200, 16, 46))          # red accent rule
    d.rectangle([0, 154, W, 156], fill=(90, 9, 24))

    # main control plate (subtle inset panel)
    img = base.convert("RGBA")
    soft_shadow(img, (24, 176, W - 24, H - 24), 18, alpha=90)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([24, 176, W - 24, H - 24], radius=18, fill=(30, 31, 35, 255),
                        outline=(60, 62, 68, 255), width=2)

    # recessed VU window (the live bar is drawn on top by the skin; no scale here so it is not doubled)
    if not a.no_vu_window:
        soft_shadow(img, (884, 456, 1212, 552), 12, alpha=120)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([880, 452, 1216, 556], radius=10, fill=(9, 10, 12, 255),
                            outline=(90, 92, 98, 255), width=3)

    # (no decorative footswitches: they collided with the bottom row's live value readouts)
    vignette(img)
    top_sheen(img)
    out = img.convert("RGB")
    out.save(a.out)
    print("wrote", a.out, out.size)


if __name__ == "__main__":
    main()
