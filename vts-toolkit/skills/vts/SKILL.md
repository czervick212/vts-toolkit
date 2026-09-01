---
name: vts
description: Run the biweekly VTS leasing-update loop for a property — export the leasing report from VTS, diff it against the version the user edited, push their changed comments and stage moves back into VTS via its JSON API, create any new deals they added, then re-export a clean formatted report for the landlord. Use whenever the user says "/vts <property>", "update VTS", "push my leasing report", "run the leasing update for <property>", "sync <property> to VTS", "I finished the leasing report", "post these comments to VTS", or hands over an edited leasing update spreadsheet and wants VTS brought in line. Also use when they ask what changed since the last cycle, or want a fresh leasing report generated for a landlord.
---

# VTS Leasing Update

Brokers maintain a leasing report for each landlord client on a two-week cadence. The report *is* a
VTS export, so the same information lives in two places, and the manual version of this is typing it
twice — once in Excel for the landlord, once through dozens of separate comment modals in VTS. This
skill collapses that into one edit.

**The loop:** VTS export → they edit comments in Excel → this skill pushes the edits back →
re-export a clean report for the landlord.

Excel is the editing surface because bulk-editing a spreadsheet (or dictating into it) is far faster
than clicking through modals. VTS stays the system of record. The final deliverable is regenerated
from VTS so it's correct by construction.

**Argument:** the property name — `/vts Fairfax Propane`.

## Which Python command

`python3` on macOS/Linux, `python` on Windows — try one, and if it reports "command not found"
use the other. **Every command below is written as `python3`; substitute accordingly.** All paths
use `${CLAUDE_PLUGIN_ROOT}` and forward slashes, which work on all three platforms.

## Step 0 — Load config

Everything account-specific — user ID, taxonomy IDs, property IDs, folder paths — lives in config,
not in this file:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/vts_config.py" show
```

Exit code 2 means it has never been set up. **Stop and run `/vts-setup`** — without a real user ID,
any deal created here gets filed under the wrong person on a landlord's audit trail.

**If anything below fails — a script errors, a folder is missing, a write is rejected — run the
diagnostic before debugging by hand.** It checks Python, dependencies, config, and every recorded
path, and prints the fix for whatever is broken:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py"
```

The report scripts re-exec themselves under the plugin venv if `openpyxl` is missing, so a plain
`ModuleNotFoundError` should never surface. If one does, the venv is gone — `/vts-setup` rebuilds it.

Resolve the property argument against config:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/vts_config.py" find-property "<argument>"
```

One hit, use it. Several, ask which — names are not unique in VTS, so two entries can share a name and differ only by id and address. None, see *Finding a property that isn't in config* below.

## Before anything else

**VTS has a usable write API — use it.** The UI is a React front end over a JSON API on the same
origin, and every write this skill needs (deals, stage changes, dead-deal reasons, comments, comment
edits) goes through it. Drive it with `javascript_tool` on an open VTS tab, using the user's
authenticated session. Contracts are in **The write API** below.

Clicking is the fallback, not the default. On a 100+ write run the click path silently dropped
roughly one write in four.

Connect to Chrome first, in this order — a "not connected" error almost always means no browser is
selected, **not** a broken extension:

1. `mcp__claude-in-chrome__list_connected_browsers`
2. `mcp__claude-in-chrome__select_browser` with the `deviceId` that comes back
3. `tabs_context_mcp`

Never suggest reinstalling the extension unless step 1 returns an empty list. The user must be
signed into VTS **in Chrome specifically** — if their daily driver is another browser, the session
doesn't carry over.

## The write API

Grab the CSRF token once per page load — it does not survive a navigation:

```js
window.__csrf = document.querySelector('meta[name="csrf-token"]').content;
const H = {'Content-Type':'application/json','Accept':'application/json',
           'X-CSRF-Token':window.__csrf,'X-Requested-With':'XMLHttpRequest'};
```

**Read every deal on a property** (`page_size` up to 100):

```
GET /api/horse/deals?activity_report_filter[properties][]=<PROP>
    &activity_report_filter[page]=1&activity_report_filter[page_size]=100
    &properties[]=<PROP>&page=1&page_size=100
