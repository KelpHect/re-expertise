---
name: re-rea
description: >-
  Use rea, a Ghidra-backed reverse-engineering agent CLI/MCP, against a binary you own for interoperability and
  modding research, and make it reuse an already-analysed Ghidra project instead of re-importing on every call.
  Use when you want a single "evidence" answer that holds a whole function picture (assembly, callers, callees,
  references, basic blocks, decompiler output, value-flow) or bounded def-use tracing, and when you need to cut
  rea's per-call cost from re-analysing the binary every time (~1278 s) to seconds on a reused project copy.
license: MIT
---

# rea: Ghidra-backed evidence on a reused project

[rea](https://github.com/morluto/rea) (npm package `rea-agents`) wraps Ghidra in a CLI and a stdio MCP server
whose answers are structured JSON "evidence": a function dossier with assembly, callers/callees, references,
basic blocks, decompiler output, and p-code value-flow. It is the tool to reach for when one answer should
carry the whole picture of a function, or for bounded def-use tracing — not for a quick instruction read (use
`re-tooling`) or for renaming in a shared project (use `re-ghidra-mcp`).

Pin a known version (the project this was distilled from pinned `6.4.0`). Install with your package manager and
point npm's cache at a data drive, not the system drive.

## The problem it has, and the fix

Out of the box, rea **imports and auto-analyses the target on every CLI call or MCP session**. On a large game
binary that was measured at about **1278 s and ~2 GB of RAM for a single `function` query**, and every function
comes back as an anonymous `FUN_...` because nothing is labelled. That is unusable for iterative work.

The fix is to make rea **open a copy of a project you already analysed** (see `re-ghidra-mcp`) instead of
importing:

- Patch rea's Ghidra launcher so that, **only when an environment variable points at your prepared project**,
  it runs headless with `-process <program> -noanalysis -readOnly` and **drops** `-deleteProject`. Otherwise it
  behaves exactly as upstream.
- Apply the patch by **exact-string replacement** against the known upstream launcher text, and **refuse** if
  the upstream text is not found (so a rea upgrade cannot be silently mis-patched). Keep a `.orig` copy and
  re-patch from it, so a re-run repairs a bad patch.
- Work on a **copy** of the project, because Ghidra locks an open project: one rea process per copy, and take a
  copy only while the source project is closed. A parallel agent gets its own numbered copy.
- Re-apply your committed labels to the copy (a "labels only" pass, `re-ghidra-mcp`), so answers carry your
  names and notes instead of `FUN_...`.

## Performance, reused project (what to expect; your binary will differ)

These are the figures measured on one large binary on a 24-core machine, with the project reused. Quote each
command's own figure — the 14–26 s is for `function` only, not a blanket number:

| operation | CLI (one call: JVM start + project open) | MCP (same session) |
|---|---|---|
| `function` (full dossier) | 14–26 s | ~1.3 s |
| `decompile` | 12–14 s | ~1.8 s |
| `xrefs` | ~13 s | ~0.2 s |
| `trace-native-values --max-depth 2` | ~39 s | not measured |
| `search <text>` | 14–17 s | not measured |
| opening the project (first query of a session) | — | ~10 s |

Each rea process costs about 1 GB of RAM and a project copy (several GB). So: for a single answer, the CLI is
fine; for many answers, run **one MCP session** and query inside it (sub-second after the ~10 s open).

## Which tool for which question

- Instructions, direct callers, string refs: the `re-tooling` offline helpers (sub-second, no JVM).
- Decompile / rename in the shared, supervised project: the `re-ghidra-mcp` server.
- One answer holding the whole function picture, or bounded value-flow tracing: rea, preferably through one
  long-lived MCP session.

## A session hazard to avoid

In a rea MCP session, **do not call whole-table name listings** such as `find_xrefs_to_name` (which lists every
name). On a large program that listing can fail after 30–40 s and then every later query in the session fails
too. Recover by closing and reopening the binary. Query **by address** instead — procedure callers/references
by address are the fast, reliable path.

## Do not invent subcommands

Use only the commands rea actually ships (`function`, `decompile`, `xrefs`, `instructions`,
`trace-native-values`, `search`, the MCP equivalents). Check `--help` for your pinned version rather than
guessing a command exists.
