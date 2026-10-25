# Install AAStremio

## 1. Pick the right APK

| APK | Use it for |
| --- | --- |
| `AAStremio-...-arm64-v8a.apk` | Almost all modern 64-bit phones |
| `AAStremio-...-armeabi-v7a.apk` | Older 32-bit ARM phones |

If you are unsure, install the ARM64 APK. Android will reject it immediately if
your phone cannot run it, without changing anything.

## 2. Install next to Stremio

AAStremio has package `com.aastremio.app`, so it installs **alongside** the
official `com.stremio.one` app. You do not need to uninstall Stremio.

1. Download the APK from the latest GitHub Release.
2. Open it on the phone.
3. Allow the browser/file manager to install unknown apps when prompted.
4. Install.
5. Open AAStremio once on the phone and sign in with **email/password**.

Social login is not available. AAStremio supports **email/password only**. The
Facebook button has been removed from the login screen; Google and Apple login
are also unsupported.

## 3. Enable Android Auto unknown sources

Android Auto only shows sideloaded apps after developer mode is enabled.

1. Open the **Android Auto** app on the phone.
2. Scroll to the bottom and tap **Version** 10 times.
3. When developer mode is enabled, open the three-dot menu.
4. Open **Developer settings**.
5. Enable **Unknown sources**.
6. Reboot the phone if AAStremio does not appear.

## 4. Connect and launch

1. Connect to the car with Android Auto (wireless or USB).
2. Open the Android Auto app launcher.
3. Start **AAStremio** while the car is parked.
4. Pick something and play it.

The first launch may take a few seconds because Stremio starts its local
streaming server.

## 5. Driving behaviour

AAStremio is declared as a game, so Android Auto:

- blocks launching it while the vehicle is moving;
- covers/blocks it if the car starts moving;
- pauses the activity when the car moves.

This is enforced by Android Auto, not by a GPS check in the app. Do not attempt
to bypass it.

## Troubleshooting

### AAStremio is not in the Android Auto launcher

- Confirm the phone is on **Android 15 or newer**.
- Update Android Auto from the Play Store.
- Confirm **Unknown sources** is enabled in Android Auto developer settings.
- Confirm AAStremio is installed in the main phone profile, not a work profile.
- Reboot the phone and reconnect.
- Make sure the official Stremio app did not replace AAStremio (they have
  different package names; both should be listed in phone settings).

### The app opens on the phone but not on the car

- Check the phone's Android Auto settings and developer options.
- Try a USB cable to rule out wireless projection issues.
- Check that the car's head unit supports third-party/parked apps.

### Login fails

- Use email/password.
- Facebook login has been removed from AAStremio.
- Google/Apple sign-in is not supported in the clone.
- You can keep the official Stremio app installed and use it for social login.
- If your Stremio account was created with Facebook, try **Forgot password**
  using the email linked to Facebook and set a password, or use the official
  Stremio app for that account.

### Playback fails

- Confirm the official Stremio app can play the same stream on the phone.
- AAStremio uses port `11475-11479`; official Stremio uses `11470`. If a firewall
  or VPN blocks localhost ports, allow them.
- Some streams may not be playable in a car environment; that is a Stremio/add-on
  issue, not an Android Auto issue.

### The app disappears or is blocked while driving

That is expected and intentional. AAStremio is parked-only.

### Both apps are running

That is supported. They use separate packages, data directories, and local
server ports.

## Uninstall

Uninstalling AAStremio does not affect the official Stremio app. App data for
AAStremio is removed with it.
