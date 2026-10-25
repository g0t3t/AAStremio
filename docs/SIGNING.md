# Signing key

AAStremio updates only work if every release is signed with the **same key**.
Android will refuse to install an APK signed by a different key over an existing
installation.

## Generate a key (Windows)

```powershell
& "C:\Program Files\Android\Android Studio\jbr\bin\keytool.exe" `
  -genkeypair -v `
  -keystore keys/aastremio-release.jks `
  -storetype PKCS12 `
  -alias aastremio `
  -keyalg RSA -keysize 4096 -validity 10000 `
  -storepass "YOUR_STRONG_PASSWORD" `
  -keypass "YOUR_STRONG_PASSWORD" `
  -dname "CN=AAStremio, OU=Release, O=AAStremio, L=Unknown, ST=Unknown, C=US"
```

Keep the `.jks` file and both passwords offline. Do not commit them.

## Verify the key

```powershell
& "C:\Program Files\Android\Android Studio\jbr\bin\keytool.exe" `
  -list -v -keystore keys/aastremio-release.jks -alias aastremio
```

The certificate SHA-256 fingerprint is what users can use to verify releases.
The key generated for this workspace has fingerprint:

```text
62ef0a906f36a55a5aa4f07572c1670f41afe6da56dbe29b47e2ab8affc74533
```

If you generate a new key, update this fingerprint in `README.md` and the
release notes template.

## Add GitHub Actions secrets

In the repository: **Settings → Secrets and variables → Actions → New repository
secret**.

| Secret | Value |
| --- | --- |
| `ANDROID_KEYSTORE_BASE64` | Base64 of the `.jks` file |
| `ANDROID_KEYSTORE_PASSWORD` | Keystore password |
| `ANDROID_KEY_ALIAS` | `aastremio` |
| `ANDROID_KEY_PASSWORD` | Key password |

PowerShell:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("keys/aastremio-release.jks")) | Set-Clipboard
```

Linux/macOS:

```bash
base64 -w0 keys/aastremio-release.jks
```

The workflow decodes the secret into `keys/release.jks` for the build and never
commits it.

## Backups

Back up:

- `keys/aastremio-release.jks`
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_PASSWORD`
- the alias (`aastremio`)

If the key is lost, existing users cannot install future APKs over the old one.
They would have to uninstall AAStremio and lose its local app data.

## Key rotation

Avoid rotating the key. If you must rotate it, publish a new package name or
accept that users need a clean uninstall. Android's signature-lineage rotation
requires the old private key.

## Upstream signing certificate

AAStremio is built from the official Stremio APK and verifies that the upstream
APK is signed by Stremio:

```text
7e6a979c968f771e3fbcf2c2e8718ce61e708d87caf91fc13e2d4c19a8022c6b
```

This is **not** the AAStremio signing key. It is only used to reject tampered
upstream downloads.
