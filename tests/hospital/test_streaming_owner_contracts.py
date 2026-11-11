#!/usr/bin/env python3
"""Hospital streaming handoff fake-process contracts. No mic/model packages."""
from __future__ import annotations

import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]
OWNER = ROOT / "scripts/hospital_streaming_vosk_owner.py"
PROBE = ROOT / "scripts/hospital_streaming_vosk_probe.py"
LIVE = ROOT / "services/hospital/HospitalLiveDictationService.qml"
MANAGER = ROOT / "widgets/HospitalWorkforceManagerView.qml"
HOST = ROOT / "widgets/HospitalW.qml"

spec = importlib.util.spec_from_file_location("hospital_stream_owner", OWNER)
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)


def build_fakes(root: Path, *, malformed: bool = False):
    decoder = root / "fake_decoder.py"
    decoder.write_text(textwrap.dedent(r"""
        import json, os, sys
        from pathlib import Path
        Path(sys.argv[1]).write_text(str(os.getpid()))
        count = 0
        revision = 0
        for frame in iter(lambda: sys.stdin.buffer.read(3200), b""):
            count += 1
            if count == 1:
                revision += 1
                print(json.dumps({"kind":"hypothesis","text":"why do",
                                  "revision":revision,
                                  "clear_provisional":False}), flush=True)
            if count == 2:
                revision += 1
                print(json.dumps({"kind":"hypothesis","text":"why did",
                                  "revision":revision,
                                  "clear_provisional":False}), flush=True)
            if count == 4:
                revision += 1
                print(json.dumps({"kind":"commit","text":"why did",
                                  "revision":revision,
                                  "clear_provisional":True}), flush=True)
        print(json.dumps({"kind":"metrics","first_hypothesis_ms":10,
                          "first_commit_ms":25,"pcm_bytes":count*3200}),
              flush=True)
        print(json.dumps({"kind":"done"}), flush=True)
    """).lstrip())
    if malformed:
        decoder.write_text(textwrap.dedent(r"""
            import sys, os
            from pathlib import Path
            Path(sys.argv[1]).write_text(str(os.getpid()))
            sys.stdout.write('{"kind":"commit","text":"bad","revision":0}\n')
            sys.stdout.flush()
            sys.stdin.buffer.read()
        """).lstrip())
    recorder = root / "fake_recorder.py"
    recorder.write_text(textwrap.dedent(r"""
        import os, sys, time
        from pathlib import Path
        Path(sys.argv[1]).write_text(str(os.getpid()))
        sample = (1700).to_bytes(2, "little", signed=True) * 1600
        for _ in range(8):
            sys.stdout.buffer.write(sample)
            sys.stdout.buffer.flush()
            time.sleep(0.025)
    """).lstrip())
    return ([sys.executable, str(recorder), str(root / "rec.pid")],
            [sys.executable, str(decoder), str(root / "dec.pid")])