```

Returns `{activity_logs:[…], total_count}`. Each entry carries `id`, `deal_name`, and
`latest_activity.activity.display_status` — the stage.

**Read every comment on a deal.** Accepts multiple ids, so batch ~8 per call:

```
GET /api/horse/deal_artifacts?activity_log_ids[]=<id>&activity_log_ids[]=<id>
```

Flat array. `class_name` is `ActivityLogIterationComment` for comments (`id`,
`artifact_message`, `artifact_date`) and `ActivityLogIteration` for stage changes. This is
the only way to see *all* comments — the Excel export shows just the latest one per deal,
which makes it useless for verifying a back-fill.

**The deals list response is an OBJECT, not an array.** Rows live under `.activity_logs`, alongside
`total_count` / `total_pages`. Treating the response as an array silently yields zero deals and
looks like an auth failure.

**Create a deal** — `POST /activity_logs`, returns 201. Substitute the bracketed values from config
(`user.id`, `ids.tenant_industry_retail_general`, `ids.deal_type_id`). Note
`activity_log_brokers_attributes`: it ships empty here, but it is the same field used to set the
deal contact (see *Writing the deal contact*) — you can populate it at creation instead of in a
second call:

```json
{"activity_log":{"contacts":[],"status":"initial_inquiry","date":"<ISO8601 with offset>",
 "undisclosedTenant":false,"space_ids":[],"property_ids":[<PROPERTY_ID>],"office_park_ids":[],
 "can_update_stage":true,"deal_type_id":<DEAL_TYPE_ID>,"tenant":"<NAME>",
 "tenant_industry_id":<RETAIL_INDUSTRY_ID>,
 "deal_leads":[{"id":<USER_ID>,"label":"<USER NAME>","value":<USER_ID>}],
 "deal_lead_ids":[<USER_ID>],
 "submarket_ids":[],"activity_log_tenants_attributes":[],"activity_log_brokers_attributes":[],
 "custom_tenant_name":null}}
```

On the account this was built against, `tenant_industry_id` 122 = `Retail (General)` and
`deal_type_id` 1 = `new`. These are platform-level rather than per-account, but read them from
config anyway — a mismatch there is invisible until a landlord notices. The large `asset_groups`
blob the UI also sends is optional; `property_ids` alone attaches the deal to the right asset.

**Change stage** — `POST /activity_logs/<dealId>/activity_log_iterations`:

```json
{"activity_log_iteration":{"status":"dead_deal","activity_log_iteration_reason_ids":[<REASON_ID>]}}
```

Reason IDs are in config under `ids.dead_deal_reasons`, keyed by name (`requirement_dead` was 35).
A reason is required for `dead_deal` and rejected for other stages. This opens a new iteration;
comments on the old one still display.

**Post a comment** — `POST /activity_log_iteration_comments`:

```json
{"activity_log_iteration_comment":{"comment":"<body>","mentions_attributes":[],"documents":[],
 "space_ids":[],"isTour":false,"comment_date":"<ISO8601 with offset>",
 "activity_log_iteration_id":<latest iteration id>,"activity_log_id":<dealId>}}
```

`activity_log_iteration_id` is the highest-id `ActivityLogIteration` from `deal_artifacts`.
`comment_date` drives the `MM/DD/YY - ` prefix on the export, so it is how you back-date.
Use `-04:00` for EDT dates (March–November), `-05:00` for EST.

**Edit or re-date a comment** — `PATCH /activity_log_iteration_comments/<commentId>` with the
same body minus the two id fields.

**Verify every batch.** Re-read `deal_artifacts` and diff against what you meant to write.
It is one cheap call and it is the only thing that catches a silent miss.

### Tenant names get normalized

VTS standardizes new tenant names against its company directory. `IKEA` came back as `Ikea`,
`MedStar Health` as `Medstar Health`, `University of Maryland Medical System` as
`University Of Maryland Medical System`. Harmless on the landlord report, but it breaks the
exact-name matching in Step 3 — so after creating deals, read the list back and match on
VTS's spelling, not the spreadsheet's.

## Step 1 — Locate the property folder

If config has a `folder` for this property, use it. Otherwise search under `paths.landlord_root`
— depth varies (some properties sit directly under a landlord, some are nested), so search rather
than assume:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/vts_paths.py" find-folders "<landlord_root>" \
  --name "Leasing Updates" --match "<property>"
```

