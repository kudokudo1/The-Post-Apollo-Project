#!/usr/bin/env python3
"""Disposable tests of workflow orchestration, not a desktop performance test."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
import cpuplus_diagnostic_workflow as w


class WorkflowTests(unittest.TestCase):
    def test_validation_and_fixed_commands(self):
        plan={"durationSeconds":10,"instruments":[{"kind":"storage"},
            {"kind":"memory","intervalMs":5000},{"kind":"threads","intervalMs":500,"topCount":4}]}
        configs=w.validate(plan)
        self.assertEqual([c["kind"] for c in configs],["threads","memory","storage"])
        commands=w.commands(configs,Path("/data"),ROOT/"scripts",{"pid":123,"startTicks":456})
        for name in ("memory","threads"):
            self.assertEqual(commands[name][-3:],["--workshop-identity","123","456"])
        self.assertEqual(commands["storage"][-4:],["--data-dir","/data","--shell-dir",str(ROOT)])
        for bad in [
            dict(plan,durationSeconds=True),dict(plan,durationSeconds=31),
            dict(plan,instruments=[{"kind":"storage"},{"kind":"storage"}]),
            dict(plan,instruments=[{"kind":"storage"},{"kind":"memory","intervalMs":5000,"pid":123}]),
            dict(plan,instruments=[{"kind":"storage"},{"kind":"threads","intervalMs":100,"topCount":4}]),
            dict(plan,instruments=[{"kind":"inventory"},{"kind":"storage"}]),
            dict(plan,autoStart=True)]:
            with self.assertRaises(ValueError): w.validate(bad)
        with self.assertRaises(ValueError): w.decode('{"a":1,"a":2}')
        with self.assertRaises(ValueError): w.decode('{"a":NaN}')

    def test_all_ten_plan_and_hardware_clock_receipts(self):
        plan={"durationSeconds":10,"instruments":[
            {"kind":"threads","intervalMs":1000,"topCount":4},
            {"kind":"memory","intervalMs":10000},
            {"kind":"census","intervalMs":10000},{"kind":"storage"},
            {"kind":"stall","thresholdMs":350},
            *({"kind":kind,"intervalMs":1000} for kind in w.HARDWARE)]}
        configs=w.validate(plan)
        self.assertEqual(tuple(c["kind"] for c in configs),w.ORDER)
        commands=w.commands(configs,Path("/data"),ROOT/"scripts",{"pid":123,"startTicks":456})
        for config in configs[5:]:
            kind=config["kind"]
            self.assertEqual(commands[kind][-1],"--workflow-clock")
            rows=[{"schema":w.HARDWARE_SCHEMAS[kind],"event":kind,"sequence":i,
                   "elapsedMs":i*1000,"intervalMs":1000} for i in range(1,11)]
            terminal={"schema":w.HARDWARE_SCHEMAS[kind],"event":"complete","samples":10,
                      "observedMs":10000,"startedMonotonicMs":1000,"monotonicMs":11000,
                      "calibration":config}
            encode=lambda values: ("\n".join(json.dumps(r) for r in values)+"\n").encode("ascii")
            self.assertEqual(w.receipt(config,encode(rows+[terminal]),None)[1:],(1000,11000))
            for bad in (dict(terminal,monotonicMs=11001),dict(terminal,samples=9),dict(terminal,startedMonotonicMs=None)):
                with self.assertRaises(ValueError): w.receipt(config,encode(rows+[bad]),None)
        with self.assertRaises(ValueError): w.validate(dict(plan,durationSeconds=30))

    def test_ten_parallel_children_and_cleanup(self):
        # Ten actual child processes, disposable barrier, no host observers.
        with tempfile.TemporaryDirectory() as folder:
            script="""import pathlib,sys,time
root=pathlib.Path(sys.argv[1]); (root/sys.argv[2]).touch()
until=time.monotonic()+5
while len(list(root.iterdir()))!=10:
    if time.monotonic()>until: sys.exit(4)
    time.sleep(.01)
print(sys.argv[2])
"""
            commands={kind:[sys.executable,"-c",script,folder,kind] for kind in w.ORDER}
            _,_,reason,result=w.collect_children(commands,1,lambda:False)
            self.assertEqual(reason,"")
            self.assertEqual(len(result),10)
            self.assertTrue(all(row["exitCode"]==0 for row in result.values()))

    def test_parallel_and_cleanup(self):
        # Both children must arrive at the barrier before either can exit.
        # Sequential execution would fail this test without relying on speed.
        with tempfile.TemporaryDirectory() as folder:
            script="""import pathlib,sys,time
root=pathlib.Path(sys.argv[1]); own=sys.argv[2]; other=sys.argv[3]
(root/own).touch()
until=time.monotonic()+3
while not (root/other).exists():
    if time.monotonic()>until: sys.exit(4)
    time.sleep(.01)
