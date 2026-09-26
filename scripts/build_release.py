#!/usr/bin/env python3
"""Build a deterministic ZIP containing only release-files.txt entries."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

from validate_release import ROOT, public_files, validate


def build():
    result = validate()
    if not result["ok"]:
        raise ValueError(json.dumps(result, indent=2))
    version = (ROOT / "VERSION").read_text().strip()
    if not version or any(c not in "0123456789.-abcdefghijklmnopqrstuvwxyz" for c in version):
        raise ValueError("Invalid release version")
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    target = dist / f"knowledge-base-kit-{version}.zip"
    hashes = {}
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in public_files():
            data = (ROOT / name).read_bytes()
            hashes[name] = hashlib.sha256(data).hexdigest()
            info = zipfile.ZipInfo("knowledge-base-kit/" + name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(".zip.sha256").write_text(f"{checksum}  {target.name}\n", encoding="utf-8")
    manifest = {"version": version, "archive": target.name, "archive_sha256": checksum,
                "files": hashes, "file_count": len(hashes)}
    (dist / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"archive": str(target), "sha256": checksum, "files": len(hashes), "bytes": target.stat().st_size}


if __name__ == "__main__":
    try:
        print(json.dumps(build(), indent=2))
    except (OSError, ValueError) as exc:
        print(f"Release build failed: {exc}", file=sys.stderr)
        sys.exit(1)
