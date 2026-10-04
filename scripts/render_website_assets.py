"""Generate Stay Awake website assets: logo, favicons, OG image, banner.

Faithful to stay_awake/app.py make_icon(): 64-unit tile (#172337, radius 18)
with a mint (#67e8b3) power glyph (arc + vertical line, width 5, round caps).
"""
import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "website" / "assets"
OUT.mkdir(parents=True, exist_ok=True)

MINT = (103, 232, 179, 255)
MINT_DIM = (103, 232, 179, 22)
TILE = (23, 35, 55, 255)
BG_TOP = (16, 24, 39, 255)
BG_BOTTOM = (10, 17, 31, 255)
WHITE = (238, 243, 251, 255)
MUTED = (166, 181, 204, 255)

MONTSERRAT_XB = "/usr/share/fonts/julietaula-montserrat-fonts/Montserrat-ExtraBold.otf"
MONTSERRAT_B = "/usr/share/fonts/julietaula-montserrat-fonts/Montserrat-Bold.otf"
MONTSERRAT_SB = "/usr/share/fonts/julietaula-montserrat-fonts/Montserrat-SemiBold.otf"
LIBERATION = "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Regular.ttf"
LIBERATION_B = "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf"
MONO = "/usr/share/fonts/adobe-source-code-pro-fonts/SourceCodePro-Medium.otf"


def _glyph_geometry(scale):
    """Arc bbox, line endpoints and pen width scaled from the 64-unit master."""
    arc = (16 * scale, 16 * scale, 48 * scale, 50 * scale)
    line = ((32 * scale, 12 * scale), (32 * scale, 30 * scale))
    width = max(1, round(5 * scale))
    return arc, line, width


def _arc_endpoints(arc):
    x0, y0, x1, y1 = arc
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
    pts = []
    for deg in (315, 225):  # gap of 90 degrees centred at the top
        rad = math.radians(deg)
        pts.append((cx + rx * math.cos(rad), cy + ry * math.sin(rad)))
    return pts


def draw_glyph(draw, origin, size, color=MINT):
    """Draw the power glyph inside a 64-unit box placed at origin with width size."""
    ox, oy = origin
    scale = size / 64
    (x0, y0, x1, y1), ((lx0, ly0), (lx1, ly1)), w = _glyph_geometry(scale)
    arc = (x0 + ox, y0 + oy, x1 + ox, y1 + oy)
    # Two segments avoid start>end wrap ambiguity; together they span 270 deg.
    draw.arc(arc, start=315, end=360, fill=color, width=w)
    draw.arc(arc, start=0, end=225, fill=color, width=w)
    for px, py in _arc_endpoints(arc):  # round caps at arc ends
        draw.ellipse([px - w / 2, py - w / 2, px + w / 2, py + w / 2], fill=color)
    draw.line([(lx0 + ox, ly0 + oy), (lx1 + ox, ly1 + oy)], fill=color, width=w)
    for px, py in ((lx0 + ox, ly0 + oy), (lx1 + ox, ly1 + oy)):
        draw.ellipse([px - w / 2, py - w / 2, px + w / 2, py + w / 2], fill=color)


def make_tile(size, full_bleed=False, color=MINT):
    """App-tile icon: rounded square + power glyph, supersampled for smooth edges."""
    ss = 4
    big = size * ss
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if full_bleed:
        d.rectangle([0, 0, big, big], fill=TILE)
        draw_glyph(d, (big * 0.19, big * 0.19), big * 0.62, color)
    else:
        m = round(2 / 64 * big)
        d.rounded_rectangle([m, m, big - m, big - m], radius=round(18 / 64 * big), fill=TILE)
        draw_glyph(d, (0, 0), big, color)
    return img.resize((size, size), Image.LANCZOS)


def vertical_gradient(w, h):
    base = Image.new("RGBA", (w, h), BG_TOP)
    d = ImageDraw.Draw(base)
    for y in range(h):
        t = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(
            round(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3)) + (255,))
    return base


