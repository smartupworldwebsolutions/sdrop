"""Makes every logo the MSIX and the Store listing need from sdrop.ico.
Usage: python Packaging/make-assets.py <msix_assets_dir> <store_logos_dir>"""
import sys, os
from PIL import Image

ico, assets, logos = "sdrop.ico", sys.argv[1], sys.argv[2]
os.makedirs(assets, exist_ok=True); os.makedirs(logos, exist_ok=True)
src = Image.open(ico).convert("RGBA")
BG = (15, 17, 23, 255)

def square(px, pad=0.0):
    im = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    s = int(px * (1 - pad)); g = src.resize((s, s), Image.LANCZOS)
    im.paste(g, ((px - s) // 2, (px - s) // 2), g); return im

def canvas(w, h, icon_ratio):
    im = Image.new("RGBA", (w, h), BG)
    s = int(min(w, h) * icon_ratio); g = src.resize((s, s), Image.LANCZOS)
    im.paste(g, ((w - s) // 2, (h - s) // 2), g); return im

# MSIX assets
square(44).save(f"{assets}/Square44x44Logo.png")
square(150).save(f"{assets}/Square150x150Logo.png")
square(50).save(f"{assets}/StoreLogo.png")
canvas(310, 150, 0.8).save(f"{assets}/Wide310x150Logo.png")
# Store listing images (Partner Center)
canvas(720, 1080, 0.7).save(f"{logos}/SDrop-store-logo-720x1080.png")
canvas(2160, 2160, 0.75).save(f"{logos}/SDrop-logo-2160.png")
square(300).save(f"{logos}/SDrop-store-logo-300x300.png")
print("assets done")
