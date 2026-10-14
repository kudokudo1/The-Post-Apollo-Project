#!/usr/bin/env python3
"""Source-only regression tests for read-only Syntagma lag-log reporter."""

import importlib.util
import io
from contextlib import redirect_stdout
from pathlib import Path
import unittest

file = Path(__file__).resolve().parents[2] / "scripts" / "syntagma_git_lag_report.py"
spec = importlib.util.spec_from_file_location("lag_report", file)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DiagnosticReporterTests(unittest.TestCase):
    def test_correlates_without_conflating_menu_state_and_cause(self):
        lines = [
            "2026-10-14 11:48:20.900  WARN qml: SYNTAGMA_LAG_PROBE // git dock toggle synchronous=2ms // nowOpen=true",
            "2026-10-14 11:48:21.210  WARN qml: SYNTAGMA_STARTUP_TRACE // git refresh finished // LIVE QUICKSHELL :: /tmp/config // wall=500ms",
            "2026-10-14 11:48:21.720  WARN qml: SYNTAGMA_LAG_PROBE // event-loop interval 737ms (target 100ms) // git=true hospital=false notifications=false",
            "2026-10-14 11:48:22.001  WARN qml: unrelated data",
        ]
        parsed = module.parse(lines)
        self.assertEqual([x[1] for x in parsed], ["toggle", "refresh", "stall"])
        stream = io.StringIO()
        with redirect_stdout(stream):
            module.render(parsed, Path("/tmp/0xls3kmwmt/log.log"))
        out = stream.getvalue()
        self.assertIn("Git button toggles: 1", out)
        self.assertIn("refresh completions: 1", out)
        self.assertIn("737ms", out)
        self.assertIn("2ms nowOpen=true", out)

    def test_missing_diagnostics(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            module.render([], Path("/tmp/0xls3kmwmt/log.log"))
        self.assertIn("No matching diagnostic lines", stream.getvalue())

    def test_rejects_unsafe_session_names(self):
        from argparse import Namespace
        with self.assertRaises(ValueError):
            module.log_path(Namespace(log=None, session="../../somewhere"))


if __name__ == "__main__":
    unittest.main()
