"""Read-only native PipeWire playback-node inventory.

PipeWire-native application streams may not appear in pactl's PulseAudio
compatibility sink-input list. Never infer an owned audio route from metadata.
No node controls, volume operations, or graph changes.
"""
from __future__ import annotations

import json
import subprocess
from typing import Any

from headless_mpd import MediaBackendError

_LIMIT_BYTES = 12_000_000
_LIMIT_OBJECTS = 10_000
_LIMIT_AUDIO_NODES = 256


def pipewire_objects() -> list[dict[str, Any]]:
    try:
        proc = subprocess.run(
            ["pw-dump"], capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        raise MediaBackendError(
            "NATIVE_AUDIO_EVIDENCE_UNAVAILABLE", "Read-only pw-dump is unavailable"
        ) from None
    if proc.returncode != 0:
        raise MediaBackendError(
            "NATIVE_AUDIO_EVIDENCE_UNAVAILABLE", "PipeWire native node query failed"
        )
    if len(proc.stdout) > _LIMIT_BYTES:
        raise MediaBackendError(
            "NATIVE_AUDIO_EVIDENCE_PROTOCOL", "PipeWire snapshot exceeds size limit"
        )
    try:
        objects = json.loads(proc.stdout)
    except (UnicodeError, ValueError):
        raise MediaBackendError(
            "NATIVE_AUDIO_EVIDENCE_PROTOCOL", "Invalid native PipeWire JSON"
        ) from None
    if not isinstance(objects, list) or len(objects) > _LIMIT_OBJECTS:
        raise MediaBackendError(
            "NATIVE_AUDIO_EVIDENCE_PROTOCOL", "Invalid PipeWire object inventory"
        )
    return objects


def _props(obj: Any) -> dict[str, Any]:
    if not isinstance(obj, dict):
        return {}
    info = obj.get("info")
    if not isinstance(info, dict):
        return {}
    props = info.get("props")
    return props if isinstance(props, dict) else {}


def _id(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        return int(value)
    return None


def _short(value: Any) -> str:
    if not isinstance(value, (str, int)):
        return ""
    return str(value)[:160]


def native_output_nodes(objects: list[Any]) -> dict[str, Any]:
    # Inspect Client properties as well as Node properties. Native MPD
    # may advertise its process identity only on the owning Client object.
    clients: dict[int, dict[str, Any]] = {}
    for obj in objects:
        if isinstance(obj, dict) and obj.get("type") == "PipeWire:Interface:Client":
            client_id = _id(obj.get("id"))
            if client_id is not None:
                clients[client_id] = _props(obj)

    rows = []
    total = 0
    for obj in objects:
        if not isinstance(obj, dict) or obj.get("type") != "PipeWire:Interface:Node":
            continue
        props = _props(obj)
        if props.get("media.class") != "Stream/Output/Audio":
            continue
        total += 1
        if len(rows) >= _LIMIT_AUDIO_NODES:
            continue
        node_id = _id(obj.get("id"))
        client_id = _id(props.get("client.id"))
        owner = clients.get(client_id, {}) if client_id is not None else {}
        node_binary = _short(props.get("application.process.binary")).lower()
        client_binary = _short(owner.get("application.process.binary")).lower()
        binary = node_binary or client_binary
        # A mismatch is evidence of disagreement, never authority.
        conflict = bool(node_binary and client_binary and node_binary != client_binary)
        basename = binary.rsplit("/", 1)[-1]
        is_mpd = basename == "mpd" and not conflict
        rows.append({
            "nodeId": node_id,
            "clientId": client_id,
            "nodeName": _short(props.get("node.name")),
            "mediaClass": "Stream/Output/Audio",
            "processBinary": binary,
            "processId": _short(props.get("application.process.id")
                                or owner.get("application.process.id")),
            "applicationName": _short(props.get("application.name")
                                      or owner.get("application.name")),
            "clientIdentityCorroborated": bool(node_binary and client_binary and not conflict),
            "clientIdentityConflict": conflict,
            "matchEvidence": "native process.binary == mpd" if is_mpd else "unverified",
            "mpdCandidate": is_mpd,
            "isolated": False,
        })
    return {
        "nativeOutputNodeCount": total,
        "nativeOutputsTruncated": total > _LIMIT_AUDIO_NODES,
        "nativeOutputNodes": rows,
        "nativeMpdCandidates": [row for row in rows if row["mpdCandidate"]],
        "nativeAudioIsolationVerified": False,
    }
