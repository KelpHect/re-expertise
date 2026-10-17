# The address table and its startup self-test

Keep every address a plugin relies on in **one** place: a table of entries, each resolvable and verifiable. The
plugin reads it at startup, resolves each entry, checks its prologue, and decides whether it is safe to run.

## Entry shape

```json
{
  "name": "Dispatch_Tick",
  "resolve": "hash",            // "symbol" | "hash" | "pattern"
  "hash": "0x1234ABCD",         // for hash resolution (a table the host/loader ships)
  "pattern": "53 48 83 EC 20 ...",   // for pattern resolution (fallback)
  "required": false,
  "expect": "53 48 83 EC 20 48 8D 0D ? ? ? ?",
  "note": "called once per frame from the main loop; see engine map"
}
```

- **resolve** — how to find the address this build. Prefer a symbol or a stable hash table; a byte pattern is
  the fallback for when neither exists.
- **required** — a required entry that does not resolve disables the whole plugin (see below). Only optional
  entries may fall back to a pattern.
- **expect** — the function's first bytes, `??`/`?` for operand bytes that vary between builds. Pin only what
  the hook needs; a longer prologue breaks on the first unrelated nearby change.
- **version** — record the build the table was verified against, as a field on the table.

## The self-test, at startup

```
for each entry:
    addr = resolve(entry)                      # by symbol / hash / pattern
    if addr is None:
        if entry.required: disable_plugin("required <name> did not resolve"); return
        else: mark unresolved; continue
    if not prologue_matches(read(addr, len(expect)), entry.expect):   # ? = wildcard
        mark unresolved; log "<name> prologue mismatch; treating as unresolved"
        continue
    mark resolved
if any required entry unresolved: disable_plugin(...)
log "self-test: <r> resolved, <reqfail> required failed, <optfail> optional failed, table hash <...>"
```

Rules this encodes:

- **A required failure disables the plugin.** Half-loading against a build you did not verify is how a process
  gets corrupted. A disabled plugin registers nothing and says why in its log.
- **A prologue mismatch means unresolved**, even if the address resolved — the function changed, so the old
  hook must not install. Leave that one feature off; keep the rest.
- **A version-string mismatch is a warning, not a block**, as long as every required entry still self-tests:
  hosts ship point updates that do not move your functions.

## Matching a prologue with wildcards

The matcher reads `len(expect)` bytes and compares, treating `?`/`??` as "any byte". Two cautions from real
incidents:

- **Size the match buffer to the prologue.** A fixed 64-byte buffer silently rejected any `expect` longer than
  64 bytes, and the self-test read that rejection as a changed prologue — a hook that would never install
  although its bytes were correct. Size by the pattern length (with a sane cap).
- **A prologue that already begins with a jump** (something else detoured this function first) cannot be
  verified. Decide a policy — keep it with a warning, or treat it as unresolved — and log which.

## Keep the table honest

An address enters the table only after it was re-derived with the offline helpers or the analysis server and
written into an engine map with its evidence (`re-workflow`). Never copy an address from someone else's project;
re-derive it against your build, with an `expect` prologue, so your self-test can defend it.
