# macOS: a launchd LaunchAgent supervisor

A per-user LaunchAgent keeps the MCP server running (`KeepAlive`), and a second periodic agent runs the real
MCP probe and restarts the server when it is unhealthy (`KeepAlive` alone only catches a process that exits,
not one that serves nothing).

## The server — `~/Library/LaunchAgents/com.you.re-mcp.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.you.re-mcp</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/you/re/venv/bin/python</string>
    <string>-m</string><string>pyghidra_mcp</string>
    <string>--transport</string><string>streamable-http</string>
    <string>--host</string><string>127.0.0.1</string>
    <string>--port</string><string>8765</string>
    <string>--project-path</string><string>/Users/you/re/mcp-copy/PROJECT</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>JAVA_TOOL_OPTIONS</key><string>-Xmx6g -XX:+ExitOnOutOfMemoryError</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/Users/you/re/logs/mcp.out.log</string>
  <key>StandardErrorPath</key><string>/Users/you/re/logs/mcp.err.log</string>
</dict>
</plist>
```

## The watchdog — `com.you.re-mcp-probe.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.you.re-mcp-probe</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/sh</string><string>-c</string>
    <string>/Users/you/re/venv/bin/python -I /Users/you/re/scripts/mcp_probe.py \
      --url http://127.0.0.1:8765/mcp --expect TARGET \
      || launchctl kickstart -k gui/$(id -u)/com.you.re-mcp</string>
  </array>
  <key>StartInterval</key><integer>60</integer>
  <key>RunAtLoad</key><true/>
</dict>
</plist>
```

## Load

```sh
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.you.re-mcp.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.you.re-mcp-probe.plist
```

`kickstart -k` restarts the server cleanly; the probe is stdlib-only Python, so it needs no extra packages.
Bind to 127.0.0.1 and keep the logs under your own directory.
