"""Same-user STOP channel: permission boundaries, exact request and recovery."""
from __future__ import annotations

import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/input"))
import AutoscrollStopChannel as stop
import AutoscrollStop as cli


class StopSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runtime = Path(self.temp.name)
        self.runtime.chmod(0o700)
        context = patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(self.runtime)})
        context.start()
        self.addCleanup(context.stop)

    def test_no_session_raises_without_creating_subdir(self):
        with self.assertRaisesRegex(stop.StopChannelError, "NO_ACTIVE_SESSION"):
            stop.send_stop()
        self.assertFalse((self.runtime / "post-apollo").exists())
        self.assertEqual(cli.main(["--bad"]), 2)

    def test_private_socket_and_same_uid_stop(self):
        with stop.StopServer() as server:
            self.assertTrue(server.healthy())
            self.assertEqual(server.path.stat().st_mode & 0o777, 0o600)
            self.assertFalse(server.poll())
            answer = {}
            def client():
                try:
                    answer["result"] = stop.send_stop()
                except BaseException as exc:
                    answer["error"] = str(exc)
            thread = threading.Thread(target=client)
            thread.start()
            triggered = False
            for _ in range(50):
                if server.poll():
                    triggered = True
                    break
                time.sleep(0.01)
            thread.join(timeout=1.0)
            self.assertTrue(triggered)
            self.assertFalse(thread.is_alive())
            self.assertNotIn("error", answer)
            self.assertEqual(answer["result"]["status"], "stop_acknowledged")
            # The acknowledgment is deliberately not a claim of process exit.
            self.assertFalse(answer["result"]["runtime_stopped"])
            self.assertTrue(server.healthy())
        self.assertFalse(server.path.exists())
        self.assertFalse(server.healthy())

    def test_unknown_payload_does_not_stop(self):
        with stop.StopServer() as server:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.connect(str(server.path))
            client.sendall(b"START\n")
            self.assertFalse(server.poll())
            client.close()
            self.assertTrue(server.healthy())

    def test_existing_socket_is_not_deleted(self):
        with stop.StopServer() as first:
            inode = first.path.lstat().st_ino
            with self.assertRaisesRegex(stop.StopChannelError,
                                        "STOP_ENDPOINT_ALREADY_EXISTS"):
                with stop.StopServer():
                    pass
            self.assertEqual(first.path.lstat().st_ino, inode)
            self.assertTrue(first.healthy())

    def test_symlink_or_foreign_file_not_replaced(self):
        parent = self.runtime / "post-apollo"
        parent.mkdir(mode=0o700)
        endpoint = parent / stop.SOCKET_NAME
        target = parent / "protected.txt"
        target.write_text("retain\n")
        endpoint.symlink_to(target)
        with self.assertRaisesRegex(stop.StopChannelError,
                                    "STOP_ENDPOINT_ALREADY_EXISTS"):
            with stop.StopServer():
                pass
        self.assertTrue(endpoint.is_symlink())
        self.assertEqual(target.read_text(), "retain\n")
        with self.assertRaisesRegex(stop.StopChannelError, "SOCKET_UNSAFE"):
            stop.send_stop()

    def test_removed_endpoint_is_fail_closed(self):
        with stop.StopServer() as server:
            server.path.unlink()
            self.assertFalse(server.healthy())

    def test_unsafe_runtime_directory_is_refused(self):
        self.runtime.chmod(0o755)
        with self.assertRaisesRegex(stop.StopChannelError, "RUNTIME_DIR_UNSAFE"):
            with stop.StopServer():
                pass


if __name__ == "__main__":
    unittest.main()