def dot_grid(w, h, step=30, alpha=10):
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for y in range(step // 2, h, step):
        for x in range(step // 2, w, step):
            d.ellipse([x - 1.5, y - 1.5, x + 1.5, y + 1.5], fill=(255, 255, 255, alpha))
    return layer


def fit_font(draw, text, path, start, max_width):
    size = start
    while size > 12:
        font = ImageFont.truetype(path, size)
        if draw.textlength(text, font=font) <= max_width:
            return font, size
        size -= 4
    return ImageFont.truetype(path, 12), 12


def social_card(w, h, path, headline_size, sub_size):
    img = vertical_gradient(w, h)
    img.alpha_composite(dot_grid(w, h))
    d = ImageDraw.Draw(img)
    # Oversized faint glyph watermark tucked off the right edge.
    wm_size = int(h * 1.35)
    wm = Image.new("RGBA", (wm_size, wm_size), (0, 0, 0, 0))
    draw_glyph(ImageDraw.Draw(wm), (0, 0), wm_size, (103, 232, 179, 12))
    img.alpha_composite(wm, (w - wm_size // 2 + 70, -(h // 4)))
    # Mint edge bar on the left.
    d.rectangle([0, 0, 14, h], fill=MINT)
    # App tile.
    tile_px = int(h * 0.34)
    tile = make_tile(256).resize((tile_px, tile_px), Image.LANCZOS)
    pad = int(w * 0.06)
    cy = h // 2
    img.alpha_composite(tile, (pad, cy - tile_px // 2 - 10))
    # Text block (auto-fit so nothing clips).
    tx = pad + tile_px + int(w * 0.035)
    max_tw = w - tx - int(w * 0.07)
    head, headline_size = fit_font(d, "Stay Awake", MONTSERRAT_XB, headline_size, max_tw)
    sub, sub_size = fit_font(
        d, "Your PC stays awake while AI does the work.", LIBERATION, sub_size, max_tw)
    small = ImageFont.truetype(LIBERATION_B, int(sub_size * 0.62))
    pill_font = ImageFont.truetype(MONTSERRAT_B, int(sub_size * 0.58))
    d.text((tx, cy - headline_size - sub_size // 2 - 26), "Stay Awake", font=head, fill=WHITE)
    d.text((tx, cy + 6), "Your PC stays awake while AI does the work.", font=sub, fill=MUTED)
    # Pill + platform line.
    pill_text = "100% FREE"
    pb = d.textbbox((0, 0), pill_text, font=pill_font)
    pw, ph = pb[2] - pb[0] + 36, int(sub_size * 1.15)
    py = cy + sub_size + 34
    d.rounded_rectangle([tx, py, tx + pw, py + ph], radius=ph // 2, fill=MINT)
    d.text((tx + 18, py + (ph - (pb[3] - pb[1])) // 2 - pb[1]),
           pill_text, font=pill_font, fill=(16, 37, 30, 255))
    d.text((tx + pw + 18, py + 6), "Windows  •  macOS  •  Linux", font=small, fill=MUTED)
    img.convert("RGB").save(path, quality=92)
    print("wrote", path, img.size)


# --- Icons -----------------------------------------------------------------
make_tile(64).save(OUT / "logo-64.png")
make_tile(512).save(OUT / "logo-512.png")
make_tile(32).save(OUT / "favicon-32x32.png")
make_tile(16).save(OUT / "favicon-16x16.png")
make_tile(180, full_bleed=True).convert("RGB").save(OUT / "apple-touch-icon.png")
make_tile(192, full_bleed=True).convert("RGB").save(OUT / "android-chrome-192x192.png")
make_tile(512, full_bleed=True).convert("RGB").save(OUT / "android-chrome-512x512.png")
make_tile(64).save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
print("wrote icons")

# --- Vector favicon ----------------------------------------------------------
svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect x="2" y="2" width="60" height="60" rx="18" fill="#172337"/>
  <path d="M 43.3 21 A 16 17 0 1 1 20.7 21" fill="none" stroke="#67e8b3" stroke-width="5" stroke-linecap="round"/>
  <path d="M 32 12 L 32 30" fill="none" stroke="#67e8b3" stroke-width="5" stroke-linecap="round"/>
</svg>
"""
(OUT / "favicon.svg").write_text(svg)
print("wrote favicon.svg")

# --- Social / banner ----------------------------------------------------------
social_card(1200, 630, OUT / "og-image.png", headline_size=116, sub_size=44)
social_card(1920, 480, OUT / "banner.png", headline_size=120, sub_size=46)

# --- Screenshots ---------------------------------------------------------------
shutil.copy(ROOT / "docs" / "stay-awake.png", OUT / "screenshot-awake.png")
shutil.copy(ROOT / "docs" / "sleep-allowed.png", OUT / "screenshot-sleep.png")
print("copied screenshots")
