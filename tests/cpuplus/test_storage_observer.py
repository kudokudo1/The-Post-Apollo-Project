import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
import cpuplus_storage_observer as probe


class StorageTests(unittest.TestCase):
    def test_metadata_only_and_state_transitions(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"file"
            uid = os.getuid()
            first = probe.observe(path,uid)
            self.assertEqual(first,("absent",None))
            row = probe.begin("fixture",first)
            path.write_text("private data")
            second = probe.observe(path,uid)
            probe.advance(row,first,second)
            self.assertEqual(row["changedIntervals"],1)
            self.assertEqual(row["finalBytes"],12)
            temp = Path(folder)/"replacement"
            temp.write_text("private data")
            os.replace(temp,path)
            third = probe.observe(path,uid)
            probe.advance(row,second,third)
            self.assertEqual(row["replacementIntervals"],1)
            self.assertEqual(row["changedIntervals"],2)
            self.assertEqual(row["comparableIntervals"],2)
            probe.advance(row,third,third)
            self.assertEqual(row["changedIntervals"],2)

    def test_symlink_fifo_and_wrong_owner_unavailable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            file = root/"file"
            file.write_text("secret")
            (root/"link").symlink_to(file)
            os.mkfifo(root/"fifo")
            for path in (root/"link",root/"fifo"):
                self.assertEqual(probe.observe(path,os.getuid()),("unavailable",None))
            self.assertEqual(probe.observe(file,os.getuid()+1),("unavailable",None))
            row = probe.begin("fixture",("unavailable",None))
            probe.advance(row,("unavailable",None),("absent",None))
            self.assertEqual(row["unavailableIntervals"],1)
            self.assertEqual(row["changedIntervals"],0)

    def test_native_metadata_capture(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/"notifications-history.json").write_text("secret payload")
            env = dict(os.environ,XDG_DATA_HOME=folder)
            p = subprocess.run([sys.executable,"-B",str(ROOT/"scripts/cpuplus_storage_observer.py"),
                                "--data-dir",folder,"--shell-dir",folder,"--duration","1"],
                               env=env,capture_output=True,text=True,timeout=10)
            self.assertEqual(p.returncode,0,p.stderr)
            rows = [json.loads(line) for line in p.stdout.splitlines()]
            self.assertEqual(rows[-1],{"schema":probe.SCHEMA,"event":"complete","samples":1})
            self.assertEqual(len(rows[0]["rows"]),len(probe.TARGETS))
            self.assertEqual(rows[0]["rows"][0]["finalBytes"],14)
            self.assertNotIn("secret payload",p.stdout)
            self.assertNotIn(folder,p.stdout)

    def test_configured_metadata_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            p=subprocess.run([sys.executable,"-B",str(ROOT/"scripts/cpuplus_storage_observer.py"),
                "--workshop","--data-dir",folder,"--shell-dir",folder,"--duration","1"],
                env=dict(os.environ,XDG_DATA_HOME=folder),capture_output=True,text=True,timeout=10)
            self.assertEqual(p.returncode,0,p.stderr)
            rows=[json.loads(line) for line in p.stdout.splitlines()]
            self.assertEqual(rows[-1]["calibration"],{"kind":"storage","durationSeconds":1})
            self.assertEqual(rows[-1]["observedMs"],rows[0]["elapsedMs"])
            self.assertEqual(rows[-1]["samples"],1)
            self.assertLessEqual(len(p.stdout.encode("ascii")),65536)


if __name__ == "__main__":
    unittest.main()
