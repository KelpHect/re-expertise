"""Unit tests for mcp_probe's body parsing and health verdict (no server needed)."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "skills", "re-ghidra-mcp", "scripts"))

import mcp_probe  # noqa: E402


class ParseBodyTests(unittest.TestCase):
    def test_plain_json(self):
        body = b'{"jsonrpc":"2.0","id":2,"result":{"binaries":["target.exe"]}}'
        msg = mcp_probe.parse_body("application/json", body, 2)
        self.assertEqual(msg["result"]["binaries"], ["target.exe"])

    def test_sse_picks_matching_id(self):
        body = (b"event: message\n"
                b'data: {"jsonrpc":"2.0","id":1,"result":{"x":1}}\n\n'
                b"event: message\n"
                b'data: {"jsonrpc":"2.0","id":2,"result":{"binaries":["target.exe"]}}\n\n')
        msg = mcp_probe.parse_body("text/event-stream; charset=utf-8", body, 2)
        self.assertEqual(msg["id"], 2)
        self.assertIn("target.exe", str(msg["result"]))

    def test_sse_ignores_done_and_garbage(self):
        body = b"data: [DONE]\ndata: not json\n"
        self.assertIsNone(mcp_probe.parse_body("text/event-stream", body, 2))

    def test_bad_json_returns_none(self):
        self.assertIsNone(mcp_probe.parse_body("application/json", b"<html>", 2))


class VerdictTests(unittest.TestCase):
    def test_listed_true_when_present(self):
        msg = {"result": {"content": [{"type": "text", "text": "target.exe analysis_complete=True"}]}}
        self.assertTrue(mcp_probe.binary_listed(msg, "target.exe"))

    def test_listed_false_when_absent(self):
        msg = {"result": {"content": [{"type": "text", "text": "other.dll"}]}}
        self.assertFalse(mcp_probe.binary_listed(msg, "target.exe"))

    def test_listed_true_when_no_expect(self):
        self.assertTrue(mcp_probe.binary_listed({"result": {}}, ""))

    def test_listed_false_without_result(self):
        self.assertFalse(mcp_probe.binary_listed({"error": {"code": -1}}, ""))
        self.assertFalse(mcp_probe.binary_listed(None, ""))


class ProbeUnreachableTests(unittest.TestCase):
    def test_unreachable_is_a_verdict_not_a_raise(self):
        ok, reason = mcp_probe.probe("http://127.0.0.1:9/mcp", timeout=1)
        self.assertFalse(ok)
        self.assertTrue(reason)


if __name__ == "__main__":
    unittest.main()
