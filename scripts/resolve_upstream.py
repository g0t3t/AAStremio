#!/usr/bin/env python3
"""Resolve the latest official Stremio APKs and decide whether to rebuild.

The official download page is the primary source. A pinned versions.json entry
is used as a fallback when the page is stale, unreachable, or missing an ABI.

Security: every downloaded APK is checked against Stremio's pinned signing
certificate before it is used. SHA-256 hashes are recorded and compared so a
silent CDN re-upload can also trigger a rebuild.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from packaging.version import InvalidVersion, Version

ROOT = Path(__file__).resolve().parent.parent
DOWNLOADS_PAGE = "https://www.stremio.com/downloads"
URL_RE = re.compile(
    r"https://dl\.strem\.io/android/v(?P<version>[^/]+)-android/"
    r"com\.stremio\.one-(?P=version)-(?P<code>\d+)-"
    r"(?P<abi>armeabi-v7a|arm64-v8a|x86|x86_64)\.apk"
)
ABIS = ("arm64-v8a", "armeabi-v7a")
USER_AGENT = "AAStremio-Builder/1.0 (+https://github.com/)"


def log(message: str) -> None:
    print(f"[resolve] {message}", flush=True)


def parse_version(value: str) -> Version:
    try:
        return Version(value)
    except InvalidVersion:
        return Version("0")


def fetch_page() -> str:
    response = requests.get(
        DOWNLOADS_PAGE,
        headers={"User-Agent": USER_AGENT, "Cache-Control": "no-cache"},
        timeout=60,
    )
    response.raise_for_status()
    return response.text


def collect_links(html: str) -> dict[str, dict[str, dict]]:
    soup = BeautifulSoup(html, "html.parser")
    section = soup.find(id="android-mobile")
    links: list[str] = []
    if section is not None:
        links = [a.get("href", "") for a in section.find_all("a")]
    else:
        links = re.findall(r'https://dl\.strem\.io/android/[^"\']+\.apk', html)

    found: dict[str, dict[str, dict]] = {}
    for href in links:
        match = URL_RE.fullmatch(href)
        if not match:
            continue
        version = match.group("version")
        abi = match.group("abi")
        found.setdefault(version, {})[abi] = {
            "url": href,
            "versionCode": int(match.group("code")),
        }
    return found


def pick_latest(found: dict[str, dict[str, dict]]) -> tuple[str, dict[str, dict]] | None:
    candidates = [
        (version, apks)
        for version, apks in found.items()
        if all(abi in apks for abi in ABIS)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: parse_version(item[0]))


def find_tool(name: str) -> str:
    env_key = f"AASTREMIO_{name.upper()}"
    if os.environ.get(env_key):
        return os.environ[env_key]
    for sdk in filter(None, [os.environ.get("ANDROID_SDK_ROOT"), os.environ.get("ANDROID_HOME")]):
        build_tools = Path(sdk) / "build-tools"
        if build_tools.is_dir():
            for directory in sorted(build_tools.iterdir(), reverse=True):
                for suffix in (".exe", ".bat", ""):
                    candidate = directory / f"{name}{suffix}"
                    if candidate.is_file():
                        return str(candidate)
    found = shutil.which(name)
    if found:
        return found
    raise SystemExit(f"Could not find {name}; set AASTREMIO_{name.upper()}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> Path:
    if destination.exists():
        log(f"Using cached {destination.name}")
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    log(f"Downloading {url}")
    with requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=600,
        stream=True,
    ) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    return destination


def signer_sha256(apk: Path) -> str:
    apksigner = find_tool("apksigner")
    proc = subprocess.run(
        [apksigner, "verify", "--print-certs", str(apk)],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        log(proc.stdout)
        log(proc.stderr)
        raise SystemExit(f"apksigner failed for {apk.name}")
    for line in proc.stdout.splitlines():
        if "Signer #1 certificate SHA-256 digest" in line:
            return line.split(":", 1)[1].strip()
    raise SystemExit(f"Could not find signer certificate in {apk.name}")


def latest_release_revision(repo: str | None, token: str | None, version: str) -> int:
    if not repo:
        return 0
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.get(
            f"https://api.github.com/repos/{repo}/releases?per_page=100",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        log(f"Could not query GitHub releases: {exc}")
        return 0
    pattern = re.compile(rf"^v{re.escape(version)}-aastremio\.(\d+)$")
    revisions = [
        int(match.group(1))
        for release in response.json()
        if (match := pattern.match(release.get("tag_name", "")))
    ]
    return max(revisions, default=0)


def write_github_output(values: dict[str, object]) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            text = str(value).lower() if isinstance(value, bool) else str(value)
            handle.write(f"{key}={text}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve the latest official Stremio APKs")
    parser.add_argument("--versions", type=Path, default=ROOT / "versions.json")
    parser.add_argument("--download-dir", type=Path, default=ROOT / "upstream")
    parser.add_argument("--output", type=Path, default=ROOT / "build-meta.json")
    parser.add_argument("--version", help="Override the upstream version")
    parser.add_argument("--arm64-url", help="Override the ARM64 APK URL")
    parser.add_argument("--arm-url", help="Override the ARM APK URL")
    parser.add_argument("--force", action="store_true", help="Build even if nothing changed")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    parser.add_argument("--skip-download", action="store_true")
    args = parser.parse_args()

    versions = json.loads(args.versions.read_text(encoding="utf-8"))
    pinned = versions.get("upstream", {})
    pinned_version = pinned.get("version", "0")
    pinned_apks: dict[str, dict] = pinned.get("apks", {})
    pinned_signer = versions.get("officialSignerSha256", "")

    page_error = None
    found: dict[str, dict[str, dict]] = {}
    try:
        html = fetch_page()
        found = collect_links(html)
        latest = pick_latest(found)
        log(f"Official page candidates: {sorted(found, key=parse_version)}")
    except Exception as exc:  # noqa: BLE001
        page_error = str(exc)
        latest = None
        log(f"Official page unavailable: {exc}")

    if args.version:
        candidate_version = args.version
        candidate = dict(found.get(candidate_version, {}))
        if candidate_version == pinned_version:
            candidate = {**pinned_apks, **candidate}

        def code_from_url(url: str) -> int:
            match = URL_RE.fullmatch(url)
            return int(match.group("code")) if match else 0

        if args.arm64_url:
            candidate["arm64-v8a"] = {"url": args.arm64_url, "versionCode": code_from_url(args.arm64_url)}
        if args.arm_url:
            candidate["armeabi-v7a"] = {"url": args.arm_url, "versionCode": code_from_url(args.arm_url)}
        reason = "manual"
    elif latest and parse_version(latest[0]) > parse_version(pinned_version):
        candidate_version, candidate = latest
        reason = "new-version"
    elif latest and parse_version(latest[0]) == parse_version(pinned_version):
        candidate_version, candidate = latest
        reason = "pinned"
    else:
        candidate_version, candidate = pinned_version, dict(pinned_apks)
        reason = "fallback" if page_error else "pinned"

    # Fill missing ABIs from the pinned version only when it is the same version.
    if candidate_version == pinned_version:
        for abi, entry in pinned_apks.items():
            candidate.setdefault(abi, entry)

    missing = [abi for abi in ABIS if abi not in candidate]
    if missing:
        raise SystemExit(
            f"Could not resolve {', '.join(missing)} for Stremio {candidate_version}. "
            f"Page error: {page_error or 'none'}. "
            "Pass --version plus --arm64-url/--arm-url to override."
        )

    if not pinned_signer:
        raise SystemExit("versions.json is missing officialSignerSha256")

    resolved: dict[str, dict] = {}
    for abi in ABIS:
        entry = candidate[abi]
        url = entry["url"]
        filename = url.rsplit("/", 1)[-1]
        destination = args.download_dir / filename
        if not args.skip_download:
            download(url, destination)
            digest = sha256(destination)
            cert = signer_sha256(destination)
            if cert != pinned_signer:
                raise SystemExit(
                    f"SECURITY: {filename} signer is {cert}, expected {pinned_signer}. "
                    "Refusing to build from an APK not signed by Stremio."
                )
        else:
            digest = entry.get("sha256", "")
            cert = pinned_signer
        resolved[abi] = {
            "url": url,
            "versionCode": int(entry.get("versionCode") or 0),
            "sha256": digest,
            "signerSha256": cert,
            "file": str(destination),
            "size": destination.stat().st_size if destination.exists() else 0,
        }
        if not resolved[abi]["versionCode"]:
            match = URL_RE.fullmatch(url)
            if match:
                resolved[abi]["versionCode"] = int(match.group("code"))
        if not resolved[abi]["versionCode"]:
            raise SystemExit(f"Could not determine versionCode for {url}")

    last_built = versions.get("lastBuilt") or {}
    pinned_hashes = {
        abi: pinned_apks.get(abi, {}).get("sha256", "") for abi in ABIS
    }
    upstream_changed = any(
        resolved[abi]["sha256"] and resolved[abi]["sha256"] != pinned_hashes.get(abi)
        for abi in ABIS
    )
    version_changed = candidate_version != last_built.get("version")
    should_build = bool(args.force or version_changed or upstream_changed)

    revision = 0
    if last_built.get("version") == candidate_version:
        revision = int(last_built.get("patchRevision", 0))
    revision = max(
        revision,
        latest_release_revision(args.repo, args.token, candidate_version),
    )
    patch_revision = revision + 1 if should_build else max(revision, 1)

    if not should_build:
        reason = "unchanged"
    elif args.force:
        reason = "forced"

    meta = {
        "shouldBuild": should_build,
        "reason": reason,
        "version": candidate_version,
        "patchRevision": patch_revision,
        "sourcePage": DOWNLOADS_PAGE,
        "officialSignerSha256": pinned_signer,
        "apks": resolved,
        "lastBuilt": last_built or None,
    }
    args.output.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    write_github_output(
        {
            "should_build": should_build,
            "version": candidate_version,
            "patch_revision": patch_revision,
            "reason": reason,
        }
    )
    log(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
