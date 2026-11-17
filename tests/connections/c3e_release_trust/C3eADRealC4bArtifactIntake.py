#!/usr/bin/env python3
"""C3e-AD: bounded, read-only intake of C4b GitHub CI metadata and ZIP bytes.

Verifies caller-provided GitHub run/job/artifact records against separately
pinned expected run/commit and hashes the exact artifact ZIP before invoking
the already-merged C3e-AB marker diagnostic.

IMPORTANT: JSON and ZIP records are caller supplied. A passing result does
not cryptographically authenticate GitHub, a booted host, release roots,
seat, user intent, credentials or production authority. The GitHub Actions
manual workflow separately fetches these records via its read-only token.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import stat
import sys
import zipfile

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "c3eab_diagnostic_for_c3ead", HERE / "C3eABIdentityRunDiagnostic.py")
if _spec is None or _spec.loader is None:
    raise RuntimeError("C3EAD_C3EAB_DEPENDENCY_MISSING")
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)

SCHEMA = "postapollo.connections.c3ead-github-ci-artifact-consistency.v1"
REPO = "kudokudo1/The-Post-Apollo-Project"
REPO_ID = 1382497333
WORKFLOW_ID = 414036409
WORKFLOW_NAME = "C4b Identity real official Silverblue signed RPM boot/rollback (CI only)"
WORKFLOW_PATH = ".github/workflows/connections-identity-silverblue-real-boot.yml"
JOB_NAME = "Actual offline KVM Silverblue + signed Identity RPM + two-reboot rollback"
ARTIFACT_NAME = "c4b-identity-silverblue-guest-markers"
ZIP_ENTRY = "c4b-identity-vm-guest-markers.log"
MAX_ZIP_BYTES = 131072
MAX_JSON_BYTES = 524288
SHA40 = re.compile(r"[0-9a-f]{40}\Z", re.ASCII)
SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z", re.ASCII)
GITHUB_UTC = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z\Z", re.ASCII)
REQUIRED_JOB_STEPS = (
    "Reject non-disposable CI and unverified source syntax",
    "Build the exact existing Identity gateway RPM on disposable Fedora 44",
    "Independently verify disposable RPM signer is untrusted before isolated import",
    "Real official offline Silverblue VM in disposable Fedora 44 KVM container",
    "Preserve bounded real-guest C4b marker evidence",
    "Confirm test did not activate sign-in or production authority",
)

class Refused(ValueError):
    """Reject inconsistent CI diagnostic inputs, never a permission decision."""

def _require(condition, code):
    if condition is not True:
        raise Refused(code)

def _id(value):
    return type(value) is int and 0 < value < 2**63

def _dict(value, code):
    _require(type(value) is dict, code)
    return value

def _github_utc(value):
    # GitHub metadata is caller-supplied to this offline checker; require
    # strict UTC and compare exact attempt-time boundaries, never local time.
    _require(type(value) is str and GITHUB_UTC.fullmatch(value) is not None,
             "GITHUB_TIMESTAMP_INVALID")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Refused("GITHUB_TIMESTAMP_INVALID") from exc

def _source_identity(run, expected_run_id, expected_sha):
    _require(_id(expected_run_id), "EXPECTED_RUN_ID_REQUIRED")
    _require(type(expected_sha) is str and SHA40.fullmatch(expected_sha) is not None,
             "EXPECTED_COMMIT_PIN_REQUIRED")
    _require(_id(run.get("id")) and run["id"] == expected_run_id,
             "GITHUB_RUN_ID_MISMATCH")
    _require(run.get("workflow_id") == WORKFLOW_ID and
             run.get("name") == WORKFLOW_NAME and
             run.get("path") == WORKFLOW_PATH,
             "GITHUB_WORKFLOW_IDENTITY_MISMATCH")
    for key in ("repository", "head_repository"):
        repository = _dict(run.get(key), "GITHUB_REPOSITORY_RECORD_MISSING")
        _require(repository.get("id") == REPO_ID and
                 repository.get("full_name") == REPO,
                 "GITHUB_REPOSITORY_IDENTITY_MISMATCH")
    _require(run.get("head_branch") == "main" and
             run.get("event") == "push" and
             run.get("head_sha") == expected_sha,
             "GITHUB_RUN_HEAD_OR_EVENT_MISMATCH")
    _require(run.get("status") == "completed" and
             run.get("conclusion") == "success" and
             _id(run.get("run_attempt")),
             "GITHUB_RUN_NOT_SUCCESSFUL")

def _require_jobs(jobs, run):
    _dict(jobs, "GITHUB_JOBS_LIST_MISSING")
    records = jobs.get("jobs")
    _require(type(records) is list and len(records) == 1 and
             jobs.get("total_count") == 1,
             "GITHUB_EXACT_ONE_JOB_REQUIRED")
    job = _dict(records[0], "GITHUB_JOB_INVALID")
    _require(job.get("run_id") == run["id"] and
             job.get("run_attempt") == run["run_attempt"] and
             job.get("head_sha") == run["head_sha"] and
             job.get("head_branch") == "main" and
             job.get("workflow_name") == WORKFLOW_NAME and
             job.get("name") == JOB_NAME,
             "GITHUB_JOB_BINDING_MISMATCH")
    _require(job.get("status") == "completed" and
             job.get("conclusion") == "success",
             "GITHUB_JOB_NOT_SUCCESSFUL")
    _require(_github_utc(run.get("run_started_at")) <=
             _github_utc(job.get("started_at")) <=
             _github_utc(job.get("completed_at")),
             "GITHUB_JOB_TIME_BINDING_MISMATCH")
    steps = job.get("steps")
    _require(type(steps) is list and len(steps) > 0 and len(steps) <= 64,
             "GITHUB_JOB_STEPS_INVALID")
    names = [x.get("name") if type(x) is dict else None for x in steps]
    _require(len(names) == len(set(names)) and all(type(n) is str for n in names),
             "GITHUB_DUPLICATE_OR_INVALID_JOB_STEP")
    _require(all(x.get("status") == "completed" and
                 x.get("conclusion") == "success" for x in steps),
             "GITHUB_JOB_STEP_FAILED_OR_INCOMPLETE")
    _require(all(name in names for name in REQUIRED_JOB_STEPS),
             "GITHUB_REQUIRED_JOB_STEP_MISSING")
    return job

def _artifact_record(artifacts, run, job, archive):
    _dict(artifacts, "GITHUB_ARTIFACT_LIST_MISSING")
    records = artifacts.get("artifacts")
    _require(type(records) is list and len(records) == 1 and
             artifacts.get("total_count") == 1,
             "GITHUB_EXACT_ONE_ARTIFACT_REQUIRED")
    artifact = _dict(records[0], "GITHUB_ARTIFACT_INVALID")
    _require(_id(artifact.get("id")) and
             artifact.get("name") == ARTIFACT_NAME and
             artifact.get("expired") is False,
             "GITHUB_ARTIFACT_MISSING_OR_EXPIRED")
    association = _dict(artifact.get("workflow_run"),
                        "GITHUB_ARTIFACT_RUN_BINDING_MISSING")
    _require(association.get("id") == run["id"] and
             association.get("repository_id") == REPO_ID and
             association.get("head_repository_id") == REPO_ID and
             association.get("head_branch") == "main" and
             association.get("head_sha") == run["head_sha"],
             "GITHUB_ARTIFACT_RUN_BINDING_MISMATCH")
    # An older run attempt can leave an otherwise valid artifact visible.
    # Refuse when the ZIP was uploaded before this successful job started.
    _require(_github_utc(artifact.get("created_at")) >=
             _github_utc(job.get("started_at")),
             "GITHUB_ARTIFACT_STALE_ATTEMPT_REFUSED")
    _require(type(archive) is bytes and 0 < len(archive) <= MAX_ZIP_BYTES,
             "GITHUB_ARCHIVE_SIZE_REFUSED")
    _require(type(artifact.get("size_in_bytes")) is int and
             artifact["size_in_bytes"] == len(archive),
             "GITHUB_ARTIFACT_ARCHIVE_SIZE_MISMATCH")
    digest = artifact.get("digest")
    _require(type(digest) is str and SHA256.fullmatch(digest) is not None and
             digest == "sha256:" + hashlib.sha256(archive).hexdigest(),
             "GITHUB_ARTIFACT_ZIP_DIGEST_MISMATCH")
    return artifact

def _exact_zip_payload(archive):
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            entries = z.infolist()
            _require(len(entries) == 1, "C4B_ZIP_ROSTER_REFUSED")
            member = entries[0]
            _require(member.filename == ZIP_ENTRY and not member.is_dir() and
                     member.flag_bits & 1 == 0 and
                     stat.S_ISREG(member.external_attr >> 16),
                     "C4B_ZIP_MEMBER_IDENTITY_REFUSED")
            _require(0 < member.file_size <= D.MAX_BYTES and
                     0 < member.compress_size <= MAX_ZIP_BYTES,
                     "C4B_ZIP_MEMBER_BOUNDS_REFUSED")
            with z.open(member) as stream:
                data = stream.read(D.MAX_BYTES + 1)
                _require(0 < len(data) <= D.MAX_BYTES and
                         stream.read(1) == b"",
                         "C4B_ZIP_UNCOMPRESSED_BYTES_REFUSED")
            _require(len(data) == member.file_size, "C4B_ZIP_LENGTH_MISMATCH")
            return data
    except (zipfile.BadZipFile, RuntimeError, EOFError, OSError) as exc:
        raise Refused("C4B_ZIP_DECODE_REFUSED") from exc

def assess_readonly(*, run, jobs, artifacts, archive,
                    expected_run_id, expected_sha):
    """Classify exact C4b CI evidence without creating any host authority."""
    _dict(run, "GITHUB_RUN_RECORD_MISSING")
    _source_identity(run, expected_run_id, expected_sha)
    job = _require_jobs(jobs, run)
    artifact = _artifact_record(artifacts, run, job, archive)
    payload = _exact_zip_payload(archive)
    try:
        diagnostic = D.require_complete_untrusted_markers(
            artifact=payload, caller_reported_workflow_conclusion="success")
    except D.Refused as exc:
        raise Refused("C3EAB_GUEST_MARKER_DIAGNOSTIC_REFUSED") from exc
    _require(diagnostic.get("completeMarkerSequenceConsistentInCI") is True,
             "C4B_FULL_ROLLBACK_MARKER_SEQUENCE_MISSING")
    return {
        "schema": SCHEMA,
        "state": "CONSISTENT_GITHUB_CI_DIAGNOSTIC_ONLY_NO_HOST_ADMISSION",
        "sourceRunId": run["id"],
        "sourceHeadSha": run["head_sha"],
        "sourceArtifactId": artifact["id"],
        "sourceArtifactZipSha256": hashlib.sha256(archive).hexdigest(),
        "sourceMarkerSha256": hashlib.sha256(payload).hexdigest(),
        "githubRunJobAndArtifactMetadataConsistentWithPinInCI": True,
        "c4bTwoBootRollbackMarkersConsistentInCI": True,
        **D.NEGATIVE,
    }

def _read_json(path):
    p = Path(path)
    if not p.is_file() or p.stat().st_size > MAX_JSON_BYTES:
        raise Refused("GITHUB_METADATA_FILE_BOUNDS_REFUSED")
    try:
        return json.loads(p.read_bytes())
    except (OSError, ValueError, UnicodeError) as exc:
        raise Refused("GITHUB_METADATA_JSON_REFUSED") from exc

def main(argv=None):
    parser = argparse.ArgumentParser(description="C3e read-only CI artifact classification")
    for name in ("run_json", "jobs_json", "artifacts_json", "artifact_zip"):
        parser.add_argument("--" + name.replace("_", "-"), required=True)
    parser.add_argument("--expected-run-id", required=True, type=int)
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args(argv)
    try:
        archive_path = Path(args.artifact_zip)
        if not archive_path.is_file() or not 0 < archive_path.stat().st_size <= MAX_ZIP_BYTES:
            raise Refused("C4B_ZIP_FILE_SIZE_REFUSED")
        outcome = assess_readonly(
            run=_read_json(args.run_json), jobs=_read_json(args.jobs_json),
            artifacts=_read_json(args.artifacts_json),
            archive=archive_path.read_bytes(),
            expected_run_id=args.expected_run_id, expected_sha=args.expected_sha)
    except (Refused, OSError) as exc:
        print("C3EAD_REFUSED // " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(outcome, sort_keys=True, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
