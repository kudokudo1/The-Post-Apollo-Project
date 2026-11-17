"""U9 source-only gates for disposable real-GIO CI round trip.

These tests never launch GIO, read the operator Trash or move a real file.
Only isolated tempfile fixtures are used for preflight and shape validators.
"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
from subprocess import CompletedProcess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts" / "trash" / "gio_disposable_roundtrip_u9.py"
spec = importlib.util.spec_from_file_location("gio_u9_fixture", PATH)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class DisposableGioFixtureTests(unittest.TestCase):
    def test_preflight_denies_non_ci_and_unsafe_runner_temp(self):
        with tempfile.TemporaryDirectory(prefix="trashpp-u9-shape-") as tmp:
            env = {"RUNNER_TEMP": tmp}
            for altered in (env, dict(env, GITHUB_ACTIONS="true"),
                            dict(env, CI="true"),
                            {"GITHUB_ACTIONS": "true", "CI": "true", "RUNNER_TEMP": "relative"}):
                with self.assertRaises(fixture.RoundTripError):
                    fixture.ci_runner_temp(altered)
            allowed = dict(env, GITHUB_ACTIONS="true", CI="true")
            self.assertEqual(fixture.ci_runner_temp(allowed), Path(tmp).resolve())

    def test_preflight_rejects_symlink_runner_temp(self):
        with tempfile.TemporaryDirectory(prefix="trashpp-u9-shape-") as tmp:
            path = Path(tmp)
            (path / "other").mkdir()
            (path / "link").symlink_to(path / "other", target_is_directory=True)
            with self.assertRaisesRegex(fixture.RoundTripError, "RUNNER_TEMP_NOT_PRIVATE"):
                fixture.ci_runner_temp({"GITHUB_ACTIONS": "true", "CI": "true",
                                        "RUNNER_TEMP": str(path / "link")})

    def test_index_requires_empty_initial_inventory(self):
        fixture.assert_empty_index({"ok": True, "complete": True, "total": 0, "items": []})
        for wrong in (
            {"ok": True, "complete": True, "total": 1, "items": [{"uri": "trash:///unknown"}]},
            {"ok": True, "complete": False, "total": 0, "items": []},
            {"ok": True, "complete": True, "total": 0, "items": [{}]},
        ):
            with self.assertRaises(fixture.RoundTripError):
                fixture.assert_empty_index(wrong)

    def test_exact_one_item_and_original_path_required(self):
        original = Path("/runner/temp/test.txt")
        row = {"uri": "trash:///test.txt", "original": str(original), "reviewId": "f" * 64}
        index = {"ok": True, "complete": True, "total": 1, "items": [row]}
        self.assertEqual(fixture.reviewed_item(index, original), row)
        for wrong in (
            dict(index, total=2),
            dict(index, items=[row, row]),
            dict(index, items=[dict(row, original="/outside/test.txt")]),
            dict(index, items=[dict(row, uri="file:///tmp/test.txt")]),
            dict(index, items=[dict(row, reviewId="nope")]),
            dict(index, complete=False),
        ):
            with self.assertRaises(fixture.RoundTripError):
                fixture.reviewed_item(wrong, original)

    def test_backend_return_code_must_match_json_receipt(self):
        success = CompletedProcess([], 0, stdout='{"ok":true,"kind":"restore"}')
        refusal = CompletedProcess([], 1, stdout='{"ok":false,"error":"RESTORE_TARGET_EXISTS"}')
        self.assertEqual(fixture.json_response(success, True)["kind"], "restore")
        self.assertEqual(fixture.json_response(refusal, False)["error"], "RESTORE_TARGET_EXISTS")
        for result, expected in ((success, False), (refusal, True),
                                 (CompletedProcess([], 0, stdout="{bad"), True),
                                 (CompletedProcess([], 1, stdout='{"ok":true}'), True)):
            with self.assertRaises(fixture.RoundTripError):
                fixture.json_response(result, expected)

    def test_non_ci_main_cannot_create_sandbox_or_run_gio(self):
        with tempfile.TemporaryDirectory(prefix="trashpp-u9-shape-") as tmp:
            stream = io.StringIO()
            with patch.dict("os.environ", {"RUNNER_TEMP": tmp, "GITHUB_ACTIONS": "false",
                                           "CI": "false"}, clear=True):
                with patch.object(fixture, "run_roundtrip", side_effect=AssertionError("called")):
                    with contextlib.redirect_stdout(stream):
                        code = fixture.main(["script"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(stream.getvalue())["error"], "CI_ONLY")
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
