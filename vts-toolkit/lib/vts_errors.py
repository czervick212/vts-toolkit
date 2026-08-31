#!/usr/bin/env python3
"""Plain-language failures.

Two audiences read these: the person at the keyboard, who is a commercial real estate
broker and not a programmer, and Claude, which needs enough detail to fix the problem.
So every message leads with a sentence anyone can act on, and puts the technical detail
underneath where it doesn't have to be understood to be useful.

Never let a raw traceback be the last thing a user sees.
"""
import os
import sys
from pathlib import Path


def die(problem, detail=None, fixes=None, technical=None, code=1):
    """Print a readable failure and exit."""
    out = ["", f"  {problem}"]
    if detail:
        out += ["", f"  {detail}"]
    if fixes:
        out += ["", "  What to try:"]
        out += [f"    - {f}" for f in fixes]
    if technical:
        out += ["", f"  (technical detail: {technical})"]
    out.append("")
    print("\n".join(out), file=sys.stderr)
    sys.exit(code)


def check_report_file(path, label="report"):
    """Validate a spreadsheet before openpyxl gets a chance to throw at it."""
    p = Path(path).expanduser()

    if not p.exists():
        die(f"Can't find the {label}.",
            f"Looked for: {p}",
            ["Check the file name and folder are spelled right.",
             "If it lives in a cloud folder, open that folder once so the file downloads.",
             "If you just exported it from VTS, make sure the download finished."],
            "file does not exist")

    if p.is_dir():
        die(f"That's a folder, not a {label} file.",
            f"Got: {p}",
            ["Point at the .xlsx file itself, not the folder it's in."],
            "path is a directory")

    if p.suffix.lower() not in (".xlsx", ".xlsm"):
        die(f"That {label} isn't an Excel file.",
            f"Got: {p.name}",
            ["The toolkit reads .xlsx files — the format VTS exports.",
             "If you saved it as .xls or .csv, re-save it as .xlsx."],
            f"unsupported extension {p.suffix!r}")

    try:
        size = p.stat().st_size
    except OSError as e:
        die(f"Can't open the {label}.", f"File: {p}",
            ["Check you have permission to read that folder."], str(e))

    if size == 0:
        die(f"That {label} is empty (0 bytes).",
            f"File: {p}",
            ["This usually means a cloud folder hasn't downloaded the file yet — "
             "it looks like it's there but the contents aren't on this computer.",
             "Open the folder in Finder or File Explorer, wait for the file to finish "
             "downloading, then try again.",
             "In Dropbox you can right-click the file and choose to make it "
             "available offline."],
            "zero-byte file, almost certainly a cloud placeholder")

    if p.name.startswith("~$"):
        die(f"That's a temporary Excel lock file, not the {label}.",
            f"Got: {p.name}",
            ["Files starting with ~$ are created while a spreadsheet is open in Excel.",
             "Pick the real file — the same name without the ~$ prefix."],
            "Excel lock file")

    return str(p)


def check_folder(path, label="folder"):
    p = Path(path).expanduser()
    if not p.exists():
        die(f"Can't find the {label}.",
            f"Looked for: {p}",
            ["Check the folder path is right.",
             "If it's in a cloud folder, make sure it's synced to this computer."],
            "folder does not exist")
    if not p.is_dir():
        die(f"That {label} is a file, not a folder.", f"Got: {p}",
            ["Point at the folder your leasing reports live in."], "not a directory")
    return str(p)


def friendly_open(path, label="report"):
    """Wrap openpyxl so a corrupt file doesn't surface as a zipfile traceback."""
    import openpyxl
    check_report_file(path, label)
    try:
        return openpyxl.load_workbook(path)
    except Exception as e:
        die(f"Couldn't read that {label} — the file may be damaged.",
            f"File: {Path(path).name}",
            ["Try opening it in Excel. If Excel can't open it either, the download "
             "was probably interrupted — export it from VTS again.",
             "Make sure it's the Excel export from VTS, not a PDF renamed to .xlsx."],
            f"{type(e).__name__}: {e}")


def _locked_msg(dest, action, technical):
    die(f"Can't {action} the report — the file is open somewhere else.",
        f"File: {Path(dest).name}",
        ["Close the file in Excel, then run this again. Windows won't let anything "
         "change a spreadsheet while Excel has it open.",
         "If Excel isn't open, check whether anyone else has the file open from a "
         "shared folder.",
         "A cloud sync client mid-upload can also hold the file for a few seconds — "
         "wait a moment and retry."],
        technical)


def friendly_save(wb, dest):
    """openpyxl save, but a locked file explains itself instead of raising WinError 32."""
    try:
        wb.save(dest)
    except PermissionError as e:
        _locked_msg(dest, "save", f"PermissionError: {e}")
    except OSError as e:
        die("Couldn't save the finished report.",
            f"Tried to write: {dest}",
            ["Check the folder still exists and you can write to it.",
             "If it's a cloud folder, make sure it's finished syncing."],
            f"{type(e).__name__}: {e}")


def friendly_move(src, dst):
    """Move the superseded report aside, explaining a lock rather than raising."""
    import shutil
    try:
        shutil.move(src, dst)
    except PermissionError as e:
        _locked_msg(src, "replace", f"PermissionError: {e}")
    except OSError as e:
        die("Couldn't move the previous report aside.",
            f"File: {src}",
            ["Close it if it's open, then try again."],
            f"{type(e).__name__}: {e}")
