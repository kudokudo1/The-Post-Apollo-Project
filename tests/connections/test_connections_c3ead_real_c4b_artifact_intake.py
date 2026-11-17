#!/usr/bin/env python3
"""C3e-AD: adversarial tests for bounded C4b GitHub CI artifact intake."""
from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
AREA = ROOT / "tests/connections/c3e_release_trust"
_spec = importlib.util.spec_from_file_location("c3ead", AREA / "C3eADRealC4bArtifactIntake.py")
assert _spec and _spec.loader
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)

PIN = "b660efe31f1bf21a427e83320b34cf54a1e0ec44"
RUN = 44050838865
CRITICAL = A.REQUIRED_JOB_STEPS


def markers():
    return ("\n".join((*A.D.REQUIRED_ORDER, "C4B_ID_VM_PROCESS_EXIT // 0")) + "\n").encode("ascii")


def pack(payload=None, *, entry=A.ZIP_ENTRY, extra=None, file_mode=stat.S_IFREG | 0o600):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        info = zipfile.ZipInfo(entry)
        info.create_system = 3
        info.external_attr = file_mode << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, markers() if payload is None else payload)
        if extra:
            z.writestr("unexpected-extra.log", extra)
    return stream.getvalue()


def fixture(archive=None):
    archive = pack() if archive is None else archive
    run = {
        "id": RUN, "name": A.WORKFLOW_NAME,
        "workflow_id": A.WORKFLOW_ID, "path": A.WORKFLOW_PATH,
        "repository": {"id": A.REPO_ID, "full_name": A.REPO},
        "head_repository": {"id": A.REPO_ID, "full_name": A.REPO},
        "head_branch": "main", "head_sha": PIN, "event": "push",
        "run_attempt": 1, "status": "completed", "conclusion": "success",
    }
    jobs = {"total_count": 1, "jobs": [{
        "run_id": RUN, "head_sha": PIN, "head_branch": "main",
        "run_attempt": 1, "workflow_name": A.WORKFLOW_NAME,
        "name": A.JOB_NAME, "status": "completed", "conclusion": "success",
        "steps": [{"name": name, "status": "completed", "conclusion": "success"}
                  for name in CRITICAL],
    }]}
    artifact = {
        "id": 14314862260, "name": A.ARTIFACT_NAME,
        "expired": False, "size_in_bytes": len(archive),
        "digest": "sha256:" + hashlib.sha256(archive).hexdigest(),
        "workflow_run": {
            "id": RUN, "repository_id": A.REPO_ID,
            "head_repository_id": A.REPO_ID, "head_branch": "main",
            "head_sha": PIN,
        }
    }
    return {"run": run, "jobs": jobs,
            "artifacts": {"total_count": 1, "artifacts": [artifact]},
            "archive": archive, "expected_run_id": RUN, "expected_sha": PIN}