class OwnedStreamingTests(unittest.TestCase):
    def test_finite_single_recorder_one_child_provisional_and_final(self):
        with tempfile.TemporaryDirectory(prefix="hospital-stream-owner-") as tmp:
            folder = Path(tmp)
            rec, dec = build_fakes(folder)
            output = io.StringIO()
            result = owner.run_trial(tmp, recorder_command=rec,
                                     decoder_command=dec,
                                     commands=io.BytesIO(b""), output=output)
            self.assertEqual(result, 0, output.getvalue())
            packets = [json.loads(line) for line in output.getvalue().splitlines()]
            self.assertIn({"kind":"stage","detail":"STREAM_RECORDER_STARTED"}, packets)
            self.assertIn({"kind":"stage","detail":"CAPTURE_SOURCE_ENDED"}, packets)
            self.assertIn({"kind":"stage","detail":"CAPTURE_STOPPED"}, packets)
            speech = [(p["kind"], p["text"]) for p in packets
                      if p["kind"] in ("hypothesis", "commit")]
            self.assertEqual(speech, [
                ("hypothesis", "why do"), ("hypothesis", "why did"),
                ("commit", "why did")])
            self.assertEqual(sum(p["kind"]=="done" for p in packets), 1)
            self.assertEqual(sum(p["kind"]=="metrics" for p in packets), 1)
            for name in ("rec.pid", "dec.pid"):
                with self.assertRaises(ProcessLookupError):
                    os.kill(int((folder / name).read_text()), 0)

    def test_stop_and_cancel_both_terminate_owned_children(self):
        for command, code in ((b"STOP\n", 0), (b"CANCEL\n", 130)):
            with self.subTest(command=command):
                with tempfile.TemporaryDirectory(
                        prefix="hospital-stream-stop-") as tmp:
                    folder=Path(tmp)
                    rec, dec=build_fakes(folder)
                    output=io.StringIO()
                    result=owner.run_trial(tmp, recorder_command=rec,
                                           decoder_command=dec,
                                           commands=io.BytesIO(command),
                                           output=output)
                    self.assertEqual(result, code, output.getvalue())
                    events=[json.loads(v) for v in output.getvalue().splitlines()]
                    if code == 0:
                        self.assertIn({"kind":"stage",
                                       "detail":"CAPTURE_USER_STOP"}, events)
                        self.assertIn({"kind":"done"}, events)
                    else:
                        self.assertNotIn({"kind":"done"}, events)
                    for name in ("rec.pid","dec.pid"):
                        if (folder / name).exists():
                            with self.assertRaises(ProcessLookupError):
                                os.kill(int((folder / name).read_text()), 0)

    def test_invalid_decoder_message_fails_closed_and_reaps_children(self):
        with tempfile.TemporaryDirectory(prefix="hospital-stream-bad-") as tmp:
            root=Path(tmp)
            rec, dec=build_fakes(root,malformed=True)
            output=io.StringIO()
            result=owner.run_trial(tmp, recorder_command=rec,
                                   decoder_command=dec,
                                   commands=io.BytesIO(b""), output=output)
            self.assertEqual(result,70,output.getvalue())
            self.assertIn('STREAMING_TRIAL_FAILED',output.getvalue())
            self.assertNotIn('"text":"bad"',output.getvalue())
            for name in ("rec.pid","dec.pid"):
                if (root / name).exists():
                    with self.assertRaises(ProcessLookupError):
                        os.kill(int((root / name).read_text()),0)

    def test_strict_child_packets_and_explicit_cli_hold(self):
        self.assertFalse(owner.safe_decoder_packet({
            "kind":"commit","text":"guess","revision":0,
            "clear_provisional":True}))
        self.assertFalse(owner.safe_decoder_packet({
            "kind":"hypothesis","text":"x","revision":1,
            "clear_provisional":True}))
        self.assertFalse(owner.safe_decoder_packet({"kind":"save","text":"hello"}))
        self.assertFalse(owner.safe_decoder_packet({"kind":"done","extra":True}))
        self.assertFalse(owner.safe_decoder_packet({
            "kind":"metrics","pcm_bytes":2,"first_hypothesis_ms":False,
            "first_commit_ms":10}))
        self.assertTrue(owner.safe_decoder_packet({
            "kind":"commit","text":"one two","revision":1,
            "clear_provisional":True}))
        run=subprocess.run([sys.executable,str(OWNER)],input=b"",
                           capture_output=True,timeout=3)
        self.assertEqual(run.returncode,64)
        self.assertIn("STREAMING_TRIAL_HOLD",run.stdout.decode())
        self.assertEqual(owner.PCM_BUDGET,800000)
        self.assertEqual(owner.WALL_BUDGET,45)
        self.assertEqual(owner.MODEL_FINISH_SECONDS,5)

    def test_gated_single_host_process_and_surgery_preview_path(self):
        host=HOST.read_text()
        live=LIVE.read_text()
        manager=MANAGER.read_text()
        self.assertIn("property bool streamingTrialAllowed: false",live)
        self.assertIn('property string streamingModelDir: ""',live)
        self.assertIn("streamingRequested = requestedDecoderMode",live)
        self.assertIn('streamingOwnerScript, "--streaming-trial"',live)
        self.assertIn("if (!streamingRequested) {",live)
        self.assertIn("liveProcess.exec(command);",live)
        self.assertEqual(live.count("id: liveProcess"),1)
        self.assertIn('signal streamingPacketReady(var packet)',live)
        self.assertIn("streamingPacketReady(data);",live)
        self.assertIn("root.streamingFinished();",live)
        self.assertIn("streamingPreviewState.active",manager)
        self.assertIn('svc.startRecording("STREAMING")',manager)
        self.assertIn('root.beginStreamingPreview(key, token)',manager)
        self.assertIn("root.acceptStreamingPreview(state.token, packet)",manager)
        self.assertIn("root.speechInputService.cancel();",manager)
        self.assertIn('label: "VOICE // STREAMING MODEL TRIAL"',manager)
        self.assertIn("root.speechInputService.streamingTrialAllowed",manager)
        self.assertIn("root.speechInputService.streamingModelDir.trim()",manager)
        self.assertIn("workforceSpeechInputService",host)
        self.assertNotIn("streamingTrialAllowed: true",host)
        self.assertNotIn("streamingModelDir:",host)
        self.assertNotIn("hospital_streaming_vosk_owner",host)
        self.assertIn("MAX_WALL_SECONDS = 45",PROBE.read_text())
        for dangerous in ("OPENAI_API_KEY","requests.post(","urllib.request",
                          "saveRoom(","activateAssignment(","session-attach"):
            self.assertNotIn(dangerous,OWNER.read_text())


if __name__=="__main__":
    unittest.main(verbosity=2)
