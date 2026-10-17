---
name: re-ghidra-mcp
description: >-
  Set up Ghidra headless analysis of a binary you own and keep a decompiler/analysis MCP server always-on and
  supervised, for interoperability and modding research. Use when an agent needs to decompile, cross-reference
  or search a large binary through an MCP tool, when importing your own symbol names as labels with prologue
  checks, or when the MCP server keeps dropping (reboots, stale pidfiles, project locks, JVM heap). Includes a
  stdlib-only MCP health probe and Windows/systemd/launchd supervisor templates.
license: MIT
---

# Ghidra headless + an always-on MCP server

Ghidra analyses a binary once (tens of minutes on a large one), then an MCP server exposes decompile /
cross-reference / search / rename to agents. This skill is about running that reliably: a headless import, your
own labels applied with prologue checks, and a supervisor that keeps the server up and actually serving.

`scripts/mcp_probe.py` is the one piece of code here — a stdlib-only health probe. Everything else is recipe,
with service templates in `references/`.

## Headless analysis

1. Install Ghidra (needs a recent JDK — check the Ghidra release's required version). Keep the install, the
   analysis project and any Python venv **out of version control**; they are large and rebuildable. Put them
   on a fast data drive, not the system drive.
2. Import and auto-analyse headless (`analyzeHeadless <projectdir> <projectname> -import <binary>`), or through
   PyGhidra (`pyghidra.open_program(..., analyze=True)` then save). Measured on a large game binary on a
   24-core machine: import ~35 s, analysis ~27 min, 6–10 GB RAM — budget an hour on a small machine.
3. An interrupted headless analysis cannot resume; it restarts from scratch. Let it finish.
4. Name the project after the binary's build/version. After the target updates, re-import into a new project
   and diff (see `re-runtime-introspection`).

## Apply your own labels, with a prologue check

The binary names almost nothing. Keep your findings in a small, committed table — one row per function:
address, your name, and the function's first bytes (the `expect` prologue). On every labelling pass, compare
each function's current bytes against the stored prologue:

- match → apply the label (and a plate comment with your note);
- mismatch → **do not** apply it, log `PROLOGUE MISMATCH` — the function moved or changed, so the label would
  lie. This is the same check `re-hooking`'s startup self-test runs.

Support `?` wildcard bytes in a prologue (a relative displacement varies between builds); treat `?`/`??` as
"any byte" when matching, and size the read by the prologue length. Re-label is cheap (seconds); re-analysis is
not. See `references/labels.md`.

## The MCP server, always-on and supervised

A server started by hand dies at the next reboot and nothing restarts it. Sessions then open with the MCP
endpoint refused. Supervise it. The supervisor must:

- **Probe with a real MCP exchange, not a port check.** A process can hold the port while serving nothing.
  `scripts/mcp_probe.py` does the full handshake (`initialize` → `notifications/initialized` → `tools/call
  list_project_binaries`), checks the expected binary is listed, then deletes the session. Exit 0 = healthy.
- **Restart with backoff** (e.g. 2, 4, 8 … capped), reset after a spell of health. Count a few consecutive
  failed probes, or no healthy probe within a startup grace, as "restart".
- **Serve a copy of the analysis project, never the source.** Ghidra locks an open project, so serving the
  source blocks re-analysis and other tools. Refresh the copy when the source changed and its lock is free.
  Any renames/comments made through the server land in the copy and are lost on refresh — so commit findings to
  the labels table (above), which is the durable truth.
- **Bind to 127.0.0.1 only.** These servers can run scripts; do not expose them.
- **Adopt, don't kill, a foreign port owner.** If something you did not start owns the port, log it and leave
  it; only restart servers you own (track pid + start time).

### The traps that actually bite (write them in your runbook)

- **JVM heap.** PyGhidra ignores Ghidra's `MAXMEM`; its launcher reads only the `VMARGS` lines of
  `support/launch.properties`. Without a cap the JVM grabs a quarter of RAM. Set the cap via the environment
  the launcher honours — `JAVA_TOOL_OPTIONS=-Xmx<N>g -XX:+ExitOnOutOfMemoryError` — so an out-of-memory server
  exits and is restarted instead of lingering and answering nothing. You will see `Picked up JAVA_TOOL_OPTIONS`
  in its log.
- **Read-only vs restore flag.** Opening a project "read-write to restore" holds the lock other tools need.
  Open the served copy read-only.
- **Stale pidfile after a reboot.** A reused pid reads as "already running" and a naive starter refuses to
  start. Check the pid's **identity** (process name + start time against the pidfile's mtime), not just that a
  pid is alive.
- **Reboots kill it.** The supervisor must start at logon/boot, not only on demand.
- **Don't call whole-table "xref by name" tools.** On a large program they can hang for tens of seconds and
  wedge the whole session (see `re-rea`). Query by address.

## Supervisor templates (cross-platform)

Pick one; each runs the same probe-restart loop. See the files:

- `references/windows-scheduled-task.md` — a per-user Scheduled Task (logon + every few minutes), no admin.
- `references/systemd-user-unit.md` — a `--user` service with a watchdog timer.
- `references/launchd-agent.md` — a LaunchAgent with `KeepAlive`.

## Querying from a shell

If an agent's host has no live MCP connection, query the server over HTTP from a script. The probe module shows
the exchange; a fuller client adds `decompile`, `disassemble`, `search_symbols`, `list_xrefs`, `rename`, etc.,
by name/address. Until the server has finished indexing (it reports `code_indexed` / `strings_indexed`), code
and string search answer "not indexed" — use the `re-tooling` offline helpers meanwhile.

## Health check

`python -I scripts/mcp_probe.py --url http://127.0.0.1:8765/mcp --expect <binary name>` → `OK healthy ...`
(exit 0) or `FAIL <reason>` (exit 3). Wire the same call into the supervisor and into your "is my environment
ready" check.
