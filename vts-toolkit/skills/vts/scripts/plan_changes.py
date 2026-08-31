#!/usr/bin/env python3
"""Diff the edited leasing report against a fresh VTS export.

The fresh export is ground truth for what VTS currently holds. Anything that
differs in his edited file is therefore a pending edit that needs pushing.
Matching is by tenant name, which is safe because tenant names in the export
are identical to what VTS stores (and he always creates custom tenants, so
they stay identical going forward).

    python plan_changes.py <edited.xlsx> <fresh_export.xlsx> [--json]

Emits a change plan:
    comment_changes — comment body differs; post the new body as a new comment
    stage_changes   — he moved the row into a different section
    new_deals       — in his file, absent from VTS; create via + Deal
    vanished        — in VTS, absent from his file (usually means he deleted a
                      row by accident — surfaced for review, never acted on)
"""
import json
import pathlib
import sys

from parse_report import parse
from vts_errors import check_report_file


def expand(p):
    """Windows shells do not expand ~, so every path arg goes through here."""
    return str(pathlib.Path(p).expanduser())



def index_by_tenant(deals):
    """Tenant name -> deal. Case/whitespace-insensitive to survive light retyping."""
    out = {}
    for d in deals:
        out[d["tenant"].strip().lower()] = d
    return out


def plan(edited_path, fresh_path):
    edited = parse(edited_path)
    fresh = parse(fresh_path)

    mine = index_by_tenant(edited["deals"])
    theirs = index_by_tenant(fresh["deals"])

    comment_changes, stage_changes, new_deals, vanished = [], [], [], []

    for key, d in mine.items():
        current = theirs.get(key)

        if current is None:
            new_deals.append({
                "tenant": d["tenant"],
                "category": d["category"],
                "stage": d["stage"],
                "broker": d["broker"],
                "contact": d["contact"],
                "comment": d["comment"],
                "row": d["row"],
            })
            continue

        if d["comment"] and d["comment"] != current["comment"]:
            comment_changes.append({
                "tenant": d["tenant"],
                "stage": current["stage"],
                "old": current["comment"],
                "new": d["comment"],
                "row": d["row"],
            })

        if d["stage"] != current["stage"]:
            stage_changes.append({
                "tenant": d["tenant"],
                "from": current["stage"],
                "to": d["stage"],
                "row": d["row"],
            })

    for key, d in theirs.items():
        if key not in mine:
            vanished.append({"tenant": d["tenant"], "stage": d["stage"]})

    return {
        "edited_file": edited_path,
        "fresh_export": fresh_path,
        "edited_as_of": edited["as_of"],
        "fresh_as_of": fresh["as_of"],
        "counts": {
            "comment_changes": len(comment_changes),
            "stage_changes": len(stage_changes),
            "new_deals": len(new_deals),
            "vanished": len(vanished),
        },
        "comment_changes": comment_changes,
        "stage_changes": stage_changes,
        "new_deals": new_deals,
        "vanished": vanished,
    }


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    check_report_file(expand(sys.argv[1]), "edited report")
    check_report_file(expand(sys.argv[2]), "fresh VTS export")
    p = plan(expand(sys.argv[1]), expand(sys.argv[2]))

    if "--json" in sys.argv:
        print(json.dumps(p, indent=2))
        return

    c = p["counts"]
    print(f"Edited:  {p['edited_as_of']}")
    print(f"In VTS:  {p['fresh_as_of']}")
    print(f"\n{c['comment_changes']} comment(s), {c['stage_changes']} stage move(s), "
          f"{c['new_deals']} new deal(s), {c['vanished']} missing\n")

    if p["comment_changes"]:
        print("COMMENTS TO POST")
        for x in p["comment_changes"]:
            print(f"\n  {x['tenant']}  [{x['stage']}]")
            print(f"    was: {x['old'][:100]}")
            print(f"    now: {x['new'][:100]}")

    if p["stage_changes"]:
        print("\nSTAGE MOVES")
        for x in p["stage_changes"]:
            print(f"  {x['tenant']:<38} {x['from']} -> {x['to']}")

    if p["new_deals"]:
        print("\nNEW DEALS TO CREATE")
        for x in p["new_deals"]:
            print(f"  {x['tenant']:<38} {x['category']:<30} [{x['stage']}]")

    if p["vanished"]:
        print("\nIN VTS BUT NOT IN YOUR FILE (review — nothing will be done)")
        for x in p["vanished"]:
            print(f"  {x['tenant']:<38} [{x['stage']}]")


if __name__ == "__main__":
    main()
