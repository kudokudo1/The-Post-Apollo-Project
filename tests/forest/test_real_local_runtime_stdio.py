"""Real held Runtime subprocess, no mock provider or native authorization."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import tempfile
import select
import time

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts/forest"
sys.path.insert(0, str(SCRIPTS))
from real_local_runtime_stdio import decode, Refusal, INPUT_CAP
from first_light_trial_host import MODEL, PROMPT


def frame(seq, op, data):
    return json.dumps(dict(seq=seq, op=op, data=data),
                      ensure_ascii=True, separators=(",", ":")).encode() + b"\n"


class RealStdioTests(unittest.TestCase):
    def test_codec_refuses_before_dispatch(self):
        for raw in (
            b'{"seq":1,"seq":1,"op":"OBSERVE","data":{"epoch":1}}\n',
            b'{"seq":1,"op":"OBSERVE","data":{"epoch":true}}\n',
            b'{"seq":1,"op":"OBSERVE","data":{"epoch":1e999}}\n',
            b'{"seq":1,"op":"OBSERVE","data":{"epoch":1,"extra":1}}\n',
            frame(2,"OBSERVE",{"epoch":1}),
            b"[" * 12 + b"]" * 12 + b"\n",
            b"x" * INPUT_CAP + b"\n",
            frame(1,"SUBMIT_BEGIN",dict(epoch=1,model=MODEL,prompt="☀"*1366)),
        ):
            with self.subTest(raw=raw[:40]), self.assertRaises(Refusal):
                decode(raw,1)
        prompt = "Public café ☀"
        self.assertEqual(decode(frame(1,"SUBMIT_BEGIN",dict(
            epoch=1, model=MODEL, prompt=prompt)),1)[1]["prompt"],prompt)

    def test_worker_rejected_commands_preserve_attachment(self):
        # Command-state translation only; no provider or native admission.
        from unittest.mock import Mock
        from real_local_runtime_stdio import Worker
        worker = Worker.__new__(Worker)
        worker.bridge = Mock()
        worker.kind = worker.pending = None
        worker.observed_epoch = 3
        worker.attached = True
        corr = {"token": "a" * 32}
        worker.bridge.observe.return_value = False
        self.assertFalse(worker.command("OBSERVE", {"epoch": 2}))
        self.assertTrue(worker.attached)
        worker.bridge.observe.return_value = True
        self.assertTrue(worker.command("OBSERVE", {"epoch": 3}))
        self.assertTrue(worker.attached)
        worker.bridge.attach.return_value = False
        self.assertFalse(worker.command("ATTACH", {"correlation": corr}))
        self.assertTrue(worker.attached)
        worker.bridge.withdraw.return_value = False
        self.assertFalse(worker.command("WITHDRAW", {"correlation": corr}))
        self.assertTrue(worker.attached)
        self.assertTrue(worker.command("OBSERVE", {"epoch": 4}))
        self.assertFalse(worker.attached)
        self.assertEqual(worker.observed_epoch, 4)
        worker.bridge.attach.return_value = True
        self.assertTrue(worker.command("ATTACH", {"correlation": corr}))
        worker.bridge.withdraw.return_value = True
        self.assertTrue(worker.command("WITHDRAW", {"correlation": corr}))
        self.assertFalse(worker.attached)
        self.assertIsNone(worker.observed_epoch)

    def launch(self, home, *args):
        return subprocess.Popen([sys.executable,"-I","-B","-u",
            str(SCRIPTS/"real_local_runtime_stdio.py"),*args],
            cwd=home, env={"HOME":home,"TMPDIR":home,"LANG":"C.UTF-8"},
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_actual_child_held_submit_and_clean_close(self):
        with tempfile.TemporaryDirectory() as home, self.launch(home) as p:
            seq = 0
            def command(op, **data):
                nonlocal seq
                seq += 1
                p.stdin.write(frame(seq,op,data)); p.stdin.flush()
                self.assertTrue(select.select([p.stdout],[],[],5)[0])
                reply = json.loads(p.stdout.readline(100001))
                self.assertEqual(reply["seq"],seq)
                return reply["result"]
            try:
                self.assertTrue(command("OBSERVE",epoch=1))
                self.assertEqual(command("SUBMIT_BEGIN",epoch=1,model=MODEL,prompt=PROMPT),"PENDING")
                end = time.monotonic()+4
                while True:
                    result = command("SUBMIT_POLL")
                    if result != "PENDING": break
                    self.assertLess(time.monotonic(),end)
                    time.sleep(.02)
                self.assertEqual(result,"HELD")
                corr = {"token":"a"*32}
                self.assertFalse(command("ATTACH",correlation=corr))
                self.assertIsNone(command("TAKE",correlation=corr))
                self.assertFalse(command("STOP",correlation=corr))
                self.assertTrue(command("OBSERVE",epoch=2))
                self.assertEqual(command("CLOSE"),"UNKNOWN_HOLD")
                self.assertEqual(p.wait(timeout=5),0)
                self.assertEqual(p.stdout.read(),b"")
                self.assertEqual(p.stderr.read(),b"")
                self.assertEqual(os.listdir(home),[])
            finally:
                if p.poll() is None: p.kill(); p.wait(timeout=5)

    def test_malformed_and_extra_argv_fail_closed(self):
        with tempfile.TemporaryDirectory() as home:
            for args, raw in [((), frame(2,"OBSERVE",{"epoch":1})),
                              (("endpoint",), b""),
                              ((), b"x"*(INPUT_CAP+1)+b"\n")]:
                with self.launch(home,*args) as p:
                    out, err = p.communicate(raw,timeout=5)
                    self.assertEqual((p.returncode,out,err),(2,b"",b""))


if __name__ == "__main__":
    unittest.main()
