import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
import provider_digest_i6b as M

NAME = "example:latest"
A = "a" * 64
B = "b" * 64


def tags(digest=A, name=NAME, size=100):
    return {"models": [{"name": name, "model": name, "digest": digest, "size": size}]}


def ps(digest=A, name=NAME, size=120, vram=60):
    return {"models": [{"name": name, "model": name, "digest": digest,
                        "size": size, "size_vram": vram, "context_length": 2048}]}


EMPTY = {"models": []}


class ObservationTests(unittest.TestCase):
    def observe(self, first=None, resident=None, second=None, **kwargs):
        first = tags() if first is None else first
        second = first if second is None else second
        resident = ps() if resident is None else resident
        with patch.object(M, "_tags", side_effect=[first, second]) as t, \
             patch.object(M.p0, "_read_json", return_value=resident) as p:
            result = M.observe(NAME, **kwargs)
            self.assertEqual(t.call_count, 2)
            p.assert_called_once_with("127.0.0.1", 11434, "/api/ps")
            return result

    def test_match_and_redaction(self):
        result = self.observe(expected_digest="sha256:" + A)
        self.assertTrue(result["installed_resident_digest_match_reported"])
        self.assertTrue(result["expected_digest_match_reported"])
        self.assertEqual(result["resident_memory_bytes_reported"], 120)
        self.assertEqual(result["resident_vram_bytes_reported"], 60)
        for key in ("model_artifact_verified", "model_binding_verified",
                    "memory_attributed_to_model", "runner_mapping_verified",
                    "permission_granted", "production_authority",
                    "generation_requested", "model_load_requested"):
            self.assertIs(result[key], False)
        self.assertNotIn(A, json.dumps(result))
        self.assertNotIn(NAME, json.dumps(result))

    def test_prefix_normalization(self):
        self.assertTrue(self.observe(resident=ps("sha256:" + A))[
            "installed_resident_digest_match_reported"])

    def test_idle(self):
        result = self.observe(resident=EMPTY)
        self.assertTrue(result["installed_reported"])
        self.assertFalse(result["resident_reported"])
        self.assertIsNone(result["resident_memory_bytes_reported"])
        self.assertIsNone(result["installed_resident_digest_match_reported"])

    def test_absent(self):
        result = self.observe(first=EMPTY, resident=EMPTY, expected_digest=A)
        self.assertFalse(result["installed_reported"])
        self.assertIsNone(result["expected_digest_match_reported"])

    def test_other_name_not_substituted(self):
        result = self.observe(resident=ps(name="different:latest"))
        self.assertFalse(result["resident_reported"])

    def test_unknown_vram(self):
        self.assertIsNone(self.observe(resident=ps(vram=None))["resident_vram_bytes_reported"])

    def test_mismatch(self):
        for kwargs, code in (
            ({"resident": ps(B)}, "RESIDENT_DIGEST_MISMATCH"),
            ({"second": tags(B)}, "SELECTED_INVENTORY_CHANGED"),
            ({"second": tags(size=101)}, "SELECTED_INVENTORY_CHANGED"),
            ({"first": EMPTY}, "RESIDENT_WITHOUT_INSTALLED_REFERENCE"),
            ({"expected_digest": B}, "EXPECTED_DIGEST_MISMATCH"),
            ({"resident": ps(digest=None)}, "INVALID_PROVIDER_DIGEST"),
            ({"first": tags(digest="a"*12)}, "INVALID_PROVIDER_DIGEST"),
        ):
            with self.subTest(code=code), self.assertRaisesRegex(M.DigestRefusal, code):
                self.observe(**kwargs)

    def test_duplicate_models(self):
        row = tags()["models"][0]
        with self.assertRaisesRegex(M.DigestRefusal, "LOCAL_PROVIDER_OBSERVATION_UNAVAILABLE"):
            self.observe(first={"models": [row, row]})

    def test_alias_mismatch(self):
        data = tags()
        data["models"][0]["model"] = "other"
        with self.assertRaisesRegex(M.DigestRefusal, "MODEL_ALIAS_MISMATCH"):
            self.observe(first=data)

    def test_bad_inputs_before_io(self):
        with patch.object(M, "_tags") as t:
            for model, digest, endpoint in (
                ("bad name", None, M.inventory.DEFAULT_ENDPOINT),
                (NAME, "short", M.inventory.DEFAULT_ENDPOINT),
                (NAME, None, "http://example.com:11434"),
            ):
                with self.assertRaises(M.DigestRefusal):
                    M.observe(model, expected_digest=digest, endpoint=endpoint)
            t.assert_not_called()

    def test_cli_refusal_redacted(self):
        with patch.object(M, "observe", side_effect=M.DigestRefusal("RESIDENT_DIGEST_MISMATCH")), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(M.main(["observe", "--model", NAME]), 2)
        result = json.loads(out.getvalue())
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertNotIn(NAME, out.getvalue())
        self.assertFalse(result["production_authority"])


class TagsTransportTests(unittest.TestCase):
    def read(self, body, status=200, media="application/json"):
        connection = Mock()
        response = connection.getresponse.return_value
        response.status = status
        response.getheader.return_value = media
        response.read.return_value = body
        with patch.object(M.http.client, "HTTPConnection", return_value=connection):
            try:
                return M._tags("127.0.0.1", 11434)
            finally:
                connection.request.assert_called_once_with(
                    "GET", "/api/tags", headers={"Accept": "application/json"})
                connection.close.assert_called_once()

    def test_fixed_read(self):
        self.assertEqual(self.read(b'{"models":[]}'), EMPTY)

    def test_reject_ambiguous_json(self):
        for body in (b'{"models":[],"models":[]}', b'{"models":NaN}', b'not JSON'):
            with self.assertRaises(M.DigestRefusal):
                self.read(body)

    def test_reject_redirect_wrong_media_oversize(self):
        for body, status, media in (
            (b"{}", 302, "application/json"),
            (b"{}", 200, "text/html"),
            (b"x"*(M.p0.MAX_BODY_BYTES+1), 200, "application/json"),
        ):
            with self.assertRaises(M.DigestRefusal):
                self.read(body, status, media)
