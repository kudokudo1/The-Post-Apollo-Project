"""Offline Stage 1 checks. No HTTP, no artifact acquisition or execution."""
import hashlib
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
            else:
                info.type = tarfile.FIFOTYPE
                archive.addfile(info)
    return io.BytesIO(buf.getvalue())


class Stage1Tests(unittest.TestCase):
    def test_fixed_sources_and_exact_redirect_paths(self):
        digest = "sha256:" + "a"*64
        stage.target(stage.RELEASE, "archive")
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
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records, links, total = stage.unpack(tar_bytes([
                ("./bin/ollama", "file", b"not executable"),
                ("lib/alias", "link", "../bin/ollama")]), root, time.monotonic()+5)
            self.assertEqual(total, 14)
            self.assertEqual(records["bin/ollama"][1], hashlib.sha256(b"not executable").hexdigest())
            self.assertEqual(links, {"lib/alias": "bin/ollama"})
            self.assertFalse((root/"lib/alias").exists())
            self.assertFalse((root/"bin/ollama").stat().st_mode & 0o111)

    def test_unsafe_archive_refuses(self):
        cases = [
            [("../escape", "file", b"x")],
            [("/absolute", "file", b"x")],
            [("link", "link", "../escape")],
            [("fifo", "fifo", b"")],
            [("bin/ollama", "file", b"x"), ("link", "link", "missing")],
            [("bin/ollama", "file", b"x"), ("bin/ollama", "file", b"y")],
            [("bin", "link", "other"), ("bin/ollama", "file", b"x")],
        ]
        for items in cases:
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(stage.Hold):
                    stage.unpack(tar_bytes(items), Path(tmp), time.monotonic()+5)

    def test_unqualified_environment_stops_before_acquisition(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(stage.Hold, "RUNNER_SCOPE"):
                stage.preflight(Path(tmp))


if __name__ == "__main__":
    unittest.main()
