#!/usr/bin/env python3
"""mcp_probe: one real health exchange with a streamable-HTTP MCP server, stdlib only.

A supervisor (scheduled task, systemd unit, launchd agent) runs this to decide whether a decompiler/analysis
MCP server is actually serving, not merely listening. It performs the full MCP handshake and one tool call,
then checks the expected binary is listed, then deletes the session. Exit 0 = healthy, 3 = unreachable or
unhealthy, 2 = usage.

Usage: python -I mcp_probe.py --url http://127.0.0.1:8765/mcp [--tool list_project_binaries]
                              [--expect <name substring>] [--timeout 120]

The body parser handles both a JSON reply and a text/event-stream (SSE) reply, because MCP servers may answer
either. It raises on nothing: a failure is a (False, reason) verdict.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request

MCP_PROTOCOL = "2025-06-18"


def parse_body(content_type: str, body: bytes, want_id):
    """Return the JSON-RPC result dict for id `want_id`, from a JSON or an SSE body."""
    text = body.decode("utf-8", "replace")
    ct = (content_type or "").lower()
    if "text/event-stream" in ct:
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                msg = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == want_id:
                return msg
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _post(url, payload, session, timeout):
    data = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json",
               "Accept": "application/json, text/event-stream"}
    if session:
        headers["Mcp-Session-Id"] = session
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return (resp.headers.get("Mcp-Session-Id") or session,
                resp.headers.get("Content-Type", ""), resp.read())


def _delete(url, session, timeout):
    req = urllib.request.Request(url, headers={"Mcp-Session-Id": session or ""}, method="DELETE")
    try:
        urllib.request.urlopen(req, timeout=timeout).read()
    except Exception:
        pass


def binary_listed(result_msg, expect):
    """True when the tool's result text mentions `expect` (or expect is empty)."""
    if result_msg is None or "result" not in result_msg:
        return False
    if not expect:
        return True
    return expect.lower() in json.dumps(result_msg["result"]).lower()


def probe(url, tool="list_project_binaries", expect="", timeout=120):
    """(ok: bool, reason: str). One initialize + initialized + tools/call + listed check + delete."""
    session = None
    try:
        session, ct, body = _post(url, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": MCP_PROTOCOL, "capabilities": {},
                       "clientInfo": {"name": "mcp-probe", "version": "1"}}}, None, timeout)
        init = parse_body(ct, body, 1)
        if init is None or "result" not in init:
            return False, "initialize returned no result"
        _post(url, {"jsonrpc": "2.0", "method": "notifications/initialized"}, session, timeout)
        _, ct, body = _post(url, {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                                  "params": {"name": tool, "arguments": {}}}, session, timeout)
        res = parse_body(ct, body, 2)
        if res is None or "result" not in res:
            return False, "tool %s returned no result (%s)" % (tool, (res or {}).get("error"))
        if not binary_listed(res, expect):
            return False, "expected %r not listed" % expect
        return True, "healthy (tool %s ok%s)" % (tool, "; %s listed" % expect if expect else "")
    except urllib.error.URLError as e:
        return False, "unreachable: %s" % getattr(e, "reason", e)
    except Exception as e:  # a probe never raises
        return False, "%s: %s" % (type(e).__name__, e)
    finally:
        if session:
            _delete(url, session, 10)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--url", default="http://127.0.0.1:8765/mcp")
    ap.add_argument("--tool", default="list_project_binaries")
    ap.add_argument("--expect", default="")
    ap.add_argument("--timeout", type=float, default=120)
    a = ap.parse_args(argv)
    ok, reason = probe(a.url, a.tool, a.expect, a.timeout)
    print(("OK " if ok else "FAIL ") + reason)
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
