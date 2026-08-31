#!/usr/bin/env python3
"""Cross-platform dependency bootstrap for the VTS Toolkit (macOS / Linux / Windows).

Creates a Python venv in the plugin's data dir and installs openpyxl, which all three
report scripts need. Idempotent — re-installs only when requirements.txt changes.

Writes the resolved interpreter path to <data>/venv-python.txt so the skills can find it
regardless of OS (venv/bin/python on Unix, venv\\Scripts\\python.exe on Windows).

Run with whatever Python the machine has:  python3 bootstrap.py   (or)   python bootstrap.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.abspath(os.path.join(HERE, ".."))
DATA = os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.expanduser("~/.vts-toolkit")
REQ = os.path.join(ROOT, "requirements.txt")
VENV = os.path.join(DATA, "venv")
STAMP = os.path.join(DATA, "requirements.installed.txt")
PYBIN_FILE = os.path.join(DATA, "venv-python.txt")


def venv_python(venv):
    if os.name == "nt":
        return os.path.join(venv, "Scripts", "python.exe")
    return os.path.join(venv, "bin", "python")


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def main():
    if sys.version_info < (3, 9):
        print(f"\n  This computer's version of Python is too old for the toolkit.\n\n"
              f"  Found version {sys.version.split()[0]}; it needs 3.9 or newer.\n\n"
              f"  What to try:\n"
              f"    - Install the latest Python from https://www.python.org/downloads\n",
              file=sys.stderr)
        return 1

    os.makedirs(DATA, exist_ok=True)
    vpy = venv_python(VENV)

    if os.path.exists(vpy) and _read(REQ) is not None and _read(REQ) == _read(STAMP):
        with open(PYBIN_FILE, "w", encoding="utf-8") as f:
            f.write(vpy)
        print(f"[vts-toolkit] Ready — everything needed is already installed.\n                (using {vpy})")
        return 0

    print("[vts-toolkit] Installing what the toolkit needs to read Excel files. One moment...")
    try:
        subprocess.run([sys.executable, "-m", "venv", VENV], check=True)
    except (subprocess.CalledProcessError, OSError) as e:
        print("\n  Couldn't set up the toolkit's private workspace.\n\n"
              "  This nearly always means Python isn't fully installed on this computer.\n\n"
              "  What to try:", file=sys.stderr)
        if os.name == "nt":
            print("    - Re-run the installer from https://www.python.org/downloads and "
                  "make sure\n"
                  "      the box marked 'Add Python to PATH' is TICKED on the first "
                  "screen.\n"
                  "      (Missing that box is the single most common cause.)", file=sys.stderr)
        else:
            print("    - Install Python 3.9 or newer from https://www.python.org/downloads",
                  file=sys.stderr)
        print(f"\n  (technical detail: {e})\n", file=sys.stderr)
        return 1

    vpy = venv_python(VENV)
    subprocess.run([vpy, "-m", "pip", "install", "--quiet", "--upgrade", "pip"], check=False)
    r = subprocess.run([vpy, "-m", "pip", "install", "--quiet", "-r", REQ])
    if r.returncode != 0:
        print("\n  Couldn't download the piece that reads Excel files.\n\n"
              "  What to try:\n"
              "    - Check this computer is online, then run /vts-setup again.\n"
              "    - If you're on a company network, a firewall may be blocking it — "
              "your IT team\n"
              "      would need to allow access to pypi.org.\n\n"
              f'  (technical detail: pip install failed; manual command:\n'
              f'   "{vpy}" -m pip install -r "{REQ}")\n', file=sys.stderr)
        return 1

    req = _read(REQ)
    if req is not None:
        with open(STAMP, "w", encoding="utf-8") as f:
            f.write(req)
    with open(PYBIN_FILE, "w", encoding="utf-8") as f:
        f.write(vpy)
    print(f"[vts-toolkit] Done — the toolkit can now read Excel files.\n                (using {vpy})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
