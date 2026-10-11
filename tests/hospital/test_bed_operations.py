#!/usr/bin/env python3
"""Disposable Git fixture regressions for Hospital Bed register/create/list."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/hospital-bed-operations.py"
REPOSITORY = "kudokudo1/taskbars-post-apollo"


def git(path, *args):
    return subprocess.check_output(
        ["git", "-C", str(path), *args],
        text=True, stderr=subprocess.DEVNULL,
    ).strip()


class BedOperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.seed = self.root / "seed"
        self.seed.mkdir()
        git(self.seed, "init", "-q")
        git(self.seed, "config", "user.name", "Hospital Tests")
        git(self.seed, "config", "user.email", "hospital@example.invalid")
        (self.seed / "tracked.txt").write_text("safe\n")
        git(self.seed, "add", "tracked.txt")
        git(self.seed, "commit", "-qm", "initial")
        git(self.seed, "checkout", "-qb", "feature/seed")
        git(self.seed, "branch", "feature/new-room")
        git(self.seed, "remote", "add", "origin",
            "git@github.com:kudokudo1/taskbars-post-apollo.git")
        self.registry = self.root / "registry.json"
        self.beds = self.root / "beds"

    def run_cmd(self, action, *args, success=True):
        out = subprocess.run(
            [sys.executable, str(SCRIPT), "--registry", str(self.registry),
             action, *map(str, args)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=False, timeout=15
        )
        try:
            payload = json.loads(out.stdout)
        except ValueError:
            self.fail(f"bad stdout {out.stdout!r}, stderr {out.stderr!r}")
        if success:
            self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
            self.assertTrue(payload["ok"])
        else:
            self.assertNotEqual(out.returncode, 0, out.stdout)
            self.assertFalse(payload["ok"])
        return payload

    def test_register_and_list(self):
        data = self.run_cmd("register", "--path", self.seed, "--repository", REPOSITORY,
                            "--branch", "feature/seed")["bed"]
        self.assertEqual(data["branch"], "feature/seed")
        self.assertEqual(data["repository"], REPOSITORY)
        self.assertEqual(data["verification"], "CANDIDATE_UNVERIFIED")
        self.assertEqual(json.loads(self.registry.read_text())[0]["path"], str(self.seed))
        self.assertEqual(self.registry.stat().st_mode & 0o777, 0o600)
        listed = self.run_cmd("list", "--repository", REPOSITORY)
        self.assertEqual(len(listed["beds"]), 1)
        self.assertEqual(listed["stale"], [])

    def test_register_does_not_clear_dirty_bed(self):
        (self.seed / "tracked.txt").write_text("in progress\n")
        data = self.run_cmd("register", "--path", self.seed, "--repository", REPOSITORY,
                            "--branch", "feature/seed")["bed"]
        self.assertTrue(data["dirty"])
        self.assertEqual((self.seed / "tracked.txt").read_text(), "in progress\n")

    def test_wrong_repository_refused(self):
        got = self.run_cmd("register", "--path", self.seed, "--repository", "other/other",
                           "--branch", "feature/seed", success=False)
        self.assertEqual(got["code"], "PATIENT_REPOSITORY_MISMATCH")

    def test_wrong_branch_refused(self):
        got = self.run_cmd("register", "--path", self.seed, "--repository", REPOSITORY,
                           "--branch", "feature/wrong", success=False)
        self.assertEqual(got["code"], "BED_BRANCH_MISMATCH")

    def test_unanchored_origin_refused(self):
        git(self.seed, "remote", "set-url", "origin", REPOSITORY)
        got = self.run_cmd("register", "--path", self.seed, "--repository", REPOSITORY,
                           "--branch", "feature/seed", success=False)
        self.assertEqual(got["code"], "PATIENT_REPOSITORY_MISMATCH")

    def test_local_origin_refused(self):
        git(self.seed, "remote", "set-url", "origin", str(self.root / "other"))
        got = self.run_cmd("register", "--path", self.seed, "--repository", REPOSITORY,
                           "--branch", "feature/seed", success=False)
        self.assertEqual(got["code"], "PATIENT_REPOSITORY_MISMATCH")

    def test_missing_path_refused(self):
        got = self.run_cmd("register", "--path", self.root / "missing",
                           "--repository", REPOSITORY, "--branch", "feature/seed",
                           success=False)
        self.assertEqual(got["code"], "BED_MISSING")

    def test_relative_bed_path_refused(self):
        got = self.run_cmd("register", "--path", "seed",
                           "--repository", REPOSITORY,
                           "--branch", "feature/seed", success=False)
        self.assertEqual(got["code"], "BED_PATH_NOT_ABSOLUTE")

    def test_relative_destination_root_refused(self):
        got = self.run_cmd("create", "--seed-path", self.seed,
                           "--repository", REPOSITORY,
                           "--branch", "feature/new-room",
                           "--bed-root", "relative/path", success=False)
        self.assertEqual(got["code"], "BED_ROOT_NOT_ABSOLUTE")

    def test_register_idempotent(self):
        for _ in range(2):
            self.run_cmd("register", "--path", self.seed,
                         "--repository", REPOSITORY, "--branch", "feature/seed")
        self.assertEqual(len(json.loads(self.registry.read_text())), 1)

    def test_new_worktree_uses_same_git_family_without_disturbing_seed(self):
        (self.seed / "tracked.txt").write_text("unfinished\n")
        bed = self.run_cmd("create", "--seed-path", self.seed,
                           "--repository", REPOSITORY,
                           "--branch", "feature/new-room",
                           "--bed-root", self.beds)["bed"]
        target = Path(bed["path"])
        self.assertTrue(target.is_dir())
        self.assertEqual(git(target, "branch", "--show-current"), "feature/new-room")
        self.assertEqual(bed["verification"], "CANDIDATE_UNVERIFIED")
        self.assertEqual((self.seed / "tracked.txt").read_text(), "unfinished\n")
        self.assertEqual(git(self.seed,"branch","--show-current"), "feature/seed")
        self.assertEqual(len(self.run_cmd("list")["beds"]), 1)

    def test_create_rejects_branch_occupied_by_seed(self):
        got = self.run_cmd("create", "--seed-path", self.seed,
                           "--repository", REPOSITORY, "--branch", "feature/seed",
                           "--bed-root", self.beds, success=False)
        self.assertEqual(got["code"], "BRANCH_ALREADY_OCCUPIED")
        self.assertEqual(list(self.beds.iterdir()), [],
                         "Refused move must not leave an unrequested Bed")

    def test_create_rejects_nonexistent_branch_without_fetch(self):
        got = self.run_cmd("create", "--seed-path", self.seed,
                           "--repository", REPOSITORY, "--branch", "feature/never-fetched",
                           "--bed-root", self.beds, success=False)
        self.assertEqual(got["code"], "BRANCH_NOT_AVAILABLE_LOCALLY")

    def test_create_rejects_path_traversal(self):
        got = self.run_cmd("create", "--seed-path", self.seed,
                           "--repository", REPOSITORY, "--branch", "feature/new-room",
                           "--bed-root", self.beds, "--name", "../outside", success=False)
        self.assertEqual(got["code"], "BED_NAME_INVALID")

    def test_create_rejects_destination_collision(self):
        self.beds.mkdir()
        (self.beds/"taken").write_text("do not touch")
        got = self.run_cmd("create", "--seed-path", self.seed, "--repository", REPOSITORY,
                           "--branch", "feature/new-room", "--bed-root", self.beds,
                           "--name", "taken", success=False)
        self.assertEqual(got["code"], "BED_DESTINATION_EXISTS")
        self.assertEqual((self.beds/"taken").read_text(),"do not touch")

    def test_missing_registered_path_becomes_stale_not_trusted(self):
        self.run_cmd("register", "--path", self.seed, "--repository", REPOSITORY,
                     "--branch", "feature/seed")
        git(self.seed, "remote", "set-url", "origin", "https://github.com/other/other")
        listed = self.run_cmd("list")
        self.assertEqual(len(listed["beds"]), 0)
        self.assertEqual(listed["stale"][0]["reason"], "PATIENT_REPOSITORY_MISMATCH")

    def test_invalid_branch_is_refused(self):
        for branch in ("", "../escape", "-f", "DETACHED", "HEAD"):
            data = self.run_cmd("create", "--seed-path", self.seed,
                                "--repository", REPOSITORY, "--branch=" + branch,
                                "--bed-root", self.beds, success=False)
            self.assertEqual(data["code"], "BRANCH_UNRESOLVED", branch)


if __name__ == "__main__":
    unittest.main()
