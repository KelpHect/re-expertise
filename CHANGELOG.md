# Changelog

All notable changes to this repository are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project aims to follow semantic versioning.

## [0.1.0] - 2026-10-17

Initial release: seven universal reverse-engineering skills for interoperability and modding of software you
own.

### Added
- **re-workflow** — the evidence-first method: citation rules, recon and engine-map templates, the gotchas-log
  format with the parallel-branch numbering rule, the three-attempt cap, multi-agent lanes, and a legal/ethics
  note.
- **re-tooling** — dependency-light offline PE (x64) helpers (`pecore.py` + `petool.py`): fingerprint,
  disassemble, function bounds, callers, callees, references, strings, imports. Every output starts with the
  binary's fingerprint. Needs only capstone and pefile; notes where ELF/Mach-O differ.
- **re-ghidra-mcp** — headless analysis, label application with prologue checks, and an always-on supervised
  MCP server with a stdlib-only health probe (`mcp_probe.py`) and Windows / systemd / launchd supervisor
  templates.
- **re-rea** — using the `rea` Ghidra-backed agent CLI/MCP and reusing an analysed project copy instead of
  re-importing on every call.
- **re-hooking** — version-robust address resolution, a startup self-test that refuses to hook on a prologue
  mismatch, pointer validation, thread/stage correctness, and the detour contract. Core rule: plugin code must
  never fault inside the host process (validate, don't catch).
- **re-runtime-introspection** — reflection/RTTI dumps, cross-build snapshot diffing to catch moved offsets,
  and safe live-object readers.
- **re-verification** — diagnostic logs plus an automated self-check, owner-vs-observer lines in the same
  terms, and measuring on a calm baseline.
- Repository tooling: `tools/validate.py` (layout + frontmatter + link checks), unit tests over a hand-built PE
  fixture (`tests/make_pe.py`), and a CI workflow.
