#!/usr/bin/env python3
"""No-hardware read-only MPD/PipeWire CAVA readiness contract."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "media"))
from headless_mpd import MediaBackendError
from mpd_audio_probe import MpdAudioEvidenceProbe, candidate_streams, parse_mpd_outputs, pipewire_sink_inputs
from media_controller import MediaController
from test_headless_controller import FakeMpd


class FakeAudioMpd(FakeMpd):
    def command(self, command, *args):
        if command == "outputs":
            self.calls.append((command,))
            return ["outputid: 0", "outputname: PulseAudio",
                    "outputenabled: 1", "plugin: pulse",
                    "outputid: 1", "outputname: ALSA",
                    "outputenabled: 0", "plugin: alsa"]
        return super().command(command, *args)


class ProbeTests(unittest.TestCase):
    def test_parse_outputs_as_distinct_units(self):
        rows = parse_mpd_outputs(["outputid: 0", "outputname: Pulse",
                                  "outputenabled: 1", "outputid: 1",
                                  "outputname: ALSA", "outputenabled: 0"])
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0]["enabled"])
        self.assertFalse(rows[1]["enabled"])

    def test_mpd_candidate_is_not_certified_isolation(self):
        props = {"application.process.binary": "mpd",
                 "application.process.id": "305",
                 "application.name": "Music Player Daemon",
                 "media.name": "Playback"}
        rows = [{"index": 24, "properties": props, "mute": False, "sink": 0},
                {"index": 25, "properties": {**props,
                    "application.process.binary": "brave"}, "mute": False}]
        out = candidate_streams(rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["index"], 24)
        self.assertFalse(out[0]["isolated"])

    def test_two_mpd_streams_still_unverified(self):
        rows = [{"index": i, "properties": {"application.process.binary": "mpd"}}
                for i in [14, 15]]
        probe = MpdAudioEvidenceProbe(FakeAudioMpd(), sink_provider=lambda: rows)
        result = probe.observe()
        self.assertEqual(len(result["mpdCandidates"]), 2)
        self.assertFalse(result["playerVolumeAvailable"])
        self.assertFalse(result["playerCavaAvailable"])
        self.assertFalse(result["isolated"])

    def test_no_streams_or_mpd_output_does_not_fabricate_cava(self):
        result = MpdAudioEvidenceProbe(FakeAudioMpd(), sink_provider=lambda: []).observe()
        self.assertEqual(result["observedSinkInputCount"], 0)
        self.assertFalse(result["playerCavaAvailable"])
        self.assertEqual(len(result["mpdOutputs"]), 2)

    def test_other_browser_cannot_become_player_target(self):
        result = MpdAudioEvidenceProbe(FakeAudioMpd(), sink_provider=lambda: [{
          "index": 2, "properties": {"application.process.binary": "brave",
                                     "application.name": "Music"}}
        ]).observe()
        self.assertEqual(result["mpdCandidates"], [])
        self.assertFalse(result["isolated"])

    def test_unavailable_mpd_and_audio_are_reported_separately(self):
        class OfflineMpd(FakeAudioMpd):
            def command(self, command, *args):
                raise MediaBackendError("BACKEND_OFFLINE", "missing")
        def unavailable():
            raise MediaBackendError("AUDIO_EVIDENCE_UNAVAILABLE", "PipeWire absent")
        result = MpdAudioEvidenceProbe(OfflineMpd(), sink_provider=unavailable).observe()
        self.assertEqual(result["mpdError"]["code"], "BACKEND_OFFLINE")
        self.assertEqual(result["pipewireError"]["code"], "AUDIO_EVIDENCE_UNAVAILABLE")
        self.assertIsNone(result["observedSinkInputCount"])

    def test_pactl_command_only_reads_and_sanitizes_failure(self):
        class Completed:
            returncode = 0
            stdout = json.dumps([{"index": 5, "properties": {
                "application.process.binary": "mpd"}}])
        with patch("mpd_audio_probe.subprocess.run", return_value=Completed()) as run:
            rows = pipewire_sink_inputs()
            self.assertEqual(len(rows), 1)
            command = run.call_args.args[0]
            self.assertEqual(command, ["pactl", "-f", "json", "list", "sink-inputs"])
            self.assertNotIn("set", command)

    def test_bad_pactl_json_fails_closed(self):
        class Completed:
            returncode = 0
            stdout = '{"not":"list"}'
        with patch("mpd_audio_probe.subprocess.run", return_value=Completed()):
            with self.assertRaises(MediaBackendError):
                pipewire_sink_inputs()

    def test_controller_readonly_audio_api_does_not_mutate(self):
        fake = FakeAudioMpd()
        controller = MediaController(fake)
        controller.audio_probe = MpdAudioEvidenceProbe(fake, sink_provider=lambda: [])
        result = controller.request({"version": 1, "op": "audio_evidence"})
        self.assertTrue(result["ok"])
        self.assertFalse(result["result"]["playerCavaAvailable"])
        self.assertFalse(result["result"]["playerVolumeAvailable"])
        self.assertFalse(any(cmd[0] in ("playid", "setvol", "volume", "stop", "pause")
                             for cmd in fake.calls))

    def test_invalid_candidate_pid_cannot_raise_ownership_claim(self):
        rows = [{"index": 22, "properties": {
            "application.process.binary": "mpd",
            "application.process.id": "bad pid"}}]
        out = candidate_streams(rows)
        self.assertEqual(out[0]["processId"], "bad pid")
        self.assertFalse(out[0]["isolated"])


if __name__ == "__main__":
    unittest.main()
