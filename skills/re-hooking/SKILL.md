---
name: re-hooking
description: >-
  Resolve engine function addresses robustly across versions and attach function hooks safely, in a plugin for
  software you own, for interoperability and modding. Use when adding or auditing a native hook: building a
  version-checked address table with prologue self-tests that refuse to hook on a mismatch, validating every
  pointer before reading it, running on the correct thread or stage, and following a detour contract that stays
  safe at install, teardown and failure. Core rule: plugin code must never fault inside the host process.
license: MIT
---

# Address resolution and safe function hooks

For a plugin that extends software you own, attaching to a native function is sometimes the only seam. Two
things make that safe and maintainable: **resolving the right address across builds**, and **never faulting
inside the host process**. This skill covers both, plus the detour contract.

## Address resolution that survives updates

Hardcoding a raw offset breaks on the next update and, worse, silently points at the wrong code. Resolve
instead, and verify:

1. **A symbol or an exported resolver**, when the platform provides one — the most stable.
2. **A stable hash / table** the host or its loader ships that maps a name to the current address, when
   available.
3. **A byte-pattern (signature) scan** as a fallback, when neither of the above exists.

Whatever the method, **pin a prologue and verify it**. Each table entry carries the function's first bytes
(`expect`), with `?` wildcards for operands that vary between builds. See `references/address-table.md` for the
format and the self-test.

## The startup self-test (refuse to hook on a mismatch)

Before installing any hook, resolve every entry and check its prologue:

- A **required** entry that fails to resolve → the plugin **disables itself** and reports why. A plugin that
  half-loads against a mismatched build is how you corrupt a process.
- An **optional** entry whose resolved bytes do not match its `expect` → treat it as **unresolved**; leave that
  one hook uninstalled, keep the rest. A build that kept the address but changed the function must not get the
  old detour.
- Compare a hash of the resolved required set between peers if you replicate across machines, so two machines
  do not disagree about what they hooked.

This is the runtime twin of the label prologue check in `re-ghidra-mcp`. Pin the prologue to only what the hook
needs; an over-long `expect` breaks on the first unrelated change nearby.

## The one rule: never fault inside the host process

**Plugin code must never raise a hardware exception (an access violation / segfault) inside the host.** The
reasoning:

- You do not control the host's fault handling. Many hosts install their own crash handling; a fault from your
  code, even one you think you can handle, can terminate the process or leave it hung — the outcome is the
  host's to decide, not yours, and it is never good.
- Therefore the answer is **validate, do not catch.** Catching a fault you caused is not a safety net; the only
  safe path is to not cause it. Check before you read.

What that means in practice:

- **Validate every pointer before dereferencing it.** Confirm the object is the type you expect (e.g. a type
  tag / parent-chain check against the class you want), that any strong/refcount invariant holds, and that the
  address you will read stays **inside the object's known allocation**. Reject anything that fails — a rejected
  read returns "no", never a fault. See `references/pointer-safety.md`.
- **Read bounded, typed spans.** Know the size of the structure; a `static_assert`-style bound keeps a read
  inside it. Do not chase a pointer whose target you have not proven.
- **Run on the right thread or stage.** Hook a function that runs on the thread and at the point in the frame
  you expect; verify with a logged thread id. Touching engine state from the wrong thread is a race or a fault.
  Keep the hooked path free of anything that can block or allocate where the host does not expect it.

If a read genuinely cannot be proven safe ahead of time, the honest conclusion is **do not do it** — find a
different seam, or a scripting API, or leave the feature out. "I'll guard it and catch the fault" is the trap:
in a host with its own crash handling, a fault is fatal or hangs the process regardless of your guard.

## The detour contract

A detour must be safe at install, at teardown, and at failure. See `references/detour-contract.md`:

- **Pass-through first.** A detour whose feature is off, or whose target is not one you care about, calls the
  original and returns, deciding that with cheap lock-free reads — no lock, no allocation on the hot path.
- **Count in-flight calls** for the whole body, including the call into the original.
- **Teardown:** switch to pass-through first; then detach; then wait for the in-flight count to drain before
  freeing anything. A failed detach keeps the detour installed and passing through — never null the saved
  original pointer, or you swallow every call the host (and anything downstream) expected.
- Do not reuse a raw object address as an identity across time; an address can be recycled. Key on a stable id.

## Checklist before shipping a hook

- [ ] Address resolved by symbol/hash/pattern, not a bare offset.
- [ ] `expect` prologue pinned; startup self-test refuses on mismatch; required failure disables the plugin.
- [ ] Every pointer validated (type, invariant, in-allocation bound) before any read.
- [ ] No code path in the hook can fault, block, or allocate where the host forbids it.
- [ ] Runs on the intended thread/stage (verified by a logged thread id).
- [ ] Detour: pass-through fast path, in-flight count, pass-through-then-drain teardown, failed-detach keeps
      the original.
- [ ] A log line proving the hook installed against this build, and a self-check (`re-verification`).
