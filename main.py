#!/usr/bin/env python3
"""News poster for Tuesday 17 November 2026.

Draws a 1024x1024 PNG summarising the day's world news: a big dated
header plus six story panels, each with a small pictogram scene, a
headline and one factual sub-label. Pure standard library, no network,
fully deterministic: the same bytes on every run.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 243, 234)      # warm newsprint background
NAVY = (16, 38, 63)         # header band and headlines
NAVY_SOFT = (38, 64, 92)
RED = (178, 44, 36)         # accent rule and flags
GOLD = (201, 148, 52)       # thin rule under the header
WHITE = (255, 255, 255)
CARD = (255, 255, 255)
CARD_EDGE = (205, 198, 182)
SUB = (74, 68, 58)          # sub-label grey-brown
SKY = (214, 231, 242)       # scene backgrounds
SKY2 = (226, 236, 224)
SKY3 = (238, 228, 214)
SKY4 = (220, 230, 240)
SKY5 = (232, 226, 238)
SKY6 = (224, 236, 232)
SEA = (110, 158, 196)
INK = (24, 40, 58)          # pictogram ink
MID = (90, 110, 130)

# ---------------------------------------------------------------- canvas


class Canvas:
    """A plain RGB pixel buffer with a few drawing helpers."""

    def __init__(self, width, height, bg):
        self.w = width
        self.h = height
        self.pix = bytearray(bg[0] for _ in range(width * height * 3))
        # fill properly: bytearray above repeats only the red channel,
        # so repaint every pixel through rect.
        self.rect(0, 0, width, height, bg)

    def set(self, x, y, colour):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.pix[i] = colour[0]
            self.pix[i + 1] = colour[1]
            self.pix[i + 2] = colour[2]

    def rect(self, x, y, w, h, colour):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.pix[i] = colour[0]
                self.pix[i + 1] = colour[1]
                self.pix[i + 2] = colour[2]

    def line(self, x0, y0, x1, y1, colour, thick=1):
        """Bresenham line, optionally thickened into a square brush."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        half = thick // 2
        while True:
            for ox in range(-half, half + 1):
                for oy in range(-half, half + 1):
                    self.set(x + ox, y + oy, colour)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def circle(self, cx, cy, r, colour, fill=False):
        if fill:
            for yy in range(cy - r, cy + r + 1):
                half = int((r * r - (yy - cy) ** 2) ** 0.5) if abs(yy - cy) <= r else 0
                for xx in range(cx - half, cx + half + 1):
                    self.set(xx, yy, colour)
            return
        x = 0
        y = r
        d = 3 - 2 * r
        while x <= y:
            for px, py in ((cx + x, cy + y), (cx - x, cy + y),
                           (cx + x, cy - y), (cx - x, cy - y),
                           (cx + y, cy + x), (cx - y, cy + x),
                           (cx + y, cy - x), (cx - y, cy - x)):
                self.set(px, py, colour)
            if d < 0:
                d += 4 * x + 6
            else:
                d += 4 * (x - y) + 10
                y -= 1
            x += 1

    def arc(self, cx, cy, r, a0, a1, colour):
        """Quarter-ish arc by angle in degrees, 0 = east, going clockwise."""
        steps = max(8, r * 2)
        for k in range(steps + 1):
            a = math.radians(a0 + (a1 - a0) * k / steps)
            self.set(int(cx + r * math.cos(a)), int(cy + r * math.sin(a)), colour)


# ---------------------------------------------------------------- 5x7 font
# Each glyph is 7 rows of 5 pixels, "#" = on, "." = off. Hand-drawn here.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "00000", "01100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ":": ("00000", "01100", "00000", "00000", "00000", "01100", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    ";": ("00000", "01100", "00000", "00000", "01100", "01100", "01000"),
}


def text_width(text, scale):
    """Advance width in pixels of `text` at this scale (6 units per char)."""
    return len(text) * 6 * scale


def draw_text(cv, x, y, text, scale, colour):
    """Draw uppercase text; glyphs are 5x7 scaled by `scale`."""
    cx = x
    for ch in text:
        glyph = FONT.get(ch, FONT[" "])
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit == "1":
                    cv.rect(cx + gx * scale, y + gy * scale, scale, scale, colour)
        cx += 6 * scale
    return cx


def wrap_text(text, max_width, scale):
    """Greedy word wrap; returns a list of lines fitting max_width."""
    words = text.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- scenes
# Each scene draws a simple pictogram inside the box (bx, by, bw, bh).

