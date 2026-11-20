#!/usr/bin/env python3
"""Adversarial disposable Sway IPC GET_TREE, never production pairing."""
from __future__ import annotations

import copy
import json
import os
import socket
import struct
import sys
import threading
import unittest
from pathlib import Path

if sys.platform != "linux" or os.environ.get("CI") != "true" or os.environ.get("GITHUB_ACTIONS") != "true":
    raise SystemExit("C3E_TIMEW_SWAY_IPC_CI_ONLY")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests/connections/c3e_timew"))
import TimeWSwayIpcTreeReadPreflight as S


def tree(*, second=False):
    first = {"id": 4, "type": "con", "app_id": "brave-browser",
             "pid": 902, "name": "arbitrary title", "nodes": [], "floating_nodes": []}
    items = [first]
    if second:
        items.append({"id": 5, "type": "con", "app_id": "brave-browser",
                      "pid": 902, "nodes": [], "floating_nodes": []})
    return {"id": 1, "type": "root", "nodes": [
        {"id": 2, "type": "output", "name": "HDMI-A-1", "nodes": [
            {"id": 3, "type": "workspace", "name": "1", "nodes": items,
             "floating_nodes": []}], "floating_nodes": []}],
        "floating_nodes": []}


class FakeSwayIpcTests(unittest.TestCase):
    def exchange(self, *, item=None, raw=None, magic=S.MAGIC,
                 reply_type=S.GET_TREE, length=None, truncate=0):
        client, server = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(client.close)
        client.settimeout(0.7)
        if raw is None:
            raw = json.dumps(tree() if item is None else item, separators=(",", ":")).encode()
        frame = S.HEADER.pack(magic, len(raw) if length is None else length, reply_type) + raw
        if truncate:
            frame = frame[:-truncate]
        errors = []
        def reply():
            try:
                server.settimeout(1)
                request = b""
                while len(request) < S.HEADER.size:
                    part = server.recv(S.HEADER.size - len(request))
                    if not part:
                        break
                    request += part
                if request:
                    if request != S.HEADER.pack(S.MAGIC, 0, S.GET_TREE):
                        errors.append("unexpected outgoing request")
                    server.sendall(frame)
            except (OSError, TimeoutError):
                pass
            finally:
                server.close()
        worker = threading.Thread(target=reply, daemon=True)
        worker.start()
        self.addCleanup(lambda: worker.join(2))
        return client, errors

    def check_refused(self, code, **args):
        client, errors = self.exchange(**args)
        with self.assertRaisesRegex(S.Refused, code):
            S.inspect_fake_sway_ipc_ci_only(connection=client)
        self.assertFalse(errors)

    def test_01_one_brave_surface_is_not_authenticated(self):
        client, errors = self.exchange()
        result = S.inspect_fake_sway_ipc_ci_only(connection=client)
        self.assertEqual(result["braveLeafCountInCi"], 1)
        self.assertFalse(result["braveLeavesSharePidInCi"])
        self.assertFalse(errors)
        for key in S.DENIED:
            self.assertIs(result[key], False, key)

    def test_02_two_brave_windows_same_pid_ambiguous(self):
        client, errors = self.exchange(item=tree(second=True))
        result = S.inspect_fake_sway_ipc_ci_only(connection=client)
        self.assertTrue(result["braveLeavesSharePidInCi"])
        self.assertEqual(result["braveLeafCountInCi"], 2)
        self.assertFalse(result["canRestoreBrave"])
        self.assertFalse(errors)

    def test_03_spoofed_title_does_not_create_identity(self):
        item = tree()
        item["nodes"][0]["nodes"][0]["nodes"][0]["name"] = "owner:trusted:window-key"
        item["nodes"][0]["nodes"][0]["nodes"][0]["browser_window_ref"] = "fake"
        client, errors = self.exchange(item=item)
        result = S.inspect_fake_sway_ipc_ci_only(connection=client)
        self.assertIsNone(result["browserWindowReferenceInSwayIpc"])
        self.assertFalse(result["browserWindowToWaylandSurfaceBound"])
        self.assertFalse(errors)

    def test_04_unrecognized_app_does_not_gain_brave_identity(self):
        item = tree()
        item["nodes"][0]["nodes"][0]["nodes"][0]["app_id"] = "firefox"
        client, errors = self.exchange(item=item)
        result = S.inspect_fake_sway_ipc_ci_only(connection=client)
        self.assertEqual(result["braveLeafCountInCi"], 0)
        self.assertFalse(errors)

    def test_05_wrong_magic(self):
        self.check_refused("WRONG_IPC_RESPONSE_TYPE", magic=b"fake!!")

    def test_06_wrong_response_opcode(self):
        self.check_refused("WRONG_IPC_RESPONSE_TYPE", reply_type=0)

    def test_07_reply_too_large_refused_before_allocation(self):
        self.check_refused("UNBOUNDED_IPC_PAYLOAD", length=S.MAX_REPLY + 1)

    def test_08_truncated_header(self):
        self.check_refused("INCOMPLETE_RESPONSE", truncate=len(json.dumps(tree()).encode()) + 5)

    def test_09_truncated_payload(self):
        self.check_refused("INCOMPLETE_RESPONSE", truncate=3)

    def test_10_duplicate_json_property(self):
        self.check_refused("DUPLICATE_JSON_FIELD", raw=b'{"type":"root","id":1,"id":2}')

    def test_11_invalid_root(self):
        self.check_refused("INVALID_TREE_ROOT", item={"id":1,"type":"workspace"})

    def test_12_duplicate_container_id(self):
        item = tree(second=True)
        item["nodes"][0]["nodes"][0]["nodes"][1]["id"] = 4
        self.check_refused("DUPLICATE_OR_INVALID_CONTAINER_ID", item=item)

    def test_13_bad_pid_rejected_even_as_fixture(self):
        item = tree()
        item["nodes"][0]["nodes"][0]["nodes"][0]["pid"] = True
        self.check_refused("UNATTRIBUTABLE_BRAVE_LEAF", item=item)

    def test_14_unbounded_children(self):
        item = tree()
        item["nodes"] = [{"id": 20+i, "type": "con"} for i in range(S.MAX_CHILDREN+1)]
        self.check_refused("INVALID_TREE_CHILDREN", item=item)

    def test_15_non_stream_socket_or_unbounded_timeout(self):
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.addCleanup(a.close); self.addCleanup(b.close)
        a.settimeout(0.5)
        with self.assertRaisesRegex(S.Refused, "UNSUPPORTED_SOCKET_TYPE"):
            S.inspect_fake_sway_ipc_ci_only(connection=a)
        c, d = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(c.close); self.addCleanup(d.close)
        with self.assertRaisesRegex(S.Refused, "BOUNDED_TIMEOUT_REQUIRED"):
            S.inspect_fake_sway_ipc_ci_only(connection=c)

    def test_16_native_issuer_unconditionally_refuses(self):
        with self.assertRaisesRegex(S.Refused, "NATIVE_BRAVE_WAYLAND_TRUST_NOT_IMPLEMENTED"):
            S.run_native_sway_window_identity_issuer(
                compositor_trusted=True, operator_approved=True, can_restore=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
