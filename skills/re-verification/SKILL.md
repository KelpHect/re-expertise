---
name: re-verification
description: >-
  Make every reverse-engineered feature prove itself with diagnostic logs plus an automated self-check, in
  software you own, for interoperability and modding. Use when building or reviewing a feature: deciding what to
  log, writing ground-truth vs mirror lines in the same terms so owner and observer compare directly, ensuring
  measurements run on a calm baseline, and writing a parser that returns pass/fail. Also: why per-step
  diagnostic logs must never be stripped.
license: MIT
---

# Verification: logs plus a self-check, every feature

A reverse-engineered feature is not done when it compiles or when a bone/field log "looks right". It is done
when a tool can show it working — ideally without a human. Build the verification **with** the feature, not
after; design the log lines and the self-check in the recon doc (`re-workflow`, section 6).

## Every feature ships two things

1. **Diagnostic log lines** that explain *why*, step by step: what the code decided, with what values, when,
   on which channel. Enough that a failure localizes itself from the log alone.
2. **A self-check tool** that parses those lines (or a live dump) and returns pass/fail, so the feature can be
   re-checked on demand and in CI-like runs, not by eyeballing.

## Ground-truth vs mirror lines, in the same terms

The strongest automated check for anything replicated or made to interoperate: have the **owner** emit a
ground-truth line, and the **observer** emit a mirror line **in the same terms** (same fields, same units, same
format). Then the two logs diff directly, field by field, and the tool just compares them.

```
owner:    truth  id=42 pos=(12.0, 3.5, 0.0) state=running t=10.250
observer: mirror id=42 pos=(12.0, 3.5, 0.0) state=running t=10.266
```

If the owner logs position as a vector and the observer logs it as three scalars with different rounding, the
tool cannot compare them and you are back to eyeballing. Make the formats identical on purpose; pin them with a
contract test that ties the code's format strings to the patterns the tool parses, so a change to one fails
until the other matches.

## Measure on a calm baseline (the idle check)

A measurement on a shifted baseline proves nothing. Before driving the target to measure anything, confirm it
is idle and configured as the test expects: nothing else running, options/config at the expected values, past
loading, a calm snapshot. A number taken while the target was still settling, or while a previous scenario was
still running, or with a different config, is noise that looks like a result. Record the build and config with
every measurement.

## Never strip per-step diagnostic logs

The per-poll / per-part lines ("part N added", "chunk moved", "bound to id X") are **deliberate step-by-step
verification**, not spam. Do not delete, cap, or rate-limit them in a cleanup or an audit — they are how a
feature built piece by piece is confirmed piece by piece, and how the next bug in that area is found. If a line
looks noisy, **add** information to it rather than removing it. The one thing worth rate-limiting is input
driven by an untrusted peer (e.g. unknown message ids) — and say so explicitly when you do.

## What a self-check looks like

- Parse the logs (or run a live reader, `re-runtime-introspection`) after a scripted scenario.
- Pair owner and observer records by id; report gaps, jumps, missing copies, wrong values, timing lag.
- Exit non-zero on failure with the offending lines quoted, so it drops into a scenario runner or CI.
- Keep a scenario that drives the feature end to end and asserts the good-run shape.

## What still needs a human

Some qualities cannot be read from a log: visual correctness, motion smoothness, "does this look right". For
those, let numeric diagnostics **localize** the cause first (a field check, a position error, a parity count),
so the human is asked a precise question about a specific thing — not "is everything okay". Keep the
human-judgement step explicit in the recon doc so it is not mistaken for something the tool already covered.

## Before calling a change ready

Type-check / compile, run the relevant tests and the feature's self-check on a calm baseline, and for generated
artifacts rebuild and verify them. A build pass is not a feature pass; the self-check is.
