#!/usr/bin/env python3
"""Contracts for transfer content preservation before mutation."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


def require_regex(path: str, pattern: str, message: str) -> None:
    text = read(path)
    assert re.search(pattern, text, re.S), f"{message}: {path}"


CHANGES = "widgets/GitChangesView.qml"
TRANSFER = "widgets/GitChangeTransferView.qml"
LINE = "widgets/GitLineTransferView.qml"

require_regex(
    CHANGES,
    r"GitContentRecoveryService \{.*"
    r"id: contentRecoveryService.*"
    r"repositoryPath:.*root\.gitService",
    "Changes must own one repository-scoped content artifact store",
)
require_regex(
    CHANGES,
    r"GitChangeTransferView \{.*"
    r"contentRecoveryService: contentRecoveryService",
    "file/hunk transfer must receive the content store",
)
require_regex(
    CHANGES,
    r"GitLineTransferView \{.*"
    r"contentRecoveryService: contentRecoveryService",
    "line transfer must receive the content store",
)

require(
    TRANSFER,
    "required property var contentRecoveryService",
    "file/hunk transfer panel must require content preservation",
)
require_regex(
    TRANSFER,
    r"function executeTransfer\(\).*"
    r"contentRecoveryService\.capture\(.*"
    r"transferScope.*"
    r"filePath.*"
    r'root\.transferService\.previewFingerprint',
    "file/hunk Execute must capture the exact preview patch first",
)
require_regex(
    TRANSFER,
    r"function onArtifactReady\(fingerprint, artifactPath, bytes\).*"
    r"transferService\.previewFingerprint.*"
    r"String\(fingerprint \|\| \"\"\) !== expected.*"
    r"root\.transferService\.execute\(\)",
    "file/hunk mutation may only start after matching artifactReady",
)
require_regex(
    TRANSFER,
    r'\? "PRESERVING".*'
    r'transferService\.transferBusy.*'
    r'\? "TRANSFERRING"',
    "file/hunk UI must expose preservation as a distinct phase",
)

require(
    LINE,
    "required property var contentRecoveryService",
    "line transfer panel must require content preservation",
)
require_regex(
    LINE,
    r"function executeTransfer\(\).*"
    r"contentRecoveryService\.capture\(.*"
    r'"line".*'
    r"filePath.*"
    r"hunkIndex.*"
    r"lineIndex.*"
    r'root\.lineTransferService\.fingerprint',
    "line Execute must preserve its exact accepted line patch first",
)
require_regex(
    LINE,
    r"function onArtifactReady\(fingerprint, artifactPath, bytes\).*"
    r"lineTransferService\.fingerprint.*"
    r"String\(fingerprint \|\| \"\"\) !== expected.*"
    r"root\.lineTransferService\.execute\(\)",
    "line mutation may only start after matching artifactReady",
)
require_regex(
    LINE,
    r'\? "PRESERVING".*'
    r'lineTransferService\.transferBusy.*'
    r'\? "TRANSFERRING"',
    "line UI must expose preservation as a distinct phase",
)

print("Git transfer content-preservation UI contracts: PASS")
