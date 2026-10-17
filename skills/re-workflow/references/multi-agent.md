# Multi-agent and parallel RE work

Reverse-engineering parallelises well across independent subsystems and badly across shared state. The patterns
below keep several people or agents productive without corrupting each other's work or measurements.

## Lanes

Split the work into lanes, one per subsystem or per independent fix. Lanes that do not share files run in
parallel; lanes that share a file chain behind each other. Each lane:

1. reads the subsystem's engine map and the gotchas log,
2. derives its evidence with the tooling skills,
3. implements with its own verification tooling,
4. gets a review, then a fix pass if the review lists anything.

## The integrator owns shared generated files

Some files are generated or are edited by everyone: the address table, generated headers/bindings, a shared
schema. If two lanes edit them in parallel, the merge is a mess and numbers collide. Rule: **one integrator**
merges lanes and owns those files. Lanes propose changes to them in their own notes; the integrator applies and
renumbers (gotchas numbers, address-table rows) at merge time. See the numbering rule in
`gotchas-format.md`.

## The skeptic

A finding that a new hook or offset depends on is re-derived independently before it is trusted — ideally by a
different person/agent (or a different analysis tool), so one tool's mistake does not propagate. Cap the
skeptic's rounds (e.g. re-investigate once if it refutes); endless back-and-forth is its own failure mode. A
different model or a different tool is valued for catching different mistakes, not for being authoritative.

## Worktrees that start at an old commit

A fresh worktree created for a lane may be checked out at an old commit of another branch. Before building or
trusting any repo file (including this kind of guidance), run `git log -1` and reset to the intended branch.
Measurements and "the file says X" conclusions taken on the wrong commit are worthless.

## The lock on a single shared resource

When the work needs the one target process, the one analysis project, or a fixed port, only one lane may use it
at a time. A second lane driving the same process corrupts both measurements, and a project opened twice hits a
lock anyway. Pattern:

- Builds and offline analysis need no lock — do them first, outside the lock.
- Take the lock right before the step that uses the shared resource (install / launch / drive / analyze).
- Hold it for the whole session (install → run → measure → close), then release it.
- A lock record names the owner, the purpose, the holder's pid with its start time, and when it was last used,
  so a stale lock (holder gone, nothing running, past a grace period) can be taken over safely — a reused pid
  with a different start time counts as gone.
- Never break another owner's live lock except by an explicit force by a human.

## Never discard a lane's output

If a lane's build crashes or its feature misbehaves, fix it forward — find the cause and repair it, keeping the
feature and the investigation. Reverting a lane throws away the evidence it gathered, which is the expensive
part. Add a test that catches the failure class so it does not return.