class C3eADTests(unittest.TestCase):
    def positive(self, **changes):
        data = fixture()
        data.update(changes)
        return A.assess_readonly(**data)

    def refuse(self, data):
        with self.assertRaises(A.Refused):
            A.assess_readonly(**data)

    def test_01_complete_synthetic_metadata_and_markers_only_diagnostic(self):
        result = self.positive()
        self.assertTrue(result["githubRunJobAndArtifactMetadataConsistentWithPinInCI"])
        self.assertTrue(result["c4bTwoBootRollbackMarkersConsistentInCI"])
        self.assertEqual(result["sourceRunId"], RUN)
        self.assertEqual(result["sourceHeadSha"], PIN)
        for key in A.D.NEGATIVE:
            self.assertIs(result[key], False)

    def test_02_expected_run_or_commit_must_be_pinned_separately(self):
        for key, value in (("expected_run_id", RUN + 1),
                           ("expected_run_id", True),
                           ("expected_sha", PIN[:-1] + "0"),
                           ("expected_sha", ""),
                           ("expected_sha", None)):
            with self.subTest(key=key, value=value):
                d = fixture()
                d[key] = value
                self.refuse(d)

    def test_03_wrong_repository_or_workflow_identity_denied(self):
        for path, value in (
            (("run", "workflow_id"), 999),
            (("run", "path"), "tests/fake.yml"),
            (("run", "name"), "a different workflow"),
            (("run", "repository", "id"), 888),
            (("run", "head_repository", "full_name"), "attacker/fork"),
        ):
            d = fixture()
            ref = d
            for item in path[:-1]:
                ref = ref[item]
            ref[path[-1]] = value
            with self.subTest(path=path):
                self.refuse(d)

    def test_04_non_main_or_non_push_or_failed_run_denied(self):
        for key, value in (
            ("head_branch", "untrusted-feature"),
            ("event", "pull_request"),
            ("status", "in_progress"),
            ("conclusion", "failure"),
            ("run_attempt", False),
        ):
            d = fixture()
            d["run"][key] = value
            with self.subTest(key=key):
                self.refuse(d)

    def test_05_wrong_job_commit_attempt_name_or_run_denied(self):
        for key, value in (
            ("run_id", RUN + 1),
            ("head_sha", "f" * 40),
            ("run_attempt", 2),
            ("head_branch", "other"),
            ("workflow_name", "forged"),
            ("name", "other-job"),
        ):
            d = fixture()
            d["jobs"]["jobs"][0][key] = value
            with self.subTest(key=key):
                self.refuse(d)

    def test_06_missing_failed_duplicate_or_added_job_denied(self):
        for mode in ("failed", "missing", "duplicate", "additional"):
            d = fixture()
            if mode == "failed":
                d["jobs"]["jobs"][0]["steps"][2]["conclusion"] = "failure"
            if mode == "missing":
                d["jobs"]["jobs"][0]["steps"].pop(2)
            if mode == "duplicate":
                d["jobs"]["jobs"][0]["steps"].append(
                    copy.deepcopy(d["jobs"]["jobs"][0]["steps"][0]))
            if mode == "additional":
                d["jobs"]["jobs"].append(copy.deepcopy(d["jobs"]["jobs"][0]))
                d["jobs"]["total_count"] = 2
            with self.subTest(mode=mode):
                self.refuse(d)

    def test_07_artifact_belongs_to_exact_same_run_and_repo(self):
        for key, value in (
            ("id", RUN + 4),
            ("repository_id", 42),
            ("head_repository_id", 42),
            ("head_branch", "other"),
            ("head_sha", "b" * 40),
        ):
            d = fixture()
            d["artifacts"]["artifacts"][0]["workflow_run"][key] = value
            with self.subTest(key=key):
                self.refuse(d)

    def test_08_expired_or_misnamed_artifact_denied(self):
        for key, value in (
            ("expired", True),
            ("name", "forged"),
            ("id", 0),
            ("size_in_bytes", 20),
            ("digest", "sha256:" + "0" * 64),
            ("digest", None),
        ):
            d = fixture()
            d["artifacts"]["artifacts"][0][key] = value
            with self.subTest(key=key):
                self.refuse(d)

    def test_09_archive_digest_detects_mutation(self):
        d = fixture()
        d["archive"] = d["archive"][:-1] + b"x"
        self.refuse(d)

    def test_10_zip_path_traversal_and_extra_member_denied(self):
        for archive in (pack(entry="../forged.log"),
                        pack(extra=b"unwanted"),
                        pack(entry="folder/c4b-identity-vm-guest-markers.log")):
            d = fixture(archive)
            self.refuse(d)

    def test_11_symlink_and_invalid_zip_refused(self):
        for archive in (pack(file_mode=stat.S_IFLNK | 0o777),
                        b"not a zip file"):
            d = fixture(archive)
            self.refuse(d)

    def test_12_missing_rollback_is_not_complete_evidence(self):
        lines = [x for x in A.D.REQUIRED_ORDER
                 if x != "C4B_ID_PASS // REAL_SILVERBLUE_IDENTITY_RPM_LAYER_REMOVED"]
        payload = ("\n".join([*lines, "C4B_ID_VM_PROCESS_EXIT // 0"]) + "\n").encode()
        self.refuse(fixture(pack(payload)))

    def test_13_nested_failed_marker_is_denied(self):
        payload = ("\n".join((*A.D.REQUIRED_ORDER,
                    "C4B_ID_SERVICE_PROBE_DETAIL // C4B_ID_BLOCKED // forged",
                    "C4B_ID_VM_PROCESS_EXIT // 0")) + "\n").encode()
        self.refuse(fixture(pack(payload)))

    def test_14_serial_prefix_is_not_a_sanitized_marker(self):
        payload = ("\n".join(["serial> " + x for x in A.D.REQUIRED_ORDER] +
                             ["C4B_ID_VM_PROCESS_EXIT // 0"]) + "\n").encode()
        self.refuse(fixture(pack(payload)))

    def test_15_incomplete_json_and_truncated_archive_denied(self):
        d = fixture()
        d["jobs"] = {}
        self.refuse(d)
        d = fixture()
        d["archive"] = b""
        self.refuse(d)

    def test_16_cli_consumes_local_json_only_and_does_not_grant(self):
        d = fixture()
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            for key in ("run", "jobs", "artifacts"):
                (p / (key + ".json")).write_text(json.dumps(d[key]), encoding="utf-8")
            (p / "artifact.zip").write_bytes(d["archive"])
            argv = [
                "--run-json", str(p / "run.json"),
                "--jobs-json", str(p / "jobs.json"),
                "--artifacts-json", str(p / "artifacts.json"),
                "--artifact-zip", str(p / "artifact.zip"),
                "--expected-run-id", str(RUN),
                "--expected-sha", PIN,
            ]
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = A.main(argv)
            self.assertEqual(rc, 0)
            self.assertFalse(json.loads(out.getvalue())["productionAuthority"])

    def test_17_no_network_or_permission_side_effects(self):
        source = (AREA / "C3eADRealC4bArtifactIntake.py").read_text()
        for bad in ("socket.socket(", "subprocess.run(", "urllib.request",
                    "requests.get(", "credentialActionsEnabled\": True",
                    "productionAuthority\": True"):
            self.assertNotIn(bad, source)
        self.assertEqual(A.REPO_ID, 1382497333)
        self.assertEqual(A.WORKFLOW_ID, 414036409)


if __name__ == "__main__":
    unittest.main(verbosity=2)
