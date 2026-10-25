# Architecture

## Why a clone?

Stremio's mobile source is not public, so AAStremio cannot be compiled from
source. It is built by unpacking the official APK, changing its identity and
Android Auto metadata, rebuilding, and re-signing it.

The package is changed to `com.aastremio.app` so the official Stremio app and
AAStremio can be installed at the same time.

## APK changes

### Identity

- Manifest package: `com.stremio.one` → `com.aastremio.app`
- Label: `Stremio` → `AAStremio`
- Icon: AAStremio icon overlay
- Package-scoped authorities/permissions renamed:
  - `*.firebaseinitprovider`
  - `*.FacebookInitProvider`
  - `*.androidx-startup`
  - `*.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION`
- Facebook callback host renamed
- Facebook login buttons removed from the login, signup, and intro screens
- `aastremio://` scheme added (the original `stremio://` scheme is kept)

### Android Auto

- `<application android:appCategory="game">`
- `android.intent.category.CAR_LAUNCHER` on `MainActivity`
- No `distractionOptimized` metadata

Android Auto treats the app as a parked game. The OS enforces parked-only use;
the app does not implement its own speed/GPS check.

### Local server port

Stremio runs a local Node.js streaming server on port `11470`. If both apps tried
to use it, AAStremio would talk to official Stremio's server. The port is moved
to `11475` in:

- `assets/server.js` (including the CORS origin and max-port fallback)
- the smali classes (subtitle and localhost URLs)
- `libstremio_core_kotlin.so` (`STREAMING_SERVER_URL`)

Apktool decodes the dex files to smali, applies the string and UI patches, and
reassembles them. The Facebook login buttons are replaced with no-ops in the
login, signup, and intro screens before rebuilding.

## Versioning

```text
versionName = <upstream>-aastremio.<revision>
versionCode = <upstreamVersionCode> * 10 + <revision>
```

The multiplier keeps rebuilds of the same upstream version installable over each
other.

## Build pipeline

1. `scripts/resolve_upstream.py` fetches `https://www.stremio.com/downloads`.
2. It parses the Android Mobile links and picks the highest version with both
   ARM64 and ARM APKs.
3. If the page is stale or unreachable, it uses `versions.json`.
4. It downloads the APKs and verifies:
   - Stremio's signing certificate against the pinned SHA-256;
   - the SHA-256 of the APK against `versions.json`.
5. If the version or hashes changed, it increments the patch revision.
6. `scripts/patch_apk.py` builds and verifies each ABI.
7. The workflow creates a GitHub Release and updates `versions.json`.

The pipeline runs on the 1st and 15th of each month, plus manual dispatch.

## Security model

- The official APK is never committed.
- The upstream signer certificate is pinned. A CDN compromise or mirror cannot
  silently replace the APK.
- Upstream and output hashes are published.
- The AAStremio signing key is stored only in GitHub Actions secrets and offline
  backups.

## Known limitations

- Android 15+ is required for Android Auto parked apps.
- Social login is unavailable. The Facebook button is removed; email/password
  is the supported login method. Google/Apple login is not supported.
- Stremio may change its manifest, server port, or native code in a future
  release; the scripts fail loudly rather than producing a broken APK.
- Android Auto may change its parked-app rules in a future version.
- The app UI is Stremio's phone UI; it may letterbox or feel cramped on some head
  units.
- Video playback depends on Stremio's player rendering correctly on the
  projected display.
- Audio pause on driving depends on Stremio's activity lifecycle; test it and
  add a pause hook if necessary.
