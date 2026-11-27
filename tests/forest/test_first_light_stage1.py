"""Offline Stage 1 checks. No HTTP, no artifact acquisition or execution."""
import fcntl
import hashlib
import os
import signal
import socket
import subprocess
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import first_light_stage1 as stage


def tar_bytes(items):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as archive:
        for name, kind, data in items:
            info = tarfile.TarInfo(name)
            if kind == "file":
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            elif kind == "link":
                info.type = tarfile.SYMTYPE
                info.linkname = data
                archive.addfile(info)
            elif kind == "dir":
                info.type = tarfile.DIRTYPE
                archive.addfile(info)
            else:
                info.type = tarfile.FIFOTYPE
                archive.addfile(info)
    return io.BytesIO(buf.getvalue())


class Stage1Tests(unittest.TestCase):
    def test_fixed_sources_and_exact_redirect_paths(self):
        digest = "sha256:" + "a"*64
        stage.target(stage.RELEASE, "archive")
        cdn = ("https://release-assets.githubusercontent.com/github-production-release-asset/"
               "658928958/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
               "?sig=fixture&response-content-disposition=attachment%3B%20filename%3D"
               "ollama-linux-amd64.tar.zst")
        stage.target(cdn, "archive", redirected=True)
        for wrong in (cdn.replace("658928958", "123"),
                      cdn.replace("ollama-linux-amd64.tar.zst", "other.tar.zst"),
                      cdn.replace("sig=fixture&", "")):
            with self.assertRaises(stage.Hold):
                stage.target(wrong, "archive", redirected=True)
        stage.target(stage.REGISTRY+"manifests/2b", "manifest")
        stage.target(stage.REGISTRY+"blobs/"+digest, "blob", digest)
        stage.target("https://"+stage.R2+"/ollama/docker/registry/v2/blobs/sha256/aa/"
                     +"a"*64+"/data?signature=fixture", "blob", digest, True)
        for url in ("https://evil.example/data?sig=x", "https://"+stage.R2+"/wrong?sig=x",
                    "http://"+stage.R2+"/wrong?sig=x", "https://user@"+stage.R2+"/wrong"):
            with self.assertRaises(stage.Hold):
                stage.target(url, "blob", digest, True)
        with self.assertRaises(stage.Hold):
            stage.target("https://"+stage.R2+"/wrong?sig=x", "manifest", redirected=True)

    def test_manifest_pin_and_bounded_descriptors(self):
        obj = {"schemaVersion": 2,
               "config": {"mediaType": "config", "digest": "sha256:"+"a"*64, "size": 8},
               "layers": [{"mediaType": "layer", "digest": "sha256:"+"b"*64, "size": 16}]}
        raw = json.dumps(obj).encode()
        with self.assertRaisesRegex(stage.Hold, "MANIFEST_DIGEST"):
            stage.parse_manifest(raw)
        with patch.object(stage, "MANIFEST_SHA", hashlib.sha256(raw).hexdigest()):
            self.assertEqual(sum(stage.parse_manifest(raw).values()), 24)
        for mutation in ("duplicate", "url", "size"):
            altered = json.loads(raw)
            if mutation == "duplicate":
                altered["layers"][0]["digest"] = altered["config"]["digest"]
            elif mutation == "url":
                altered["layers"][0]["urls"] = ["https://evil.example"]
            else:
                altered["layers"][0]["size"] = stage.MODEL_LIMIT+1
            data = json.dumps(altered).encode()
            with patch.object(stage, "MANIFEST_SHA", hashlib.sha256(data).hexdigest()):
                with self.assertRaises(stage.Hold):
                    stage.parse_manifest(data)

    def test_safe_regular_hash_and_unmaterialized_link(self):
        records, links, total = stage.unpack(tar_bytes([
            ("./bin/ollama", "file", b"not executable"),
            ("lib/alias", "link", "../bin/ollama")]), time.monotonic()+5)
        self.assertEqual(total, 14)
        self.assertEqual(records["bin/ollama"][1], hashlib.sha256(b"not executable").hexdigest())
        self.assertEqual(links, {"lib/alias": "bin/ollama"})

    def test_unsafe_archive_refuses(self):
        cases = [
            [("../escape", "file", b"x")],
            [("/absolute", "file", b"x")],
            [("link", "link", "../escape")],
            [("fifo", "fifo", b"")],
            [("bin/ollama", "file", b"x"), ("link", "link", "missing")],
            [("bin/ollama", "file", b"x"), ("bin/ollama", "file", b"y")],
            [("bin", "link", "other"), ("bin/ollama", "file", b"x")],
            [("bin", "dir", ""), ("./bin/", "dir", ""),
             ("bin/ollama", "file", b"x")],
        ]
        for items in cases:
            with self.assertRaises(stage.Hold):
                stage.unpack(tar_bytes(items), time.monotonic()+5)

    def test_complete_physical_tar_tail_including_buffered_nonzero(self):
        good = tar_bytes([("bin/ollama", "file", b"x")]).getvalue()
        self.assertEqual(stage.unpack(io.BytesIO(good), time.monotonic()+5)[2], 1)
        bad = bytearray(good)
        bad[4096] = 1
        for raw in (bytes(bad), good[:1024], good[:1536], good[:2047],
                    good[:2048] + good):
            with self.subTest(length=len(raw)), self.assertRaises(stage.Hold):
                stage.unpack(io.BytesIO(raw), time.monotonic()+5)

    def test_actual_inherited_file_pipe_socket_high_fd_are_closed_only_in_child(self):
        env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}
        launcher = str(Path(__file__).with_name("first_light_stage1_launcher.py"))
        raw = str(Path(__file__).resolve())
        base = ["/usr/bin/python3", "-I", "-B"]
        sock, peer = socket.socketpair()
        with tempfile.TemporaryFile() as marker, sock, peer:
            marker.write(b"fixture")
            marker.flush()
            marker.seek(0)
            rd, wr = os.pipe()
            high = fcntl.fcntl(marker.fileno(), fcntl.F_DUPFD, 256)
            fds = (marker.fileno(), rd, wr, sock.fileno(), high)
            try:
                for fd in fds:
                    os.set_inheritable(fd, True)
                opts = dict(env=env, stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, timeout=10, pass_fds=fds)
                refused = subprocess.run(base + [raw, "--fd-witness"], **opts)
                self.assertEqual((refused.returncode, refused.stdout, refused.stderr),
                                 (2, "STAGE1_HOLD INHERITED_FD\n", ""))
                good = subprocess.run(
                    ["/usr/bin/timeout", "--signal=TERM", "--kill-after=2s", "5s"]
                    + base + [launcher, "--offline-witness"], **opts)
                self.assertEqual((good.returncode, good.stdout, good.stderr),
                                 (0, "STAGE1_OFFLINE_FD_PASS\n", ""))
                # All original parent descriptors still exist and work.
                for fd in fds:
                    os.fstat(fd)
                self.assertEqual(os.read(high, 7), b"fixture")
                os.write(wr, b"x")
                self.assertEqual(os.read(rd, 1), b"x")
                peer.sendall(b"s")
                self.assertEqual(sock.recv(1), b"s")
            finally:
                os.close(high)
                os.close(rd)
                os.close(wr)

    def test_original_timeout_owns_exec_replacement(self):
        env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}
        launcher = str(Path(__file__).with_name("first_light_stage1_launcher.py"))
        result = subprocess.run(
            ["/usr/bin/timeout", "--signal=TERM", "--kill-after=2s", "2s",
             "/usr/bin/python3", "-I", "-B", launcher, "--offline-wait"],
            env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=8)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (124, "STAGE1_OFFLINE_FD_PASS\n", ""))

    def test_launcher_refuses_extra_environment_and_nonnull_stdin(self):
        env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}
        argv = ["/usr/bin/python3", "-I", "-B",
                str(Path(__file__).with_name("first_light_stage1_launcher.py")),
                "--offline-witness"]
        for kwargs in (dict(env={**env, "FIXTURE_SECRET": "not-a-real-secret"},
                            stdin=subprocess.DEVNULL),
                       dict(env=env, input="fixture")):
            result = subprocess.run(argv, capture_output=True, text=True, timeout=5, **kwargs)
            self.assertEqual((result.returncode, result.stdout, result.stderr),
                             (2, "STAGE1_HOLD LAUNCHER_REFUSAL\n", ""))

    def test_unqualified_environment_stops_before_acquisition(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(stage.Hold, "RUNNER_SCOPE"):
                stage.preflight(Path(tmp))


if __name__ == "__main__":
    if sys.argv[1:] in (["--fd-witness"], ["--fd-wait"]):
        # Fixed no-acquisition child; invoke the real independent verifier
        # FD guard, not a mock. Never call stage.run or stage.fetch.
        try:
            stage.require_closed_fds()
        except stage.Hold as exc:
            print("STAGE1_HOLD " + str(exc), flush=True)
            sys.exit(2)
        print("STAGE1_OFFLINE_FD_PASS", flush=True)
        if sys.argv[1:] == ["--fd-wait"]:
            signal.pause()
            sys.exit(2)
    else:
        unittest.main()
