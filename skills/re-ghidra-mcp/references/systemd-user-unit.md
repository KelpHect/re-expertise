# Linux: a systemd user service supervisor

A `--user` service runs the MCP server and restarts it; a separate watchdog timer runs the real MCP probe and
restarts the service when it is unhealthy (systemd's own restart only catches a process that exits, not one
that lingers while serving nothing).

## The service — `~/.config/systemd/user/re-mcp.service`

```ini
[Unit]
Description=RE analysis MCP server (local only)
After=default.target

[Service]
Type=simple
Environment=JAVA_TOOL_OPTIONS=-Xmx6g -XX:+ExitOnOutOfMemoryError
# Serve a COPY of the project, read-only, bound to localhost.
ExecStart=%h/re/venv/bin/python -m pyghidra_mcp --transport streamable-http \
    --host 127.0.0.1 --port 8765 --project-path %h/re/mcp-copy/PROJECT
Restart=always
RestartSec=2
# Backoff: give up fast restarts if it crash-loops, then systemd waits.
StartLimitIntervalSec=300
StartLimitBurst=5

[Install]
WantedBy=default.target
```

## The watchdog — `re-mcp-probe.service` + `.timer`

`re-mcp-probe.service`:

```ini
[Unit]
Description=Probe the RE MCP server and restart it if unhealthy

[Service]
Type=oneshot
ExecStart=/bin/sh -c '%h/re/venv/bin/python -I %h/re/scripts/mcp_probe.py \
    --url http://127.0.0.1:8765/mcp --expect TARGET || systemctl --user restart re-mcp.service'
```

`re-mcp-probe.timer`:

```ini
[Unit]
Description=Run the RE MCP probe periodically

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min

[Install]
WantedBy=timers.target
```

## Enable

```sh
systemctl --user daemon-reload
systemctl --user enable --now re-mcp.service re-mcp-probe.timer
loginctl enable-linger "$USER"     # so the user service survives logout / starts at boot
```

The probe is a stdlib Python script, so it needs no extra packages beyond a Python interpreter; using the venv
Python keeps it uniform with the server.
