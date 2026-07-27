# Build resources (icons & signing)

electron-builder reads this directory (`directories.buildResources`).

## Icons

Shipped in this directory — the Keel K monogram on a mist-to-cream gradient:

- `icon.png` — 1024×1024 master (electron-builder's source; also used for Linux).
- `icon.icns` — macOS app icon, embeds 16/32/64/128/256/512/1024.
- `icon.ico` — Windows app icon, embeds 16/24/32/48/64/128/256.

To regenerate from the SVG sources (`dashboard/frontend/public/favicon.svg`
for the mark; the K monogram is inlined in the generator), run:

```bash
python3 scripts/gen_icons.py
```

The script rasterizes via cairosvg and packs multi-size ICO/ICNS via Pillow.

## Signing / notarization (v2, currently out of scope)
- macOS: `entitlements.mac.plist` + an Apple Developer ID cert (`CSC_LINK`,
  `CSC_KEY_PASSWORD`), then set `mac.notarize` with `APPLE_ID` / `APPLE_APP_SPECIFIC_PASSWORD`.
- Windows: a code-signing cert via `CSC_LINK` / `CSC_KEY_PASSWORD`.

Keep all secrets in CI, never in the repo.
