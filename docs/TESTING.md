# Testing AAStremio

Do not test the moving-vehicle behaviour while driving. Use a parked, safe area,
or have a passenger operate the phone.

## 1. Static verification

The build script verifies these automatically:

```text
package = com.aastremio.app
versionName = <upstream>-aastremio.<revision>
versionCode = upstreamVersionCode * 10 + revision
application appCategory = game (0)
MainActivity has android.intent.category.CAR_LAUNCHER
server.js, classes*.dex and libstremio_core_kotlin.so use port 11475
APK is signed by the AAStremio release key
```

Manual check:

```bash
aapt2 dump badging dist/AAStremio-*.apk
aapt2 dump xmltree --file AndroidManifest.xml dist/AAStremio-*.apk | grep -E 'appCategory|CAR_LAUNCHER'
apksigner verify --print-certs dist/AAStremio-*.apk
sha256sum dist/AAStremio-*.apk
```

## 2. Phone install test

1. Install AAStremio on a phone that already has official Stremio.
2. Confirm both apps appear in the phone launcher with different icons.
3. Open AAStremio on the phone.
4. Sign in with email/password.
5. Open a catalog and a detail page.
6. Play a stream on the phone.
7. Confirm the official Stremio app still opens and plays while AAStremio is
   installed.
8. If possible, run both apps at once and confirm they do not fight over the
   local server.

## 3. Android Auto test

### Desktop Head Unit (DHU)

You can test without the car using the Android Auto Desktop Head Unit.

Prerequisites:

- USB debugging enabled on the phone.
- Phone unlocked.
- Official Android Auto installed and updated.
- Android Auto developer mode enabled.
- **Unknown sources** enabled.
- **Add new cars to Android Auto** enabled.
- AAStremio installed.

On the phone:

1. Settings → About device → Version → tap **Build number** seven times.
2. Settings → System → Developer options → enable **USB debugging**.
3. Connect the phone to the PC with a data cable.
4. Accept the **Allow USB debugging** prompt.
5. Open Android Auto → three-dot menu → **Start head unit server**.
6. Confirm the head unit server notification is showing.

On the PC:

```powershell
adb devices
# Must show: <serial>  device
# If it shows "unauthorized", accept the prompt on the phone.
# If it is empty, USB debugging or the ADB driver is not working.

adb forward tcp:5277 tcp:5277
cd "$env:LOCALAPPDATA\Android\Sdk\extras\google\auto"
.\desktop-head-unit.exe -c "C:\path\to\AAStremio\tools\dhu_1280x720.ini"
```

The DHU window is the emulated car screen. Click it to simulate touch.

If the DHU is blank, close it, stop and restart the head unit server, re-run
`adb forward`, and start the DHU again. Accept any permission prompts on the
phone.

### Test AAStremio

1. Log in to AAStremio on the phone before starting DHU, so the DHU session is
   already signed in.
2. In the DHU app launcher, open **AAStremio**.
3. Test touch, scrolling, playback, audio and subtitles.
4. In the terminal where DHU is running, type:

```text
screenshot dhu-parked.png
```

### If the DHU mouse cannot scroll

The login screen is scrollable, but the DHU window must be focused and the
content area must be tall enough. The old wide config (`marginheight = 220`)
only gave the app a 1280x500 area, which clips the login form. The current
`tools/dhu_1280x720.ini` uses full 1280x720.

1. Restart DHU with the current config and explicit touch mode:

```powershell
cd "$env:LOCALAPPDATA\Android\Sdk\extras\google\auto"
.\desktop-head-unit.exe -i touch -c "C:\path\to\AAStremio\tools\dhu_1280x720.ini"
```

2. Click once inside the DHU screen to focus it.
3. Hold the left mouse button and drag **up** from the lower half of the
   screen, then release. Use `config\default.ini` (800x480) if 720p is too large.

If mouse drag still does nothing, inject the swipe directly into AAStremio's
Android Auto display with ADB:

```powershell
.\tools\aa-input.ps1 -Action up
```

Other actions:

```powershell
.\tools\aa-input.ps1 -Action down
.\tools\aa-input.ps1 -Action tap -X 640 -Y 430
.\tools\aa-input.ps1 -Action back
.\tools\aa-input.ps1 -Action screenshot
```

The script finds the `NativeDisplay:ComponentInfo{com.aastremio.app...}`
display automatically. You can also pass `-DisplayId <id>`. If PowerShell blocks
the script, run it with:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\aa-input.ps1 -Action up
```

### Test the driving block

The DHU console accepts the following commands:

```text
restrict all      # simulate driving / UX restrictions (Shift+U)
restrict none     # simulate parked (U)
```

Test:

1. With `restrict none`, start playback in AAStremio.
2. Type `restrict all`.
3. Confirm AAStremio is covered/blocked and cannot be interacted with.
4. Confirm audio pauses.
5. Type `restrict none` and confirm AAStremio is usable again.
6. Take a screenshot with `screenshot dhu-driving.png`.

You can also try sensor-based simulation:

```text
parking_brake engaged false
gear 100
speed 10
```

`speed` is in metres per second, so `10` is 36 km/h. The `tools/dhu_1280x720.ini`
file enables the speed, parking-brake and gear sensors.

Useful DHU commands: `help`, `keycode home`, `keycode back`, `tap x y`,
`quit`.

If AAStremio does not appear in the DHU launcher:

- Confirm **Unknown sources** is enabled in Android Auto developer settings.
- Reboot the phone and reconnect.
- Confirm `adb shell pm list packages | findstr aastremio` shows
  `com.aastremio.app`.
- Update Android Auto.
- The DHU is from 2022 and may lag behind the car's head unit for the newest
  parked-app/game behaviour; the car remains the definitive test.

## 4. Parked-state enforcement test

With the car stationary and in a safe area:

1. Start playback in AAStremio.
2. Release the parking brake / put the car in drive so Android Auto reports
   movement.
3. Confirm AAStremio is covered by Android Auto's driving overlay and cannot be
   interacted with.
4. Confirm audio pauses. If audio continues, record it; a small pause hook may
   be needed.
5. Stop, park, and confirm AAStremio becomes usable again.
6. Try launching AAStremio from the Android Auto launcher while moving; it
   should be blocked.

Do not attempt to bypass the overlay.

## 5. Update test

1. Build a new APK with a higher patch revision.
2. Install it over the existing AAStremio APK.
3. Confirm it updates without uninstalling and that login/library data is
   preserved.
4. Confirm the official Stremio app is unaffected.

## 6. Login check

- Confirm the **Continue with Facebook** button is gone from the login and
  signup screens.
- Sign in with email/password.
- Confirm Google/Apple login is not offered.
- Confirm the official Stremio app can still be used for social login if needed.