If that misses, list the landlord folders and match by eye — the property may be named differently
on disk than in VTS. Once found, record it so the next run skips the search:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/vts_config.py" add-property "<name>" <id> --folder "<path>"
```

Then open the property's deal pipeline in VTS:

```
https://app.vts.com/lease/deals?properties=<PROPERTY_ID>&page=1
```

### Finding a property that isn't in config

One read-only call lists every property the user can see:

```js
const H={'Accept':'application/json','X-Requested-With':'XMLHttpRequest'};
const j = await (await fetch('/api/horse/properties?page=1&page_size=100',
  {headers:H, credentials:'same-origin'})).json();
j.properties.filter(p=>/<search>/i.test(p.name)).map(p=>({id:p.id, name:p.name, where:p.city_state}));
```

Page with `&page=N` up to `j.num_pages`. Add what you find via `add-property` so it's there next
time. (The manual route — clicking the asset switcher at top-left of the sidebar and reading
`properties=<id>` out of the URL — still works, but there's no reason to use it. Note that clicking
the asset's thumbnail does nothing; you have to click the name text.)

## Step 2 — Export the current state from VTS

This gives you ground truth for what VTS holds right now.

1. Click **Export** → **Leasing Activity Excel**
2. In the settings dialog, click **Export** immediately

**Do not click the dialog's left-nav tabs.** They are real `<a href="/lease/deals">` links —
clicking one navigates the page underneath and silently strips the `properties=` filter, which
widens the export from one property to the user's entire portfolio. If the filter drops, re-navigate
to the filtered URL and start the export over.

The file lands in the user's Downloads folder as `leasing-activity-MM-DD-YY.xlsx`. Locate it
without guessing at the path — Downloads is not `~/Downloads` everywhere:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/vts_paths.py" downloads
```

That prints the newest matching export. Add `--all` to list them newest-first when several runs
have piled up and you need to be sure which one you just made.

Two browser habits worth keeping, both learned the hard way:

- **Use `find` to get element refs rather than screenshot coordinates.** Screenshot dimensions shift
  between calls (1444×851 vs 1426×840), and a stale coordinate once hit the asset switcher and blew
  away the filter.
- **Re-`find` after any navigation.** Refs don't survive a page load.

## Step 3 — Work out what changed

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/vts/scripts/plan_changes.py" \
  "<their edited report>.xlsx" "<fresh export>.xlsx"
```

Their edited report is the newest `.xlsx` in the property's leasing-updates folder:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/vts_paths.py" newest "<leasing updates folder>"
``` The fresh export
is ground truth, so anything that differs in their file is a pending edit.

The plan comes back in four buckets:

| Bucket | Meaning | Action |
|---|---|---|
| `comment_changes` | Comment body differs | Post the new body as a new comment |
| `stage_changes` | Row moved to a different section | Change the stage |
| `new_deals` | In their file, not in VTS | Create via the API (confirm first) |
| `vanished` | In VTS, not in their file | **Report only — never act on it** |

`vanished` almost always means a row got deleted by accident during editing. Deleting a deal in VTS
because a spreadsheet row went missing would be destructive and unrecoverable, so surface it and let
them decide.

**Sanity-check the shape of the plan before showing it.** If `new_deals` and `vanished` are both
large — most of the sheet on each side — the two files are almost certainly *different properties*,
not a real diff. Both scripts print the property title on their first line; compare them. Pushing
that plan would create a whole property's deals on the wrong asset. Re-check which export you
grabbed before going further.

If every bucket is empty, they haven't edited anything yet. Say so, and offer to finalize a fresh
report (Step 7) so they have something current to edit.

Add `--json` for machine-readable output when you need to drive the pushes programmatically.

## Step 4 — Show them the plan

Before writing anything, show what you're about to do: the comments (old → new), the stage moves,
and the new deals. These writes land in a **landlord client's** system of record with the user's
name on the audit trail, so a preview is cheap insurance against a mis-parsed spreadsheet.

Once they confirm, push everything without stopping to ask again per row — the point is speed, and
they've already reviewed the list.

## Step 5 — Push comments

For each entry in `comment_changes`, POST to `/activity_log_iteration_comments` (see **The write
API**). Loop in one `javascript_tool` call with a ~350ms pause between posts, then re-read
`deal_artifacts` to confirm every one landed with the right body and date.

