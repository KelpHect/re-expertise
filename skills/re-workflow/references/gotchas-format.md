# The gotchas log: format and discipline

A gotchas log is a living file of real incidents, read before guessing at a symptom and appended to with every
fix. Its value is that the same wall is hit once, not every few weeks by a different person (or a different
agent).

## Entry format

```
### G<n>. <symptom as a person would actually say it>
- Cause: <the proven mechanism; or "not proven" and say so>
- Fix: <what was changed; or "none confirmed">
- Proof: <the exact line(s) that distinguish a good run from a bad one>
- Status: <FIXED | OPEN | UNVERIFIED>   (<binary build>)
```

The symptom is the heading because that is what the next person searches for ("head gear is broken", "the game
freezes while loading", "both processes close at startup"). They will not search for the cause; they do not
know it yet.

## Proof-line marks

- `[exact]` — quoted verbatim from a real run's log or a tool's output. Trustworthy.
- `[shape]` — the format string exists in the code (name the file) but no real line has been captured yet. Grep
  a real log for the literal before relying on the wording.

An UNVERIFIED entry (cause or proof not measured) and an OPEN entry (no confirmed fix) are not solved. Do not
cite them as settled facts.

## Discipline

- Every fix adds an entry. A fix with no gotchas entry is unfinished.
- Record the mechanism, not a story. If you did not prove the cause, write "not proven" — a wrong cause in the
  log is worse than none.
- A heading elsewhere that says "solved" is not proof; cite the line.
- Keep diagnostic log lines that a feature emits step by step; do not delete or throttle them as "noise". They
  are how the next bug in that area gets found. (See `re-verification`.)

## Numbering across parallel branches

When several branches each add entries at the same time, their numbers collide. The rule: a branch numbers its
new entries from the next free number **on the mainline at merge time**, not at branch start. Whoever merges a
branch into the mainline renumbers any clashing entries and the references the branch added to them. Decide one
owner for the renumber (the integrator) so two branches do not both claim G200.

## What makes a good entry (generic examples)

- *"An install reverted a working feature."* Cause: a packaging step ran without a fresh build and shipped an
  older artifact. Fix: build first; diff the installed files against the repo before blaming code. Proof: the
  diff.
- *"Both processes close while loading."* Cause: a registration contract broke (a missing type, a re-declared
  field). Fix: a test that fails on that class of error. Proof: that test; the loader's refusal line.
- *"A measurement showed fine, the result was wrong."* Cause: the measurement checked an intermediate value
  while a later step still overrode it. Fix: measure the final observable, not the intermediate. Proof: the two
  differing lines.
