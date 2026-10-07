#!/usr/bin/env python3
"""Focused contracts for durable Git content-recovery artifacts."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SERVICE = "services/git/GitContentRecoveryService.qml"


def read() -> str:
    return (ROOT / SERVICE).read_text(encoding="utf-8")


def require(needle: str, message: str) -> None:
    text = read()
    assert needle in text, f"{message}: missing {needle!r}"


def require_regex(pattern: str, message: str) -> None:
    assert re.search(pattern, read(), re.S), message


require(
    "function capture(scope, path, hunkIndex, lineIndex, expectedFingerprint)",
    "content store must capture exact accepted transfer scope",
)
require(
    '["file", "hunk", "line"].indexOf(kind) < 0',
    "content store must explicitly constrain supported transfer granularities",
)
require(
    '/^[0-9a-f]{64}$/.test(expected)',
    "artifact identity must be a full SHA-256 fingerprint",
)
require(
    'git("diff", "--binary", "--full-index", "--", path)',
    "whole-file recovery must preserve binary-capable full-index patch bytes",
)
require(
    'patch = "".join(header + hunks[hunk_index])',
    "hunk recovery must preserve exactly one indexed hunk",
)
require(
    'difflib.unified_diff(base, target',
    "line recovery must use the same index-based minimal line patch semantics",
)
require(
    'actual = hashlib.sha256(patch).hexdigest()',
    "content store must hash regenerated patch bytes",
)
require(
    'RECOVERY PATCH DOES NOT MATCH ACCEPTED PREVIEW',
    "content store must refuse fingerprint mismatch before persistence",
)
require(
    'os.environ.get("XDG_STATE_HOME")',
    "recovery artifacts must live in XDG state rather than the repository",
)
require(
    '"post-apollo", "git-recovery"',
    "content recovery must have a dedicated state namespace",
)
require(
    'os.makedirs(directory, mode=0o700, exist_ok=True)',
    "recovery artifact directory must default private",
)
require(
    'os.chmod(directory, 0o700)',
    "existing recovery directory permissions must be corrected to private",
)
require(
    'os.fchmod(fd, 0o600)',
    "temporary artifact bytes must be private before writing",
)
require(
    'os.fsync(handle.fileno())',
    "artifact bytes must be flushed durably before publication",
)
require(
    'os.replace(temporary, destination)',
    "artifact publication must be atomic",
)
require(
    'os.chmod(destination, 0o600)',
    "published patch artifact must remain private",
)
require_regex(
    r"signal artifactReady\(.*"
    r"string fingerprint.*"
    r"string artifactPath.*"
    r"int bytes",
    "capture completion must expose stable artifact identity and size",
)
require(
    'SELECTED PATH HAS STAGED CHANGES',
    "artifact capture must preserve the same staged-overlap refusal as transfer",
)
require(
    'CONFLICTED SOURCE PATH',
    "artifact capture must refuse conflicted source content",
)

print("Git content recovery artifact contracts: PASS")
