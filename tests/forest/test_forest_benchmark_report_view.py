"""ForestW P2B report review: actual backend output from fake HTTP only."""
from pathlib import Path
import json
import shutil
import subprocess
import unittest
import test_performance_benchmark_p2b as fixture

ROOT=Path(__file__).resolve().parents[2]


class ForestBenchmarkReportsTests(unittest.TestCase):
    def test_ui_has_no_benchmark_execution_path(self):
        view=(ROOT/"widgets/ForestW.qml").read_text()
        pane=(ROOT/"widgets/ForestBenchmarkReportView.qml").read_text()
        self.assertIn("visible: root.modelPopupOpen && root.benchmarkReportsOpen",view)
        self.assertIn("visible: !root.autoPreviewOpen && !root.benchmarkReportsOpen",view)
        self.assertIn("onAutoPreviewOpenChanged: if (autoPreviewOpen) benchmarkReportsOpen = false",view)
        self.assertIn("onBenchmarkReportsOpenChanged: if (benchmarkReportsOpen) autoPreviewOpen = false",view)
        self.assertIn("IMPORTED REPORTS // UNVERIFIED",view)
        self.assertIn("Reports.parseReport(reportInput.text)",pane)
        self.assertIn("maximumLength: 8193",pane)
        self.assertIn("onVisibleChanged: if (!visible) clearReports()",pane)
        self.assertIn("NO QUALITY SCORE, HARDWARE PROOF, OR SPEED WINNER",pane)
        for forbidden in ("Process {","Timer {","XMLHttpRequest","FileView {",
                          "performance_benchmark_p2b.py","forestPromptInput",
                          "chooseModelForm(","equipLocalModel(","saveModelPreferences("):
            self.assertNotIn(forbidden,pane)
        self.assertIn("readonly property bool chatHostTrusted: false",view)
        self.assertIn("readonly property bool voiceHostTrusted: false",view)

    @unittest.skipUnless(shutil.which("node"),"Node unavailable")
    def test_actual_backend_metadata_and_negative_matrix(self):
        # Reuse the existing disposable fake-loopback producer, not invented JSON.
        cls=fixture.BenchmarkP2BTests
        cls.setUpClass()
        case=cls("test_warm_metadata_only_and_one_post")
        try:
            case.setUp()
            warm=case.run_one()
            fixture.Handler.ps_rows=[[],[fixture.resident()]]
            fixture.Handler.ps_calls=0
            cold=case.run_one(scenario="cold")
            self.assertEqual(len(fixture.Handler.post_payloads),2)
        finally:
            case.doCleanups()
            cls.tearDownClass()
        js=r"""
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const p=vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1],"utf8"),p);
const a=p.parseReport(process.argv[2]),b=p.parseReport(process.argv[3]);
assert(a && b);
assert.strictEqual(a.scenario,"warm");
assert.strictEqual(b.scenario,"cold");
assert.strictEqual(a.provider_generated_tokens_per_second,10);
assert.strictEqual(a.provider_prompt_cached_count,null);
assert.strictEqual(p.metric(null,"ms"),"?");
assert.strictEqual(p.comparison(a,b),"DIFFERENT COLD/WARM SCENARIOS");
assert(p.comparison(a,a).includes("EQUIVALENCE UNKNOWN"));
assert(p.comparison(a,{...a,ollama_version:"1.0"}).includes("DIFFERENT OLLAMA VERSIONS"));
assert.strictEqual(p.comparison(a,null),"TWO COMPLETE REPORTS REQUIRED");
for(const [k,v] of [
 ["status","REFUSED"],["permission_granted",true],["production_authority",true],
 ["model","../bad"],["requested_thinking",true],["requested_context_tokens",4096],
 ["first_visible_content_ms",-1],["headers_latency_ms",120001],
 ["client_complete_ms",-1],["provider_eval_count",1.5],
 ["provider_prompt_cached_count",-1],["before_resident",false],
 ["provider_generated_tokens_per_second","10"],["after_resident",false]
]){
 assert.strictEqual(p.parseReport(JSON.stringify({...a,[k]:v})),null,k);
}
assert.strictEqual(p.parseReport(JSON.stringify({...a,content:"private"})),null);
const missing={...a};delete missing.provider_load_ms;
assert.strictEqual(p.parseReport(JSON.stringify(missing)),null);
assert.strictEqual(p.parseReport("x".repeat(8193)),null);
assert.strictEqual(p.parseReport(JSON.stringify({...a,provider_eval_count:0,provider_generated_tokens_per_second:10})),null);
"""
        run=subprocess.run(["node","-e",js,str(ROOT/"services/forest/ForestBenchmarkReportPolicy.js"),
                            json.dumps(warm),json.dumps(cold)],capture_output=True,text=True,check=False)
        self.assertEqual(run.returncode,0,run.stderr)


if __name__=="__main__":
    unittest.main()
