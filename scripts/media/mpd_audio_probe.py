"""Read-only MPD output and PipeWire sink-input evidence for future Player CAVA.

Even a unique 'mpd' sink input is evidence, not certified dedicated routing.
No mutations, no pactl set-* commands, no Process/volume ownership claims.
"""
from __future__ import annotations

import json
import subprocess
from typing import Any, Callable

from headless_mpd import MediaBackendError
from native_pipewire_evidence import pipewire_objects, native_output_nodes


def parse_mpd_outputs(lines: list[str]) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    current: dict[str, str] = {}
    for line in lines:
        key, sep, value = line.partition(": ")
        if not sep:
            continue
        if key == "outputid" and current:
            outputs.append(current)
            current = {}
        if key in ("outputid", "outputname", "outputenabled", "plugin"):
            current[key] = value
    if current:
        outputs.append(current)
    return [
        {"id": o.get("outputid"), "name": o.get("outputname"),
         "enabled": o.get("outputenabled") == "1",
         "plugin": o.get("plugin", "")}
        for o in outputs
    ]


def pipewire_sink_inputs() -> list[dict[str, Any]]:
    try:
        run = subprocess.run(
            ["pactl", "-f", "json", "list", "sink-inputs"],
            capture_output=True, text=True, timeout=4, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise MediaBackendError("AUDIO_EVIDENCE_UNAVAILABLE",
                                "PipeWire/PulseAudio read-only query failed") from None
    if run.returncode != 0:
        raise MediaBackendError("AUDIO_EVIDENCE_UNAVAILABLE",
                                "PipeWire/PulseAudio sink input query refused")
    if len(run.stdout) > 2_000_000:
        raise MediaBackendError("AUDIO_EVIDENCE_PROTOCOL", "Audio snapshot exceeds size limit")
    try:
        data = json.loads(run.stdout)
    except (UnicodeError, ValueError):
        raise MediaBackendError("AUDIO_EVIDENCE_PROTOCOL", "Invalid audio snapshot JSON") from None
    if not isinstance(data, list):
        raise MediaBackendError("AUDIO_EVIDENCE_PROTOCOL", "Expected audio snapshot list")
    return data


def candidate_streams(rows: list[Any]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        props = row.get("properties") or {}
        if not isinstance(props, dict):
            continue
        binary = str(props.get("application.process.binary") or "").strip().lower()
        name = str(props.get("application.name") or "").strip()
        if binary != "mpd":
            continue
        index = row.get("index")
        if not isinstance(index, int) or isinstance(index, bool) or index < 0:
            continue
        output.append({
            "index": index,
            "processId": str(props.get("application.process.id") or ""),
            "processBinary": binary,
            "applicationName": name,
            "mediaName": str(props.get("media.name") or ""),
            "sinkIndex": row.get("sink"),
            "muted": row.get("mute"),
            "matchEvidence": "process.binary == mpd",
            "isolated": False,
        })
    return output


class MpdAudioEvidenceProbe:
    def __init__(self, backend: Any,
                 sink_provider: Callable[[], list] = pipewire_sink_inputs,
                 native_provider: Callable[[], list] = pipewire_objects):
        self.backend = backend
        self.sink_provider = sink_provider
        self.native_provider = native_provider

    def observe(self) -> dict[str, Any]:
        try:
            mpd_outputs = parse_mpd_outputs(self.backend.command("outputs"))
            mpd_error = None
        except MediaBackendError as exc:
            mpd_outputs = []
            mpd_error = {"code": exc.code, "reason": "MPD outputs unavailable"}
        try:
            rows = self.sink_provider()
            streams = candidate_streams(rows)
            total = len(rows)
            audio_error = None
        except MediaBackendError as exc:
            streams = []
            total = None
            audio_error = {"code": exc.code, "reason": exc.reason}
        try:
            native = native_output_nodes(self.native_provider())
            native_error = None
        except MediaBackendError as exc:
            native = native_output_nodes([])
            native_error = {"code": exc.code, "reason": exc.reason}
        return {
            "mpdOutputs": mpd_outputs, "mpdError": mpd_error,
            **native, "pipewireNativeError": native_error,
            "observedSinkInputCount": total,
            "mpdCandidates": streams, "pipewireError": audio_error,
            "isolated": False, "playerVolumeAvailable": False,
            "playerCavaAvailable": False,
            "reason": "PulseAudio streams and native PipeWire nodes are observations; neither alone proves a dedicated MPD-only monitor or audio route",
        }
