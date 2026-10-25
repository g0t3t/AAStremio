#!/usr/bin/env python3
"""Generate GitHub release notes for an AAStremio build."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--meta", type=Path, default=ROOT / "build-meta.json")
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    parser.add_argument("--output", type=Path, default=ROOT / "release-notes.md")
    args = parser.parse_args()

    meta = json.loads(args.meta.read_text(encoding="utf-8"))
    version = meta["version"]
    revision = meta["patchRevision"]

    summaries: dict[str, dict] = {}
    for path in args.dist.glob("AAStremio-*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        summaries[data.get("abi", "")] = data

    lines: list[str] = []
    lines.append(f"# AAStremio {version}")
    lines.append("")
    lines.append(
        f"Unofficial Android Auto build of Stremio, cloned as "
        f"`com.aastremio.app`. This release is based on upstream Stremio "
        f"**{version}** and is patch revision **{revision}**."
    )
    lines.append("")
    lines.append("## Downloads")
    lines.append("")
    lines.append("| ABI | APK | versionCode | SHA-256 |")
    lines.append("| --- | --- | --- | --- |")
    for abi, entry in meta["apks"].items():
        summary = summaries.get(abi, {})
        sha = summary.get("sha256") or "see SHA256SUMS.txt"
        lines.append(
            f"| `{abi}` | `AAStremio-{version}-aastremio.{revision}-{abi}.apk` | "
            f"`{summary.get('versionCode', entry.get('versionCode', ''))}` | `{sha}` |"
        )
    lines.append("")
    lines.append("Use **arm64-v8a** unless you know your phone is 32-bit only.")
    lines.append("")
    lines.append("## Upstream integrity")
    lines.append("")
    lines.append(f"- Official download page: {meta['sourcePage']}")
    lines.append(f"- Pinned Stremio signer SHA-256: `{meta['officialSignerSha256']}`")
    for abi, entry in meta["apks"].items():
        lines.append(f"- `{abi}` upstream SHA-256: `{entry.get('sha256', '')}`")
    lines.append("")
    lines.append("## Install")
    lines.append("")
    lines.append("1. Download the APK for your phone.")
    lines.append("2. Install it next to the official Stremio app.")
    lines.append("3. Enable Android Auto developer mode and **Unknown sources**.")
    lines.append("4. Connect to the car and open **AAStremio** while parked.")
    lines.append("5. Sign in with Stremio email/password.")
    lines.append("")
    lines.append(
        "Requires **Android 15+** for Android Auto parked-app support. "
        "Email/password login only; Facebook/Google/Apple sign-in is not available."
    )
    lines.append("")
    lines.append("## Safety")
    lines.append("")
    lines.append(
        "AAStremio is a parked app. Android Auto blocks it while the vehicle is "
        "moving. Do not watch video while driving and do not attempt to bypass "
        "Android Auto's safety restrictions. Use only while parked or as a passenger."
    )
    lines.append("")
    lines.append("## Disclaimer")
    lines.append("")
    lines.append(
        "AAStremio is an unofficial, non-profit, open-source project. It is not "
        "affiliated with Stremio, Google, Android Auto, or any vehicle "
        "manufacturer. It is provided **as-is**, without warranty. The maintainers "
        "take no responsibility or liability for damage, accidents, traffic "
        "violations, data loss, account action, or legal issues. You must comply "
        "with Stremio's terms and all applicable laws. Stremio's name, logo, and "
        "code belong to their respective owners."
    )
    lines.append("")
    lines.append("See the repository README and DISCLAIMER.md for the full text.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("Built automatically by GitHub Actions.")
    lines.append("")

    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
