#!/usr/bin/env python3
"""Update versions.json after a successful build/release."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--meta", type=Path, default=ROOT / "build-meta.json")
    parser.add_argument("--versions", type=Path, default=ROOT / "versions.json")
    args = parser.parse_args()

    meta = json.loads(args.meta.read_text(encoding="utf-8"))
    versions = json.loads(args.versions.read_text(encoding="utf-8"))

    versions["officialSignerSha256"] = meta["officialSignerSha256"]
    versions["upstream"] = {
        "version": meta["version"],
        "sourcePage": meta["sourcePage"],
        "apks": {
            abi: {
                "url": entry["url"],
                "versionCode": entry["versionCode"],
                "sha256": entry["sha256"],
            }
            for abi, entry in meta["apks"].items()
        },
    }
    versions["lastBuilt"] = {
        "version": meta["version"],
        "patchRevision": meta["patchRevision"],
        "at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    args.versions.write_text(json.dumps(versions, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {args.versions}")


if __name__ == "__main__":
    main()
