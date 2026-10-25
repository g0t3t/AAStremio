# AAStremio

<p align="center">
  <img src="overlay/icon-preview.png" width="128" alt="AAStremio icon">
</p>

**AAStremio is an unofficial, non-profit, open-source Android Auto build of Stremio.**
It is the official Stremio Android app cloned under a separate package
(`com.aastremio.app`) with Android Auto's parked-app support enabled. The
original Stremio app stays installed and untouched.

AAStremio is not affiliated with Stremio, Google, Android Auto, or any vehicle manufacturer.

> **Project status: public beta.** This is an unofficial, non-commercial
> project. It has been tested on a limited number of vehicles. Behavior may
> vary by phone, Android Auto version, and head unit.

> **Safety:** AAStremio is classified by Android Auto as a parked app. Android
> Auto blocks it while the vehicle is moving. Do not watch video while driving,
> and do not attempt to bypass Android Auto's safety restrictions. Use it only
> while parked or as a passenger.

## Why this exists

Google allows **games** to run on the Android Auto head unit while the vehicle
is parked. The same mechanism can host a normal Android app if it declares the
game category and the `CAR_LAUNCHER` intent category. AAStremio does exactly
that. When the car moves, Android Auto covers/blocks the app and pauses the
activity. No GPS hacks, no speed monitoring, no root.

## Features

- Stremio on the Android Auto display, including touch input.
- Parked-only enforcement by Android Auto itself.
- Installs **alongside** the official Stremio app.
- Works over wired and wireless Android Auto.
- Email/password login only. The Facebook button has been removed from the
  login screen; Google and Apple login are not supported.
- Automatic build pipeline: checks the official Stremio download page on the
  1st and 15th of each month.
- ARM64 and ARM builds.
- No additional accounts, analytics, or telemetry added by this project.

## Requirements

- An Android phone running **Android 15 or newer** (required for Android Auto
  parked apps).
- Android Auto installed and updated.
- A car head unit that supports Android Auto (wired or wireless).
- The APK for your phone's ABI:
  - **arm64-v8a** for almost all modern phones.
  - **armeabi-v7a** for older 32-bit devices.
- Android Auto developer mode + **Unknown sources** enabled.

## Install

1. Download the latest APK from the **Releases** page of this repository.
   Choose `arm64-v8a` unless you know your phone is 32-bit only.
2. Allow your file manager/browser to install unknown apps, then install the
   APK. AAStremio installs next to the official Stremio app.
3. On the phone, open **Android Auto** settings:
   - Tap **Version** at the bottom 10 times to enable developer mode.
   - Open the three-dot menu → **Developer settings**.
   - Enable **Unknown sources**.
4. Connect the phone to the car (wireless or USB).
5. Open the Android Auto app launcher and start **AAStremio** while parked.
6. Sign in with your **Stremio email/password**.

Full instructions: [docs/INSTALL.md](docs/INSTALL.md).

## Important notes

- **Both apps can coexist.** AAStremio uses package `com.aastremio.app` and its
  own data directory. The official Stremio app is not modified.
- **Server ports are separated.** Official Stremio uses port `11470`;
  AAStremio uses `11475-11479`, so both can run at the same time.
- **Email/password login only.** Facebook, Google, and Apple sign-in are not
  supported. The Facebook button has been removed from the login screen because
  the clone has a different package name and signing certificate.
- **Social-login users:** keep the official Stremio app installed if you need
  Facebook/Google/Apple login.
- **No OTA/self-update.** The GitHub Actions pipeline builds a new APK when
  Stremio publishes a new version. Download the new APK from Releases and
  install it over the old one; app data is preserved.

## Known limitations

- Tested on one vehicle and one phone so far.
- Requires Android 15 or newer for Android Auto parked apps.
- Requires Android Auto developer mode and **Unknown sources**.
- Email/password login only. Facebook, Google, and Apple login are not available.
- Head-unit layout, touch behavior, and playback may vary by vehicle.
- No OTA updates. Install new releases manually.
- This project publishes modified Stremio APKs and may be removed on request.

## How it works

`scripts/patch_apk.py`:

1. Downloads the official Stremio APK.
2. Verifies that it is signed by Stremio's pinned certificate.
3. Unpacks it with Apktool.
4. Changes the package to `com.aastremio.app`, renames package-scoped
   providers/permissions, and changes the app label/icon.
5. Adds `android:appCategory="game"` and
   `android.intent.category.CAR_LAUNCHER`.
6. Moves the local streaming server from `11470` to `11475` in
   `assets/server.js`, the dex files, and the native core.
