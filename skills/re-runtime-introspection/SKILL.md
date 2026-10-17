---
name: re-runtime-introspection
description: >-
  Capture and use a target's own type/reflection metadata and live object state to replace guessed offsets with
  cited facts, in software you own, for interoperability and modding. Use when the engine has reflection/RTTI
  you can dump (classes, fields with offsets and types, functions, enums), when you want to diff those dumps
  between two builds to catch moved offsets after an update, or when a live object reader is safer and clearer
  than static analysis. Pairs with re-tooling (static) and re-hooking (safe reads).
license: MIT
---

# Runtime introspection: reflection dumps, snapshot diffing, live readers

If the target keeps its own type metadata (an RTTI/reflection system — many engines and managed runtimes do),
that metadata is the strongest evidence you can get about layout: the engine itself tells you a class's parent,
its fields with offsets and types, its functions and enums. Prefer it to guessing offsets from disassembly, and
use it to detect when an update moved something.

## Dump the metadata to greppable lines

Write the reflection data out as line-per-record text (JSONL is convenient) so a plan can cite a line:

- **classes** — name, parent, size, field count, flags.
- **fields / properties** — class, name, offset, type, and **where the value lives**: at `object + offset`, or
  in an indirection (a value holder / side table). This distinction is a frequent silent bug; record it.
- **functions** — class, name, signature (return + parameters with in/out/optional), flags (static, native,
  event).
- **enums / bitfields** — members and values.

Each dump carries a manifest: the build (version string + binary hash), counts, and any classes that could not
be read (record the failures; do not silently drop them). A dump with unexplained warnings is not trustworthy
yet — fix the dumper before citing it.

Two things that will mislead you if forgotten:

- **"value holder" fields** are not at `object + offset`; they are in a separate indirection. Reading
  `object + offset` for one gives a garbage value that looks plausible.
- **Two property lists.** Some runtimes expose a class's fields through more than one internal list (e.g. a
  script list and a native list). Dump the **union**, tag each field with its source, and record how many the
  canonical accessor reports that neither list holds — that count should be zero. If a live reader and a static
  dump disagree, that is a dumper question, not a finding (see `re-workflow` evidence notes).

## Diff two builds — catch moved offsets after an update

Store a dump per build (`<version>-<hash>/`). After the target updates, take a fresh dump and **diff** against
the old one before trusting any hardcoded offset:

- classes added / removed / resized / reparented;
- fields added / removed / **moved** (offset changed) / retyped.

A moved offset that your code still reads at the old value is a crash or a silent corruption. The diff is the
cheap way to find them all at once. Keep small artifacts (manifest, summary, compressed class/enum lists) in
version control so a fresh checkout can answer class/enum questions and diff two builds without re-dumping.

## Live object readers

A live reader walks an actual instance and prints `Class.field @offset type = value`, resolving handles and
arrays. It is often clearer than static analysis for "what is actually in this object right now", and it is the
ground truth for a replication/interop check.

A live reader reads memory you do not fully own, so it obeys `re-hooking` pointer safety without exception:

- validated, typed, **in-allocation** reads only; nothing that can fault;
- bound the walk (max depth, max fields, max bytes, one visit per object) so a cycle or a huge array cannot run
  away;
- expand a handle's target only when you can prove its type; otherwise print a placeholder, never a guessed
  value;
- a value that cannot be read safely prints `<unreadable>`, never faults.

## How this fits the rest

- `re-tooling` gives you static offsets from disassembly; reflection dumps confirm or replace them with the
  engine's own numbers.
- `re-hooking` governs every live read.
- `re-verification` turns a live reader into an automated owner-vs-observer check.
