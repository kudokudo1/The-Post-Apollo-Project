"""Joined I1/I2 synthetic reference integration; no model or runtime action."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
HELPER=ROOT/"scripts/forest/ui_binding_example.py"
sys.path.insert(0,str(HELPER.parent))
from ui_binding_example import evaluate

CASES={
    "unbound":"FORM_UNBOUND",
    "missing":"MODEL_EVIDENCE_MISSING",
    "mismatch":"MODEL_EVIDENCE_MISMATCH",
    "not-installed":"MODEL_NOT_INSTALLED",
    "install-unknown":"INSTALL_STATUS_UNKNOWN",
    "capability-unknown":"CAPABILITY_EVIDENCE_UNKNOWN",
    "feature-unsupported":"REQUIRED_FEATURE_UNSUPPORTED",
    "context-insufficient":"CONTEXT_LIMIT_INSUFFICIENT",
    "match":"REFERENCE_BINDING_MATCH_AUTHORITY_HOLD",
}


class ForestBindingPreviewTests(unittest.TestCase):
    def test_actual_core_all_outcomes_and_form_continuity(self):
        for form,complexity,expected in (("auto","low","small"),("auto","high","big"),
                                         ("small","high","small"),("big","low","big")):
            for scenario,reason in CASES.items():
                with self.subTest(form=form,complexity=complexity,scenario=scenario):
                    args=[form,"deep",complexity,"absent","unknown",scenario]
                    d=evaluate(args)
                    self.assertEqual(d["inputs"],args)
                    self.assertEqual(d["routing"]["recommendedForm"],expected)
                    b=d["binding"]
                    self.assertEqual(b["recommendedForm"],expected)
                    self.assertEqual(b["reason"],reason)
                    self.assertIs(b["referenceBindingMatched"],scenario=="match")
                    self.assertIsNone(b["resolvedForm"])
                    self.assertIsNone(b["resolvedBinding"])
                    self.assertEqual(b["status"],"UNKNOWN_HOLD")
                    for flag in ("sourceAuthenticated","permissionGranted","resourceFitEstablished",
                                 "productionAuthority","modelExecutionPermitted"):
                        self.assertIs(b[flag],False)
                    self.assertEqual(b["safeActions"],[])
                    self.assertNotIn("sha256:",json.dumps(d))
                    self.assertNotIn("fixture:",json.dumps(d))

    def test_refuses_invalid_example(self):
        for args in (["auto","normal","low","absent","unknown","other"],
                     ["auto","normal","invalid","absent","unknown","match"],
                     ["auto","normal","low","absent","unknown","match","extra"]):
            r=subprocess.run([sys.executable,"-B",str(HELPER),*args],
                             capture_output=True,text=True,timeout=5)
            self.assertEqual(r.returncode,2)
            self.assertEqual(r.stdout,"")

    @unittest.skipUnless(shutil.which("node"),"Node unavailable")
    def test_actual_receipt_and_refusal_matrix(self):
        args=["auto","deep","high","absent","unknown","match"]
        run=subprocess.run([sys.executable,"-B",str(HELPER),*args],
                           capture_output=True,text=True,timeout=5,check=True)
        js=r"""
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const p=vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1],"utf8"),p);
const d=JSON.parse(process.argv[2]),args=d.inputs;
const r=p.parseBinding(JSON.stringify(d),args);
assert.strictEqual(r.form,"BIG");
assert.strictEqual(r.referenceMatched,true);
assert.strictEqual(r.bindingReason,"REFERENCE BINDING MATCH AUTHORITY HOLD");
for(const [k,v] of [["permissionGranted",true],["sourceAuthenticated",true],
 ["resourceFitEstablished",true],["productionAuthority",true],["modelExecutionPermitted",true],
 ["resolvedForm","big"],["resolvedBinding","fixture"],["safeActions",["run"]],
 ["recommendedForm","small"],["referenceBindingMatched",false],["reason","OTHER"]]){
 assert.strictEqual(p.parseBinding(JSON.stringify({...d,binding:{...d.binding,[k]:v}}),args),null);
}
assert.strictEqual(p.parseBinding(JSON.stringify(d),[...args.slice(0,5),"missing"]),null);
assert.strictEqual(p.parseBinding(JSON.stringify({...d,routing:{...d.routing,permissionGranted:true}}),args),null);
"""
        r=subprocess.run(["node","-e",js,str(ROOT/"services/forest/ForestAutoPolicyPreview.js"),run.stdout],
                         capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)

    def test_ui_scope(self):
        pane=(ROOT/"widgets/ForestAutoPolicyPreview.qml").read_text()
        self.assertIn("I2 // FICTIONAL BINDING EVIDENCE",pane)
        self.assertIn("LIVE BINDING // UNRESOLVED",pane)
        self.assertIn("AutoPreview.parseBinding(output,submitted)",pane)
        self.assertIn("submitted = [requestedForm,effort,complexity,failure,suitability,bindingScenario]",pane)
        self.assertIn("if (!discard && visible)",pane)
        self.assertEqual(pane.count("Process {"),1)
        self.assertIn("resolve_reference(route, registry",HELPER.read_text())


if __name__=="__main__":
    unittest.main()
