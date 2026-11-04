"""CI raster contract for compact zodiac vectors. No host fonts needed.

Usage:
  python3 tests/weather/test_magick_zodiac_visible_m5i_pixels.py /tmp/zodiac.svg
"""
import io
import math
import sys
from pathlib import Path

import cairosvg
from PIL import Image

if len(sys.argv) != 2:
    raise SystemExit("Expected compact SVG fixture")

svg = Path(sys.argv[1]).read_bytes()
scale = 4
bitmap = cairosvg.svg2png(bytestring=svg, scale=scale)
image = Image.open(io.BytesIO(bitmap)).convert("RGB")
assert image.size == (410 * scale, 112 * scale), image.size

palette = (
    (237, 152, 26),   # fire
    (158, 206, 106),  # earth
    (85, 207, 202),   # air
    (199, 78, 199),   # water
)
w, h = 410, 112
radius = 40
visible = []
for sign in range(12):
    theta = (sign + 0.5) * math.pi / 6
    r = min(radius + 14, min(w, h) / 2 - 10)
    cx = (w / 2 + r * math.sin(theta)) * scale
    cy = (h / 2 - r * math.cos(theta)) * scale
    expected = palette[sign % 4]
    hit_count = 0
    # Inspect only the INNER glyph, excluding its 9.3px border ring.
    for x in range(max(0, int(cx - 7.5 * scale)),
                   min(image.width, int(cx + 7.5 * scale))):
        for y in range(max(0, int(cy - 7.5 * scale)),
                       min(image.height, int(cy + 7.5 * scale))):
            if math.hypot(x - cx, y - cy) > 7.5 * scale:
                continue
            rgb = image.getpixel((x, y))
            if max(abs(rgb[i] - expected[i]) for i in range(3)) < 48:
                hit_count += 1
    assert hit_count >= 30, (
        f"zodiac sign {sign} has only {hit_count} visible color pixels "
        "at actual compact wheel dimensions"
    )
    visible.append(hit_count)

print("PASS: all twelve zodiac glyphs rasterize at 410x112 without fonts")
print("Colored glyph pixels per sign:", visible)
