#!/usr/bin/env python3
"""M11s four-case suite smoke/failure regression on synthetic temp directories."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "tests/tasks/fixtures"
GATE = ROOT / "services/projects/TaskJsonGateCandidateM11l.py"


def load(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


suite_tool=load(SCRIPTS/"TaskNativeFaultMatrixM11s.py","m11s_test_suite")
gate=load(GATE,"m11s_test_owner")


def updated(counter):
    return (json.dumps({
        "version":3, "nextId":2, "nextProjectId":1, "projects":[],
        "tasks":[{
            "id":"t1", "title":"M11M_TEST_"+str(counter), "done":False,
            "createdAtMs":1000, "updatedAtMs":1000+counter,
            "priority":"none", "description":"",
            "dueDate":None, "projectId":None
        }]
    },indent=2)+"\n").encode()


def fake_fileview_copy(source, data):
    staged=source.parent/"m11s-new-copy.json"
    fd=os.open(staged,os.O_EXCL|os.O_CREAT|os.O_WRONLY,0o600)
    with os.fdopen(fd,"wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(staged,source)


class NativeFaultSuiteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.parent=Path(self.temp.name)/"private-parent"
        self.parent.mkdir(mode=0o700)

    def tearDown(self):
        self.temp.cleanup()

    def suite(self):
        payload=suite_tool.prepare(self.parent)
        self.assertTrue(payload["syntheticOnly"])
        self.assertEqual(payload["runMode"],"MANUAL_QUICKSHELL_ONLY")
        self.assertEqual(set(payload["fixtures"]),set(suite_tool.CASES))
        root=Path(payload["suite"])
        self.assertEqual(root.stat().st_mode & 0o777,0o700)
        for name,filename in payload["fixtures"].items():
            p=Path(filename)
            self.assertEqual(p.name,"todo-copy.json")
            self.assertEqual(p.parent.name,"m11l-tasks-copy")
            self.assertEqual(json.loads(p.read_text())["tasks"][0]["title"],
                             "M11M_TEST_0")
            self.assertEqual(p.stat().st_mode & 0o777,0o600)
            self.assertFalse((p.parent/"gate-review.db").exists())
        return root

    def simulate(self,root):
        cases=suite_tool.CASES
        for fault,label in cases.items():
            source=root/label/"m11l-tasks-copy"/"todo-copy.json"
            with gate.CandidateOwner(source.parent,"m11s-fixture-owner-001",
                                     bootstrap=True) as owner:
                stage=owner.reserve("m11s-manual-fault-stage-001",updated(1))
                if fault!="AFTER_RESERVE":
                    fake_fileview_copy(source,updated(1))
                if fault=="AFTER_SETTLEMENT":
                    owner.verify(stage["stageId"],stage["epoch"])

    def test_fresh_suite_does_not_claim_native_success(self):
        root=self.suite()
        report=suite_tool.verify_suite(root)
        self.assertFalse(report["complete"])
        self.assertFalse(report["nativeCallbacksObservedByThisTool"])
        self.assertTrue(all(x["status"]=="NOT_RUN" for x in report["cases"]))
        self.assertNotIn(str(root),json.dumps(report))
        again=self.suite()
        self.assertNotEqual(again,root)
        self.assertEqual(len(list(self.parent.iterdir())),2)
        self.assertFalse((root/"after-reserve"/"m11l-tasks-copy"/
                          "gate-review.db").exists())

    def test_four_faults_and_recovery_are_read_only(self):
        root=self.suite()
        self.simulate(root)
        sources=[root/label/"m11l-tasks-copy"/"todo-copy.json"
                 for label in suite_tool.CASES.values()]
        prior=[source.read_bytes() for source in sources]
        with tempfile.TemporaryDirectory() as marker_dir:
            report=suite_tool.verify_suite(root)
            self.assertTrue(report["complete"],report)
            self.assertEqual(len(report["cases"]),4)
            self.assertTrue(all(x["status"]=="PASS" for x in report["cases"]))
            self.assertFalse(report["nativeCallbacksObservedByThisTool"])
            self.assertNotIn(str(root),json.dumps(report))
        self.assertEqual([source.read_bytes() for source in sources],prior)
        for fault,label in suite_tool.CASES.items():
            path=root/label/"m11l-tasks-copy"
            with gate.CandidateOwner(path,"m11s-fresh-reviewer-002") as owner:
                self.assertEqual(owner.state()["phase"],"RECOVERY_REVIEW")
        after=suite_tool.verify_suite(root,reopened=True)
        self.assertTrue(after["complete"])
        self.assertEqual(after["inspection"],"AFTER_EXISTING")
        self.assertTrue(all(x["phase"]=="RECOVERY_REVIEW"
                            for x in after["cases"]))

    def test_mismatched_fault_report_is_refused_or_failed(self):
        root=self.suite()
        self.simulate(root)
        case=root/"after-saved"/"m11l-tasks-copy"/"todo-copy.json"
        fake_fileview_copy(case,updated(9))
        report=suite_tool.verify_suite(root)
        failed={r["fault"]:r["status"] for r in report["cases"]}
        self.assertEqual(failed["AFTER_SAVED"],"FAIL")
        self.assertFalse(report["complete"])

    def test_nonprivate_or_wrong_prefix_is_denied(self):
        root=self.suite()
        self.parent.chmod(0o755)
        with self.assertRaises(ValueError):
            suite_tool.prepare(self.parent)
        self.parent.chmod(0o700)
        wrong=Path(self.temp.name)/"not-m11s"
        wrong.mkdir(mode=0o700)
        with self.assertRaises(ValueError):
            suite_tool.verify_suite(wrong)
        root.chmod(0o755)
        with self.assertRaises(ValueError):
            suite_tool.verify_suite(root)
        root.chmod(0o700)

    def test_cli_inspect_and_no_sensitive_report(self):
        root=self.suite()
        script=SCRIPTS/"TaskNativeFaultMatrixM11s.py"
        proc=subprocess.run([sys.executable,"-B","-I",str(script),
            "inspect","--suite-dir",str(root)],
            capture_output=True,text=True,timeout=10)
        self.assertEqual(proc.returncode,1,proc.stderr)
        self.assertIn("NOT_RUN",proc.stdout)
        self.assertNotIn(str(root),proc.stdout)
        self.assertNotIn("todo-copy.json",proc.stdout)
        bad=subprocess.run([sys.executable,"-B","-I",str(script),
            "inspect","--suite-dir",str(self.parent)],
            capture_output=True,text=True,timeout=10)
        self.assertEqual(bad.returncode,2)
        self.assertEqual(bad.stdout.strip(),"M11S_OPERATION_REFUSED")


if __name__=="__main__":
    unittest.main(verbosity=2)