def scene_bridge(cv, bx, by, bw, bh):
    water_y = by + bh - 26
    cv.rect(bx, water_y, bw, 26, SEA)
    for wx in range(bx + 8, bx + bw - 8, 34):
        cv.line(wx, water_y + 9, wx + 16, water_y + 9, WHITE, 2)
        cv.line(wx + 6, water_y + 18, wx + 22, water_y + 18, WHITE, 2)
    deck_y = by + 58
    # deck in two spans with a broken gap in the middle
    cv.rect(bx + 12, deck_y, 180, 5, INK)
    cv.rect(bx + bw - 192, deck_y, 180, 5, INK)
    # fallen span, tilted down into the water
    cv.line(bx + 198, deck_y + 2, bx + 252, water_y + 4, INK, 4)
    cv.line(bx + 206, deck_y + 6, bx + 240, deck_y + 16, RED, 2)
    # towers
    for tx in (bx + 84, bx + bw - 108):
        cv.rect(tx, deck_y - 46, 8, 46, INK)
        cv.rect(tx - 4, deck_y - 52, 16, 6, INK)
    # cables from tower tops to the deck
    cv.line(bx + 88, deck_y - 46, bx + 20, deck_y, MID, 1)
    cv.line(bx + 88, deck_y - 46, bx + 178, deck_y, MID, 1)
    cv.line(bx + bw - 100, deck_y - 46, bx + bw - 186, deck_y, MID, 1)
    cv.line(bx + bw - 100, deck_y - 46, bx + bw - 20, deck_y, MID, 1)
    # smoke puffs over the gap
    cv.circle(bx + 222, deck_y - 16, 7, MID, fill=True)
    cv.circle(bx + 234, deck_y - 26, 9, (150, 160, 170), fill=True)
    cv.circle(bx + 214, deck_y - 30, 6, (150, 160, 170), fill=True)


def scene_drones(cv, bx, by, bw, bh):
    # radar dish on the left
    base_x = bx + 70
    cv.rect(base_x - 4, by + bh - 34, 8, 34, INK)
    cv.rect(base_x - 26, by + bh - 8, 52, 8, INK)
    cv.line(base_x, by + 34, base_x - 34, by + 62, INK, 3)
    cv.line(base_x, by + 34, base_x + 34, by + 62, INK, 3)
    cv.arc(base_x, by + 62, 34, 180, 360, INK)
    cv.line(base_x, by + 34, base_x + 26, by + 14, RED, 2)
    # three drones crossing the sky
    for dx, dy, s in ((bx + 220, by + 26, 1), (bx + 300, by + 48, 1),
                      (bx + 380, by + 22, 1)):
        cv.line(dx - 14, dy - 8, dx + 14, dy + 8, INK, 3)
        cv.line(dx - 14, dy + 8, dx + 14, dy - 8, INK, 3)
        cv.circle(dx, dy, 4, INK, fill=True)
        cv.line(dx - 22, dy - 12, dx - 14, dy - 12, MID, 2)
        cv.line(dx + 14, dy - 12, dx + 22, dy - 12, MID, 2)
    # dashed interception lines from the radar
    for i in range(6):
        x0 = base_x + 30 + i * 26
        cv.line(x0, by + 44, x0 + 12, by + 44, RED, 2)
    # burst where one drone is hit
    hx, hy = bx + 380, by + 22
    for ang in range(0, 360, 45):
        r = 16
        cv.line(hx, hy, int(hx + r * math.cos(math.radians(ang))),
                int(hy + r * math.sin(math.radians(ang))), RED, 2)


def scene_summit(cv, bx, by, bw, bh):
    # three flags on poles above a table
    table_y = by + bh - 22
    cv.rect(bx + 60, table_y, bw - 120, 6, INK)
    cv.rect(bx + 80, table_y + 6, 8, 16, INK)
    cv.rect(bx + bw - 88, table_y + 6, 8, 16, INK)
    flags = [
        (bx + 92, RED, "CN"),
        (bx + 212, NAVY_SOFT, "US"),
        (bx + 332, MID, "RU"),
    ]
    for fx, _, _ in flags:
        cv.rect(fx, by + 12, 4, table_y - by - 12, INK)
    # China flag: red field, yellow stars
    cv.rect(bx + 96, by + 12, 52, 32, RED)
    cv.circle(bx + 108, by + 24, 4, GOLD, fill=True)
    cv.circle(bx + 124, by + 18, 2, GOLD, fill=True)
    cv.circle(bx + 128, by + 28, 2, GOLD, fill=True)
    # US flag: stripes and blue canton
    for k in range(4):
        cv.rect(bx + 216, by + 12 + k * 8, 52, 4, RED)
        cv.rect(bx + 216, by + 16 + k * 8, 52, 4, WHITE)
    cv.rect(bx + 216, by + 12, 24, 16, NAVY)
    for sx in (222, 230, 238):
        for sy in (16, 24):
            cv.set(sx, sy, WHITE)
    # Russia flag: white, blue, red bands
    cv.rect(bx + 336, by + 12, 52, 11, WHITE)
    cv.rect(bx + 336, by + 23, 52, 10, (30, 90, 180))
    cv.rect(bx + 336, by + 33, 52, 11, RED)
    # three heads behind the table
    for hx in (bx + 118, bx + 238, bx + 358):
        cv.circle(hx, table_y - 8, 10, (196, 150, 110), fill=True)
        cv.rect(hx - 12, table_y - 2, 24, 4, NAVY_SOFT)


