# Committing your labels, with prologue checks

The analysis project's own renames are not durable: a supervised MCP server serves a refreshed **copy**, so
renames made through it are lost on the next refresh. Keep the durable truth in a small, committed table and
re-apply it on every labelling pass.

## The labels table

One row per function you have named. A tab-separated file is enough:

```
# address  name          note / evidence                            expect (first bytes, hex; ? = wildcard)
0x1000     Config_Load   references the "config.json" string         53 48 83 EC 20 48 8D 0D ? ? ? ?
0x1040     Value_Read    reads the settings dword; called from load  8B 05 ? ? ? ? C3
0x1060     Tick_Dispatch tail-calls the value reader each frame      31 C0 E9 ? ? ? ?
```

(Addresses and bytes above are from the test fixture in this repo, not from any real product.)

- **address** — an RVA (preferred) or VA.
- **name** — your symbol; keep a prefix (e.g. `RE_`) so your labels are distinguishable from the binary's own.
- **note** — the evidence, so the row is self-justifying.
- **expect** — the function's first N bytes. `?`/`??` mean "any byte" for a displacement that varies between
  builds (a rip-relative operand, a relocation).

## The labelling pass

On import, and again any time you add rows, iterate the table:

1. Read the function's current first bytes at its address.
2. Compare against `expect`, treating `?` as a wildcard and sizing the read by the prologue length.
3. On a match, create the label and a plate comment carrying your note.
4. On a mismatch, **skip the label** and log `PROLOGUE MISMATCH <name> at <addr>` — the function moved or
   changed; applying the name would mislead every later reader. This is the same safety check the runtime
   self-test runs before it allows a hook (`re-hooking`).

Re-labelling is seconds; a full re-analysis is tens of minutes. Keep a "labels only" mode that skips analysis.

## Pitfall: wildcard bytes in the prologue

If you store `?` wildcards in `expect`, the code that *reads* the table must not try to parse `?` as a hex
byte. One real incident: a labelling pass aborted with `invalid literal for int() with base 16: '?'` because
the parser assumed every token was hex, and no labels were saved after the project's last good save. Keep two
notions separate: "bytes to write" (exact, no wildcards) and "bytes to match" (wildcards allowed).

## Why a prefix and a note per row

A name with no evidence is a guess that looks like a fact to the next reader. The note (a string xref, a call
site, a dump line) lets anyone re-derive it, and lets the skeptic (`re-workflow`) check it independently.
