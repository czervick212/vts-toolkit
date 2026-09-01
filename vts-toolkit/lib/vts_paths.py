#!/usr/bin/env python3
"""Locate the VTS export the browser just downloaded.

The toolkit does not go looking for the user's own files — they hand those over.
The one thing worth finding is the export we just triggered, and Windows lets the
Downloads folder be redirected, so ask the OS rather than assuming.

    python3 lib/vts_paths.py downloads [--all]
    python3 lib/vts_paths.py newest "<folder>"      # only when a folder is given explicitly
"""
import argparse
import json
import os
import sys
from pathlib import Path

def expand(p) -> Path:
    """Windows shells don't expand ~, so do it ourselves, always."""
    return Path(p).expanduser().resolve()


def newest(folder, ext=".xlsx", prefix=None):
    folder = expand(folder)
    if not folder.is_dir():
        return None
    files = []
    for f in folder.iterdir():
        try:
            if not f.is_file() or f.suffix.lower() != ext.lower():
                continue
            if f.name.startswith("~$"):        # Excel lock files
                continue
            if prefix and not f.name.lower().startswith(prefix.lower()):
                continue
            files.append((f.stat().st_mtime, str(f)))
        except (PermissionError, OSError):
            continue
    if not files:
        return None
    return max(files)[1]


def downloads_dir() -> Path:
    """The user's real Downloads folder.

    On Windows this is a "known folder" that can be redirected somewhere other than
    %USERPROFILE%\\Downloads, so ask the OS rather than assuming. Falls back to the
    obvious location everywhere else.
    """
    if os.name == "nt":
        try:
            import winreg
            key = (r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer"
                   r"\\Shell Folders")
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
                # {374DE290-...} is the Downloads known-folder GUID
                val, _ = winreg.QueryValueEx(k, "{374DE290-123F-4565-9164-39C4925E467B}")
                d = Path(os.path.expandvars(val))
                if d.is_dir():
                    return d
        except Exception:
            pass
    return Path.home() / "Downloads"


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("newest")
    n.add_argument("folder")
    n.add_argument("--ext", default=".xlsx")
    n.add_argument("--prefix")

    d = sub.add_parser("downloads")
    d.add_argument("--prefix", default="leasing-activity")
    d.add_argument("--ext", default=".xlsx")
    d.add_argument("--all", action="store_true")

    a = ap.parse_args(argv)

    if a.cmd == "newest":
        hit = newest(a.folder, a.ext, a.prefix)
        print(hit or "")
        return 0 if hit else 3

    if a.cmd == "downloads":
        dl = downloads_dir()
        if not dl.is_dir():
            print(f"no Downloads folder at {dl}", file=sys.stderr)
            return 3
        if a.all:
            files = sorted(
                (f.stat().st_mtime, str(f)) for f in dl.iterdir()
                if f.is_file() and f.suffix.lower() == a.ext.lower()
                and f.name.lower().startswith(a.prefix.lower())
            )
            print(json.dumps([p for _, p in reversed(files)], indent=2))
            return 0 if files else 3
        hit = newest(dl, a.ext, a.prefix)
        print(hit or "")
        return 0 if hit else 3

    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
