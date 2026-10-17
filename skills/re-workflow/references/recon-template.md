# Recon template (phase 0 for a feature, or a bug that failed three times)

Copy this to `recon/<feature>.md`, fill every section, and get the verdict before writing code. Recon is static
work: no target is launched unless a section says "needs a run".

The rule behind it: no plan may cite a field, offset or function without evidence (a dump line, a disassembly
line or a log line, each with the build). "I believe class C has field F" is a guess; a guess goes in section 7
as a question, never into the design as a fact.

```
# Recon: <feature or failing symptom>

Date / author:
Target + build (version string + sha256 prefix or timestamp):
Repo commit:
```

## 0. Go / no-go

One of:
- **go** — every unknown below is answered with evidence;
- **go with a spike** — one named unknown needs a bounded experiment (listed in section 7);
- **no-go** — the target does not allow it, or the cost is out of proportion; say what to do instead.

Write the verdict first, then the evidence for it. A feature with no verdict is not started.

## 1. What must be true

State the feature as a chain of checkable claims: "the copy of X is created by Y", "Z reads field F at offset O
of class C", "function G runs on the main thread once per frame". Each claim gets a status row in section 6.

## 2. Known behaviour (read these first, cite them)

- The gotchas log: matching symptom or subsystem entries (list the numbers read, or "none match").
- The subsystem's engine map: its call graph, offsets, open questions.
- Existing hooks / address table entries for this subsystem.
- Reflection dumps and a live dump of a similar object.

## 3. Hook point

| Question | Answer | Evidence |
|---|---|---|
| A scripting/extension seam instead of a native hook? | | file:line, or dump line |
| If native: the function, its RVA, how it is resolved (symbol / hash / pattern) | | disasm + the `expect` prologue |
| Calling convention, `this` type, thread (main / worker / render) | | disasm or a logged thread id |
| Detour contract (pass-through on failure, state kept, drain on detach) | | `re-hooking` |
| Pointer-safety: every read is validated, nothing can fault | | `re-hooking` |
| Prologue stable across the supported builds | | the startup self-test line |

## 4. Evidence log

| # | Claim | Kind (dump/disasm/log) | Evidence (verbatim line or path:line) | Build |
|---|---|---|---|---|
| 1 | | | | |

A row with no verbatim evidence is a guess; move it to section 7.

## 5. Design

- Owner and direction of data.
- Any new generated-file / schema changes, and a version bump if a wire format changes.
- Failure modes and what each looks like in the logs (this becomes a gotchas entry if it ever happens).
- Config switch and its default; how to turn the feature off at runtime.

## 6. Verification plan (built with the feature)

- Log lines the feature emits (never capped or stripped), by channel, with the shape of a good and a bad run.
- A self-check tool that parses those lines and returns pass/fail (`re-verification`).
- The calm-baseline / idle check before any measurement.
- Anything that cannot be automated (e.g. a visual check): what a person is asked to look at.

## 7. Open questions and spikes

| Question | Why it matters | Bounded experiment (≤3 attempts) | Result |
|---|---|---|---|

**Spike rule:** the same failed attempt three times (same hypothesis, small variations) ends the spike. Write
what was tried and the log lines here and escalate. Do not try a fourth variation.

## 8. Out of scope

Name the tempting things this feature does not do, so a later reader knows they were considered.
