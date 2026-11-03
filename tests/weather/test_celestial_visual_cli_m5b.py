"""M5b CLI transport: bounded --query-json stays compatible with file/stdin."""
import contextlib
import io
import json
from pathlib import Path
import sys
from unittest import mock
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "weather"))
import celestial_visual_data as visual

QUERY = {
    "format": visual.FORMAT,
    "start_utc": "2026-10-01T00:00:00Z",
    "end_utc": "2026-10-03T00:00:00Z",
    "bodies": ["moon", "sun"],
    "step_hours": 12,
    "include_events": True,
}


class CliTransportTests(unittest.TestCase):
    def run_cli(self, arguments, stdin=None):
        output, errors = io.StringIO(), io.StringIO()
        with mock.patch.object(visual, "compute_visual_data",
                               return_value={"format": visual.FORMAT, "sample_count": 5}) as call, \
             mock.patch("sys.stdin", stdin or io.StringIO("")), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            result = visual.main(arguments)
        return result, output.getvalue(), errors.getvalue(), call

    def test_argv_json_accepted_without_shell_or_files(self):
        raw = json.dumps(QUERY, separators=(",", ":"))
        code, out, error, worker = self.run_cli(
            ["--kernel", "/placeholder.bsp", "--query-json", raw])
        self.assertEqual(code, 0)
        self.assertEqual(error, "")
        self.assertEqual(json.loads(out)["format"], visual.FORMAT)
        worker.assert_called_once_with(QUERY, "/placeholder.bsp")

    def test_stdin_backwards_compatibility(self):
        code, out, err, worker = self.run_cli(
            ["--kernel", "/placeholder.bsp"], io.StringIO(json.dumps(QUERY)))
        self.assertEqual(code, 0)
        worker.assert_called_once_with(QUERY, "/placeholder.bsp")

    def test_invalid_and_oversized_argv_fails_closed(self):
        for bad in ("not-json", " " * 4097):
            code, out, error, worker = self.run_cli(
                ["--kernel", "/placeholder.bsp", "--query-json", bad])
            self.assertEqual(code, 2)
            self.assertEqual(out, "")
            self.assertTrue(error)
            worker.assert_not_called()

    def test_local_file_and_argv_mutually_exclusive(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                visual.main(["--kernel", "/placeholder.bsp",
                             "--query-json", "{}", "--query", "a.json"])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