print(own)
"""
            args={a:[sys.executable,"-c",script,folder,a,b] for a,b in [("a","b"),("b","a")]}
            start,end,reason,result=w.collect_children(args,1,lambda:False)
            self.assertEqual(reason,"")
            self.assertEqual([result[k]["exitCode"] for k in args],[0,0])
            self.assertEqual(result["a"]["raw"],b"a\n")
            self.assertLessEqual(start,result["a"]["launchMonotonicMs"])
            self.assertGreaterEqual(end,result["b"]["launchMonotonicMs"])
        args={"a":[sys.executable,"-c","import time; time.sleep(60)"],
              "b":[sys.executable,"-c","import time; time.sleep(60)"]}
        began=time.monotonic()
        _,_,reason,result=w.collect_children(args,10,lambda:time.monotonic()-began>.2)
        self.assertEqual(reason,"CANCELLED")
        self.assertTrue(all(x["exitCode"] is not None for x in result.values()))
        self.assertLess(time.monotonic()-began,5)

    def test_byte_limit_and_failure_isolation(self):
        args={"a":[sys.executable,"-c","print('x'*70000)"],
              "b":[sys.executable,"-c","print('ok')"]}
        _,_,_,result=w.collect_children(args,1,lambda:False)
        self.assertEqual(result["a"]["error"],"OUTPUT LIMIT")
        self.assertLessEqual(len(result["a"]["raw"]),w.CHILD_BYTES)
        self.assertEqual(result["b"]["exitCode"],0)
        self.assertEqual(result["b"]["raw"],b"ok\n")

    def test_receipts_and_overlap(self):
        p={"durationSeconds":5,"instruments":[{"kind":"threads","intervalMs":1000,"topCount":2},
                                              {"kind":"memory","intervalMs":5000}]}
        pin={"pid":123,"startTicks":456}
        configs=w.validate(p)
        tag={"workshopSchema":"post-apollo-thread-calibration-v1",**pin}
        thread=[dict(tag,event="start",durationSeconds=5,intervalMs=1000,topCount=2,monotonicMs=1000),
                dict(pin,event="threads",monotonicMs=6000),
                dict(tag,event="complete",samples=1,observedMs=5000,monotonicMs=6000)]
        memory=[dict(pin,event="memory",monotonicMs=1100),dict(pin,event="memory",monotonicMs=6100),
                dict(pin,event="complete",workshopSchema="post-apollo-observer-calibration-v1",
                     calibration=configs[1],samples=2,observedMs=5000,monotonicMs=6100)]
        encode=lambda rows: ("\n".join(json.dumps(r) for r in rows)+"\n").encode("ascii")
        self.assertEqual(w.receipt(configs[0],encode(thread),pin)[1:],(1000,6000))
        for bad in [[thread[0],dict(thread[1],startTicks=999),thread[2]],
                    [thread[0],dict(thread[1],monotonicMs=999),thread[2]],
                    [thread[0],thread[1],dict(thread[2],observedMs=4999)]]:
            with self.assertRaises(ValueError): w.receipt(configs[0],encode(bad),pin)
        children={name:dict(exitCode=0,launchMonotonicMs=900,error="",raw=encode(rows))
                  for name,rows in [("threads",thread),("memory",memory)]}
        with patch.object(w,"pin_quickshell",return_value=pin),patch.object(w,"collect_children",return_value=(900,6200,"",children)):
            result=w.run(p,Path("/data"),lambda:False)
        self.assertEqual(result["status"],"COLLECTED")
        self.assertEqual(result["overlapMs"],4900)
        self.assertEqual(result["pinnedQuickshell"],pin)

    def test_actual_storage_and_census(self):
        with tempfile.TemporaryDirectory() as folder:
            result=w.run({"durationSeconds":1,"instruments":[{"kind":"storage"},
                {"kind":"census","intervalMs":1000}]},Path(folder),lambda:False)
            self.assertEqual(result["status"],"COLLECTED",result)
            self.assertTrue(result["overlapMs"]>0)
            self.assertTrue(all(i["payloadBytes"]<=w.CHILD_BYTES for i in result["instruments"]))
            self.assertIsNone(result["pinnedQuickshell"])

    def test_configured_storage_workflow(self):
        plan={"durationSeconds":5,"instruments":[{"kind":"storage","sampleSeconds":2,"reportSeconds":4},
                                                 {"kind":"stall","thresholdMs":350}]}
        configs=w.validate(plan)
        self.assertEqual(configs[0]["sampleSeconds"],2)
        self.assertEqual(w.commands(configs,Path("/data"),ROOT/"scripts",None)["storage"][-4:],
                         ["--sample-seconds","2","--report-seconds","4"])
        with tempfile.TemporaryDirectory() as folder:
            result=w.run(plan,Path(folder),lambda:False)
            self.assertEqual(result["status"],"COLLECTED",result)
            item=result["instruments"][0]
            self.assertEqual(item["config"],configs[0])
            self.assertEqual([r["intervals"] for r in item["records"][:-1]],[2,3])
            self.assertEqual(item["records"][-1]["calibration"],configs[0])
            self.assertGreater(result["overlapMs"],0)
        for bad in ({"kind":"storage","sampleSeconds":2},
                    {"kind":"storage","sampleSeconds":2,"reportSeconds":3}):
            with self.assertRaises(ValueError):
                w.validate(dict(plan,instruments=[bad,plan["instruments"][1]]))

    def test_actual_storage_and_stall_witness(self):
        with tempfile.TemporaryDirectory() as folder:
            plan={"durationSeconds":5,"instruments":[{"kind":"storage"},{"kind":"stall","thresholdMs":350}]}
            config=w.validate(plan)
            self.assertEqual(w.commands(config,Path(folder),ROOT/"scripts",None)["stall"][-3:],
                             ["--workflow","--duration","5"])
            result=w.run(plan,Path(folder),lambda:False)
            self.assertEqual(result["status"],"COLLECTED",result)
            self.assertGreater(result["overlapMs"],0)
            item=result["instruments"][1]
            self.assertEqual(item["records"][0]["schema"],"post-apollo-stall-clock-v1")
            self.assertNotIn("ticks",item["records"][0])
            self.assertEqual(item["config"]["thresholdMs"],350)
            with self.assertRaises(ValueError):
                w.validate(dict(plan,instruments=[{"kind":"storage"},{"kind":"stall","thresholdMs":351}]))


if __name__=="__main__":
    unittest.main()
