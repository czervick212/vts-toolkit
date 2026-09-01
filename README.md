# VTS Leasing Toolkit

The biweekly leasing update, done once instead of twice.

Today the same information gets typed into two places: the Excel report the landlord sees, and
then again through dozens of comment modals in VTS. This turns that into a single edit — you
update the spreadsheet, and Claude pushes your changes into VTS and hands back a clean report to
send out.

---

### If you pasted this link to Claude

Claude: the person reading this wants the VTS Leasing Toolkit working on their machine. Do this:

1. Have them install the plugin. **You cannot do this for them** — it must be typed by the user.
   The terminal form is the least error-prone, especially on Windows:
   ```
   claude plugin marketplace add czervick212/vts-toolkit
   ```
   ```
   claude plugin install vts-toolkit@leasing-tools
   ```
   The slash-command equivalents (`/plugin marketplace add …`) also work, but only at Claude's
   own prompt. `'/plugin' is not recognized as the name of a cmdlet` means they typed it at the
   Windows prompt — point them at the terminal form above.
2. Once installed, run the `vts-setup` skill yourself and walk them through it. It installs
   dependencies, connects to VTS in Chrome, discovers their account and properties, finds their
   report folders, and finishes by rehearsing the whole loop **without writing anything to VTS**.
3. They need: Claude Code on a paid plan, the Claude Chrome extension, a VTS login, and Python.
   Setup checks all of it and names whatever is missing.
4. On Windows, read `references/windows.md` in the plugin before debugging anything.

Everything after this point is written for the human.

---

## There's nothing to download

This isn't a program you install and open. It's an add-on (a "plugin") for **Claude Code**.
You paste two short commands into Claude and it fetches everything for you — no files, no
unzipping, no GitHub account needed.

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

## Install

There are two ways. Either is fine — pick whichever prompt you're looking at.

### Option A — from a terminal (simplest on Windows)

Open **PowerShell** (or Terminal on a Mac) and run these two lines. These *are* ordinary
commands, so they work at the normal Windows prompt:

```
claude plugin marketplace add czervick212/vts-toolkit
```
```
claude plugin install vts-toolkit@leasing-tools
```

> If `claude` isn't recognized, Claude Code isn't installed yet — get it from
> https://claude.com/download, then **close and reopen** the terminal window. A newly installed
> command isn't visible to a window that was already open.

### Option B — from inside Claude

Start Claude Code (type `claude` in a terminal and wait for its prompt), then type these into
**the same box you'd type a question into**:

```
/plugin marketplace add czervick212/vts-toolkit
```
```
/plugin install vts-toolkit@leasing-tools
```

> Slash commands only work at Claude's own prompt. If you see
> `The term '/plugin' is not recognized as the name of a cmdlet`, that's Windows answering —
> you're at the PowerShell prompt, so use Option A instead.

Then set it up once:

```
/vts-setup
```

Setup does the whole thing with you: installs what it needs, connects to VTS, confirms who you're
signed in as, pulls in every property on your account automatically, and finds your report folders.

Then it **rehearses the real thing** — exports your data, diffs it against your last report, and
shows you exactly what it would change, **without writing anything to VTS**. So you watch it work
before you trust it with a live run. Five minutes or so.

If anything ever misbehaves later, run `/vts-setup` again — it re-checks everything and tells you
what's wrong and how to fix it.

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
