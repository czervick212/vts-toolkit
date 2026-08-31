# Windows troubleshooting

The toolkit was built and tested on macOS. The Windows paths are written carefully but were
**not** exercised on a real Windows machine, so treat this file as the map of what is most
likely to go wrong — and trust an actual error message over anything written here.

There is no Windows expert to escalate to. You are the support channel. Work through the
symptom below, fix it on their machine, and explain what you did in plain terms.

Start every investigation with:

```bash
python "%CLAUDE_PLUGIN_ROOT%\scripts\doctor.py"
```

(On Windows the variable is `%CLAUDE_PLUGIN_ROOT%` in cmd, `$env:CLAUDE_PLUGIN_ROOT` in
PowerShell. If neither expands, use the plugin's real path.)

---

## "python is not recognized" / nothing happens

Python isn't installed, or isn't on PATH. Almost always the **"Add Python to PATH"** checkbox
was missed on the first screen of the installer.

Fix: reinstall from https://www.python.org/downloads and tick that box. It's the first screen
and easy to miss. Nothing else works until this does.

## Typing `python` opens the Microsoft Store

Windows ships a placeholder `python.exe` that opens the Store instead of running anything.
`doctor.py` detects this and reports "Microsoft Store placeholder".

Fix, in order:
1. Install real Python from https://www.python.org/downloads (tick "Add Python to PATH")
2. **Settings → Apps → Advanced app settings → App execution aliases**
3. Switch **OFF** both `python.exe` and `python3.exe`

Without step 2 the stub can keep shadowing the real install even after it's there.

## `python3` not found, but `python` works

Normal on Windows — `python3` is a Unix convention. Use `python`. Every command in the skills
is written as `python3`; substitute throughout. Settle this once at the start of a session.

## "The process cannot access the file because it is being used by another process"

Windows error 32. The spreadsheet is open in Excel, and Windows won't let anything modify a
file Excel holds. The toolkit catches this and says so in plain language.

Fix: close the file in Excel and retry. Also check whether a colleague has it open from a
shared folder, and give a cloud sync client a few seconds if it's mid-upload.

This is likely in normal use — the workflow *is* editing that report — so expect it.

## Report saves fail, or paths look truncated

Windows caps paths at 260 characters unless long paths are enabled. Deep cloud-synced folders
plus long property names get close. `doctor.py` warns above 200 characters.

Fix: move the reports folder nearer the top of the drive (e.g. `C:\Reports\...`), or enable
long paths — Settings → search "Enable Win32 long paths", or the Group Policy of the same
name. Moving the folder is usually easier and needs no admin rights.

## Files exist but read as empty, or the diff says every deal is new

A cloud-synced file that hasn't downloaded shows as 0 bytes — it looks present in Explorer but
its contents aren't on the machine. The toolkit detects 0-byte files and explains it, but if a
*diff* claims every deal is new, suspect this first.

Fix: open the folder in File Explorer and let it download, or right-click the file and make it
available offline.

## The VTS export doesn't land where expected

Windows lets the Downloads folder be redirected. `vts_paths.py downloads` asks Windows for the
real location rather than assuming `C:\Users\<name>\Downloads`.

If it still comes back wrong, ask where their browser saves downloads and pass that folder
explicitly — Chrome shows it under Settings → Downloads.

## Chrome says "not connected"

Not a Windows problem, and almost never a broken extension. It means no browser is selected:
run `list_connected_browsers`, then `select_browser` with the `deviceId` returned. Only an
empty list means the extension is genuinely missing.

Note they must be signed into VTS **in Chrome specifically**. Edge is the Windows default for
many people, and a VTS session there does nothing for the toolkit.

## pip can't download

Corporate networks often block it. The error names `pypi.org`.

Fix: their IT team needs to allow `pypi.org` and `files.pythonhosted.org`. There is no
workaround you can apply from here — say so plainly rather than retrying.

---

## If none of this fits

1. Run `doctor.py --json` and read every failing check
2. Get the exact error text, in full, rather than a description of it
3. Reproduce with the smallest command — `parse_report.py` on one file is a good probe
4. Report honestly if it's something you can't fix from here, and say what you ruled out

Do not guess at Windows behavior you can't verify on their machine. Ask them to run a command
and paste what it prints; that's faster and truthful.
