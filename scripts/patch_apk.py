#!/usr/bin/env python3
"""Build AAStremio by cloning the official Stremio APK.

This script does not compile Stremio from source. It unpacks the official
APK, applies the AAStremio identity + Android Auto manifest changes, moves the
local streaming server off the official app's port, rebuilds, aligns and signs
the result.

Usage:
  python scripts/patch_apk.py \
      --input upstream/com.stremio.one-2.4.0-8145728-arm64-v8a.apk \
      --output dist/AAStremio-2.4.0-aastremio.1-arm64-v8a.apk \
      --upstream-version 2.4.0 --upstream-version-code 8145728 \
      --abi arm64-v8a --patch-revision 1 \
      --keystore keys/aastremio-release.jks
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ANDROID = "http://schemas.android.com/apk/res/android"
A = f"{{{ANDROID}}}"
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKAGE = "com.aastremio.app"
DEFAULT_LABEL = "AAStremio"
DEFAULT_PORT = 11475
OFFICIAL_PACKAGE = "com.stremio.one"

ET.register_namespace("android", ANDROID)


def log(message: str) -> None:
    print(f"[patch] {message}", flush=True)


def run(cmd: list[str], *, env: dict[str, str] | None = None, quiet: bool = False) -> subprocess.CompletedProcess:
    log("$ " + " ".join(str(c) for c in cmd))
    proc = subprocess.run(
        [str(c) for c in cmd],
        env=env,
        text=True,
        stdout=subprocess.PIPE if quiet else None,
        stderr=subprocess.STDOUT if quiet else None,
    )
    if quiet and proc.returncode != 0:
        if proc.stdout:
            print(proc.stdout)
    if proc.returncode != 0:
        raise SystemExit(f"Command failed with exit code {proc.returncode}: {cmd[0]}")
    return proc


def find_build_tool(name: str) -> str:
    env_key = f"AASTREMIO_{name.upper()}"
    if os.environ.get(env_key):
        return os.environ[env_key]

    candidates: list[Path] = []
    sdk_roots = [
        os.environ.get("ANDROID_SDK_ROOT"),
        os.environ.get("ANDROID_HOME"),
        str(Path.home() / "AppData/Local/Android/Sdk"),
        str(Path.home() / "Android/Sdk"),
    ]
    for sdk in filter(None, sdk_roots):
        build_tools = Path(sdk) / "build-tools"
        if build_tools.is_dir():
            candidates.extend(sorted(build_tools.iterdir(), reverse=True))

    for directory in candidates:
        for suffix in (".exe", ".bat", ""):
            candidate = directory / f"{name}{suffix}"
            if candidate.is_file():
                return str(candidate)

    found = shutil.which(name)
    if found:
        return found
    raise SystemExit(
        f"Could not find {name}. Set AASTREMIO_{name.upper()} or install Android build-tools."
    )


def apktool_command(apktool: str | None) -> list[str]:
    jar = apktool or os.environ.get("APKTOOL_JAR")
    if jar:
        return ["java", "-jar", jar]
    wrapper = shutil.which("apktool")
    if wrapper:
        return [wrapper]
    raise SystemExit("Could not find apktool. Set APKTOOL_JAR or pass --apktool.")


def patch_manifest(path: Path, package: str, label_resource: str | None) -> dict:
    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag != "manifest":
        raise SystemExit(f"Unexpected manifest root: {root.tag}")

    root.set("package", package)
    app = root.find("application")
    if app is None:
        raise SystemExit("AndroidManifest.xml has no <application>")

    app.set(f"{A}appCategory", "game")

    # Remove anything that would let the app be treated as distraction-optimized.
    for meta in list(app.findall("meta-data")):
        if meta.get(f"{A}name") == "distractionOptimized":
            app.remove(meta)

    main_activity = None
    for activity in app.findall("activity"):
        if activity.get(f"{A}name") == "com.stremio.android.MainActivity":
            main_activity = activity
            break
    if main_activity is None:
        raise SystemExit("MainActivity not found; Stremio manifest changed")

    main_filter = None
    for intent_filter in main_activity.findall("intent-filter"):
        actions = {a.get(f"{A}name") for a in intent_filter.findall("action")}
        if "android.intent.action.MAIN" in actions:
            main_filter = intent_filter
            break
    if main_filter is None:
        raise SystemExit("MainActivity MAIN intent-filter not found")

    categories = {c.get(f"{A}name") for c in main_filter.findall("category")}
    if "android.intent.category.CAR_LAUNCHER" not in categories:
        ET.SubElement(main_filter, "category", {f"{A}name": "android.intent.category.CAR_LAUNCHER"})

    # Keep the original stremio:// scheme, and add aastremio:// so users can
    # explicitly target the clone when both apps are installed.
    has_aa_scheme = False
    for intent_filter in main_activity.findall("intent-filter"):
        for data in intent_filter.findall("data"):
            if data.get(f"{A}scheme") == "aastremio":
                has_aa_scheme = True
    if not has_aa_scheme:
        intent_filter = ET.SubElement(main_activity, "intent-filter")
        ET.SubElement(intent_filter, "action", {f"{A}name": "android.intent.action.VIEW"})
        ET.SubElement(intent_filter, "category", {f"{A}name": "android.intent.category.DEFAULT"})
        ET.SubElement(intent_filter, "category", {f"{A}name": "android.intent.category.BROWSABLE"})
        ET.SubElement(intent_filter, "data", {f"{A}scheme": "aastremio"})

    if label_resource:
        app.set(f"{A}label", label_resource)

    # Display continuity: moving to/from the car display should not recreate
    # the activity. Stremio already handles most config changes.
    config_changes = main_activity.get(f"{A}configChanges", "")
    if "density" not in config_changes.split("|"):
        main_activity.set(f"{A}configChanges", f"{config_changes}|density" if config_changes else "density")
        config_changes = main_activity.get(f"{A}configChanges", "")

    # Rename package-scoped authorities, permissions and callback hosts.
    for element in root.iter():
        for key, value in list(element.attrib.items()):
            if isinstance(value, str) and OFFICIAL_PACKAGE in value:
                element.set(key, value.replace(OFFICIAL_PACKAGE, package))

    ET.indent(tree, space="    ")
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return {
        "package": package,
        "app_category": app.get(f"{A}appCategory"),
        "car_launcher": "android.intent.category.CAR_LAUNCHER" in {
            c.get(f"{A}name") for c in main_filter.findall("category")
        },
        "aastremio_scheme": True,
    }


def patch_apktool_yml(path: Path, version_name: str, version_code: int) -> None:
    text = path.read_text(encoding="utf-8")
    text, n_code = re.subn(r"(?m)^(\s*versionCode:\s*).*$", rf"\g<1>{version_code}", text)
    text, n_name = re.subn(r"(?m)^(\s*versionName:\s*).*$", rf"\g<1>{version_name}", text)
    if n_code != 1 or n_name != 1:
        raise SystemExit("Could not update versionInfo in apktool.yml")
    path.write_text(text, encoding="utf-8")


def patch_strings(res: Path, label: str) -> None:
    changed = 0
    for strings in res.glob("values*/strings.xml"):
        text = strings.read_text(encoding="utf-8")
        new, n = re.subn(
            r'(<string\s+name="app_name"[^>]*>).*?(</string>)',
            rf"\g<1>{label}\g<2>",
            text,
        )
        if n:
            strings.write_text(new, encoding="utf-8")
            changed += n
    if changed == 0:
        raise SystemExit("app_name string not found")


def patch_launcher_color(res: Path) -> None:
    colors = res / "values" / "colors.xml"
    if not colors.is_file():
        return
    text = colors.read_text(encoding="utf-8")
    new, n = re.subn(
        r'(<color\s+name="ic_launcher_background">).*?(</color>)',
        r"\g<1>#ff100f1f\g<2>",
        text,
    )
    if n:
        colors.write_text(new, encoding="utf-8")


def copy_overlay(overlay: Path, res: Path) -> None:
    if not overlay.is_dir():
        log("No overlay directory; keeping upstream icon")
        return
    # The upstream adaptive icon is vector-based. Replace it with our bitmap
    # versions and remove the old XML so resource resolution picks the PNG.
    for stale in (
        res / "drawable" / "ic_launcher_foreground.xml",
        res / "drawable" / "ic_launcher_monochrome.xml",
    ):
        if stale.exists():
            stale.unlink()
    for source in overlay.rglob("*"):
        if source.is_dir():
            continue
        relative = source.relative_to(overlay)
        target = res / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    log(f"Copied overlay resources from {overlay}")


def patch_smali(decoded: Path, base_port: int) -> tuple[int, int]:
    """Patch port strings and remove the Facebook login buttons.

    Returns (port replacements, Facebook button calls removed).
    """
    port_hits = 0
    facebook_hits = 0
    facebook_screens = {
        "LoginScreenKt.smali",
        "SignupScreenKt.smali",
        "IntroScreenKt.smali",
    }
    facebook_pattern = re.compile(
        r"(?m)^(\s*)invoke-static \{[^}]+\}, "
        r"Lcom/stremio/android/ui/screens/intro/FacebookButtonKt;->"
        r"FacebookButton\(Landroidx/compose/runtime/Composer;I\)V\s*$"
    )

    for smali_root in sorted(decoded.glob("smali_classes*")):
        for path in smali_root.rglob("*.smali"):
            text = path.read_text(encoding="utf-8")
            new_text, port_count = re.subn(r"11470", str(base_port), text)
            facebook_count = 0
            if path.name in facebook_screens:
                new_text, facebook_count = facebook_pattern.subn(r"\1nop", new_text)
            if port_count or facebook_count:
                path.write_text(new_text, encoding="utf-8")
                port_hits += port_count
                facebook_hits += facebook_count

    if facebook_hits == 0:
        raise SystemExit("Facebook login button call not found; Stremio UI changed")
    log(f"Patched smali: {port_hits} port string(s), removed {facebook_hits} Facebook button call(s)")
    return port_hits, facebook_hits


def patch_server_js(decoded: Path, base_port: int) -> int:
    server = decoded / "assets" / "server.js"
    if not server.is_file():
        raise SystemExit("assets/server.js not found; Stremio packaging changed")
    text = server.read_text(encoding="utf-8", errors="surrogateescape")
    max_port = base_port + 4
    text, n_max = re.subn(r"\b11474\b", str(max_port), text)
    text, n_base = re.subn(r"\b11470\b", str(base_port), text)
    server.write_text(text, encoding="utf-8", errors="surrogateescape")
    log(f"Patched server.js: {n_base} base port(s), {n_max} max port(s)")
    return n_base + n_max


def patch_native_libs(decoded: Path, base_port: int) -> int:
    total = 0
    for so in decoded.glob("lib/*/*.so"):
        data = so.read_bytes()
        count = data.count(b"11470")
        if count:
            so.write_bytes(data.replace(b"11470", str(base_port).encode("ascii")))
            total += count
            log(f"Patched {so.relative_to(decoded)}: {count} port string(s)")
    return total


def build_apk(decoded: Path, unsigned: Path, apktool: str | None) -> None:
    if unsigned.exists():
        unsigned.unlink()
    run(apktool_command(apktool) + ["b", str(decoded), "-o", str(unsigned)])


def align_apk(unsigned: Path, aligned: Path, zipalign: str) -> None:
    if aligned.exists():
        aligned.unlink()
    # -P 16 aligns uncompressed .so files to 16 KB pages (Android 15+).
    # It cannot be combined with -p, so fall back to -p on older build-tools.
    command = [zipalign, "-P", "16", "-f", "4", str(unsigned), str(aligned)]
    log("$ " + " ".join(command))
    proc = subprocess.run(command, text=True, capture_output=True)
    if proc.returncode != 0 and ("unknown option" in proc.stdout.lower() or "unknown option" in proc.stderr.lower()):
        run([zipalign, "-p", "-f", "4", str(unsigned), str(aligned)])
    elif proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
        raise SystemExit(f"zipalign failed with exit code {proc.returncode}")


def sign_apk(
    aligned: Path,
    output: Path,
    apksigner: str,
    keystore: Path,
    key_alias: str,
    ks_pass: str,
    key_pass: str,
) -> None:
    if output.exists():
        output.unlink()
    env = dict(os.environ)
    env["AASTREMIO_KS_PASS"] = ks_pass
    env["AASTREMIO_KEY_PASS"] = key_pass
    run(
        [
            apksigner,
            "sign",
            "--ks",
            str(keystore),
            "--ks-key-alias",
            key_alias,
            "--ks-pass",
            "env:AASTREMIO_KS_PASS",
            "--key-pass",
            "env:AASTREMIO_KEY_PASS",
            "--min-sdk-version",
            "24",
            "--v1-signing-enabled",
            "true",
            "--v2-signing-enabled",
            "true",
            "--v3-signing-enabled",
            "true",
            "--out",
            str(output),
            str(aligned),
        ],
        env=env,
    )


def verify_output(
    output: Path,
    package: str,
    version_name: str,
    version_code: int,
    base_port: int,
    abi: str,
    apksigner: str,
    aapt2: str,
) -> dict:
    proc = subprocess.run([apksigner, "verify", "--verbose", "--print-certs", str(output)], text=True, capture_output=True)
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
        raise SystemExit("apksigner verification failed")

    badging = subprocess.run([aapt2, "dump", "badging", str(output)], text=True, capture_output=True)
    if badging.returncode != 0:
        print(badging.stderr)
        raise SystemExit("aapt2 dump badging failed")
    first = badging.stdout.splitlines()[0]
    if f"name='{package}'" not in first:
        raise SystemExit(f"Package verification failed: {first}")
    if f"versionCode='{version_code}'" not in first:
        raise SystemExit(f"versionCode verification failed: {first}")
    if f"versionName='{version_name}'" not in first:
        raise SystemExit(f"versionName verification failed: {first}")

    manifest = subprocess.run(
        [aapt2, "dump", "xmltree", "--file", "AndroidManifest.xml", str(output)],
        text=True,
        capture_output=True,
    )
    if manifest.returncode != 0:
        print(manifest.stderr)
        raise SystemExit("aapt2 dump xmltree failed")
    if "appCategory" not in manifest.stdout or not re.search(
        r"appCategory\([^)]*\)=0\b", manifest.stdout
    ):
        raise SystemExit("AA game category missing from built manifest")
    if "CAR_LAUNCHER" not in manifest.stdout:
        raise SystemExit("CAR_LAUNCHER missing from built manifest")

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        server = archive.read("assets/server.js")
        if str(base_port).encode() not in server:
            raise SystemExit("server.js base port patch missing")
        if b"11470" in server:
            raise SystemExit("server.js still contains the official port")
        dex_hits = 0
        for name in names:
            if re.fullmatch(r"classes\d*\.dex", name):
                dex_hits += archive.read(name).count(str(base_port).encode())
        if dex_hits == 0:
            raise SystemExit("dex port patch missing")
        native = f"lib/{abi}/libstremio_core_kotlin.so"
        if native in names and str(base_port).encode() not in archive.read(native):
            raise SystemExit("native core port patch missing")

    cert = ""
    for line in proc.stdout.splitlines():
        if "certificate SHA-256 digest" in line:
            cert = line.split(":", 1)[1].strip()
            break

    return {
        "output": str(output),
        "size": output.stat().st_size,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "package": package,
        "versionName": version_name,
        "versionCode": version_code,
        "abi": abi,
        "signerSha256": cert,
        "basePort": base_port,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Clone the official Stremio APK into AAStremio")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--upstream-version", required=True)
    parser.add_argument("--upstream-version-code", required=True, type=int)
    parser.add_argument("--abi", required=True, choices=["arm64-v8a", "armeabi-v7a", "x86", "x86_64"])
    parser.add_argument("--patch-revision", type=int, default=int(os.environ.get("AASTREMIO_PATCH_REVISION", "1")))
    parser.add_argument("--package", default=DEFAULT_PACKAGE)
    parser.add_argument("--label", default=DEFAULT_LABEL)
    parser.add_argument("--base-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--workdir", type=Path, default=ROOT / ".work")
    parser.add_argument("--overlay", type=Path, default=ROOT / "overlay" / "res")
    parser.add_argument("--apktool", default=None, help="Path to apktool.jar (or set APKTOOL_JAR)")
    parser.add_argument("--zipalign", default=None)
    parser.add_argument("--apksigner", default=None)
    parser.add_argument("--aapt2", default=None)
    parser.add_argument("--keystore", type=Path, required=True)
    parser.add_argument("--key-alias", default=os.environ.get("AASTREMIO_KEY_ALIAS", "aastremio"))
    parser.add_argument("--ks-pass", default=os.environ.get("AASTREMIO_KEYSTORE_PASSWORD", ""))
    parser.add_argument("--key-pass", default=os.environ.get("AASTREMIO_KEY_PASSWORD", ""))
    parser.add_argument("--keep-work", action="store_true")
    args = parser.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"Input APK not found: {args.input}")
    if not args.keystore.is_file():
        raise SystemExit(f"Keystore not found: {args.keystore}")
    if not args.ks_pass or not args.key_pass:
        raise SystemExit("Keystore passwords are required (env or --ks-pass/--key-pass)")
    if not (10000 <= args.base_port <= 65530):
        raise SystemExit("Base port out of range")

    version_name = f"{args.upstream_version}-aastremio.{args.patch_revision}"
    version_code = args.upstream_version_code * 10 + args.patch_revision

    work = args.workdir / args.abi
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    decoded = work / "decoded"
    unsigned = work / "unsigned.apk"
    aligned = work / "aligned.apk"
    args.output.parent.mkdir(parents=True, exist_ok=True)

    log(f"Decoding {args.input.name}")
    run(apktool_command(args.apktool) + ["d", "-f", "-o", str(decoded), str(args.input)])

    log("Patching AndroidManifest.xml")
    manifest_result = patch_manifest(decoded / "AndroidManifest.xml", args.package, None)
    log(json.dumps(manifest_result))

    patch_apktool_yml(decoded / "apktool.yml", version_name, version_code)
    patch_strings(decoded / "res", args.label)
    patch_launcher_color(decoded / "res")
    copy_overlay(args.overlay, decoded / "res")
    patch_server_js(decoded, args.base_port)
    port_hits, facebook_hits = patch_smali(decoded, args.base_port)
    patch_native_libs(decoded, args.base_port)

    log(f"Rebuilding {args.abi} APK")
    build_apk(decoded, unsigned, args.apktool)

    zipalign = args.zipalign or find_build_tool("zipalign")
    apksigner = args.apksigner or find_build_tool("apksigner")
    aapt2 = args.aapt2 or find_build_tool("aapt2")

    align_apk(unsigned, aligned, zipalign)
    log("Signing APK")
    sign_apk(aligned, args.output, apksigner, args.keystore, args.key_alias, args.ks_pass, args.key_pass)

    result = verify_output(
        args.output,
        args.package,
        version_name,
        version_code,
        args.base_port,
        args.abi,
        apksigner,
        aapt2,
    )
    result["upstreamVersion"] = args.upstream_version
    result["upstreamVersionCode"] = args.upstream_version_code
    result["patchRevision"] = args.patch_revision
    result["inputSha256"] = hashlib.sha256(args.input.read_bytes()).hexdigest()
    result["portStringsPatched"] = port_hits
    result["facebookButtonsRemoved"] = facebook_hits

    if not args.keep_work:
        shutil.rmtree(work)

    print(json.dumps(result, indent=2))
    summary = args.output.with_suffix(".json")
    summary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
