# Evidence: what counts, and how to cite it

A claim about a binary is only as good as the line you can point at. Three kinds of evidence, in rough order of
strength for a given question:

| Kind | What it is | Good for | Cite as |
|---|---|---|---|
| **dump** | a reflection / RTTI / type-info line, or a live object dump | class→parent, a field's offset and type, a function signature | the dump file and line, e.g. `classes.jsonl:8277`, plus the build |
| **disasm** | a disassembly or decompile line | what a function does, a call target, a thread, a calling convention | the tool, the address, the instruction bytes, plus the build |
| **log** | a line a running build emitted | that a code path ran, with what values, when | the channel, the exact line, the run time, plus the build |

## The build fingerprint

Every citation names the exact build, because an address is meaningless without it. A workable fingerprint:

- the product/version string the binary reports (from its version resource, or a banner it logs);
- a short hash of the file (sha256 prefix) **and/or** the PE `TimeDateStamp` (ELF: build-id; Mach-O: uuid);
- the image base, when you quote VAs rather than RVAs.

The `re-tooling` helpers print this as their first output line (`# bin <name> size .. sha256 .. machine .. tds
.. base ..`). Copy that line into any note that quotes an address from that run. Prefer RVAs (VA = base + RVA)
so a note survives a rebased load.

## Reading a decompiler honestly

A decompiler is a reading aid, not a measurement. Two traps seen in practice:

- **Dropped register arguments.** A float passed through untouched in a vector register can vanish from a
  decompiler's argument list, because it never sees a definition. Read float/vector arguments off the
  disassembly, not off the decompiler's argument list.
- **Data "references" that are not pointers.** A reference to a function from a read-only or exception-data
  section is often an unwind table row (begin/end/unwind), not a function pointer. Read the bytes before
  calling it a pointer; only `lea`/`mov` of the address in code, and genuine vtable slots, count as a real
  reference.

## Labels are not truth

A name you gave an address in an analysis tool is a hypothesis until the table or a prologue proves it. Treat
tool-applied labels as ground truth only where (a) the binary ships that symbol, or (b) you pinned the
function's first bytes (`expect` prologue, see `re-hooking`) and they still match this build.

## When evidence conflicts

If a live dump disagrees with a static dump (e.g. two different property lists for a class), that is a tooling
question, not a finding. Reconcile the tools first; do not commit a conclusion built on the discrepancy.
