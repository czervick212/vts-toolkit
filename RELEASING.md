# Releasing an update

Users only receive an update when the `version` field in
`vts-toolkit/.claude-plugin/plugin.json` changes. Push all the commits you like — if the version
is unchanged, nothing reaches anyone.

So, every time:

1. Make the change.
2. **Bump `version`** in `vts-toolkit/.claude-plugin/plugin.json`.
3. Commit and push to `master`.

Optionally tag the release (this validates that plugin.json and the marketplace entry agree):

```bash
claude plugin tag ./vts-toolkit
```

## How it reaches users

Claude Code refreshes marketplaces and updates installed plugins in the background shortly after
a session starts, then prompts to run `/reload-plugins`.

**But auto-update is OFF by default for third-party marketplaces like this one.** Each user turns
it on once:

`/plugin` → **Marketplaces** → select `leasing-tools` → **Enable auto-update**

After that they get updates without doing anything.

Anyone who hasn't enabled it can pull an update on demand:

```bash
claude plugin marketplace update leasing-tools
claude plugin update vts-toolkit@leasing-tools
```

The plugin name must carry its marketplace (`vts-toolkit@leasing-tools`). The bare name
reports `Plugin "vts-toolkit" not found`.

Then restart Claude Code, or run `/reload-plugins`.

Simplest thing to tell a user: *"ask Claude to update the VTS toolkit."* It can run both commands.

## Version history

| Version | Change |
|---|---|
| 0.3.0 | Archive properties you've finished leasing, so they stop cluttering the list |
| 0.2.1 | Property identity keyed on VTS id, not name — two assets can share a name |
| 0.2.0 | Columns located by header label instead of fixed position; section headings detected structurally (fixes a phantom deal and misfiled stages) |
| 0.1.0 | Initial release |