7. Rebuilds, aligns to 16 KB pages, signs with the AAStremio release key, and
   verifies the result.

The launcher icon is based on Stremio's launcher icon with AA added. See
[docs/ICON.md](docs/ICON.md) for the source image, sizes, and replacement
instructions. Stremio's logo and trademarks belong to Stremio.

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Automatic builds

The workflow in `.github/workflows/build.yml` runs on:

- the **1st and 15th** of each month at 03:00 UTC, and
- manual `workflow_dispatch`.

It reads the official Stremio download page, falls back to the pinned
`versions.json` if the page is stale, verifies the upstream signer certificate,
downloads the APKs, checks their SHA-256 hashes, builds both ABIs, verifies
them, and publishes a GitHub Release.

### Manual upstream override

If Stremio's download page is stale or unreachable, run **Actions → Build
AAStremio → Run workflow** and provide:

- `version`: the upstream version, e.g. `2.5.0`
- `arm64_url`: the official ARM64 APK URL
- `arm_url`: the official ARM APK URL
- `force`: optional, to rebuild an unchanged version

The pipeline still verifies Stremio's signing certificate before using the APK.

### Repository secrets

Add these in **Settings → Secrets and variables → Actions**:

| Secret | Value |
| --- | --- |
| `ANDROID_KEYSTORE_BASE64` | Base64 of your `.jks` file |
| `ANDROID_KEYSTORE_PASSWORD` | Keystore password |
| `ANDROID_KEY_ALIAS` | Key alias (default `aastremio`) |
| `ANDROID_KEY_PASSWORD` | Key password |

See [docs/SIGNING.md](docs/SIGNING.md) for generating and backing up the key.
**Back up the keystore.** If it is lost, future APKs cannot be installed over
existing ones; users would have to uninstall and lose app data.

AAStremio release certificate SHA-256 (the current build key):
`62ef0a906f36a55a5aa4f07572c1670f41afe6da56dbe29b47e2ab8affc74533`.
Verify a download with:

```bash
apksigner verify --print-certs AAStremio-*.apk
```

## Local build (Windows)

```powershell
# Java 21+, Python 3.12+, Android build-tools 36.1.0, Apktool 2.12.1
python -m pip install -r requirements.txt

$env:APKTOOL_JAR = "C:\Windows\apktool.jar"
$env:AASTREMIO_KEYSTORE_PASSWORD = "..."
$env:AASTREMIO_KEY_PASSWORD = "..."

python scripts/patch_apk.py `
  --input upstream/com.stremio.one-2.4.0-8145728-arm64-v8a.apk `
  --output dist/AAStremio-2.4.0-aastremio.1-arm64-v8a.apk `
  --upstream-version 2.4.0 `
  --upstream-version-code 8145728 `
  --abi arm64-v8a `
  --patch-revision 1 `
  --keystore keys/aastremio-release.jks
```

The script verifies the package name, version, AA category, `CAR_LAUNCHER`, the
patched port, and the final signature before it reports success.

## Versioning

- Upstream version: `2.4.0`
- AAStremio version: `2.4.0-aastremio.1`
- Android `versionCode`: `upstreamVersionCode * 10 + patchRevision`

The multiplier guarantees that a rebuild of the same upstream version still
installs over the previous AAStremio build.

## Security

- Upstream APKs are **never committed** to this repository. They are downloaded
  during the build.
- Every upstream APK must match Stremio's pinned signing certificate.
- Upstream and output SHA-256 hashes are recorded in release notes and
  `SHA256SUMS.txt`.
- The AAStremio signing key lives only in GitHub Actions secrets and in the
  maintainer's offline backup.

## Disclaimer

This project is **non-profit, open source, and provided as-is**, without any
warranty. It is an unofficial modification of the Stremio Android APK. It is not
affiliated with, endorsed by, or supported by Stremio. Stremio's name, logo, and
code belong to their respective owners.

By downloading or using AAStremio you accept that:

- You use it entirely at your own risk.
- The maintainers take **no responsibility or liability** for any damage,
  accident, traffic violation, data loss, account action, or legal issue.
- You must comply with Stremio's terms of service and all applicable laws.
- You must not watch video while driving. AAStremio is for parked or passenger
  use only.
- AAStremio does not bypass Android Auto's driving restrictions; it relies on
  them.
- The project may be discontinued or removed at any time.

Read the full [DISCLAIMER.md](DISCLAIMER.md).

## License

The scripts and documentation in this repository are released under the MIT
License. The MIT License does **not** apply to the Stremio APK or to Stremio's
trademarks. See [LICENSE](LICENSE).
