#!/usr/bin/env python3
"""Synthetic Hospital streaming partial/final contract, no microphone or Vosk."""
from __future__ import annotations
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/hospital_streaming_vosk_probe.py"
spec = importlib.util.spec_from_file_location("hospital_streaming_probe", SOURCE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class FakeVosk:
    """One finite recognizer; returns provisional revisions before commit."""
    def __init__(self, steps, final=""):
        self.steps = list(steps)
        self.final = final
        self.consumed = 0

    def AcceptWaveform(self, pcm):
        assert len(pcm) == probe.READ_BYTES
        self.consumed += 1
        self.current = self.steps.pop(0)
        return self.current[0] == "final"

    def PartialResult(self):
        return json.dumps({"partial": self.current[1]})

    def Result(self):
        return json.dumps({"text": self.current[1]})

    def FinalResult(self):
        return json.dumps({"text": self.final})


class StreamingContractTests(unittest.TestCase):
    def test_revisable_preview_never_becomes_committed_automatically(self):
        reducer = probe.HypothesisReducer()
        events = []
        for words in ("why", "why do", "why did", "why did"):
            events.extend(reducer.hypothesis(json.dumps({"partial": words})))
        self.assertEqual([x["text"] for x in events],
                         ["why", "why do", "why did"])
        self.assertTrue(all(x["kind"] == "hypothesis" for x in events))
        self.assertEqual(reducer.committed_chars, 0)
        final = reducer.commit(json.dumps({
            "text": "why did my transcription stop early"}))
        self.assertEqual(len(final), 1)
        self.assertEqual(final[0]["kind"], "commit")
        self.assertTrue(final[0]["clear_provisional"])
        self.assertEqual(reducer.provisional, "")
        self.assertEqual(final[0]["revision"], 4)

    def test_fake_100ms_pcm_produces_live_revision_then_final_without_duplicates(self):
        steps = [
            ("partial", "one"),
            ("partial", "one too"),
            ("partial", "one two"),
            ("final", "one two"),
            ("partial", "why do"),
            ("partial", "why did"),
            ("final", "why did"),
        ]
        backend = FakeVosk(steps)
        events = []
        raw_pcm = io.BytesIO(bytes(probe.READ_BYTES * len(steps)))
        count = probe.process_pcm(raw_pcm, backend, events.append)
        self.assertEqual(count, probe.READ_BYTES * len(steps))
        speech = [e for e in events if e["kind"] in ("hypothesis", "commit")]
        self.assertEqual(
            [(e["kind"], e["text"]) for e in speech],
            [("hypothesis", "one"),
             ("hypothesis", "one too"),
             ("hypothesis", "one two"),
             ("commit", "one two"),
             ("hypothesis", "why do"),
             ("hypothesis", "why did"),
             ("commit", "why did")])
        self.assertEqual([e["revision"] for e in speech],
                         list(range(1, len(speech) + 1)))
        # Simulate correct UI behavior: replace provisional, append ONLY
        # committed words. Never append "one too" or the intermediate "do".
        committed = []
        provisional = ""
        for event in speech:
            if event["kind"] == "hypothesis":
                provisional = event["text"]
            else:
                self.assertTrue(event["clear_provisional"])
                committed.append(event["text"])
                provisional = ""
        self.assertEqual(committed, ["one two", "why did"])
        self.assertEqual(provisional, "")
        self.assertEqual(events[-1], {"kind": "done"})
        self.assertEqual(len([e for e in events if e["kind"] == "metrics"]), 1)

    def test_silent_or_empty_final_clears_preview_without_creating_text(self):
        bridge = probe.HypothesisReducer()
        self.assertEqual(
            bridge.hypothesis(json.dumps({"partial": "[SILENCE]"})), [])
        first = bridge.hypothesis(json.dumps({"partial": "maybe"}))
        self.assertEqual(first[0]["kind"], "hypothesis")
        clear = bridge.commit(json.dumps({"text": ""}))
        self.assertEqual(clear[0]["text"], "")
        self.assertEqual(clear[0]["kind"], "hypothesis")
        self.assertEqual(bridge.committed_chars, 0)
        self.assertEqual(bridge.commit(json.dumps({"text": ""})), [])

    def test_strict_shape_and_control_characters_fail_closed(self):
        bridge = probe.HypothesisReducer()
        for raw in ("{}", '{"partial":3}', "not json",
                    json.dumps({"partial": "bad\x00word"}),
                    json.dumps({"partial": "x" * 4001})):
            with self.assertRaises(ValueError):
                bridge.hypothesis(raw)
        with self.assertRaises(ValueError):
            bridge.commit(json.dumps({"text": ["wrong type"]}))
        with self.assertRaises(ValueError):
            probe.process_pcm(io.BytesIO(b"\x00"), FakeVosk([]), lambda e: None)
        with self.assertRaises(ValueError):
            probe.process_pcm(io.BytesIO(b""), FakeVosk([]), lambda e: None,
                              max_bytes=probe.MAX_AUDIO_BYTES + 2)

    def test_pcm_cap_never_spawns_more_model_calls(self):
        steps = [("partial", "one"), ("final", "one two")]
        backend = FakeVosk(steps, final="")
        events = []
        source = io.BytesIO(bytes(probe.READ_BYTES * 5))
        read = probe.process_pcm(source, backend, events.append,
                                 max_bytes=probe.READ_BYTES * 2)
        self.assertEqual(read, probe.READ_BYTES * 2)
        self.assertEqual(backend.consumed, 2)
        self.assertEqual(source.tell(), probe.READ_BYTES * 2)
        self.assertIn({"kind": "status", "code": "CAPTURE_DURATION_LIMIT"}, events)
        self.assertEqual([e["text"] for e in events if e["kind"] == "commit"],
                         ["one two"])

    def test_unconfigured_cli_refuses_without_loading_or_hardware(self):
        result = subprocess.run([sys.executable, str(SOURCE)],
                                input=b"", capture_output=True, timeout=4)
        self.assertEqual(result.returncode, 64)
        self.assertEqual(json.loads(result.stdout),
                         {"kind": "status", "code": "PROBE_DISABLED"})
        text = SOURCE.read_text()
        self.assertIn('parser.add_argument("--offline-probe"', text)
        self.assertIn("import vosk", text)
        self.assertIn("sys.stdin.buffer", text)
        for forbidden in ("pw-record", "sounddevice", "pyaudio",
                          "requests.post(", "urllib.request", "subprocess.Popen(",
                          "OPENAI_API_KEY"):
            self.assertNotIn(forbidden, text)
        for path in ("widgets/HospitalW.qml",
                     "services/hospital/HospitalLiveDictationService.qml"):
            self.assertNotIn("hospital_streaming_vosk_probe",
                             (ROOT / path).read_text())
        self.assertEqual(probe.READ_BYTES, 3200)
        self.assertEqual(probe.MAX_AUDIO_SECONDS, 25)
        self.assertEqual(probe.MAX_CORES, 2)
        self.assertEqual(probe.MAX_CPU_SECONDS, 12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
