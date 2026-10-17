# Engine-map template (one per subsystem)

An engine map describes what a part of the target does, through which classes, functions and data, on which
threads, what state is owned where, and where you can observe or attach. Every claim cites a disassembly
address, a dump line, a script/resource line, or one of your own log lines; anything else is an open question.

Write a subsystem's map before implementing a feature that touches it. Status (what is done) lives elsewhere
(a TODO list, a checklist); the map describes the target, not your progress.

Copy this to `engine/<subsystem>.md`.

```
# <Subsystem>

Target + build (version string + sha256 prefix / timestamp):
Evidence basis (static only? which runs? which dumps?):
```

## Summary

Two or three sentences: what the subsystem is and the one or two facts that matter most for your work.

## Classes and data

| Item | Value | Evidence |
|---|---|---|
| <class / field / global> | <offset / type / address> | <dump line, or disasm line> |

Note which fields live at `object + offset` and which live in an indirection (a value holder, a side table):
reading the wrong one is a classic silent bug.

## Functions and call graph

| RVA | Name (yours) | What it does | Evidence |
|---|---|---|---|
| | | | disasm / decompile line |

Give the call graph for the path you care about: who calls what, and where your observation or attach point
sits in it.

### Threads

Which function runs on which thread (main / job worker / render / UI), and how you know (a logged thread id, or
the disassembly of the dispatcher). Attaching on the wrong thread is a crash or a race.

## State ownership

For each piece of state: is it per-instance, global/world, or UI-local? Which side owns it? This decides what
interop/modding must replicate, replay, suppress, or leave alone.

## What interop / modding needs

For each behaviour: replicate (copy the state), replay (re-run the owner's stream), suppress (stop a local
duplicate), or per-side (each side keeps its own). Tie each to a task id if you track them.

## Hook and call points

| Point | Kind (script seam / native detour / observe-only) | Risk | Evidence |
|---|---|---|---|

An address enters your address table only after it is re-derived here with an `expect` prologue (`re-hooking`).

## Open questions

Numbered. Each is the next thing to measure before the code that depends on it is written. An open question is
not a TODO; it is a hole in the evidence.
