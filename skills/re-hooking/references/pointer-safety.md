# Pointer safety: validate, do not catch

The rule from the skill: plugin code must never fault inside the host process, so the only safe read is one you
have proven safe before you make it. This file is the "how".

## Before any dereference

Ask three questions, and reject the read if any answer is no:

1. **Is this the type I think it is?** Check a discriminator you trust — a type tag, a vtable identity, a
   parent-chain `IsA`-style check against the class you expect. A pointer that is "an object" is not enough;
   you are about to read a specific field of a specific class.
2. **Does the object's own invariant hold?** If the type has a liveness or refcount notion, check it. A pointer
   to a freed or half-constructed object passes a null check and still faults.
3. **Does the exact range I will touch stay inside the object's allocation?** You read `[base + off, base + off
   + size)`. Know `size` for the field and the object; a `static_assert`-style compile-time bound on `off +
   size <= sizeof(struct)` keeps a typed read honest. Do not read past the structure because "there is usually
   something there".

Only then read. A read that fails any check returns a negative result (a `false`, an empty optional) — never a
fault, never an exception you then try to swallow.

## Do not chase unproven pointers

A multi-hop chase (`[[base + a] + b] + c`) multiplies the risk: each hop can be a non-pointer. Prove each hop,
or do not take it. A real incident: a hook chased `[[req+8]+0x200]+0x48`, but `+0x200` lay **past the end** of
the `req` structure, so the last hop read a garbage value and faulted — which hung the whole process. The fix
was to read only a bounded, typed span **inside** the known structure and follow no pointer at all. When you
genuinely need one hop outside, prove the intermediate's type first (question 1 above), and keep it behind an
off-by-default switch until a log-only run confirms it.

## Reading memory you are unsure about

Sometimes you must read an address whose validity you cannot establish structurally (scraping a region for
hints). Then do not read it in-process with a raw dereference. Use an OS primitive that returns a failure code
instead of faulting:

- query the page first (is it committed, readable, not a guard page?) and skip it if not;
- or copy through a syscall that reports failure (`NtReadVirtualMemory` / `process_vm_readv` on self /
  `vm_read`), after a range sanity-check (plausible magnitude, no wrap).

Both return "could not read" rather than raising. Keep such reads rare and clearly bounded; they are a last
resort, not the normal path. The normal path is a validated, typed, in-allocation read.

## Threads

A pointer that is valid on one thread may be mid-mutation on another. Read engine state on the thread that owns
it (hook a function that runs there, verified by a logged thread id), or take the object's own documented
synchronization — bounded, non-blocking, and skipped rather than waited on if contended. Do not block a host
thread or wait on its job system from inside a hook.
