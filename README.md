# VTS Leasing Toolkit

The biweekly leasing update, done once instead of twice.

Today the same information gets typed into two places: the Excel report the landlord sees, and
then again through dozens of comment modals in VTS. This turns that into a single edit — you
update the spreadsheet, and Claude pushes your changes into VTS and hands back a clean report to
send out.

---

### If you pasted this link to Claude

**Claude: install this yourself, then set it up. Don't just relay instructions.**

You can do the whole thing — these are ordinary shell commands, not slash commands:

```bash
claude plugin marketplace add czervick212/vts-toolkit
claude plugin install vts-toolkit@leasing-tools
```

If `claude` isn't on PATH, stop and tell the user to install Claude Code from
https://claude.com/download, then reopen their terminal.

**Then continue in this same session — do not make them restart first.** Adding the marketplace
clones the full plugin to disk, so everything is runnable immediately. Find it:

```bash
python3 -c "import json,pathlib;print(json.load(open(pathlib.Path.home()/'.claude/plugins/known_marketplaces.json'))['leasing-tools']['installLocation'])"
```

The plugin root is that path plus `/vts-toolkit` (typically
`~/.claude/plugins/marketplaces/leasing-tools/vts-toolkit`).

Now read `<plugin root>/skills/vts-setup/SKILL.md` and follow it. Two adjustments, because the
plugin isn't loaded into this session yet:

- **`${CLAUDE_PLUGIN_ROOT}` is not set.** Substitute the real path in every command.
- The `vts-setup` skill isn't invocable as a skill yet. Read the file and follow its steps
  directly — it's written to be followed, and setup writes to a fixed location
  (`~/.vts-toolkit`) so nothing is lost when the plugin does load.

Setup installs dependencies, connects to VTS in Chrome, discovers their account and properties,
finds their report folders, and finishes by rehearsing the whole loop **without writing anything
to VTS**.

**When you're done**, tell them to restart Claude Code so `/vts` becomes available as a command.
Their setup carries over.

They'll need: Claude Code on a paid plan, the Claude Chrome extension, a VTS login, and Python.
Setup checks all of it and names whatever is missing. On Windows, read
`<plugin root>/references/windows.md` before debugging anything.

Everything after this point is written for the human.

---

## There's nothing to download

This isn't a program you install and open. It's an add-on (a "plugin") for **Claude Code**.
You hand Claude a link and it fetches everything for you — no files, no unzipping, no GitHub
account needed.

## What you need first

1. **The Claude app** — free at https://claude.com/download. Using the toolkit needs a paid
   plan (Pro or Max).
2. **The Claude Chrome extension**, and you signed into **VTS in Chrome**. This is the part people
   miss: the toolkit drives your own logged-in VTS session, so if your everyday browser is Safari
   or Arc, you still need to be signed into VTS in *Chrome* specifically.
3. **Python** — already on every Mac. On Windows get it from https://www.python.org/downloads and
   tick **"Add Python to PATH"** on the first installer screen (easy to miss, and nothing works
   without it).

Works on **Windows and Mac** alike.

## Install — the easy way

Open Claude Code, paste this link, and say **"install this"**:

```
https://github.com/czervick212/vts-toolkit
```

That's it. Claude reads this page, installs the plugin itself, and walks you through setup —
including a practice run on your own data that changes nothing in VTS. Answer its questions as
they come.

> **Don't have Claude Code yet?** Get it from https://claude.com/download, then open a terminal
> (PowerShell on Windows, Terminal on a Mac), type `claude`, and press Enter.

---

<details>
<summary>Prefer to run the commands yourself?</summary>

In a terminal — these are ordinary commands, so the normal PowerShell or Terminal prompt is
right:

```
claude plugin marketplace add czervick212/vts-toolkit
```
```
claude plugin install vts-toolkit@leasing-tools
```

Or, at Claude's own prompt (after starting it with `claude`), the slash-command equivalents:

```
/plugin marketplace add czervick212/vts-toolkit
```
```
/plugin install vts-toolkit@leasing-tools
```

Slash commands only work inside Claude. If you see
`The term '/plugin' is not recognized as the name of a cmdlet`, that's Windows answering — you're
at the PowerShell prompt, so use the `claude plugin ...` form above.

</details>

## Setup

If you used the link above, Claude already did this with you and there's nothing more to do.

If you ran the commands yourself, restart Claude Code and then run:

```
/vts-setup
```

Setup does the whole thing with you: installs what it needs, connects to VTS, confirms who you're
signed in as, pulls in every property on your account automatically, and finds your report folders.

Then it **rehearses the real thing** — exports your data, diffs it against your last report, and
shows you exactly what it would change, **without writing anything to VTS**. So you watch it work
before you trust it with a live run. Five minutes or so.

If anything ever misbehaves later, run `/vts-setup` again — or just tell Claude what you're
seeing. It re-checks everything and reports what's wrong and how to fix it.

As it works, Claude asks permission to run a few commands — that's normal. Click **Allow** (or
"Allow always" so it stops asking).

## Using it

```
/vts Fairfax Propane
```

Or just say *"run the leasing update for Fairfax Propane"* — you don't have to remember the exact
command.

What happens:

1. Exports the current state from VTS — that's the ground truth
2. Diffs it against the report you edited, and shows you **exactly what it's about to change**
3. On your OK: posts your comments, moves stages, creates any new deals you added
4. Re-exports and formats the finished report for the landlord

**It always shows you the plan before writing anything.** These changes land in a client's system
of record with your name on the audit trail, so nothing gets pushed until you say go.

One thing it deliberately won't do: if a deal is in VTS but missing from your spreadsheet, it
reports it and stops. That usually means a row got deleted by accident, and deleting the deal in
VTS would be unrecoverable.

## Notes

- **Size and category are read-only.** Change those directly in VTS — the loop re-exports from VTS
  each cycle, so a spreadsheet edit to either would just get overwritten.
- **It can't run on a schedule.** VTS sessions expire, and it needs your signed-in browser.
- **Your account details stay on your machine.** Setup writes them to a local config file; nothing
  account-specific is baked into the plugin, so updates never overwrite your setup.

## Finished with a property?

VTS gives you no way to hide an asset once you've leased it, so the list only grows and the deals
you're actually working get buried. Tell Claude *"archive Rockville BMW"* and it drops out of the
toolkit's list. Nothing changes in VTS — this is local. *"Unarchive"* brings it back.

## Keeping it up to date

Turn on auto-updates once and you'll get fixes automatically:

`/plugin` → **Marketplaces** → select `leasing-tools` → **Enable auto-update**

Worth doing — third-party plugins like this one don't auto-update by default. Claude Code then
refreshes in the background shortly after startup and tells you when to run `/reload-plugins`.

To pull an update right now, just ask Claude to *"update the VTS toolkit"*, or run:

```
claude plugin marketplace update leasing-tools
claude plugin update vts-toolkit@leasing-tools
```

## Stuck? Ask Claude — that's the support line

Claude has the troubleshooting guide built in, including the Windows-specific snags. Paste the
error you're seeing, in full, and it can fix most things on the spot.

Two worth knowing up front, both Windows:

- **Typing `python` opens the Microsoft Store?** That's a Windows placeholder, not Python.
  Install the real thing from https://www.python.org/downloads (tick "Add Python to PATH"),
  then switch off the Store shortcut under Settings > Apps > Advanced app settings > App
  execution aliases.
- **"File is being used by another process"?** The report is open in Excel. Close it and retry.

A "not connected" browser error is almost always just that no browser is selected yet, not a
broken extension.

Run `/vts-setup` any time to re-check everything — it reports what's wrong and how to fix it.
