#!/usr/bin/env python3
"""Guard the owner-approved WiejskaPaka UI against accidental replacements.

Usage: python scripts/check_approved_ui.py
The baseline follows the owner-confirmed browser view and the approved demo release.
Only the three layout entry files are byte-locked here; new features may be
added through separate assets without silently replacing these files.
"""
from pathlib import Path
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[1]
# Release 2c193f4 retains the approved layout and loads the new admin-only panel.
APPROVED_GIT_BLOBS = {
    "web/index.html": "79775b5f63356f32612aefe3900cf41a43d02363",
    "web/style.css": "4b16e2dda3241c6fe3d97e210cea31c74204b1b1",
    "web/app.js": "5b61bac6e32db5b30069d1be0dbb4fc01fb51409",
}

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()

def main() -> int:
    failures = []
    for name, expected in APPROVED_GIT_BLOBS.items():
        path = ROOT / name
        if not path.is_file():
            failures.append(f"MISSING: {name}")
            continue
        actual = git_blob_sha(path.read_bytes())
        if actual != expected:
            failures.append(f"CHANGED: {name}: {actual} != {expected}")
        else:
            print(f"OK: {name}")
    if failures:
        print("APPROVED UI REGRESSION: do not merge before owner review.", file=sys.stderr)
        for issue in failures:
            print(issue, file=sys.stderr)
        return 1
    print("Approved layout entry files match the owner-confirmed baseline.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
