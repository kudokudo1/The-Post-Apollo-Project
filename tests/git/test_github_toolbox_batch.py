#!/usr/bin/env python3
"""Offline contracts for the GitHub read-batch runner.

No GitHub connection, real Toolbox, live desktop, credentials or host writes.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "services/github/GitHubToolboxBatch.js"
WORK = ROOT / "services/github/GitHubWorkItemsService.qml"
ATTENTION = ROOT / "services/github/GitHubAttentionProvider.qml"
WIDGET = ROOT / "widgets/GitW.qml"


def runner_source() -> str:
    src = SCRIPT.read_text(encoding="utf-8")
    match = re.search(r'const runner = \[\n(.*?)\n    \]\.join\("\\n"\);',
                      src, re.DOTALL)
    if match is None:
        raise AssertionError("Missing exact GitHub batch runner")
    lines = []
    for item in match.group(1).splitlines():
        item = item.strip().removesuffix(",")
        if not item:
            continue
        lines.append(ast.literal_eval(item))
    return "\n".join(lines)


class BatchTests(unittest.TestCase):
    def test_shell_syntax(self):
        result = subprocess.run(["bash", "-n", "-c", runner_source()],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_exact_wrapper_selects_one_toolbox_and_preserves_parameters(self):
        with tempfile.TemporaryDirectory(prefix="pa-github-batch-") as folder:
            home = Path(folder)
            bin_dir = home / ".local/bin"
            bin_dir.mkdir(parents=True)
            wrapper = bin_dir / "gh"
            wrapper.write_text(
                '#!/usr/bin/env bash\n'
                'exec toolbox run -c fedora-toolbox-44 /usr/bin/gh "$@"\n'
            )
            wrapper.chmod(0o700)
            log = home / "calls"
            fake_toolbox = bin_dir / "toolbox"
            fake_toolbox.write_text(
                '#!/usr/bin/env bash\n'
                'printf "toolbox\\n" >> "$PA_GH_TEST_LOG"\n'
                '[[ "$1" == "run" && "$2" == "-c" '
                '&& "$3" == "fedora-toolbox-44" ]] || exit 62\n'
                'shift 3\n'
                'exec "$@"\n'
            )
            fake_toolbox.chmod(0o700)
            env = dict(os.environ, HOME=str(home),
                       PATH=str(bin_dir) + ":" + os.environ["PATH"],
                       PA_GH_TEST_LOG=str(log))
            batch = 'printf "<%s>|<%s>|<%s>" "$0" "$1" "$2"'
            result = subprocess.run(
                ["bash", "-c", runner_source(), "pa-batch", batch,
                 "value one", "value;two"],
                env=env, capture_output=True, text=True, timeout=7)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout,
                             "<pa-batch>|<value one>|<value;two>")
            self.assertEqual(log.read_text().splitlines(), ["toolbox"])

    def test_changed_wrapper_falls_back_without_toolbox(self):
        with tempfile.TemporaryDirectory(prefix="pa-github-normal-") as folder:
            home = Path(folder)
            bin_dir = home / ".local/bin"
            bin_dir.mkdir(parents=True)
            wrapper = bin_dir / "gh"
            wrapper.write_text('#!/usr/bin/env bash\nprintf "native:%s\\n" "$1"\n')
            wrapper.chmod(0o700)
            env = dict(os.environ, HOME=str(home),
                       PATH=str(bin_dir) + ":" + os.environ["PATH"])
            result = subprocess.run(
                ["bash", "-c", runner_source(), "pa-batch",
                 'gh one; gh two'],
                env=env, capture_output=True, text=True, timeout=7)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(),
                             ["native:one", "native:two"])

    def test_no_batched_mutations_or_transcription_changes(self):
        source = SCRIPT.read_text(encoding="utf-8")
        work = WORK.read_text(encoding="utf-8")
        attention = ATTENTION.read_text(encoding="utf-8")
        widget = WIDGET.read_text(encoding="utf-8")
        self.assertIn('grep -Fxq', source)
        self.assertIn('GitHubBatch.wrap(', work)
        self.assertIn('GitHubBatch.wrap(', attention)
        self.assertIn('jobs -rp | wc -l)" -ge 2', work)
        self.assertNotIn('jobs -rp | wc -l)" -ge 8', work)
        self.assertIn('commits/$sha/check-runs?per_page=100', work)
        self.assertIn('pulls/$number/reviews?per_page=100', work)
        self.assertIn('gitService', widget)


if __name__ == "__main__":
    unittest.main(verbosity=2)
