#!/usr/bin/env python3
"""M11r read-only synthetic fault matrix; never inspects live TASKS."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
INSPECTOR = ROOT / "tests/tasks/fixtures/TaskNativeFaultInspectorM11r.py"
HOST = ROOT / "services/projects/TaskJsonGateCandidateM11l.py"


def module(filename, name):
    spec = importlib.util.spec_from_file_location(name, filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


owner = module(HOST, "m11r_test_owner")
audit = module(INSPECTOR, "m11r_native_inspector")


def fixture(revision):
    return (json.dumps({
        "version":3, "nextId":2, "nextProjectId":1,
        "projects":[], "tasks":[{
            "id":"t1", "title":"M11M_TEST_"+str(revision),
            "done":False, "createdAtMs":1000,
            "updatedAtMs":1000+revision, "priority":"none",
            "description":"", "dueDate":None, "projectId":None
        }]
    }, indent=2) + "\n").encode()


def private_file(path, payload):
    fd = os.open(path, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def simulated_fileview_replace(path, payload):
    tmp = path.parent / "m11r-fileview-atomic.json"
    private_file(tmp, payload)
    os.replace(tmp, path)


class ReadOnlyFaultInspection(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name) / "m11l-tasks-copy"
        self.folder.mkdir(mode=0o700)
        self.file = self.folder / "todo-copy.json"
        private_file(self.file, fixture(0))

    def tearDown(self):
        self.temp.cleanup()

    def run_fault(self, fault):
        with owner.CandidateOwner(self.folder, "m11r-test-owner-001",
                                  bootstrap=True) as host:
            if fault != "AFTER_RESERVE":
                pass
            ticket = host.reserve("m11r-synthetic-stage-001",fixture(1))
            if fault != "AFTER_RESERVE":
                simulated_fileview_replace(self.file,fixture(1))
            if fault == "AFTER_SETTLEMENT":
                host.verify(ticket["stageId"], ticket["epoch"])
        prior = audit.inspect(self.file, fault)
        self.assertTrue(prior["expectationMet"],prior)
        self.assertEqual(prior["phase"],"JSON_ACTIVE")
        self.assertFalse(prior["productionWriterAuthorized"])
        self.assertFalse(prior["nativeCallbackTraceObserved"])
        self.assertNotIn("stageId",prior)
        self.assertNotIn("sourcePath",prior)
        with owner.CandidateOwner(self.folder, "m11r-review-owner-002") as later:
            self.assertEqual(later.state()["phase"],"RECOVERY_REVIEW")
            self.assertFalse(later.state()["liveWriterAuthorized"])
        after = audit.inspect(self.file,fault,reopened=True)
        self.assertTrue(after["expectationMet"],after)
        self.assertEqual(after["epoch"],prior["epoch"]+1)

    def test_all_four_disposable_fault_expectations(self):
        for fault in sorted(audit.FAULTS):
            with self.subTest(fault=fault):
                # Each case has an independent journal and private copy.
                with tempfile.TemporaryDirectory() as root:
                    folder = Path(root)/"m11l-tasks-copy"
                    folder.mkdir(mode=0o700)
                    self.folder = folder
                    self.file = folder/"todo-copy.json"
                    private_file(self.file,fixture(0))
                    self.run_fault(fault)

    def test_corrupt_file_after_reserved_stage_is_not_accepted(self):
        with owner.CandidateOwner(self.folder, "m11r-test-owner-001",
                                  bootstrap=True) as host:
            host.reserve("m11r-test-stage-corrupt-001",fixture(1))
        simulated_fileview_replace(self.file,fixture(9))
        report = audit.inspect(self.file,"AFTER_SAVED")
        self.assertFalse(report["expectationMet"])
        self.assertFalse(report["sourceHashMatchesJournal"])

    def test_no_private_path_or_user_data_in_output(self):
        with owner.CandidateOwner(self.folder, "m11r-test-owner-001",
                                  bootstrap=True) as host:
            host.reserve("m11r-test-stage-path-001",fixture(1))
        cmd = [sys.executable,"-B","-I",str(INSPECTOR),
               "--test-file",str(self.file),"--fault","AFTER_RESERVE"]
        proc = subprocess.run(cmd,capture_output=True,text=True,timeout=10)
        self.assertEqual(proc.returncode,0,proc.stderr)
        report = json.loads(proc.stdout)
        self.assertEqual(report["scope"],"SYNTHETIC_COPY_ONLY")
        self.assertNotIn(str(self.folder),proc.stdout)
        self.assertNotIn("m11r-test-stage-path-001",proc.stdout)
        self.assertNotIn("tasks",proc.stdout.lower())

    def test_nonfixture_path_refused(self):
        outside = Path(self.temp.name)/"userlike.json"
        private_file(outside,fixture(0))
        with self.assertRaises(ValueError):
            audit.inspect(outside,"AFTER_RESERVE")
        proc=subprocess.run([
            sys.executable,"-B","-I",str(INSPECTOR),
            "--test-file",str(outside),"--fault","AFTER_RESERVE"
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(proc.returncode,2)
        self.assertEqual(proc.stdout.strip(),"M11R_INSPECTION_REFUSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
