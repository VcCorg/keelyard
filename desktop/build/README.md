# Build resources (icons & signing)

electron-builder reads this directory (`directories.buildResources`).

## Icons (add before first release)
- `icon.icns` — macOS app icon (1024×1024 source).
- `icon.ico` — Windows app icon (256×256).

Until these exist, electron-builder uses the default Electron icon (fine for dev
builds). Generate both from a single PNG with `electron-icon-builder` or `iconutil`.

## Signing / notarization (v2, currently out of scope)
- macOS: `entitlements.mac.plist` + an Apple Developer ID cert (`CSC_LINK`,
  `CSC_KEY_PASSWORD`), then set `mac.notarize` with `APPLE_ID` / `APPLE_APP_SPECIFIC_PASSWORD`.
- Windows: a code-signing cert via `CSC_LINK` / `CSC_KEY_PASSWORD`.

Keep all secrets in CI, never in the repo.
