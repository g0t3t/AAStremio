# Agent Instructions

## Text style

- Do not use em dashes (U+2014) or en dashes (U+2013) in repository text. Use commas, colons, parentheses, or regular hyphens.
- Do not mention specific vehicle brands or models. Use generic wording such as "the car", "the head unit", or "the vehicle".
- Keep README and documentation generic for all vehicles.

## Product rules

- AAStremio is an unofficial clone of Stremio for Android Auto.
- Keep the package name `com.aastremio.app` so it installs next to official Stremio.
- Keep Android Auto parked-only enforcement intact: `appCategory=game`, `CAR_LAUNCHER`, no `distractionOptimized`, no bypass.
- Login is email/password only. Do not add Facebook, Google, or Apple login, and do not spoof signing key hashes.
- Do not add code that allows video playback while the car is moving.

## Build and release

- Keep the local streaming server on port `11475`.
- Keep `versionCode = upstreamVersionCode * 10 + patchRevision`.
- Use the official Stremio APK as the source and verify its signer certificate and SHA-256 hashes.
- Do not commit upstream APKs, signing keys, or build outputs.
- Keep the repository marked as a public beta until the maintainer changes that status.
- Preserve the non-profit, as-is, no-liability disclaimer.

## Icon

- The icon is based on the Stremio launcher icon with AA added. Stremio's logo and trademarks belong to Stremio.
- Source image: `overlay/source-icon.webp`.
- Regenerate icons with `python scripts/make_icon.py`.
- Keep the transparent safe margin for the adaptive icon.
