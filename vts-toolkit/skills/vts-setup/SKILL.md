---
name: vts-setup
description: First-run setup and health check for the VTS Leasing Toolkit — install dependencies, connect Chrome, verify the VTS session, discover this user's VTS user ID, taxonomy IDs and full property list, locate their report folders, then rehearse the whole leasing-update loop without writing anything. Use when someone installs the VTS toolkit, says "set up VTS", "configure the VTS tools", "get /vts working", "check my VTS setup", "vts doctor", "something's wrong with /vts", or when the /vts skill reports that config is missing or a script fails.
---

# VTS Toolkit — Setup

Run once per machine, and again any time something breaks. The goal is that by the end, the
user has watched the real loop run on their own data — so the first live run is boring.

Work through the phases in order. **After each phase, say what happened in one line.** Setup
that runs silently for three minutes and then declares success is not reassuring; a person
watching wants to see it working.

## Which Python command

`python3` on macOS/Linux, `python` on Windows — try one, and if it reports "command not found"
use the other. **Every command below is written as `python3`; substitute accordingly.** Settle
this once at the start and use the same one throughout.

**Windows: if typing `python` opens the Microsoft Store, that's a placeholder, not Python.**
It's the most common Windows snag and it looks like nothing happened. See
`${CLAUDE_PLUGIN_ROOT}/references/windows.md` — it needs a real install *and* turning off the
Store alias in Settings.

## Phase 1 — Dependencies

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py"
```

Creates a venv and installs `openpyxl`. Idempotent, so re-running is instant and safe.

If it fails to create the venv, Python isn't properly installed. On Windows that's almost always
the **"Add Python to PATH"** checkbox missed during install — the fix is to re-run the python.org
installer and tick it. Don't try to work around it.

## Phase 2 — Baseline health check

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py"
```

Every check with the exact fix for anything failing. On a fresh install expect the config checks
to fail — that's what the rest of this does. Note what it says so you can compare at the end.

## Phase 3 — Chrome and the VTS session

VTS runs on the user's authenticated browser session; there is no API key. Connect in this order —
a "not connected" error almost always means **no browser is selected**, not a broken extension:

1. `mcp__claude-in-chrome__list_connected_browsers`
2. `mcp__claude-in-chrome__select_browser` with the `deviceId` that comes back
3. `tabs_context_mcp`

Only if step 1 returns an empty list is the extension actually missing.

Then open `https://app.vts.com/lease/deals`.

**If they land on a login screen, stop and ask them to sign in**, then continue when they say
they're done. Never type credentials for them.

Worth saying out loud here, because it's the thing people trip on: the toolkit drives *Chrome
specifically*. If their everyday browser is Edge, Safari or Arc, being signed into VTS there does
nothing — they need to be signed in on Chrome.

## Phase 4 — Discover the account

Run the contents of `${CLAUDE_PLUGIN_ROOT}/skills/vts-setup/discover.js` via `javascript_tool` on
that tab. It is read-only — GETs only, no writes. Keep the leading `await`.

It returns:

| Field | What it is |
|---|---|
| `user.id` | Their VTS user ID — becomes the deal-lead on deals `/vts` creates |
| `user.name`, `user.email`, `user.account_id` | Identity, for confirming with them |
| `ids.tenant_industry_retail_general` | Industry ID for new deals |
| `ids.deal_type_id` | Deal type `new` |
| `ids.dead_deal_reasons` | Every dead-deal reason, keyed by name |
| `ids.deal_stages` | Every stage `status` → display name |
| `properties[]` | **Every property they can see**, with `id`, `name`, `city_state` |

Where this comes from: VTS bootstraps a global `vts` object into the page holding `vts.user` and
`vts.reference_data`. That's the whole discovery — there is no "current user" API endpoint to hunt
for. The property list is `GET /api/horse/properties?page=1&page_size=100`, paged.

**If `ok` is false, stop and read `errors`.** A missing `retail (general)` industry or
`requirement_dead` reason means this account's taxonomy differs from the one the toolkit was built
against, and creating deals would file them wrong. Report it rather than writing a partial config.

**Confirm the identity out loud before writing anything.** Show them `user.name` and `user.email`
and ask if that's right. A wrong user ID silently files every deal they create under someone else,
and that shows up on a landlord's audit trail.

Then write it:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/vts_config.py" set \
  user.id <id> user.name "<name>" user.email "<email>" user.account_id <account_id> \
  ids.tenant_industry_retail_general <id> ids.deal_type_id <id>
```

Add each discovered property — one call each, and worth doing for all of them so `/vts <anything>`
resolves without a lookup:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/vts_config.py" add-property "<name>" <id> --address "<city_state>"
```

Also merge the full `dead_deal_reasons` map into `ids.dead_deal_reasons` — that's a nested map, so
write the config JSON directly rather than using `set`.

Tell them how many properties came back. If it's a surprising number, that's worth catching now.

## Phase 5 — Rehearsal (this is the point)

