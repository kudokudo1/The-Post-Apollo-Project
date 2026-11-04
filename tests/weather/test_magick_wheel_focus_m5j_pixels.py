"""M5j selected-vs-idle zodiac visual contract at compact Qt dimensions.

Rasterizes the SAME Leo vector using the exact pure-policy style fields at
two positions. Contrast is checked inside the glyph, not just chip outlines.
Dependency installed in disposable CI only.
"""
import io
import sys
from pathlib import Path
import cairosvg
from PIL import Image

if len(sys.argv)!=2:
    raise SystemExit("Expected M5j focused/idle SVG path")
png=cairosvg.svg2png(bytestring=Path(sys.argv[1]).read_bytes(),scale=4)
im=Image.open(io.BytesIO(png)).convert("RGB")
assert im.size==(880,352),im.size
def counts(cx):
    bright=0
    visible=0
    for x in range(int((cx-10)*4),int((cx+10)*4)):
        for y in range(int((44-10)*4),int((44+10)*4)):
            # Same color and identical source geometry, only style differs.
            r,g,b=im.getpixel((x,y))
            if r>115 and g>62 and b<73:
                visible+=1
            if r>203 and g>122 and b<63:
                bright+=1
    return visible,bright
idle=counts(65)
focused=counts(155)
assert idle[0]>=25,("Idle sign lost contrast",idle)
assert focused[0]>idle[0]*1.2,("Focus sign must be visibly larger",idle,focused)
assert focused[1]>idle[1]+20,("Focus sign must be visibly brighter",idle,focused)
print("PASS // M5j idle and selected zodiac are both visible")
print("Idle glyph visible/bright pixels:",idle)
print("Selected glyph visible/bright pixels:",focused)
