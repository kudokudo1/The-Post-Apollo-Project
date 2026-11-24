"""I5 UI integration: actual Core observer against disposable counter files."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import test_cgroup_observation_i5 as fixture

ROOT=Path(__file__).resolve().parents[2]
M=fixture.M


class ForestGroupObservationTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"),"Node unavailable")
    def test_actual_i5_report_projection(self):
        with tempfile.TemporaryDirectory() as root:
            g=fixture.ObserverTests().fixture(root)
            values=iter([1200,1400,1100,1300])
            def step(_):
                (g/"memory.current").write_text(str(next(values))+"\n")
            with patch.object(M,"ROOT",root),patch.object(M,"_mount",return_value=(b"1",b"0:1")),patch.object(M.time,"sleep",side_effect=step):
                report=M.observe("/group",samples=5,interval_ms=250)
            self.assertNotIn(root,str(report))
            self.assertEqual(report["charged_memory_sampled_max_bytes"],1400)
            self.assertEqual(report["charged_memory_sampled_increase_bytes"],376)
        js=r"""
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const p=vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1],"utf8"),p);
const d=JSON.parse(process.argv[2]),r=p.parse(JSON.stringify(d));
assert(r);
assert.strictEqual(r.charged_memory_first_bytes,1024);
assert.strictEqual(r.charged_memory_last_bytes,1300);
assert.strictEqual(r.charged_memory_sampled_max_bytes,1400);
assert.strictEqual(r.kernel_memory_peak_last_bytes_reported,2048);
assert.strictEqual(r.swap_last_bytes_reported,null);
assert.strictEqual(p.mib(null),"?");
assert.strictEqual(p.mib(0),"0.00 MiB");
assert.strictEqual(p.cpu(0),"0.000 CPU-s");
assert.strictEqual(p.limit(r),"UNLIMITED (LOCAL ONLY)");
assert.strictEqual(p.limit({...r,local_memory_max_status:"FINITE",local_memory_max_bytes:1048576}),"1.00 MiB");
for(const flag of p.FLAGS) assert.strictEqual(p.parse(JSON.stringify({...d,[flag]:true})),null,flag);
for(const [key,value] of [
 ["status","UNAVAILABLE"],["sample_count",2],["elapsed_ns",0],
 ["charged_memory_sampled_max_bytes",1000],["charged_memory_sampled_increase_bytes",1],
 ["swap_last_bytes_reported",-1],["cpu_usage_usec_delta",1.5],
 ["tasks_last_reported",Number.MAX_SAFE_INTEGER+1],["local_memory_max_status","FINITE"],
 ["safe_actions",["run"]],["descendants_included_by_kernel",false]
]) assert.strictEqual(p.parse(JSON.stringify({...d,[key]:value})),null,key);
assert.strictEqual(p.parse(JSON.stringify({...d,path:"/private"})),null);
const missing={...d};delete missing.swap_last_bytes_reported;
assert.strictEqual(p.parse(JSON.stringify(missing)),null);
for(const path of ["/","relative","/a/../b","/a//b","/a/","/a\n","/a\\b","/"+ "x".repeat(129)])
 assert.strictEqual(p.validGroup(path),false,path);
assert.strictEqual(p.validGroup("/system.slice/ollama.service"),true);
"""
        result=subprocess.run(["node","-e",js,str(ROOT/"services/forest/ForestGroupObservationPolicy.js"),json.dumps(report)],
                              capture_output=True,text=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_ui_only_explicit_group_observation(self):
        pane=(ROOT/"widgets/ForestGroupObservationView.qml").read_text()
        hardware=(ROOT/"widgets/ForestHardwareCapacityView.qml").read_text()
        self.assertIn("ForestGroupObservationView {",hardware)
        self.assertIn('Quickshell.shellPath("scripts/forest/cgroup_observation_i5.py")',pane)
        self.assertIn('"observe", "--cgroup", submittedGroup, "--samples", "5", "--interval-ms", "250"',pane)
        self.assertIn("onLeftClicked: pane.checkGroup()",pane)
        self.assertIn("!busy || !stdoutSeen || !stderrSeen || !exitSeen",pane)
        self.assertIn("!discard && visible && expanded && submittedGroup === groupInput.text",pane)
        self.assertIn("onTextChanged: pane.clearReport()",pane)
        self.assertIn("onVisibleChanged: if (!visible) clearReport()",pane)
        self.assertIn("onExpandedChanged: if (!expanded) clearReport()",pane)
        self.assertIn("if (busy) discard = true;",pane)
        self.assertIn("HISTORICAL COUNTERS, NOT MODEL MEMORY OR FREE CAPACITY",pane)
        self.assertEqual(pane.count("Process {"),1)
        for forbidden in ("Timer {","XMLHttpRequest","capacity.data","selectedModelName","/api/chat",
                          "systemctl","Component.onCompleted: checkGroup","FileView {"):
            self.assertNotIn(forbidden,pane)


if __name__=="__main__":
    unittest.main()