Everything above is configuration. This is where they watch it actually work — a complete pass
through the real loop on their own data that **writes nothing to VTS**.

Pick any property with deals in VTS. **No saved report needed** — the rehearsal works whether or
not they keep them.

**5a. Read their deals back.** Proves the session and the property ID together:

```js
const H={'Accept':'application/json','X-Requested-With':'XMLHttpRequest'};
const r = await fetch('/api/horse/deals?activity_report_filter[properties][]=<ID>'
  +'&activity_report_filter[page]=1&activity_report_filter[page_size]=100'
  +'&properties[]=<ID>&page=1&page_size=100', {headers:H, credentials:'same-origin'});
const j = await r.json();
({total: j.total_count, sample: j.activity_logs.slice(0,3).map(d=>d.deal_name)});
```

A deal count and real tenant names means reads work. **The response is an object, not an array** —
rows are under `.activity_logs`; treating it as an array yields zero deals and looks like an auth
failure.

**5b. Export from VTS.** Walk them through it once, because the trap here is expensive:
**Export → Leasing Activity Excel → Export.** Do **not** click the settings dialog's left-nav
tabs — they are real links that navigate the page underneath and silently strip the `properties=`
filter, widening the export from one property to their entire portfolio.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/vts_paths.py" downloads
```

**5c. Parse it.** First real exercise of the scripts and the venv:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/vts/scripts/parse_report.py" "<the export>"
```

Should print the property title, the as-of date, and a deal count matching 6a. If the count
disagrees with VTS, the export was filtered differently — sort that out now, not mid-run.

**5d. Prove the diff.**

If they happen to have an edited or previously-sent report handy, diff it against the fresh
export — the real thing:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/vts/scripts/plan_changes.py" "<their report>" "<the export>"
```

**Otherwise diff the export against itself** — most people won't have one. It should report zero changes in
every bucket, which proves the machinery end-to-end and is a genuinely useful demonstration:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/vts/scripts/plan_changes.py" "<the export>" "<the export>"
```

Then explain the real shape: *"Next cycle you'll edit the comments in this file and hand it back
to me — everything that differs gets pushed."*

Interpret whatever you get with them:

- **Everything empty** — expected if their saved report is already in sync. The loop works; there's
  just nothing pending. Good outcome.
- **A few comment changes** — real pending edits. Show them and explain these are what `/vts` would
  post.
- **`new_deals` and `vanished` both large** — the two files are *different properties*. Both scripts
  print the property title on line one; compare them. Catching this here is exactly why the
  rehearsal exists.

**5e. Rehearse the finish**, which is genuinely non-destructive:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/vts/scripts/finalize_report.py" "<the export>" --dry-run
```

Shows the sheet it would strip, the filename, and where it would land: next to the export, in
Downloads. Ask whether that filename is what they'd want to send a landlord — `--name` overrides
it, and `--out` puts it elsewhere, but only if they ask.

**Stop here. Do not push anything.** The rehearsal ends before any write.

## When something fails

**On Windows, read `${CLAUDE_PLUGIN_ROOT}/references/windows.md` before debugging anything.**
It maps the Windows-specific failures — the Microsoft Store Python stub, `python` vs `python3`,
Excel file locks, the 260-character path limit, redirected Downloads folders. The toolkit was
built on macOS and its Windows paths were reasoned rather than tested, so prefer the actual
error text over any assumption.


The scripts print failures in plain language, with a "What to try" list and the technical detail
underneath. **Show the user that message as written rather than paraphrasing it** — it was
written for them, and re-wording it usually strips the actionable part.

Then act on it. Most failures resolve to one of four things:

| What they'll see | What it actually is |
|---|---|
| "Can't find the report" | Wrong path, or a cloud folder that hasn't synced |
| "That report is empty (0 bytes)" | Cloud placeholder — the file looks present but isn't downloaded |
| "The toolkit isn't finished installing" | The venv is missing; `/vts-setup` rebuilds it |
| "Couldn't read that report — the file may be damaged" | Interrupted download; re-export from VTS |

The technical detail in brackets is for you, not them. Use it to diagnose, but lead with the
plain sentence.

## Phase 6 — Confirm and hand over

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py"
```

Should now be all PASS. If anything still fails, fix it before declaring done — a FAIL here becomes
a confusing error mid-run later.

Then tell them, briefly:

- Who they're signed in to VTS as
- How many properties were found
- What the rehearsal showed (in sync / N pending edits / a mismatch caught)
- That the command is `/vts <property name>`, or plain English like *"run the leasing update for
  Main Street Plaza"*, and that it will ask them to drop in their edited spreadsheet
- That `/vts` **always previews the full plan before writing**, so they get a checkpoint on the
  first real run
- That the **write** paths — posting comments, moving stages, creating deals — are exercised for
  the first time on that run. Reads are proven; writes aren't yet.
- If anything misbehaves later, `/vts-setup` re-runs these checks

Keep it to a few lines. They've just watched it work; don't recap the whole session.
