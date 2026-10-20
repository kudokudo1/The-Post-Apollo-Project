#!/usr/bin/env python3
"""Native PipeWire player-audio evidence: fake-only, read-only verification."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "media"))
from headless_mpd import MediaBackendError
from native_pipewire_evidence import native_output_nodes, pipewire_objects
from mpd_audio_probe import MpdAudioEvidenceProbe
from test_mpd_audio_probe import FakeAudioMpd


def obj(kind, ident, props):
    return {"id": ident, "type": "PipeWire:Interface:" + kind,
            "info": {"props": props}}


class NativePipeWireEvidenceTests(unittest.TestCase):
    def test_native_mpd_node_not_visible_in_pactl_is_candidate_only(self):
        sample = [
            obj("Client", 41, {
                "application.process.binary": "/usr/bin/mpd",
                "application.process.id": "8129",
                "application.name": "Music Player Daemon",
            }),
            obj("Node", 88, {
                "media.class": "Stream/Output/Audio",
                "client.id": "41", "node.name": "mpd.output",
            }),
            obj("Node", 23, {
                "media.class": "Audio/Sink", "node.name": "alsa_output.pci",
            }),
        ]
        result = MpdAudioEvidenceProbe(FakeAudioMpd(),
            sink_provider=lambda: [], native_provider=lambda: sample).observe()
        self.assertEqual(result["observedSinkInputCount"], 0)
        self.assertEqual(result["nativeOutputNodeCount"], 1)
        self.assertEqual(result["nativeMpdCandidates"][0]["nodeId"], 88)
        self.assertEqual(result["nativeMpdCandidates"][0]["clientId"], 41)
        self.assertEqual(result["nativeMpdCandidates"][0]["processId"], "8129")
        self.assertIsNone(result["pipewireNativeError"])
        self.assertFalse(result["nativeMpdCandidates"][0]["isolated"])
        self.assertFalse(result["playerCavaAvailable"])
        self.assertFalse(result["playerVolumeAvailable"])
        self.assertFalse(result["isolated"])

    def test_joins_client_identity_not_unrelated_apps(self):
        rows = [obj("Client", 44, {"application.process.binary": "brave"}),
                obj("Node", 91, {"media.class": "Stream/Output/Audio",
                                 "client.id": 44, "node.name": "audio"})]
        data = native_output_nodes(rows)
        self.assertEqual(data["nativeOutputNodeCount"], 1)
        self.assertEqual(data["nativeMpdCandidates"], [])
        self.assertEqual(data["nativeOutputNodes"][0]["processBinary"], "brave")

    def test_identity_conflict_refuses_candidate(self):
        rows = [obj("Client", 44, {"application.process.binary": "brave"}),
                obj("Node", 91, {"media.class": "Stream/Output/Audio",
                                 "client.id": 44,
                                 "application.process.binary": "mpd"})]
        data = native_output_nodes(rows)
        self.assertFalse(data["nativeOutputNodes"][0]["mpdCandidate"])
        self.assertTrue(data["nativeOutputNodes"][0]["clientIdentityConflict"])

    def test_node_only_process_binary_can_be_candidate(self):
        rows = [obj("Node", 91, {"media.class": "Stream/Output/Audio",
                                 "application.process.binary": "mpd"})]
        data = native_output_nodes(rows)
        self.assertEqual(data["nativeMpdCandidates"][0]["nodeId"], 91)
        self.assertFalse(data["nativeMpdCandidates"][0]["clientIdentityCorroborated"])

    def test_absent_or_malformed_objects_never_invent_node(self):
        rows = [None, "text", {}, {"type": "PipeWire:Interface:Node", "info": None},
                obj("Node", 9, {"media.class": "Stream/Input/Audio",
                                "application.process.binary": "mpd"})]
        data = native_output_nodes(rows)
        self.assertEqual(data["nativeOutputNodeCount"], 0)
        self.assertEqual(data["nativeMpdCandidates"], [])

    def test_native_probe_unavailable_keeps_old_probe_intact(self):
        def unavailable():
            raise MediaBackendError("NATIVE_AUDIO_EVIDENCE_UNAVAILABLE", "pw-dump absent")
        result = MpdAudioEvidenceProbe(FakeAudioMpd(),
            sink_provider=lambda: [], native_provider=unavailable).observe()
        self.assertEqual(result["mpdOutputs"][0]["id"], "0")
        self.assertEqual(result["nativeOutputNodeCount"], 0)
        self.assertEqual(result["pipewireNativeError"]["code"],
                         "NATIVE_AUDIO_EVIDENCE_UNAVAILABLE")
        self.assertFalse(result["playerCavaAvailable"])

    def test_pw_dump_invocation_is_read_only(self):
        class Finished:
            returncode = 0
            stdout = json.dumps([obj("Node", 3, {"media.class": "Stream/Output/Audio"})])
        with patch("native_pipewire_evidence.subprocess.run", return_value=Finished()) as run:
            result = pipewire_objects()
            self.assertEqual(result[0]["id"], 3)
            self.assertEqual(run.call_args.args[0], ["pw-dump"])
            self.assertEqual(run.call_args.kwargs["timeout"], 5)

    def test_malformed_pipewire_dump_fails_closed(self):
        class Finished:
            returncode = 0
            stdout = '{"objects": []}'
        with patch("native_pipewire_evidence.subprocess.run", return_value=Finished()):
            with self.assertRaises(MediaBackendError):
                pipewire_objects()

    def test_native_dump_subprocess_missing_is_not_playback_error(self):
        with patch("native_pipewire_evidence.subprocess.run",
                   side_effect=FileNotFoundError("pw-dump")):
            with self.assertRaises(MediaBackendError) as ctx:
                pipewire_objects()
        self.assertEqual(ctx.exception.code, "NATIVE_AUDIO_EVIDENCE_UNAVAILABLE")

    def test_audio_graph_size_cap_never_authorizes_output(self):
        rows = [obj("Node", i, {"media.class": "Stream/Output/Audio",
                                "application.process.binary": "mpd"})
                for i in range(300)]
        report = native_output_nodes(rows)
        self.assertEqual(report["nativeOutputNodeCount"], 300)
        self.assertEqual(len(report["nativeOutputNodes"]), 256)
        self.assertTrue(report["nativeOutputsTruncated"])
        self.assertFalse(report["nativeAudioIsolationVerified"])


if __name__ == "__main__":
    unittest.main()
