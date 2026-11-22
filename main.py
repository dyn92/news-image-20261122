#!/usr/bin/env python3
"""news-image-20261122 -- sum up 22 November 2026's world news in one image.

Draws a deterministic 1024x1024 newspaper front page (six stories) as a
PNG using only the Python standard library.  Every pixel is produced by
code below: a small raster canvas, a hand-built 5x7 bitmap font, simple
shape primitives, and a hand-rolled PNG encoder (zlib + struct).

No network access, no third-party packages, no embedded image files.
Run twice and the output bytes are identical.

Usage:
    MAKEFUN_OUTPUT_DIR=out python3 main.py   # writes out/entry.png
    python3 main.py                           # writes /output/entry.png
"""

import binascii
import os
import struct
import zlib

# ---------------------------------------------------------------- font ----
# Hand-built 5x7 bitmap font.  Each glyph is 7 rows; each row is a 5-bit
# integer where the most significant bit is the leftmost pixel.
# Only uppercase letters, digits and common punctuation are included:
# the poster is set entirely in capitals, newspaper style.
FONT = {
    "A": (0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "B": (0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110),
    "C": (0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110),
    "D": (0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110),
    "E": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111),
    "F": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000),
    "G": (0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01111),
    "H": (0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "I": (0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "J": (0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100),
    "K": (0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001),
    "L": (0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111),
    "M": (0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001),
    "N": (0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001),
    "O": (0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "P": (0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000),
    "Q": (0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101),
    "R": (0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001),
    "S": (0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110),
    "T": (0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    "U": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "V": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100),
    "W": (0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b10101, 0b01010),
    "X": (0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001),
    "Y": (0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100),
    "Z": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111),
    "0": (0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110),
    "1": (0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "2": (0b01110, 0b10001, 0b00001, 0b00110, 0b01000, 0b10000, 0b11111),
    "3": (0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110),
    "4": (0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010),
    "5": (0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110),
    "6": (0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110),
    "7": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000),
    "8": (0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110),
    "9": (0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100),
    " ": (0, 0, 0, 0, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 0b01100, 0b01100),
    ",": (0, 0, 0, 0, 0b01100, 0b00100, 0b01000),
    ":": (0, 0b01100, 0b01100, 0, 0b01100, 0b01100, 0),
    ";": (0, 0b01100, 0b01100, 0, 0b01100, 0b00100, 0b01000),
    "'": (0b00100, 0b00100, 0b01000, 0, 0, 0, 0),
    '"': (0b01010, 0b01010, 0b01010, 0, 0, 0, 0),
    "-": (0, 0, 0, 0b01110, 0, 0, 0),
    "!": (0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0, 0b00100),
    "?": (0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0, 0b00100),
    "(": (0b00010, 0b00100, 0b01000, 0b01000, 0b01000, 0b00100, 0b00010),
    ")": (0b01000, 0b00100, 0b00010, 0b00010, 0b00010, 0b00100, 0b01000),
    "/": (0b00001, 0b00010, 0b00010, 0b00100, 0b01000, 0b01000, 0b10000),
    "&": (0b01100, 0b10010, 0b10100, 0b01000, 0b10101, 0b10010, 0b01101),
    "%": (0b11001, 0b11010, 0b00010, 0b00100, 0b01000, 0b01011, 0b10011),
    "+": (0, 0b00100, 0b00100, 0b11111, 0b00100, 0b00100, 0),
    "=": (0, 0, 0b11111, 0, 0b11111, 0, 0),
    "$": (0b00100, 0b01111, 0b10100, 0b01110, 0b00101, 0b11110, 0b00100),
    "*": (0, 0b10101, 0b01110, 0b11111, 0b01110, 0b10101, 0),
    "#": (0b01010, 0b01010, 0b11111, 0b01010, 0b11111, 0b01010, 0b01010),
}

CHAR_ADVANCE = 6  # glyph width (5) + 1 column gap, in font units


def text_width(text, scale):
    """Pixel width of `text` rendered at `scale`."""
    return len(text) * CHAR_ADVANCE * scale


def wrap_text(text, max_width, scale):
    """Greedy word wrap; returns a list of lines fitting max_width px."""
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if text_width(trial, scale) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# -------------------------------------------------------------- canvas ----
class Canvas:
    """A plain RGB raster buffer with small drawing primitives."""

    def __init__(self, width, height, color):
        self.w = width
        self.h = height
        self.px = bytearray(width * height * 3)
        self.fill(color)

    def fill(self, color):
        r, g, b = color
        self.px[:] = bytes((r, g, b)) * (self.w * self.h)

    def set_px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = color[0]
            self.px[i + 1] = color[1]
            self.px[i + 2] = color[2]

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        r, g, b = color
        row = bytes((r, g, b)) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def hline(self, x, y, w, color):
        self.fill_rect(x, y, w, 1, color)

    def vline(self, x, y, h, color):
        self.fill_rect(x, y, 1, h, color)

    def line(self, x0, y0, x1, y1, color):
        """Bresenham line."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set_px(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def polyline(self, points, color):
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            self.line(ax, ay, bx, by, color)

    def fill_triangle(self, ax, ay, bx, by, cx, cy, color):
        """Scanline-filled triangle."""
        pts = sorted(((ax, ay), (bx, by), (cx, cy)), key=lambda p: p[1])
        (x0, y0), (x1, y1), (x2, y2) = pts
        if y0 == y2:
            return
        for y in range(y0, y2 + 1):
            if y < y1:
                xa = x0 + (x1 - x0) * (y - y0) / (y1 - y0) if y1 != y0 else x0
                xb = x0 + (x2 - x0) * (y - y0) / (y2 - y0)
            else:
                xa = x1 + (x2 - x1) * (y - y1) / (y2 - y1) if y2 != y1 else x1
                xb = x0 + (x2 - x0) * (y - y0) / (y2 - y0)
            lo, hi = (int(xa), int(xb)) if xa <= xb else (int(xb), int(xa))
            self.fill_rect(lo, y, hi - lo + 1, 1, color)

    def circle(self, cx, cy, r, color):
        """Midpoint circle outline."""
        x, y = 0, r
        d = 1 - r
        while x <= y:
            for px, py in ((cx + x, cy + y), (cx - x, cy + y),
                           (cx + x, cy - y), (cx - x, cy - y),
                           (cx + y, cy + x), (cx - y, cy + x),
                           (cx + y, cy - x), (cx - y, cy - x)):
                self.set_px(px, py, color)
            if d < 0:
                d += 2 * x + 3
            else:
                d += 2 * (x - y) + 5
                y -= 1
            x += 1

    def fill_circle(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            half = int((r * r - (yy - cy) ** 2) ** 0.5)
            self.fill_rect(cx - half, yy, 2 * half + 1, 1, color)

    def rect_outline(self, x, y, w, h, color, thickness=1):
        for t in range(thickness):
            self.hline(x + t, y + t, w - 2 * t, color)
            self.hline(x + t, y + h - 1 - t, w - 2 * t, color)
            self.vline(x + t, y + t, h - 2 * t, color)
            self.vline(x + w - 1 - t, y + t, h - 2 * t, color)

    def draw_text(self, x, y, text, scale, color):
        """Draw upper-case text; unknown glyphs render as a blank."""
        cx = x
        for ch in text.upper():
            glyph = FONT.get(ch)
            if glyph is None:
                cx += CHAR_ADVANCE * scale
                continue
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits & (1 << (4 - col)):
                        self.fill_rect(cx + col * scale, y + row * scale,
                                       scale, scale, color)
            cx += CHAR_ADVANCE * scale

    def draw_text_centered(self, cx, y, text, scale, color):
        self.draw_text(cx - text_width(text, scale) // 2, y, text, scale,
                       color)


# ------------------------------------------------------------ PNG encode ----
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
    return out


def encode_png(canvas):
    """Encode the canvas as a deterministic PNG (filter 0, zlib level 9)."""
    w, h = canvas.w, canvas.h
    raw = bytearray()
    row_bytes = w * 3
    for y in range(h):
        raw.append(0)  # filter type: none
        start = y * row_bytes
        raw += canvas.px[start:start + row_bytes]
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    return png

# --------------------------------------------------------------- content ----
# Six verified stories, all dated Saturday 21 November 2026 -- the latest
# full news day as of early Sunday 22 November 2026 (00:10 UTC), when this
# poster was built.  Facts checked against Reuters, AP, CNN, BBC, WSJ
# and Le Monde coverage.  Each panel carries its own honest date.
PANELS = [
    {
        "kicker": "GULF WAR - BAHRAIN",
        "date": "21 NOV 2026",
        "accent": (166, 30, 34),
        "headline": ("IRAN HITS US BASES", "IN BAHRAIN"),
        "body": ("TEHRAN CLAIMS STRIKES ON SHEIKH ISA AIR BASE AND THE "
                 "JUFFAIR NAVAL BASE, HOME OF THE US FIFTH FLEET. BAHRAIN "
                 "SAYS DEFENCES INTERCEPTED THE ATTACK; A CIVILIAN PLANT "
                 "WAS HIT AND CAUGHT FIRE."),
        "source": "SOURCE: FARS / AP / REUTERS",
        "icon": "missile",
    },
    {
        "kicker": "STRAIT OF HORMUZ - OMAN",
        "date": "21 NOV 2026",
        "accent": (14, 110, 106),
        "headline": ("TWO TANKERS HIT", "NEAR OMAN"),
        "body": ("UK MARITIME MONITORS SAY TWO TANKERS WERE STRUCK BY "
                 "PROJECTILES OFF KHASAB. IRAN SAYS ANOTHER TANKER HIT A "
                 "MINE AND CAUGHT FIRE. NO CASUALTIES WERE REPORTED."),
        "source": "SOURCE: REUTERS / UKMTO",
        "icon": "tanker",
    },
    {
        "kicker": "BALTIC SEA - FINLAND",
        "date": "21 NOV 2026",
        "accent": (46, 90, 136),
        "headline": ("RUSSIAN SHIP ABLAZE", "AFTER DRONE STRIKE"),
        "body": ("THE SANCTIONED CARGO SHIP SPARTA II, BOUND FOR "
                 "KALININGRAD, WAS HIT BY TWO DRONES AND CAUGHT FIRE. ITS "
                 "16 CREW WERE EVACUATED AS IT DRIFTED INTO FINNISH "
                 "WATERS."),
        "source": "SOURCE: REUTERS / CNN",
        "icon": "fire",
    },
    {
        "kicker": "MEXICO - SINALOA",
        "date": "21 NOV 2026",
        "accent": (138, 90, 24),
        "headline": ("FBI MOST-WANTED", "CARTEL BOSS SEIZED"),
        "body": ("FAUSTO ISIDRO MEZA FLORES, KNOWN AS EL CHAPO ISIDRO, "
                 "WAS CAPTURED IN GUASAVE. ELEVEN PEOPLE WERE KILLED AS "
                 "GUNMEN FOUGHT BACK. US INTELLIGENCE AIDED THE RAID."),
        "source": "SOURCE: REUTERS / AP",
        "icon": "shield",
    },
    {
        "kicker": "CLIMATE - ANTALYA",
        "date": "21 NOV 2026",
        "accent": (46, 125, 50),
        "headline": ("COP31 DEADLOCKED", "INTO OVERTIME"),
        "body": ("NEARLY 200 NATIONS ARE STUCK IN ANTALYA AS THE DRAFT "
                 "DEAL DROPS ALL FOSSIL FUEL LANGUAGE AND A $120BN "
                 "ADAPTATION FUND. THE EU WARNS OF A FOSSIL SUMMIT."),
        "source": "SOURCE: REUTERS / BBC",
        "icon": "globe",
    },
    {
        "kicker": "EARTHQUAKE - PERU",
        "date": "21 NOV 2026",
        "accent": (163, 74, 18),
        "headline": ("MAGNITUDE 6.9 QUAKE", "SHAKES PERU'S ANDES"),
        "body": ("A DEEP TREMOR NEAR JUNIN SHOOK CENTRAL PERU AND WAS "
                 "FELT IN LIMA. NO DAMAGE OR CASUALTIES WERE IMMEDIATELY "
                 "REPORTED, OFFICIALS SAID."),
        "source": "SOURCE: AP / USGS",
        "icon": "quake",
    },
]

# ---------------------------------------------------------------- icons ----
# Small pictograms drawn with the same shape primitives, one per story,
# inside a 64x44 box at the bottom-right of each panel.

def icon_missile(cv, x, y, color):
    # A missile streaking up-right with a burst behind it.
    cv.fill_rect(x + 6, y + 22, 26, 6, color)
    cv.fill_triangle(x + 32, y + 19, x + 32, y + 31, x + 44, y + 25, color)
    cv.fill_rect(x + 10, y + 28, 6, 8, color)
    cv.fill_rect(x + 20, y + 28, 6, 8, color)
    cx, cy = x + 52, y + 12
    for dx, dy in ((0, -9), (7, -7), (9, 0), (7, 7),
                   (0, 9), (-7, 7), (-9, 0), (-7, -7)):
        cv.line(cx, cy, cx + dx, cy + dy, color)
    cv.fill_circle(cx, cy, 3, color)


def icon_tanker(cv, x, y, color):
    # A tanker with containers on a wavy sea.
    cv.fill_rect(x + 8, y + 6, 10, 10, color)
    cv.fill_rect(x + 20, y + 6, 10, 10, color)
    cv.fill_rect(x + 32, y + 6, 10, 10, color)
    cv.fill_rect(x + 4, y + 16, 14, 8, color)
    cv.fill_rect(x + 18, y + 16, 14, 8, color)
    cv.fill_rect(x + 32, y + 16, 14, 8, color)
    cv.fill_rect(x + 2, y + 24, 60, 8, color)
    cv.fill_triangle(x + 62, y + 24, x + 62, y + 32, x + 54, y + 28, color)
    cv.fill_rect(x + 2, y + 24, 60, 2, (247, 243, 232))
    cv.hline(x + 4, y + 38, 56, color)
    cv.hline(x + 10, y + 41, 44, color)


def icon_fire(cv, x, y, color):
    # A ship with flames and smoke.
    flame = (217, 92, 12)
    cv.fill_rect(x + 6, y + 30, 52, 8, color)
    cv.fill_triangle(x + 58, y + 30, x + 58, y + 38, x + 50, y + 34, color)
    cv.fill_triangle(x + 22, y + 30, x + 34, y + 30, x + 28, y + 12, flame)
    cv.fill_triangle(x + 34, y + 30, x + 44, y + 30, x + 39, y + 18, flame)
    cv.circle(x + 20, y + 8, 4, (120, 120, 115))
    cv.circle(x + 32, y + 4, 5, (120, 120, 115))
    cv.hline(x + 4, y + 41, 56, color)


def icon_shield(cv, x, y, color):
    # A shield with a check mark: a capture, secured.
    pts = [(x + 32, y + 2), (x + 52, y + 8), (x + 52, y + 22),
           (x + 32, y + 40), (x + 12, y + 22), (x + 12, y + 8)]
    cv.polyline(pts + [pts[0]], color)
    cv.polyline([(x + 22, y + 20), (x + 29, y + 28), (x + 44, y + 12)],
                color)
    cv.polyline([(x + 22, y + 22), (x + 29, y + 30), (x + 44, y + 14)],
                color)


def icon_globe(cv, x, y, color):
    # A globe with latitude lines and a rising sun.
    cv.circle(x + 28, y + 24, 16, color)
    cv.hline(x + 13, y + 24, 30, color)
    cv.hline(x + 16, y + 15, 24, color)
    cv.hline(x + 16, y + 33, 24, color)
    cv.vline(x + 28, y + 9, 30, color)
    cv.fill_circle(x + 52, y + 10, 6, (217, 158, 40))
    cv.hline(x + 46, y + 20, 12, (217, 158, 40))


def icon_quake(cv, x, y, color):
    # A seismograph trace over a cracked ground line.
    cv.polyline([(x + 4, y + 20), (x + 12, y + 20), (x + 16, y + 8),
                 (x + 20, y + 32), (x + 24, y + 14), (x + 28, y + 26),
                 (x + 32, y + 20), (x + 40, y + 20), (x + 44, y + 10),
                 (x + 48, y + 30), (x + 52, y + 20), (x + 60, y + 20)],
                color)
    cv.hline(x + 4, y + 38, 56, color)
    cv.line(x + 18, y + 38, x + 14, y + 43, color)
    cv.line(x + 40, y + 38, x + 44, y + 43, color)


ICONS = {
    "missile": icon_missile,
    "tanker": icon_tanker,
    "fire": icon_fire,
    "shield": icon_shield,
    "globe": icon_globe,
    "quake": icon_quake,
}

# --------------------------------------------------------------- layout ----
W, H = 1024, 1024
PAPER = (247, 243, 232)
INK = (26, 26, 26)
NAVY = (16, 36, 62)
GOLD = (198, 158, 60)
WHITE = (255, 255, 255)
BODY = (40, 40, 38)
MUTED = (96, 92, 84)
RULE = (203, 196, 178)


def draw_masthead(cv):
    cv.fill_rect(20, 20, 984, 128, NAVY)
    cv.fill_rect(20, 148, 984, 4, GOLD)
    cv.draw_text_centered(512, 44, "THE WORLD IN ONE IMAGE", 4, WHITE)
    cv.draw_text_centered(512, 84, "SUNDAY, 22 NOVEMBER 2026", 2, GOLD)
    cv.draw_text_centered(
        512, 110,
        "SIX STORIES FROM AROUND THE GLOBE - ALL DATED 21 NOVEMBER 2026",
        1, WHITE)


def draw_panel(cv, px, py, panel):
    pw, ph = 484, 257
    accent = panel["accent"]
    cv.fill_rect(px, py, pw, ph, WHITE)
    cv.rect_outline(px, py, pw, ph, INK, 2)
    # Kicker strip: topic on the left, date on the right.
    cv.fill_rect(px, py, pw, 30, accent)
    cv.draw_text(px + 12, py + 8, panel["kicker"], 2, WHITE)
    date = panel["date"]
    cv.draw_text(px + pw - 12 - text_width(date, 2), py + 8, date, 2,
                 WHITE)
    # Headline, two lines.
    hy = py + 42
    for i, line in enumerate(panel["headline"]):
        cv.draw_text(px + 16, hy + i * 25, line, 3, INK)
    # Rule, then body text (up to five lines).
    cv.hline(px + 16, py + 100, pw - 32, RULE)
    lines = wrap_text(panel["body"], pw - 32, 2)[:5]
    by = py + 110
    for i, line in enumerate(lines):
        cv.draw_text(px + 16, by + i * 18, line, 2, BODY)
    # Footer row: source at bottom-left, pictogram at bottom-right.
    cv.draw_text(px + 16, py + 226, panel["source"], 1, MUTED)
    ICONS[panel["icon"]](cv, px + pw - 16 - 64, py + ph - 16 - 44, accent)


def draw_footer(cv):
    cv.draw_text_centered(
        512, 976,
        "ALL EVENTS DATED 21 NOV 2026 - SOURCES: REUTERS, AP, CNN, BBC, "
        "WSJ, LE MONDE",
        1, MUTED)


def build_poster():
    cv = Canvas(W, H, PAPER)
    draw_masthead(cv)
    x0, y0 = 20, 164
    for i, panel in enumerate(PANELS):
        px = x0 + (i % 2) * (484 + 16)
        py = y0 + (i // 2) * (257 + 14)
        draw_panel(cv, px, py, panel)
    draw_footer(cv)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    data = encode_png(build_poster())
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
