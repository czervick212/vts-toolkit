#!/usr/bin/env python3
"""Make the report scripts run under whichever Python has openpyxl.

Without this, `python3 plan_changes.py` on a machine where openpyxl lives only in the
plugin's venv dies on import — the single most likely first-run failure. Instead we
re-exec under the venv interpreter bootstrap.py recorded, so it doesn't matter which
Python the skill happened to invoke.
"""
import os
import sys

# Fixed home, not CLAUDE_PLUGIN_DATA — that is unset when setup runs before the
# plugin has been loaded into a session, which would split config from the venv.
DATA = os.environ.get("VTS_TOOLKIT_HOME") or os.path.expanduser("~/.vts-toolkit")
PYBIN_FILE = os.path.join(DATA, "venv-python.txt")
_GUARD = "VTS_TOOLKIT_REEXEC"


def ensure_deps():
    try:
        import openpyxl  # noqa: F401
        return
    except ImportError:
        pass

    # Already re-exec'd once and still missing -> real failure, don't loop.
    if os.environ.get(_GUARD):
        sys.exit("\n  The toolkit can't read Excel files yet — its setup is incomplete.\n\n"
                 "  What to try:\n"
                 "    - Run /vts-setup in Claude. It reinstalls what's missing.\n\n"
                 "  (technical detail: openpyxl missing from the plugin venv "
                 "even after re-exec)\n")

    vpy = None
    try:
        with open(PYBIN_FILE, encoding="utf-8") as f:
            vpy = f.read().strip()
    except OSError:
        pass

    if not vpy or not os.path.exists(vpy):
        sys.exit("\n  The toolkit isn't finished installing.\n\n"
                 "  What to try:\n"
                 "    - Run /vts-setup in Claude. It only takes a moment and is safe to "
                 "re-run.\n\n"
                 "  (technical detail: openpyxl not importable and no venv recorded at "
                 f"{PYBIN_FILE})\n")

    env = dict(os.environ, **{_GUARD: "1"})
    os.execve(vpy, [vpy, os.path.abspath(sys.argv[0])] + sys.argv[1:], env)
