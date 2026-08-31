#!/usr/bin/env python3
"""Turn a raw VTS export into the report you send your landlord client.

VTS downloads `leasing-activity-MM-DD-YY.xlsx` containing two sheets: an
"Overview" tab with building stats, and the deals sheet. The only manual step
he has ever done is deleting the Overview tab and renaming the file — so that
is all this does. The deals sheet is left completely untouched, because its
formatting is what he wants to preserve.

Filenames differ per property (street address for some, property name for
others, "Leasing Status Report" for one), so the convention is copied from the
newest file already sitting in the destination folder rather than invented.

    python finalize_report.py <raw_export.xlsx> <leasing_updates_folder> [--date M.D.YY] [--dry-run]
"""
import datetime as dt
import os
import pathlib
import re
import shutil
import sys

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                  "..", "..", "..", "lib"))
from vts_env import ensure_deps
from vts_errors import check_folder, friendly_move, friendly_open, friendly_save
ensure_deps()          # re-execs under the plugin venv if openpyxl is missing

import openpyxl


def expand(p):
    """Windows shells do not expand ~, so every path arg goes through here."""
    return str(pathlib.Path(p).expanduser())


NAME_RE = re.compile(
    r"^(?P<prefix>.*?)(?P<m>\d{1,2})(?P<sep>[.\-])(?P<d>\d{1,2})(?P=sep)(?P<y>\d{2,4})\.xlsx$",
    re.IGNORECASE,
)


def existing_reports(folder):
    out = []
    for f in os.listdir(folder):
        if f.startswith("~$") or not f.lower().endswith(".xlsx"):
            continue
        p = os.path.join(folder, f)
        if os.path.isfile(p):
            out.append((os.path.getmtime(p), f))
    return [f for _, f in sorted(out, reverse=True)]


def target_name(folder, today):
    """Copy the newest existing report's naming convention, swapping in today's date."""
    stamp_dot = f"{today.month}.{today.day}.{today.strftime('%y')}"
    for f in existing_reports(folder):
        m = NAME_RE.match(f)
        if m:
            sep = m.group("sep")
            stamp = f"{today.month}{sep}{today.day}{sep}{today.strftime('%y')}"
            return f"{m.group('prefix')}{stamp}.xlsx", f
    # pathlib normalizes both separators; folder.rstrip("/") missed Windows "...\\"
    parent = pathlib.Path(folder).resolve().parent
    base = parent.name or "Property"
    return f"{base} Leasing Update {stamp_dot}.xlsx", None


def finalize(raw_path, folder, date=None, dry_run=False):
    folder = check_folder(folder, "leasing updates folder")
    today = dt.date.today()
    if date:
        m, d, y = re.split(r"[.\-/]", date)
        y = int(y) + 2000 if len(y) == 2 else int(y)
        today = dt.date(y, int(m), int(d))

    name, modeled_on = target_name(folder, today)
    dest = os.path.join(folder, name)

    wb = friendly_open(raw_path, "VTS export")
    removed = [s for s in wb.sheetnames if s.lower().startswith("overview")]

    print(f"source:     {raw_path}")
    print(f"sheets:     {wb.sheetnames}")
    print(f"removing:   {removed or 'nothing (no Overview tab found)'}")
    print(f"naming:     {name}" + (f"   (matched: {modeled_on})" if modeled_on else "   (no prior file to model on)"))
    print(f"dest:       {dest}")

    if dry_run:
        print("\n[dry run — nothing written]")
        return dest

    if os.path.exists(dest):
        backup = dest.replace(".xlsx", f".superseded-{dt.datetime.now():%H%M%S}.xlsx")
        friendly_move(dest, backup)
        print(f"existing file moved aside -> {os.path.basename(backup)}")

    for s in removed:
        del wb[s]
    friendly_save(wb, dest)
    print(f"\nwrote {dest}")
    return dest


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    date = None
    for a in sys.argv[1:]:
        if a.startswith("--date"):
            date = a.split("=", 1)[1] if "=" in a else sys.argv[sys.argv.index(a) + 1]
    finalize(expand(args[0]), expand(args[1]), date=date, dry_run="--dry-run" in sys.argv)


if __name__ == "__main__":
    main()
