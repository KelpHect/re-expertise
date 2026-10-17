---
name: re-workflow
description: >-
  Evidence-first reverse-engineering method for native binaries you own (games, engines, desktop apps) for
  interoperability and modding. Use when planning or auditing RE work: deciding whether a feature is feasible
  before writing code, citing offsets/fields/functions only with proof, capping failed attempts, keeping a
  gotchas log, writing recon and engine-map notes, and splitting RE work across parallel agents. Applies to
  PE first, with notes for ELF and Mach-O.
license: MIT
---

# Reverse-engineering workflow: evidence first

The whole method is one rule: **never state a fact about a binary you have not proven from the binary.** A
field, an offset, a function address, a calling convention, a thread — each is a claim, and a claim needs a
cited line of evidence plus the exact build it came from. Everything below serves that rule.

This skill is the method. The mechanics live in sibling skills: `re-tooling` (offline disassembly helpers),
`re-ghidra-mcp` (headless analysis + an always-on query server), `re-rea` (a Ghidra-backed agent CLI),
`re-hooking` (address resolution and safe function hooks), `re-runtime-introspection` (reflection and live
dumps), `re-verification` (logs and self-check tools).

## The evidence rules

1. **Cite or it did not happen.** Any offset, field or function in a plan, a code comment or a doc carries the
   line that proves it: a disassembly line, a reflection/RTTI dump line, or a runtime log line — and the build
   it came from (version string + a hash or timestamp of the binary). See `references/evidence.md`.
2. **An uncited claim is written as a question, never as a fact.** "I believe class C has field F at 0x40" is a
   guess; put it in the recon doc's open-questions table, not in the design.
3. **Offsets are per build.** A dump or disassembly line is the citation; memory and "it was 0x40 last patch"
   are not. Re-derive after every update of the target (see `re-runtime-introspection` snapshot diffing).
4. **Tools beat reasoning.** Before explaining a symptom, read the gotchas log and the dumps. A plausible
   story that contradicts a dump line is wrong.
5. **Cap identical failed attempts at about three.** Same hypothesis with small variations, three times, then
   stop: write a recon doc with what was tried and the exact log lines, and escalate. Do not try a fourth
   variation. See `references/recon-template.md` (the spike rule).

## Two documents every RE effort keeps

- **The recon doc** — phase 0 for a feature, or for a bug that has failed three times. A go / no-go verdict, the
  chain of claims each with a status, the hook point with its evidence, an evidence log, and the open questions
  with bounded experiments. Copy `references/recon-template.md` and fill every section before writing code.
- **The engine map** — one per subsystem you touch: classes and data, functions and call graph (addresses,
  threads), state ownership, what interop/modding needs, hook and call points with risks, and open questions.
  Every line cites evidence; anything else is an open question. Copy `references/engine-map-template.md`. Read a
  subsystem's map before touching it; if none exists, write it first.

## The gotchas log

A living file of real incidents, so the same wall is hit once. One entry per fix:

```
### G<n>. <symptom, as a person would say it>
- Cause: <proven mechanism, or "not proven" — say which>
- Fix: <what was changed, or "none confirmed">
- Proof: <the exact log/disassembly line that shows good vs bad>
- Status: <FIXED | OPEN | UNVERIFIED>  (binary version)
```

Rules: every fix adds an entry; mark proof lines `[exact]` (quoted from a real run) or `[shape]` (the format
string exists but no real line is captured yet). A heading that says "solved" is not proof; cite the line. When
numbering clashes across parallel branches, the integrator renumbers at merge time from the next free number on
the mainline. Format and worked phrasing: `references/gotchas-format.md`.

## Multi-agent RE work

RE parallelises badly on shared state and well on independent subsystems. See `references/multi-agent.md`:
- One **integrator** owns shared generated files (address tables, generated headers); lanes never edit them in
  parallel.
- A **skeptic** reviewer re-derives the key addresses independently before a finding is trusted; cap its rounds.
- **Worktrees** for parallel lanes may start at an old commit — check `git log -1` and reset to the intended
  branch before building or trusting repo files.
- A **single shared resource** (one target process, one analysis project, one port) needs a lock: one lane at a
  time installs, launches or drives it. Build steps need no lock; take it right before the step that uses the
  resource and release it after.
- Never discard a lane's investigation because its build failed: fix forward, keep the finding.

## Legal and ethics

This method is for reverse-engineering software **you own**, to make it interoperate with your own tools or to
mod it, within the software's terms of use. Keep it lawful and factual:
- Work on your own installs and copies you are licensed to run.
- Do not reproduce or redistribute the target's code, assets or proprietary data; record your own findings
  (addresses, offsets, behaviour) in your own words.
- Nothing here is for defeating copy protection or license enforcement, for anti-cheat or anti-tamper evasion,
  or for touching processes or systems you do not own. Those are out of scope on purpose.
- Interoperability and modding have specific legal treatment in many jurisdictions; when in doubt, check your
  local law and the product's terms.

## A session, start to finish

1. Pick the subsystem. Read its engine map (write one if missing) and the gotchas log.
2. Open a recon doc. State the claims. Derive each with the tooling skills, citing lines.
3. Write the go / no-go verdict. If "go with a spike", run the bounded experiment (≤3 attempts).
4. Design against the evidence; design the verification (logs + a self-check tool) at the same time
   (`re-verification`).
5. Implement. For a hook, follow `re-hooking` (validate pointers, resolve addresses with version checks, the
   detour contract).
6. Verify with the self-check tool on a calm baseline. Record the result, update the map and the gotchas log.