**Post the bare comment body, never a date prefix.** The `MM/DD/YY - ` in the export is generated by
VTS from `comment_date` — `plan_changes.py` already strips it. Re-adding one produces
`08/17/26 - 08/17/26 - …` on the next export. To date a comment to when the conversation actually
happened, set `comment_date`; that is what drives the prefix.

<details><summary>Browser fallback, if the API ever changes</summary>

`find` the row's **"Leave a comment"** link (results are labelled with the tenant name, so match on
that rather than counting rows), click it, type into the textarea, set the date field, click
**Post**, confirm the "Successfully posted a comment" toast. Only the top 25 deals are on page 1;
page through with `&page=2`.

Three failure modes that cost a lot of time, all of which the API avoids:

- **Success toasts stack over the Stage dropdown.** Chain two saves and the third click lands on a
  toast instead of the control, silently doing nothing.
- **The first click after a `navigate` usually doesn't register.** Budget a throwaway click, or do
  the real click in the *next* `browser_batch` call.
- **Screenshot dimensions shift between calls**, so coordinates go stale. Prefer `find` refs, and
  re-`find` after any navigation.

</details>

## Step 6 — Create new deals

Confirm the list first, then `POST /activity_logs` per deal and read the list back to capture VTS's
normalized tenant names. If a new deal is Dead, create it as `initial_inquiry` first, then post the
stage change with its reason — the create endpoint does not take a dead-deal reason.

Tenant name goes in verbatim as `tenant`, with `custom_tenant_name: null`. This matches what the
UI's **"Cannot find tenant? Add custom tenant"** link does, and it is the point: the Tenant search
box is a fuzzy match over VTS's global company directory that *never reports a miss* — typing a
nonexistent company returns confident, plausible, wrong results (searching "Qwzzx Holdings LLC"
returns IP Holdings, Amerivon Holdings, TMC Holdings), and picking one silently attaches the deal to
an unrelated company in another state. Posting the raw string avoids the directory entirely.

The same trap bites on real companies with near-namesakes — two firms sharing a distinctive word
but operating in different states, one a national retail owner and one an unrelated family
business, are routinely conflated by the directory. When a tenant name could be ambiguous,
confirm the company's website domain with the user before writing anything.

If the deal also has a comment, post it after creating, via Step 5.

## Step 7 — Deliver the finished report

Re-export from VTS (Step 2 again) so the report reflects everything just pushed, then:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/vts/scripts/finalize_report.py" \
  "<fresh export>.xlsx" "<leasing updates folder>"
```

This deletes the Overview sheet and names the file to match the folder's existing convention —
that's the whole of the manual post-processing. The deals sheet is left untouched because its
formatting is already what gets sent.

Naming differs by property, which is why the convention is copied from the newest file present
rather than hardcoded. Shapes seen in the wild:

- `1200 Main St Leasing Update 8.3.26.xlsx` — street address
- `Riverside Commons Leasing Update 12.2.25.xlsx` — property name
- `Leasing Status Report 9.22.25.xlsx` — generic, sometimes dash-separated

Use `--dry-run` first if anything about the naming looks uncertain. If a file with the target name
already exists it's moved aside rather than overwritten.

Finish by reporting what landed: counts of comments posted, stages moved, deals created, and where
the finished report is.

## Writing the deal contact (Broker / Tenant contact)

**This is writable, and it sticks** — verified across 48 deals; the value persists and shows up in
the deals feed the export is built from.

The field is a Rails nested-attributes association called `activity_log_brokers_attributes`. It
doesn't appear in the `/api/horse/deals` list payload under that name (there it's rendered as the
read-only `tenant_contact` object), so read it from the deal's profile header:

```
GET /activity_logs/<dealId>/profile_header      -> .activity_log_brokers_attributes
```

Write it with a PUT on the activity log. Omit `id` and VTS creates the contact record and links it;
include an existing contact's `id` to attach one already in the directory:

```js
await fetch(`/activity_logs/${dealId}`, {method:'PUT', headers:H, credentials:'same-origin',
  body: JSON.stringify({activity_log:{activity_log_brokers_attributes:[{
    first_name:"Jane", last_name:"Doe", email:"jdoe@example.com",
    company_name:"Example Consulting", title:null, phone:null,
    phone_extension:null, type:"broker"}]}})});
