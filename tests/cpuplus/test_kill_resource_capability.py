#!/usr/bin/env python3
"""Hosted disposable-process-only K8c contracts, no host modification."""
import importlib.util
import json
import os
import resource
import pathlib
import subprocess
import sys
import unittest
from unittest import mock

HERE=pathlib.Path(__file__).resolve()
SOURCE=HERE.parents[2]/"services"/"kill"/"resource_capability_probe.py"
spec=importlib.util.spec_from_file_location("resource_capability_probe",SOURCE)
cap=importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)

class ProbeTest(unittest.TestCase):
    def test_invalid_and_stale_never_probe_resources(self):
        self.assertEqual(cap.observe(0,1,"x")["state"],"invalid_target")
        self.assertEqual(cap.observe(10,0,"x")["state"],"invalid_target")
        with mock.patch.object(cap,"birth_identity",return_value=("observed",("other",7))):
            self.assertEqual(cap.observe(10,7,"target")["state"],"stale_or_unobservable")

    def test_cgroup_escape_and_v1_are_not_supported(self):
        with mock.patch.object(cap,"bounded_read",return_value=("observed","0::/../../tmp\n")):
            with mock.patch.object(cap,"source_observation",return_value="observed"):
                self.assertEqual(cap.cgroup_directory(123)[0],"invalid")
        with mock.patch.object(cap,"bounded_read",return_value=("observed","2:cpu:/a\n")):
            self.assertEqual(cap.cgroup_directory(123)[0],"not_cgroup_v2")

    def test_disposable_child_does_not_attempt_mutation(self):
        child=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"])
        try:
            state,identity=cap.birth_identity(child.pid)
            self.assertEqual(state,"observed")
            name,birth=identity
            result=cap.observe(child.pid,birth,name)
            self.assertEqual(result["state"],"observed")
            evidence=result["resources"]["cpu"]["priority_evidence"]
            self.assertEqual(evidence["scope"],"leader_thread")
            self.assertEqual(evidence["nice"],os.getpriority(os.PRIO_PROCESS,child.pid))
            self.assertEqual(evidence["scheduler"],os.sched_getscheduler(child.pid))
            self.assertEqual(evidence["mutation_permission"],"not_verified")
            self.assertEqual(evidence["restoration_permission"],"not_verified")
            self.assertEqual(evidence["rlimit_nice_soft"],resource.prlimit(child.pid,resource.RLIMIT_NICE)[0])
            self.assertEqual(set(result["resources"]),set(cap.CATEGORIES))
            for value in result["resources"].values():
                self.assertEqual(value["actuation"],"not_verified")
                self.assertEqual(value["permission_to_change"],"not_verified")
            self.assertEqual(result["resources"]["network"]["observation"]["per_process_attribution"],"not_verified")
            self.assertEqual(cap.observe(child.pid,birth+1,name)["state"],"stale_or_unobservable")
            p=subprocess.run([sys.executable,str(SOURCE),"--pid",str(child.pid),
                "--start-ticks",str(birth),"--comm",name],capture_output=True,text=True,timeout=5)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertEqual(json.loads(p.stdout)["state"],"observed")
            self.assertIsNone(child.poll())
        finally:
            child.terminate()
            child.wait(timeout=5)

    def test_priority_permission_failure_is_not_a_zero_nice(self):
        with mock.patch.object(cap.os,"getpriority",side_effect=PermissionError()):
            evidence=cap.priority_evidence(123)
        self.assertIsNone(evidence["nice"])
        self.assertEqual(evidence["read_state"],"permission_denied")
        self.assertEqual(evidence["restoration_permission"],"not_verified")

    def test_stale_during_observation_discards_evidence(self):
        with mock.patch.object(cap,"birth_identity",side_effect=[
                ("observed",("x",1)),("observed",("x",2))]):
            with mock.patch.object(cap,"source_observation",return_value="missing"):
                with mock.patch.object(cap,"cgroup_directory",return_value=("missing",None)):
                    with mock.patch.object(cap,"drm_fdinfo",return_value="not_observed"):
                        self.assertEqual(cap.observe(99,1,"x")["state"],"stale_during_observation")

if __name__=="__main__":
    unittest.main()
