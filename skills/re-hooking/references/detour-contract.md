# The detour contract

A detour replaces a function's entry with a jump to your code, which may call the original and return. It must
be safe at three moments: while running (hot path), at teardown, and when something fails. Get these wrong and
you either cost the host a lot of time on every call or you swallow calls the host depended on.

## Hot path: decide fast, pass through by default

Most calls into a detoured function are not ones you care about. Decide that cheaply and get out:

- A detour whose feature is **off**, or whose target is **not** an object you track, calls the original and
  returns. Decide it with lock-free acquire loads (an atomic flag, a lock-free set membership test). **No lock,
  no allocation** on the hot path — the function may be called thousands of times a frame.
- A lock-free membership test may answer "yes" for a just-removed entry until the next rebuild; that is fine as
  long as the slow path re-checks. It must never answer a false "no" for a live entry.
- Keep any real work off the thread's critical timing. If you must sample something shared, use a `try_lock`
  and skip on contention rather than waiting.

## In-flight counting

Every detour body counts itself in flight for its **whole** duration, including the call into the original —
because teardown may free the trampoline. A scope guard that increments on entry and decrements on exit (even
on an early return) is the clean way.

## Teardown: pass-through, then detach, then drain

Order matters:

1. **Switch the detour to pass-through** (set the "off" flag) so new calls go straight to the original.
2. **Detach** the hook.
3. **Wait for the in-flight count to reach zero** (bounded, e.g. up to a couple of seconds) before freeing any
   state or trampoline. If it does not drain, leak the state rather than free it under a running callback.

## Failure: keep the original, keep passing through

A **failed detach** must keep the detour installed and in pass-through, and must **not** null the saved
original pointer. A nulled original turns every future call into a no-op — and if the host (or a quest system,
a downstream listener, anything) depended on that function running, you have silently broken it. Log the failed
detach and that the detour stays installed passing calls through; log a clean detach-and-drain when it
succeeds. (Real incident: a failed detach nulled the original and swallowed every call of a frequently-used
engine function.)

## Identity over time

Do not treat a raw object address as a stable identity. Addresses get recycled: a later, different object can
reuse the address of one you were tracking, and events get misattributed. Key your tracking on a stable id the
engine assigns, not on the pointer value, and confirm identity when you act.

## Nested detours and shared helpers

If several of your hooks share a helper that reads engine memory, the helper still obeys pointer safety
(`pointer-safety.md`): validated, typed, in-allocation reads only. A detour that calls into the original, which
is itself inside another of your guarded calls, must not leave a lock held or an in-flight count stuck if a
fault occurs deeper in the host — which is the whole reason the hot path takes no lock and the reads cannot
fault in the first place.
