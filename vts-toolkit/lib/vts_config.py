#!/usr/bin/env python3
"""Per-user config for the VTS toolkit.

Everything account-specific lives here instead of in SKILL.md, so a plugin update
never clobbers the user's IDs and the property table grows itself as new assets
are discovered.

Usage:
    python3 lib/vts_config.py show
    python3 lib/vts_config.py set user.id 12345 user.name "Jane Broker"
    python3 lib/vts_config.py add-property "Main Street Plaza" 100200 \
        --address "Bethesda, MD" --folder "~/Dropbox/Landlords/.../Leasing Updates"
    python3 lib/vts_config.py find-property "fairfax"
"""
import json
import os
import sys
from pathlib import Path

DEFAULTS = {
    "user": {"id": None, "name": None},
    "paths": {"landlord_root": None},
    # VTS taxonomy ids. Seeded from the account they were discovered on;
    # vts-setup re-probes them and overwrites if this account differs.
    "ids": {
        "tenant_industry_retail_general": 122,
        "dead_deal_reasons": {"Requirement Dead": 35},
        "deal_type_id": 1,
    },
    "properties": [],
}


def config_path() -> Path:
    data = os.environ.get("CLAUDE_PLUGIN_DATA")
    base = Path(data) if data else Path.home() / ".vts-toolkit"
    base.mkdir(parents=True, exist_ok=True)
    return base / "vts-config.json"


def load() -> dict:
    p = config_path()
    if not p.exists():
        return json.loads(json.dumps(DEFAULTS))
    cfg = json.loads(p.read_text())
    # merge forward so a plugin update that adds a key doesn't break an old config
    for k, v in DEFAULTS.items():
        if k not in cfg:
            cfg[k] = v
        elif isinstance(v, dict):
            for kk, vv in v.items():
                cfg[k].setdefault(kk, vv)
    return cfg


def save(cfg: dict) -> Path:
    p = config_path()
    p.write_text(json.dumps(cfg, indent=2) + "\n")
    return p


def is_configured(cfg: dict) -> bool:
    return bool(cfg.get("user", {}).get("id"))


def _dig(cfg, dotted, value):
    cur = cfg
    parts = dotted.split(".")
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    if isinstance(value, str) and value.isdigit():
        value = int(value)
    cur[parts[-1]] = value


def add_property(cfg, name, prop_id, address=None, folder=None):
    prop_id = int(prop_id)
    for p in cfg["properties"]:
        if p["id"] == prop_id or p["name"].lower() == name.lower():
            p.update({"name": name, "id": prop_id})
            if address:
                p["address"] = address
            if folder:
                p["folder"] = folder
            return p
    entry = {"name": name, "id": prop_id}
    if address:
        entry["address"] = address
    if folder:
        entry["folder"] = folder
    cfg["properties"].append(entry)
    return entry


def find_property(cfg, query):
    q = query.lower().strip()
    props = cfg.get("properties", [])
    exact = [p for p in props if p["name"].lower() == q]
    if exact:
        return exact
    return [p for p in props if q in p["name"].lower() or q in p.get("address", "").lower()]


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    cmd, rest = argv[0], argv[1:]
    cfg = load()

    if cmd == "show":
        print(json.dumps(cfg, indent=2))
        print(f"\n# config file: {config_path()}", file=sys.stderr)
        if not is_configured(cfg):
            print("# NOT CONFIGURED — run /vts-setup", file=sys.stderr)
            return 2
        return 0

    if cmd == "path":
        print(config_path())
        return 0

    if cmd == "set":
        if len(rest) % 2:
            print("set takes key/value pairs", file=sys.stderr)
            return 1
        for k, v in zip(rest[::2], rest[1::2]):
            _dig(cfg, k, v)
        save(cfg)
        print(json.dumps(cfg, indent=2))
        return 0

    if cmd == "add-property":
        name, prop_id = rest[0], rest[1]
        address = folder = None
        for i, a in enumerate(rest):
            if a == "--address":
                address = rest[i + 1]
            if a == "--folder":
                folder = rest[i + 1]
        entry = add_property(cfg, name, prop_id, address, folder)
        save(cfg)
        print(json.dumps(entry, indent=2))
        return 0

    if cmd == "find-property":
        hits = find_property(cfg, " ".join(rest))
        print(json.dumps(hits, indent=2))
        return 0 if hits else 3

    print(f"unknown command: {cmd}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
