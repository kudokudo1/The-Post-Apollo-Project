"""Linux actual custody supervisor tests; disposable files only."""
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "services/memory/memory_queue_custody.py"


class Custody(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir="/tmp")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.owner = self.root / "owner.py"

    def command(self, path=None, generation="1"):
        return [sys.executable, "-I", "-B", str(LAUNCHER), str(path or self.owner), generation]

    def test_exit_and_environment(self):
        self.owner.write_text("import os,sys\nassert 'PYTHONPATH' not in os.environ\nassert sys.argv[1:] == ['1']\nprint('exact child')\n")
        result = subprocess.run(self.command(), env=dict(os.environ,PYTHONPATH="/untrusted"),
                                capture_output=True,text=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),"exact child")
        self.owner.write_text("raise SystemExit(7)\n")
        self.assertNotEqual(subprocess.run(self.command(),timeout=5).returncode,0)
        self.owner.write_text("import os,signal\nos.kill(os.getpid(),signal.SIGKILL)\n")
        self.assertNotEqual(subprocess.run(self.command(),timeout=5).returncode,0)

    def test_path_and_generation_refusal(self):
        marker = self.root / "ran"
        self.owner.write_text("from pathlib import Path\nPath("+repr(str(marker))+").touch()\n")
        alias = self.root / "alias.py"
        alias.symlink_to(self.owner)
        for cmd in (self.command(alias),self.command(generation="01"),self.command(generation="0")):
            self.assertNotEqual(subprocess.run(cmd,timeout=5).returncode,0)
        self.owner.chmod(0o666)
        self.assertNotEqual(subprocess.run(self.command(),timeout=5).returncode,0)
        self.assertFalse(marker.exists())

    def test_supervisor_death_terminates_exact_child(self):
        identity = self.root / "pid"
        self.owner.write_text("import os,time\nfrom pathlib import Path\nPath("+repr(str(identity))+").write_text(str(os.getpid()))\nwhile True: time.sleep(.1)\n")
        proc = subprocess.Popen(self.command())
        fd = None
        try:
            deadline = time.monotonic()+5
            while not identity.exists() or not identity.read_text():
                self.assertIsNone(proc.poll())
                self.assertLess(time.monotonic(),deadline)
                time.sleep(.01)
            child = int(identity.read_text())
            fd = os.pidfd_open(child)
            self.assertEqual(int(Path("/proc",str(child),"stat").read_text().rsplit(")",1)[1].split()[1]),proc.pid)
            proc.kill()
            self.assertNotEqual(proc.wait(timeout=5),0)
            poll = select.poll();poll.register(fd,select.POLLIN)
            self.assertTrue(poll.poll(5000),"exact child survived supervisor death")
        finally:
            if fd is not None:
                try: signal.pidfd_send_signal(fd,signal.SIGKILL)
                except ProcessLookupError: pass
                os.close(fd)
            if proc.poll() is None: proc.kill()
            proc.wait(timeout=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
