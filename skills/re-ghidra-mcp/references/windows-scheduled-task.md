# Windows: a per-user Scheduled Task supervisor (no admin)

Run a watchdog loop at logon and every few minutes. The watchdog starts the MCP server if it is not healthy,
probes it with `mcp_probe.py`, and restarts it with backoff. A second copy of the watchdog is a no-op (guard it
with a named mutex / single-instance check).

## The watchdog loop (pseudocode, any language)

```
state = load("state.json")              # last known server pid + start time, backoff
loop forever:
    owner = pid_listening_on(PORT)
    if owner and owner is a server we started (pid + start time match state):
        if probe(URL) healthy:
            maybe_refresh_project_copy_if_source_changed_and_unlocked()
            sleep(30); continue
    if owner and not ours:
        log("foreign port owner, leaving it"); sleep(30); continue
    # not healthy: (re)start
    if backoff not elapsed: sleep(1); continue
    start_server()                       # see below; sets JAVA_TOOL_OPTIONS
    wait_until(probe healthy, up to GRACE seconds)   # measured startups: tens of seconds
    update state, backoff
```

Start the server against the **copy** of the project, read-only, bound to 127.0.0.1, with the heap capped:

```
set JAVA_TOOL_OPTIONS=-Xmx6g -XX:+ExitOnOutOfMemoryError
<venv-python> -m pyghidra_mcp --transport streamable-http --host 127.0.0.1 --port 8765 --project-path <copy>
```

## Registering the task

Register through the Task Scheduler COM API (`Schedule.Service`) rather than the `ScheduledTasks` cmdlets: the
cmdlets go through WMI/CIM provider processes, which can themselves stall on a loaded machine, and the COM API
is more robust. Settings that matter:

- triggers: **at logon of this user**, and a **repetition every 5 minutes** with no end;
- no execution time limit; allowed to run on battery; start when available;
- "if already running, do not start a new instance" (plus the mutex as a backstop);
- run with the user's interactive token (the server needs the desktop session's environment) at least
  privilege.

Run the actual server with a windowless Python (`pythonw.exe`) so no console flashes every 5 minutes.

Spawn the server **on a worker thread** inside the watchdog: on some machines `CreateProcess` can stall, and a
blocked spawn must not freeze the health loop.

## Verify after a reboot

The logon trigger starts it. After the next logon, your status command should show the task's `LastRunTime`
after the logon time and a healthy probe, and a new agent session should list the MCP server as connected.

## A known machine hazard

On some Windows + security-software combinations, new processes are created **suspended** and never resumed
machine-wide (you will see many one-thread processes in `Suspended` wait). While that lasts, `CreateProcess`
does not return, scheduled tasks that go through WMI hang, and even a process being killed can stick. It needs a
reboot or a fix by the user — it is not a bug in the supervisor. Record it if you hit it, and do not chase it as
a server bug.