// -> 200 {"notice":"Activity log entry was successfully updated.", ...}
```

`type` is `"broker"` even when the person is a principal rather than a broker — that's the only
value the column takes. Verify writes by re-reading the deals feed and checking
`tenant_contact.email`, not by trusting the 200.

**Finding an undocumented field.** `profile_header` is the general trick: it returns the deal's full
editable form state, including every `*_attributes` association the UI can write. When you need a
field the deals list doesn't expose, read `profile_header` on a deal that already has it populated
and copy the shape.

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

## What this skill does not touch

Size and category are read but never written. The loop round-trips, so if either is changed in Excel
it gets overwritten by VTS's value on the next export — tell the user to change those directly in
VTS.

## Reference

**Report layout** — a single sheet of repeating blocks: a stage heading, a column header row,
then data rows. Above the first block sit the property title and `All active deals as of MM/DD/YY`.

| Column label | Content |
|---|---|
| Tenant | `Name\nCategory\n` — the category line is the VTS Industry value |
| Broker | `Name\nFirm` |
| Tenant contact | |
| Inquiry type | |
| Size | |
| Comments | `MM/DD/YY - body`, latest comment only |

**Columns are found by their header label, never by position, and neither should you.** Which
fields appear is a per-user VTS setting ("Deal and proposal details"), so a colleague who doesn't
tick Broker gets a sheet where every later column shifts left. VTS fixes the *labels*, which is
why they're the reliable anchor. `parse_report.py` prints the columns it found and names any that
are absent — check that line if a run looks wrong.

Absent fields come back as empty strings rather than shifted data. Tenant and Comments are
required; the parser stops with an explanation if either is missing, since the first is the join
key and the second is the entire point of the round trip.

Section headings are detected structurally — a single-value row directly above a header row —
rather than matched against a fixed list of stage names, so custom or renamed VTS stages parse
correctly. (An earlier version matched a hardcoded list, which turned the unlisted `Prospects`
heading into a phantom deal named "Prospects" and filed that section's deals under the previous
stage. A push would have created that deal in the landlord's VTS.)

Untouched rows keep their original date prefix, so the prefix doubles as a record of when each
deal was last worked.

**Scripts** (under `${CLAUDE_PLUGIN_ROOT}/skills/vts/scripts/`):

- `parse_report.py <file.xlsx> [--json]` — parse an export or saved report into structured deals
- `plan_changes.py <edited.xlsx> <fresh.xlsx> [--json]` — diff and produce the change plan
- `finalize_report.py <raw.xlsx> <folder> [--date M.D.YY] [--dry-run]` — strip Overview, name, save

**Setup / diagnostics** — `${CLAUDE_PLUGIN_ROOT}/scripts/`:

- `bootstrap.py` — create the venv and install `openpyxl` (idempotent)
- `doctor.py [--json]` — preflight every check; exit code is the number of failures

**Config** — `${CLAUDE_PLUGIN_ROOT}/lib/vts_config.py`:

- `show` — print config (exit 2 = not set up)
- `find-property "<query>"` — resolve a name to an ID
- `add-property "<name>" <id> [--address …] [--folder …]` — record a property
- `list-properties [--all]` — the working list; `--all` includes archived
- `archive "<name|id>"` / `unarchive "<name|id>"` — hide a property that's done

**Archiving is how the user prunes their list.** VTS has no way to hide an asset once it's
leased, so the sidebar only ever grows and live deals get buried among finished ones. Archiving
is local to this toolkit and changes nothing in VTS. When someone says a property is leased,
done, or no longer theirs, offer to archive it — and if they ask for a property that's archived,
`find-property --all` still finds it.
- `set <key> <value> …` — dotted keys, e.g. `user.id 12345`

**Paths** — `${CLAUDE_PLUGIN_ROOT}/lib/vts_paths.py` (works identically on Windows and macOS):

- `roots` — cloud-sync folders that exist on this machine
- `find-folders <root> [--name …] [--match …]` — locate leasing-update folders
- `newest <folder> [--ext .xlsx]` — newest report in a folder, skipping Excel `~$` lock files
- `downloads [--all]` — the freshly-exported `leasing-activity-*.xlsx`

**This can never run unattended.** VTS sessions expire and it needs an authenticated Chrome, so it
doesn't belong in a scheduled task.