def scene_jets(cv, bx, by, bw, bh):
    # dashed airspace boundary down the middle
    for yy in range(by + 8, by + bh - 8, 16):
        cv.rect(bx + bw // 2, yy, 3, 9, RED)
    # two fighter jets, drawn as fuselage + swept wings
    for jx, jy in ((bx + 130, by + 34), (bx + 300, by + 70)):
        cv.line(jx - 52, jy, jx + 52, jy, INK, 4)
        cv.line(jx + 52, jy, jx + 66, jy - 4, INK, 3)
        cv.line(jx - 10, jy, jx - 34, jy - 22, INK, 3)
        cv.line(jx - 6, jy, jx - 30, jy + 20, INK, 3)
        cv.line(jx + 20, jy, jx + 6, jy - 14, INK, 3)
        cv.circle(jx + 30, jy - 3, 5, NAVY_SOFT, fill=True)
        # motion streaks
        cv.line(jx - 58, jy - 8, jx - 96, jy - 8, MID, 2)
        cv.line(jx - 58, jy + 8, jx - 90, jy + 8, MID, 2)
    # sun and clouds
    cv.circle(bx + bw - 44, by + 22, 12, GOLD, fill=True)
    cv.circle(bx + 60, by + 88, 10, WHITE, fill=True)
    cv.circle(bx + 76, by + 88, 12, WHITE, fill=True)


def scene_scales(cv, bx, by, bw, bh):
    cx = bx + bw // 2 - 60
    base_y = by + bh - 14
    # scales of justice
    cv.rect(cx - 26, base_y, 52, 6, INK)
    cv.rect(cx - 3, by + 26, 6, base_y - by - 26, INK)
    cv.line(cx - 58, by + 34, cx + 58, by + 34, INK, 3)
    for px in (cx - 58, cx + 58):
        cv.line(px, by + 34, px - 16, by + 66, INK, 2)
        cv.line(px, by + 34, px + 16, by + 66, INK, 2)
        cv.arc(px, by + 66, 16, 0, 180, INK)
        cv.line(px - 16, by + 66, px + 16, by + 66, INK, 2)
    cv.circle(cx, by + 30, 6, GOLD, fill=True)
    # gavel on the right
    gx, gy = bx + bw - 130, by + 44
    cv.line(gx, gy, gx + 56, gy + 40, (120, 82, 40), 5)
    cv.rect(gx + 48, gy + 28, 34, 16, (120, 82, 40))
    cv.rect(gx + 42, gy + 24, 6, 24, (120, 82, 40))
    # sound block
    cv.rect(bx + bw - 96, base_y - 8, 52, 8, INK)


def scene_tower(cv, bx, by, bw, bh):
    cx = bx + 120
    base_y = by + bh - 12
    # lattice radio tower
    cv.line(cx - 34, base_y, cx - 6, by + 18, INK, 3)
    cv.line(cx + 34, base_y, cx + 6, by + 18, INK, 3)
    for k in range(4):
        yy = base_y - 12 - k * 18
        half = 30 - k * 6
        cv.line(cx - half, yy, cx + half, yy, INK, 2)
        cv.line(cx - half, yy, cx + half, yy + 16, MID, 1)
        cv.line(cx + half, yy, cx - half, yy + 16, MID, 1)
    cv.line(cx, by + 18, cx, by + 6, RED, 3)
    cv.circle(cx, by + 6, 4, RED, fill=True)
    # signal arcs to the right
    for r in (26, 44, 62):
        cv.arc(cx + 60, by + 44, r, -55, 55, RED)
    # a small phone receiving the signal
    px, py = bx + bw - 130, by + 52
    cv.rect(px, py, 44, 64, NAVY)
    cv.rect(px + 5, py + 8, 34, 40, (180, 220, 240))
    cv.line(px + 10, py + 18, px + 34, py + 18, NAVY, 2)
    cv.line(px + 10, py + 26, px + 30, py + 26, NAVY, 2)
    cv.line(px + 10, py + 34, px + 26, py + 34, NAVY, 2)
    cv.circle(px + 22, py + 56, 3, WHITE, fill=True)


# ---------------------------------------------------------------- stories

STORIES = [
    ("UKRAINE HITS KERCH BRIDGE",
     "Road span collapses in 2nd night of strikes; Kyiv bridges hit in reply",
     SKY, scene_bridge),
    ("IRAN FIRES DRONES AT US RADAR IN BAHRAIN",
     "Intercepted, no damage; tankers hit by mines near Hormuz",
     SKY2, scene_drones),
    ("XI, TRUMP AND PUTIN TO MEET IN SHENZHEN",
     "China confirms first three-way talks, Thursday 19 Nov",
     SKY3, scene_summit),
    ("JAPAN SCRAMBLES FIGHTERS",
     "Two suspected Russian planes violate airspace; Tokyo protests",
     SKY4, scene_jets),
    ("UK SANCTIONS WEST BANK SETTLEMENT BUILDERS",
     "8 firms named; UK, Australia, Canada, Italy urge Gaza aid access",
     SKY5, scene_scales),
    ("NO BLACKOUT: US TESTS EMERGENCY ALERTS",
     "FEMA-FCC test 2:20pm ET; viral shutdown rumour false",
     SKY6, scene_tower),
]


def draw_panel(cv, x, y, w, h, headline, sub, scene_bg, scene_fn):
    headline = headline.upper()
    sub = sub.upper()
    cv.rect(x, y, w, h, CARD)
    cv.rect(x, y, w, 2, CARD_EDGE)
    cv.rect(x, y, 2, h, CARD_EDGE)
    cv.rect(x + w - 2, y, 2, h, CARD_EDGE)
    cv.rect(x, y + h - 2, w, 2, CARD_EDGE)
    # scene band
    sx, sy, sw, sh = x + 12, y + 12, w - 24, 112
    cv.rect(sx, sy, sw, sh, scene_bg)
    scene_fn(cv, sx, sy, sw, sh)
    # headline, scale 3, wrapped to the panel width
    tx = x + 16
    max_w = w - 32
    lines = wrap_text(headline, max_w, 3)
    hy = y + 140
    for line in lines:
        draw_text(cv, tx, hy, line, 3, NAVY)
        hy += 27
    # sub-label, scale 2
    sub_lines = wrap_text(sub, max_w, 2)
    sy2 = hy + 6
    for line in sub_lines:
        draw_text(cv, tx, sy2, line, 2, SUB)
        sy2 += 18


# ---------------------------------------------------------------- PNG


def encode_png(width, height, pixels):
    """Minimal deterministic PNG: 8-bit RGB, filter 0, zlib level 6."""

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return out

    raw = bytearray()
    stride = width * 3
    for yy in range(height):
        raw.append(0)
        raw += pixels[yy * stride:(yy + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
            + chunk(b"IEND", b""))


def build_image():
    cv = Canvas(W, H, PAPER)
    # header band
    cv.rect(0, 0, W, 170, NAVY)
    cv.rect(0, 170, W, 4, RED)
    title = "TUESDAY 17 NOVEMBER 2026"
    tx = (W - text_width(title, 6)) // 2
    draw_text(cv, tx, 34, title, 6, WHITE)
    subtitle = "THE WORLD IN ONE IMAGE"
    sx = (W - text_width(subtitle, 3)) // 2
    draw_text(cv, sx, 108, subtitle, 3, GOLD)
    # small red diamonds flanking the subtitle
    for dx in (sx - 34, sx + text_width(subtitle, 3) + 22):
        cv.rect(dx, 116, 10, 10, RED)
    # six panels: 2 columns x 3 rows
    panel_w, panel_h = 488, 266
    xs = (16, 520)
    ys = (186, 466, 746)
    for i, (headline, sub, bg, fn) in enumerate(STORIES):
        draw_panel(cv, xs[i % 2], ys[i // 2], panel_w, panel_h,
                   headline, sub, bg, fn)
    return cv.pix


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = encode_png(W, H, build_image())
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(data)


if __name__ == "__main__":
    main()
