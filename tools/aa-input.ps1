param(
    [ValidateSet("up", "down", "tap", "back", "screenshot")]
    [string]$Action = "up",
    [int]$DisplayId = 0,
    [int]$X = 0,
    [int]$Y = 0,
    [int]$Duration = 600
)

# Send touch input directly to AAStremio's Android Auto virtual display.
# Useful when the DHU window is clipped or mouse drag doesn't scroll.
#
# Examples:
#   .\tools\aa-input.ps1 -Action up
#   .\tools\aa-input.ps1 -Action down
#   .\tools\aa-input.ps1 -Action tap -X 640 -Y 430
#   .\tools\aa-input.ps1 -Action back
#   .\tools\aa-input.ps1 -Action up -DisplayId 384

$ErrorActionPreference = "Stop"

function Get-Adb {
    $adb = Get-Command adb -ErrorAction SilentlyContinue
    if ($adb) { return $adb.Source }
    $candidate = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
    if (Test-Path $candidate) { return $candidate }
    throw "adb not found. Add platform-tools to PATH or install Android SDK platform-tools."
}

$adb = Get-Adb
$devices = & $adb devices
if (-not ($devices | Select-String "\sdevice$")) {
    throw "No ADB device found. Unlock the phone, enable USB debugging, and accept the prompt."
}

$width = 1280
$height = 720

if ($DisplayId -eq 0) {
    $dump = & $adb shell dumpsys display 2>&1 | Out-String
    $pattern = 'DisplayInfo\{"NativeDisplay:ComponentInfo\{com\.aastremio\.app[^"]*", displayId (?<id>\d+)[^\n]*?real (?<w>\d+) x (?<h>\d+)'
    $match = [regex]::Match($dump, $pattern, [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if (-not $match.Success) {
        $pattern = 'NativeDisplay:ComponentInfo\{com\.aastremio\.app[^"]*"[^\n]*?displayId (?<id>\d+)[^\n]*?real (?<w>\d+) x (?<h>\d+)'
        $match = [regex]::Match($dump, $pattern, [System.Text.RegularExpressions.RegexOptions]::Singleline)
    }
    if (-not $match.Success) {
        throw "AAStremio is not running on an Android Auto display. Launch it in the DHU first, or pass -DisplayId."
    }
    $DisplayId = [int]$match.Groups["id"].Value
    $width = [int]$match.Groups["w"].Value
    $height = [int]$match.Groups["h"].Value
}

Write-Host "Using AAStremio display $DisplayId (${width}x${height})"

switch ($Action) {
    "up" {
        $x = if ($X -gt 0) { $X } else { [int]($width / 2) }
        $startY = [int]($height * 0.85)
        $endY = [int]($height * 0.15)
        & $adb shell input -d $DisplayId swipe $x $startY $x $endY $Duration
    }
    "down" {
        $x = if ($X -gt 0) { $X } else { [int]($width / 2) }
        $startY = [int]($height * 0.15)
        $endY = [int]($height * 0.85)
        & $adb shell input -d $DisplayId swipe $x $startY $x $endY $Duration
    }
    "tap" {
        $tapX = if ($X -gt 0) { $X } else { [int]($width / 2) }
        $tapY = if ($Y -gt 0) { $Y } else { [int]($height / 2) }
        & $adb shell input -d $DisplayId tap $tapX $tapY
    }
    "back" {
        & $adb shell input -d $DisplayId keyevent KEYCODE_BACK
    }
    "screenshot" {
        & $adb shell screencap -d $DisplayId -p /sdcard/aastremio-aa.png
        & $adb pull /sdcard/aastremio-aa.png .\aastremio-aa.png
        Write-Host "Saved aastremio-aa.png"
    }
}
