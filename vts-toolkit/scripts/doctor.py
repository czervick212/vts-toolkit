#!/usr/bin/env python3
"""Preflight check for the VTS Toolkit — everything that can be verified without a browser.

Prints one line per check with the exact fix for anything failing. Exit code is the
number of failures, so /vts-setup can loop until it reaches 0.

    python3 scripts/doctor.py           # human-readable
    python3 scripts/doctor.py --json    # machine-readable
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or HERE.parent)
DATA = Path(os.environ.get("VTS_TOOLKIT_HOME") or Path.home() / ".vts-toolkit")
sys.path.insert(0, str(ROOT / "lib"))

OK, WARN, FAIL = "ok", "warn", "fail"
results = []


def check(name, status, detail="", fix=""):
    results.append({"check": name, "status": status, "detail": detail, "fix": fix})


def run():
    # --- python ---------------------------------------------------------
    v = sys.version_info
    if v < (3, 9):
        check("Python installed", FAIL, f"version {v.major}.{v.minor} is too old",
              "Install the latest Python from https://www.python.org/downloads. "
              "On Windows, tick 'Add Python to PATH' on the first installer screen.")
    else:
        check("Python installed", OK, f"version {v.major}.{v.minor}.{v.micro}")

    # --- Windows-specific traps ------------------------------------------
    if os.name == "nt":
        # The Microsoft Store stub: `python` exists on PATH but is a placeholder that
        # opens the Store instead of running. Classic, and baffling without a name.
        if "windowsapps" in sys.executable.lower():
            check("Python source", FAIL,
                  "this is the Microsoft Store placeholder, not real Python",
                  "Typing 'python' opened the Microsoft Store instead of running "
                  "Python. Install Python from https://www.python.org/downloads "
                  "(tick 'Add Python to PATH'), then turn off the Store shortcut: "
                  "Settings > Apps > Advanced app settings > App execution aliases, "
                  "and switch OFF both 'python.exe' and 'python3.exe'.")
        else:
            check("Python source", OK, "real Python install")

        # 260-char path limit: deep cloud folders plus long property names hit this.
        long_paths = []
        try:
            import vts_config as _vc
            for _p in _vc.load().get("properties", []):
                f = _p.get("folder")
                if f and len(str(Path(f).expanduser())) > 200:
                    long_paths.append(_p["name"])
        except Exception:
            pass
        if long_paths:
            check("Folder path length", WARN,
                  f"very long paths: {', '.join(long_paths[:3])}",
                  "Windows limits file paths to 260 characters and these are close. "
                  "If saving a report fails, move the folder nearer the top of the "
                  "drive, or enable long paths in Windows.")

    # --- dependencies ---------------------------------------------------
    pybin = DATA / "venv-python.txt"
    vpy = pybin.read_text().strip() if pybin.exists() else None
    if vpy and Path(vpy).exists():
        check("Toolkit workspace", OK, vpy)
    else:
        check("Toolkit workspace", FAIL, "not set up yet",
              "Run /vts-setup in Claude — it builds this automatically.")

    try:
        import openpyxl  # noqa: F401
        check("Excel support", OK, "working")
    except ImportError:
        if vpy and Path(vpy).exists():
            check("Excel support", OK, "working (via the toolkit's own workspace)")
        else:
            check("Excel support", FAIL, "not installed",
                  "Run /vts-setup in Claude — it installs this automatically.")

    # --- scripts present -------------------------------------------------
    missing = [n for n in ("parse_report.py", "plan_changes.py", "finalize_report.py")
               if not (ROOT / "skills" / "vts" / "scripts" / n).exists()]
    if missing:
        check("Toolkit files", FAIL, f"missing: {', '.join(missing)}",
              "Some files didn't install. In Claude, run: "
              "/plugin install vts-toolkit@leasing-tools")
    else:
        check("Toolkit files", OK, "all present")

    # --- config ----------------------------------------------------------
    try:
        import vts_config
        cfg = vts_config.load()
    except Exception as e:
        check("Saved settings", FAIL, f"couldn't be read: {e}",
              "Run /vts-setup in Claude to rebuild them.")
        return

    if not cfg.get("user", {}).get("id"):
        check("Your VTS account", FAIL, "not linked yet",
              "Run /vts-setup in Claude. Until then the toolkit doesn't know who you "
              "are, and any deal it creates would be filed under the wrong person.")
    else:
        check("Your VTS account", OK, f'{cfg["user"].get("name") or "?"} (ID {cfg["user"]["id"]})')

    ids = cfg.get("ids", {})
    if not ids.get("tenant_industry_retail_general"):
        check("VTS deal settings", FAIL, "incomplete",
              "Run /vts-setup in Claude to read them from VTS again.")
    elif not ids.get("dead_deal_reasons"):
        check("VTS deal settings", WARN, "no 'dead deal' reasons saved",
              "Run /vts-setup again — without these, marking a deal dead will fail.")
    else:
        check("VTS deal settings", OK,
              f'{len(ids["dead_deal_reasons"])} dead-deal reasons saved')

    props = cfg.get("properties", [])
    if not props:
        check("Your properties", FAIL, "none found yet",
              "Run /vts-setup in Claude — it pulls your whole list from VTS.")
    else:
        with_folder = sum(1 for p in props if p.get("folder"))
        check("Your properties", OK, f"{len(props)} found, {with_folder} linked to a report folder")

    # --- paths -----------------------------------------------------------
    root = cfg.get("paths", {}).get("landlord_root")
    if not root:
        check("Report folder", WARN, "not set",
              "Run /vts-setup so it doesn't have to hunt for your reports each time.")
    elif not Path(root).expanduser().is_dir():
        check("Report folder", FAIL, f"can't be found: {root}",
              "The folder may have been moved or renamed, or a cloud folder may not "
              "have synced to this computer yet. Open it once in Finder or File "
              "Explorer, then run /vts-setup again.")
    else:
        check("Report folder", OK, root)

    for p in props:
        f = p.get("folder")
        if f and not Path(f).expanduser().is_dir():
            check(f'Folder for {p["name"]}', FAIL, f"can't be found: {f}",
                  "That folder moved, was renamed, or hasn't synced to this "
                  "computer. Run /vts-setup again to re-link it.")

    try:
        import vts_paths as _vp
        dl = _vp.downloads_dir()
    except Exception:
        dl = Path.home() / "Downloads"
    if dl.is_dir():
        check("Downloads folder", OK, str(dl))
    else:
        check("Downloads folder", WARN, f"not found at {dl}",
              "This is where VTS exports normally land. Tell Claude where your "
              "browser saves downloads.")

    # --- config writability ----------------------------------------------
    try:
        DATA.mkdir(parents=True, exist_ok=True)
        probe = DATA / ".write-probe"
        probe.write_text("x")
        probe.unlink()
        check("Saved settings", OK, str(DATA))
    except OSError as e:
        check("Saved settings", FAIL, f"can't be saved to {DATA}",
              "This computer is blocking writes to that folder. Your IT team can "
              "help; setup can't remember anything until it's fixed.")


def main(argv):
    run()
    fails = sum(1 for r in results if r["status"] == FAIL)
    warns = sum(1 for r in results if r["status"] == WARN)

    if "--json" in argv:
        print(json.dumps({"failures": fails, "warnings": warns, "results": results}, indent=2))
        return fails

    mark = {OK: "PASS", WARN: "WARN", FAIL: "FAIL"}
    width = max(len(r["check"]) for r in results)
    for r in results:
        line = f'  {mark[r["status"]]}  {r["check"].ljust(width)}  {r["detail"]}'
        print(line.rstrip())
        if r["fix"] and r["status"] != OK:
            print(f'        -> {r["fix"]}')
    print()
    if fails:
        print(f"{fails} thing(s) need fixing before /vts will work"
              + (f" ({warns} minor warning(s) too)" if warns else "")
              + ".\n  In most cases, running /vts-setup in Claude fixes all of it.")
    elif warns:
        print(f"Ready to go — with {warns} minor warning(s) noted above.")
    else:
        print("All checks passed — ready to run /vts <property>.")
    return fails


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
