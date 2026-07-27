"""One-shot raster generator for the Keel logo assets.

Produces:
  dashboard/frontend/public/favicon.ico       (16/32/48)
  dashboard/frontend/public/apple-touch-icon.png  (180)
  desktop/build/icon.png                      (1024, app-icon composition)
  desktop/build/icon.ico                      (16/24/32/48/64/128/256, app-icon)
  desktop/build/icon.icns                     (16/32/64/128/256/512/1024, app-icon)

Rasterizes SVG via cairosvg, packs multi-size ICO/ICNS via Pillow (Pillow
supports both formats for writing).
"""
from __future__ import annotations

import io
import os
from pathlib import Path

import cairosvg
from PIL import Image

REPO = Path(__file__).resolve().parent.parent
FAVICON_SVG = REPO / "dashboard/frontend/public/favicon.svg"

# Composed app icon: K monogram centered on a soft mist-to-cream gradient.
# Kept as a string so the raster output is reproducible from source.
APP_ICON_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#F6F1E4"/>
      <stop offset="100%" stop-color="#E5EBEE"/>
    </linearGradient>
  </defs>
  <rect width="1024" height="1024" fill="url(#bg)"/>
  <g transform="translate(256 165) scale(5.33)">
    <path d="M 0 66 L 8 66 M 30 66 L 96 66"
          stroke="#89B7D3" stroke-width="4" stroke-linecap="round" fill="none"/>
    <path d="M 12 8 L 26 8 L 26 66 L 12 66 Z" fill="#0E3B57"/>
    <path d="M 12 66 L 26 66 C 25 82, 22 102, 20 124 L 18 124 C 15 102, 12 82, 12 66 Z"
          fill="#0E3B57"/>
    <path d="M 26 44 L 66 8 L 80 8 L 26 62 Z" fill="#0E3B57"/>
    <path d="M 26 70 L 66 124 L 80 124 L 26 88 Z" fill="#0E3B57"/>
  </g>
</svg>
"""


def rasterize(svg_bytes: bytes, size: int) -> Image.Image:
    """Rasterize an SVG to a Pillow Image at `size`x`size` px, RGBA."""
    png_bytes = cairosvg.svg2png(
        bytestring=svg_bytes, output_width=size, output_height=size
    )
    return Image.open(io.BytesIO(png_bytes)).convert("RGBA")


def main() -> None:
    # 1. Favicon: mark alone, 16/32/48 packed into .ico.
    fav_svg = FAVICON_SVG.read_bytes()
    fav_sizes = [16, 32, 48]
    fav_imgs = [rasterize(fav_svg, s) for s in fav_sizes]
    fav_out = REPO / "dashboard/frontend/public/favicon.ico"
    fav_imgs[0].save(fav_out, format="ICO", sizes=[(s, s) for s in fav_sizes])
    print(f"wrote {fav_out} ({', '.join(str(s) for s in fav_sizes)})")

    # 2. Apple touch icon: 180x180. iOS ignores transparency, so composite on cream.
    apple = rasterize(fav_svg, 180)
    apple_bg = Image.new("RGBA", (180, 180), (245, 240, 230, 255))  # chart-cream
    apple_bg.alpha_composite(apple)
    apple_out = REPO / "dashboard/frontend/public/apple-touch-icon.png"
    apple_bg.convert("RGB").save(apple_out, format="PNG", optimize=True)
    print(f"wrote {apple_out}")

    # 3. Desktop app icon (K monogram on gradient bg), 1024.
    app_svg = APP_ICON_SVG.encode("utf-8")
    app_1024 = rasterize(app_svg, 1024)
    app_png_out = REPO / "desktop/build/icon.png"
    app_png_out.parent.mkdir(parents=True, exist_ok=True)
    app_1024.save(app_png_out, format="PNG", optimize=True)
    print(f"wrote {app_png_out} (1024)")

    # 4. Windows .ico: multi-size from 16 to 256.
    ico_sizes = [16, 24, 32, 48, 64, 128, 256]
    ico_imgs = [rasterize(app_svg, s) for s in ico_sizes]
    ico_out = REPO / "desktop/build/icon.ico"
    # Pillow ICO writing accepts a sizes list; give it the highest-res source
    # and it downsamples for each size.
    ico_imgs[-1].save(ico_out, format="ICO", sizes=[(s, s) for s in ico_sizes])
    print(f"wrote {ico_out} ({', '.join(str(s) for s in ico_sizes)})")

    # 5. macOS .icns: Pillow can save ICNS from a single image, embedding
    #    standard resolutions. Feed the 1024 master.
    icns_out = REPO / "desktop/build/icon.icns"
    # ICNS supports these sizes as of Pillow: 16, 32, 64, 128, 256, 512, 1024.
    icns_sizes = [(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)]
    app_1024.save(icns_out, format="ICNS", sizes=icns_sizes)
    print(f"wrote {icns_out} ({', '.join(f'{s[0]}' for s in icns_sizes)})")


if __name__ == "__main__":
    main()
